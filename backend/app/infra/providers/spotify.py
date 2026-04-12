from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime, timezone
from typing import Any, Optional

import niquests
import structlog

from app.domain.context import GenerationContext, SourceData
from app.infra.providers.protocol import VibemonProvider

log = structlog.get_logger(__name__)

_SPOTIFY_BASE = "https://api.spotify.com/v1"
_MB_BASE = "https://musicbrainz.org/ws/2"
_LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"

_MB_SEMAPHORE: asyncio.Semaphore | None = None

_AGGRESSIVE_GENRES = frozenset({
    "metal", "punk", "hardcore", "death metal", "black metal",
    "thrash metal", "heavy metal", "grindcore", "metalcore",
})
_CALM_GENRES = frozenset({
    "classical", "ambient", "folk", "acoustic", "new age",
    "meditation", "chillout", "downtempo", "lo-fi",
})
_ENERGETIC_TAGS = frozenset({
    "energetic", "upbeat", "euphoric", "happy", "dance",
    "party", "power", "hype",
})
_DARK_TAGS = frozenset({
    "dark", "melancholy", "sad", "depressive", "doom",
    "gothic", "gloomy", "bleak",
})
_CHILL_TAGS = frozenset({
    "chill", "acoustic", "relaxing", "calm", "mellow",
    "soft", "peaceful", "serene",
})
_AGGRESSIVE_TAGS = frozenset({
    "aggressive", "intense", "brutal", "angry", "rage",
    "violent", "fierce",
})


def _get_mb_semaphore() -> asyncio.Semaphore:
    global _MB_SEMAPHORE
    if _MB_SEMAPHORE is None:
        _MB_SEMAPHORE = asyncio.Semaphore(1)
    return _MB_SEMAPHORE


def _normalize_bpm(bpm: float) -> float:
    return max(0.0, min(1.0, (bpm - 60.0) / (180.0 - 60.0)))


def _normalize_track_count(count: int) -> float:
    return max(0.0, min(1.0, (count - 1) / (50 - 1)))


def _normalize_genre_count(count: int) -> float:
    return max(0.0, min(1.0, (count - 1) / (10 - 1)))


def derive_hue(energy: float, valence: float) -> float:
    base_hue = 220.0 + valence * 140.0
    energy_shift = (energy - 0.5) * -80.0
    return (base_hue + energy_shift) % 360.0


def _classify_tags(tags: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {
        "energetic": 0, "dark": 0, "chill": 0, "aggressive": 0, "calm": 0,
    }
    for t in tags:
        tl = t.lower().strip()
        if tl in _ENERGETIC_TAGS:
            counts["energetic"] += 1
        if tl in _DARK_TAGS:
            counts["dark"] += 1
        if tl in _CHILL_TAGS:
            counts["chill"] += 1
        if tl in _AGGRESSIVE_TAGS:
            counts["aggressive"] += 1
        if tl in _CALM_GENRES:
            counts["calm"] += 1
    return counts


async def _fetch_spotify_recent(token: str) -> list[dict[str, Any]]:
    url = f"{_SPOTIFY_BASE}/me/player/recently-played"
    async with niquests.AsyncSession() as session:
        r = await session.get(
            url,
            params={"limit": 50},
            headers={"Authorization": f"Bearer {token}"},
            timeout=12,
        )
    r.raise_for_status()
    data = r.json()
    return data.get("items", [])


def _extract_tracks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for item in items:
        track = item.get("track")
        if not track:
            continue
        artists = track.get("artists", [])
        artist_name = artists[0]["name"] if artists else "Unknown"
        tracks.append({
            "name": track.get("name", ""),
            "artist": artist_name,
            "album": (track.get("album") or {}).get("name", ""),
            "played_at": item.get("played_at", ""),
        })
    return tracks


def _count_recent_7d(tracks: list[dict[str, Any]], now: datetime) -> int:
    seven_days_ago = now.timestamp() - 7 * 86400
    count = 0
    for t in tracks:
        played = t.get("played_at", "")
        if not played:
            continue
        try:
            pa = played.replace("Z", "+00:00")
            dt = datetime.fromisoformat(pa)
            if dt.timestamp() >= seven_days_ago:
                count += 1
        except (ValueError, TypeError):
            count += 1
    return count


def _average_listening_hour(tracks: list[dict[str, Any]]) -> float:
    hours: list[float] = []
    for t in tracks:
        played = t.get("played_at", "")
        if not played:
            continue
        try:
            pa = played.replace("Z", "+00:00")
            dt = datetime.fromisoformat(pa)
            hours.append(float(dt.hour) + dt.minute / 60.0)
        except (ValueError, TypeError):
            pass
    if not hours:
        return 12.0
    return sum(hours) / len(hours)


def _deduplicate_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for t in tracks:
        key = (t["name"].lower(), t["artist"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


async def _query_musicbrainz(track: str, artist: str) -> dict[str, Any]:
    sem = _get_mb_semaphore()
    async with sem:
        q = f'recording:"{track}" AND artist:"{artist}"'
        url = f"{_MB_BASE}/recording"
        try:
            async with niquests.AsyncSession() as session:
                r = await session.get(
                    url,
                    params={"query": q, "fmt": "json", "limit": 1},
                    headers={"User-Agent": "Vibemon/0.1 (vibemon-game)"},
                    timeout=10,
                )
            r.raise_for_status()
            data = r.json()
            recordings = data.get("recordings", [])
            if not recordings:
                return {}
            rec = recordings[0]
            result: dict[str, Any] = {}
            tags = rec.get("tags", [])
            if tags:
                result["tags"] = [t.get("name", "") for t in tags if t.get("name")]
            releases = rec.get("releases", [])
            for rel in releases:
                for media in rel.get("media", []):
                    for track_item in media.get("track", []):
                        length = track_item.get("length")
                        if length and isinstance(length, (int, float)) and length > 0:
                            bpm_est = 120
                            result.setdefault("bpm", bpm_est)
            return result
        except Exception as err:
            log.debug("musicbrainz_query_failed", track=track, artist=artist, error=repr(err))
            return {}
        finally:
            await asyncio.sleep(1.0)


async def _query_lastfm(track: str, artist: str) -> dict[str, Any]:
    api_key = os.environ.get("LASTFM_API_KEY", "")
    if not api_key:
        return {}
    try:
        async with niquests.AsyncSession() as session:
            r = await session.get(
                _LASTFM_BASE,
                params={
                    "method": "track.getInfo",
                    "api_key": api_key,
                    "artist": artist,
                    "track": track,
                    "format": "json",
                },
                timeout=10,
            )
        r.raise_for_status()
        data = r.json()
        track_info = data.get("track", {})
        result: dict[str, Any] = {}
        top_tags = track_info.get("toptags", {}).get("tag", [])
        if top_tags:
            result["tags"] = [t.get("name", "") for t in top_tags if t.get("name")]
        duration = track_info.get("duration")
        if duration and str(duration).isdigit() and int(duration) > 0:
            pass
        return result
    except Exception as err:
        log.debug("lastfm_query_failed", track=track, artist=artist, error=repr(err))
        return {}


async def _enrich_tracks(
    unique_tracks: list[dict[str, Any]],
) -> tuple[list[float], list[str], list[str]]:
    bpms: list[float] = []
    all_tags: list[str] = []
    all_genres: list[str] = []

    cache: dict[tuple[str, str], dict[str, Any]] = {}

    batch_limit = min(len(unique_tracks), 10)

    for t in unique_tracks[:batch_limit]:
        track_name = t["name"]
        artist_name = t["artist"]
        key = (track_name.lower(), artist_name.lower())

        if key in cache:
            mb_data = cache[key]
        else:
            mb_data = await _query_musicbrainz(track_name, artist_name)
            cache[key] = mb_data

        tags = mb_data.get("tags", [])
        bpm = mb_data.get("bpm")

        if not tags:
            lfm_data = await _query_lastfm(track_name, artist_name)
            tags = lfm_data.get("tags", [])

        if bpm is not None:
            bpms.append(float(bpm))

        for tag in tags:
            tl = tag.lower().strip()
            all_tags.append(tl)
            if tl in _AGGRESSIVE_GENRES or tl in _CALM_GENRES:
                all_genres.append(tl)
            elif any(
                g in tl
                for g in ("rock", "pop", "jazz", "blues", "hip hop", "rap", "r&b",
                          "electronic", "techno", "house", "country", "reggae",
                          "soul", "funk", "disco", "ska", "latin")
            ):
                all_genres.append(tl)

    return bpms, all_tags, all_genres


class SpotifyProvider(VibemonProvider):
    @property
    def source_id(self) -> str:
        return "spotify"

    async def fetch(self, context: GenerationContext) -> SourceData:
        token = context.auth_tokens.get("spotify", "")
        if not token:
            raise ValueError("No Spotify token provided")

        try:
            items = await _fetch_spotify_recent(token)
        except Exception as err:
            log.warning("spotify_fetch_failed", error=repr(err))
            raise

        tracks = _extract_tracks(items)
        if not tracks:
            log.info("spotify_no_tracks")
            return SourceData(
                flavour_text="No recent tracks found",
                raw={"spotify": True, "track_count": 0},
            )

        now = context.timestamp or datetime.now(timezone.utc)
        track_count_7d = _count_recent_7d(tracks, now)
        avg_hour = _average_listening_hour(tracks)
        unique_tracks = _deduplicate_tracks(tracks)
        unique_artist_count = len({t["artist"].lower() for t in tracks})

        bpms, all_tags, all_genres = await _enrich_tracks(unique_tracks)

        avg_bpm = sum(bpms) / len(bpms) if bpms else 120.0
        speed_factor = _normalize_bpm(avg_bpm)

        hp_factor = _normalize_track_count(track_count_7d)

        unique_genre_set = set(all_genres)
        sp_attack_factor = _normalize_genre_count(len(unique_genre_set))

        tag_classes = _classify_tags(all_tags)

        attack_factor: Optional[float] = None
        aggressive_genre_hits = sum(1 for g in all_genres if g in _AGGRESSIVE_GENRES)
        if aggressive_genre_hits > 0:
            attack_factor = min(1.0, 0.4 + aggressive_genre_hits * 0.15)

        sp_defense_factor: Optional[float] = None
        calm_genre_hits = sum(1 for g in all_genres if g in _CALM_GENRES)
        if calm_genre_hits > 0:
            sp_defense_factor = min(1.0, 0.4 + calm_genre_hits * 0.15)

        defense_factor: Optional[float] = None
        if avg_bpm < 80:
            defense_factor = min(1.0, 0.6 + (80 - avg_bpm) / 80)

        element_votes: list[tuple[str, float]] = []
        if tag_classes["dark"] > 0:
            element_votes.append(("Dark", 0.6))
        if tag_classes["energetic"] > 0:
            element_votes.append(("Electric", 0.7))
        if tag_classes["chill"] > 0:
            element_votes.append(("Water", 0.5))
        if tag_classes["aggressive"] > 0:
            element_votes.append(("Fire", 0.6))

        if 22 <= avg_hour or avg_hour < 4:
            element_votes.append(("Dark", 0.4))

        total_mood = max(1, tag_classes["energetic"] + tag_classes["aggressive"])
        total_neg = max(1, tag_classes["dark"] + tag_classes["chill"])
        energy = min(1.0, (speed_factor + total_mood / (total_mood + total_neg)) / 2.0)
        positive_tags = tag_classes["energetic"]
        negative_tags = tag_classes["dark"] + tag_classes["chill"]
        valence = positive_tags / max(1, positive_tags + negative_tags)
        hue_primary = derive_hue(energy, valence)

        top_track_names = [t["name"] for t in tracks[:5]]
        flavour = f"Recent tracks: {', '.join(top_track_names[:3])}"

        return SourceData(
            hp_factor=hp_factor,
            attack_factor=attack_factor,
            defense_factor=defense_factor,
            sp_attack_factor=sp_attack_factor,
            sp_defense_factor=sp_defense_factor,
            speed_factor=speed_factor,
            element_votes=element_votes,
            hue_primary=hue_primary,
            luminosity=0.55,
            flavour_text=flavour,
            raw={
                "spotify": True,
                "track_count": len(tracks),
                "track_count_7d": track_count_7d,
                "unique_artists": unique_artist_count,
                "avg_bpm": round(avg_bpm, 1),
                "avg_listening_hour": round(avg_hour, 1),
                "genre_count": len(unique_genre_set),
                "enrichment_tags": all_tags[:20],
            },
        )
