"""MusicProvider: personal-listening affinity from Last.fm + MusicBrainz + ReccoBeats."""

from collections import defaultdict
from typing import Any, ClassVar
import asyncio
import math

import niquests
import pydantic
import structlog

from app.core import loop
from app.core.errors import MusicLinkRequired, MusicListeningUnavailable
from app.core.math import clamp
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.merge import filter_element_types
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.trainer import types as trainer_types
from app.domains.vibemon.identity import Identity
from app.providers import catalog_schema as catalog
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider
from app.providers.helpers import Signal, pick_starter_moves

from . import const, schema, utils
from .lastfm import schema as lastfm_schema
from .lastfm.api import LastFmAPIClient
from .musicbrainz import schema as mb_schema
from .musicbrainz.api import MusicBrainzAPIClient
from .reccobeats import schema as rb_schema
from .reccobeats.api import ReccoBeatsAPIClient

_LOGGER = structlog.get_logger(__name__)


class MusicProvider(VibeProvider[schema.MusicPayload]):
    """
    A Vibemon picks up the tunes floating through the house when it hatched.

    One hatched on late-night jazz 45s reads differently from one shaped by
    garage-rock road tapes or Sunday folk on the kitchen radio - whatever was
    in rotation when it arrived.
    """

    implemented: ClassVar[bool] = False

    name = "music"
    display_label = "MUSIC"
    tagline = "Road tapes, 45s, and kitchen-radio rotation."

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "mainstream pop, genre-neutral tags, and bright valence"),
        (VibemonTypeT.FIRE, "high-energy secondary on rock, metal, electronic, and latin tags"),
        (VibemonTypeT.WATER, "fluid, ambient, downtempo genres and subdued valence"),
        (VibemonTypeT.GRASS, "folk, acoustic, and organic singer-songwriter tags"),
        (VibemonTypeT.ICE, "minimal techno, microhouse, and crystalline electronic tags"),
        (VibemonTypeT.FLYING, "dream pop, shoegaze, ethereal wave, and spacey tags"),
        (VibemonTypeT.FIGHTING, "hardcore, punk, combative genres, and aggressive hip-hop tags"),
        (VibemonTypeT.POISON, "noise, industrial, power electronics, and harsh electronic subgenres"),
        (VibemonTypeT.GROUND, "roots, blues, and earthy Americana tags"),
        (VibemonTypeT.BUG, "hyperpop, glitch, and buzzing electronic microgenres"),
        (VibemonTypeT.ROCK, "classic rock, alt-rock, and guitar-forward genres"),
        (VibemonTypeT.GHOST, "dark ambient, dungeon synth, nostalgic mood, and low valence"),
        (VibemonTypeT.DRAGON, "power metal, symphonic metal, progressive rock, and epic scores"),
        (VibemonTypeT.ELECTRIC, "synthpop, electro, and dance-floor genres"),
        (VibemonTypeT.DARK, "goth, darkwave, minor-key melancholy, and dark hip-hop tags"),
        (VibemonTypeT.STEEL, "metal, industrial rock, and hardened genres"),
        (VibemonTypeT.FAIRY, "dance pop, k-pop, sparkly pop, bright valence, and major keys"),
        (VibemonTypeT.PSYCHIC, "classical, jazz, contemplative genres, and minor-key depth"),
    ]

    requirements = (
        catalog.OAuth2LinkRequirement(
            id="lastfm.link",
            label="Link Last.fm",
            description="Connect listening history so birth can read recent top tracks.",
            service="lastfm",
            secret_kinds=(trainer_types.LASTFM_SESSION_KEY, trainer_types.LASTFM_USERNAME),
            authorize_path="/lastfm/authorize",
        ),
    )
    data_sources = (
        catalog.DataSourceInfo(name="Last.fm", description="Recent top-track listening history."),
        catalog.DataSourceInfo(name="MusicBrainz", description="Genre, mood, and instrument tags."),
        catalog.DataSourceInfo(name="ReccoBeats", description="Audio features when track IDs resolve."),
    )

    payload_type = schema.MusicPayload

    def __init__(self) -> None:
        self.lastfm = LastFmAPIClient()
        self.musicbrainz = MusicBrainzAPIClient()
        self.reccobeats = ReccoBeatsAPIClient()

    # ── INTERNAL HELPERS ──────────────────────────────────────────────────────────────

    async def rank_search(
        self,
        track: lastfm_schema.Track,
        *,
        candidates: int = 5,
        threshold: float = 0.55,
    ) -> schema.TrackInfo | None:
        """Search for matching `canidadtes`, rank-sorting them by closest match."""
        r = await self.musicbrainz.search_recording(
            recording=track.name,
            artist_name=track.artist.name,
            artist_mbid=track.artist.mbid,
            limit=candidates,
        )

        recordings = [mb_schema.Recording.model_validate(t) for t in (r.json().get("recordings") or [])]

        if not recordings:
            return None

        scored = [utils.candidate_ranking(r, track=track) for r in recordings]
        scored.sort(key=lambda c: c[1], reverse=True)

        if scored[0][1] < threshold:
            return None

        recording = scored[0][0]

        r = await self.musicbrainz.recording(recording.id)

        if r.ok:
            recording = mb_schema.Recording.model_validate(r.json())

        return schema.TrackInfo.combine(recording=recording, track=track)

    async def resolve_track_info(self, tracks: list[lastfm_schema.Track]) -> list[schema.TrackInfo]:
        """Augment Last.fm track info with the Muscbrainz database."""
        BATCH_SIZE = 100

        resolved: list[schema.TrackInfo] = []

        has_mbid, not_mbid = loop.partition(tracks, predicate=lambda t: bool(t.mbid))

        needs_search: list[lastfm_schema.Track] = list(not_mbid)

        # Phase A - lookup by MBID (one request per recording; cached per MBID)
        for chunk in loop.chunks(has_mbid, size=BATCH_SIZE):
            rs = await asyncio.gather(*(self.musicbrainz.recording(t.mbid) for t in chunk))  # pyrefly: ignore[bad-argument-type]

            for track, r in zip(chunk, rs, strict=True):
                if not r.ok:
                    needs_search.append(track)
                    continue

                recording = mb_schema.Recording.model_validate(r.json())

                if bool(recording.isrcs or recording.first_spotify_id):
                    resolved.append(schema.TrackInfo.combine(recording=recording, track=track))
                else:
                    needs_search.append(track)

        # Phase B - search only for misses (can't batch)
        if needs_search:
            search_results = await asyncio.gather(*(self.rank_search(t) for t in needs_search))
            resolved.extend(info for info in search_results if info is not None)

        return resolved

    async def ensure_full_track(self, track_infos: list[schema.TrackInfo]) -> list[schema.Track]:
        """Attach ReccoBeats audio features to resolved tracks when available."""
        if not track_infos:
            return []

        has_ids, not_ids = loop.partition(track_infos, predicate=lambda t: bool(t.isrc or t.spotify_id))

        for info in not_ids:
            _LOGGER.warning("music.ensure_full_track.missing_valid_audio_id", track=info)

        async def lookup_audio_features(ids: list[str]) -> dict[str, rb_schema.AudioFeatures]:
            BATCH_SIZE = 40

            resolved: dict[str, rb_schema.AudioFeatures] = {}

            for chunk in loop.chunks(ids, size=BATCH_SIZE):
                r = await self.reccobeats.audio_features(*chunk)

                if not r.ok:
                    _LOGGER.error("music.ensure_track_full.reccobeats_features_failed", status=r.status_code, ids=chunk)
                    continue

                if not (rows := r.json().get("content", [])):
                    _LOGGER.error("music.ensure_track_full.reccobeats_data_missing", data=r.json(), ids=chunk)
                    continue

                for row in rows:
                    features = rb_schema.AudioFeatures.model_validate(row)

                    if not (features.isrc or features.spotify_id):
                        _LOGGER.error("music.ensure_track_full.reccobeats_data_unmatchable", data=row)
                        continue

                    for key in (features.isrc, features.spotify_id):
                        if key:
                            resolved[key] = features

            return resolved

        lookup: dict[str, rb_schema.AudioFeatures] = {}

        # CHECK BY isrc.
        lookup.update(await lookup_audio_features([t.isrc for t in has_ids if t.isrc is not None]))

        # CHECK BY spotify_id FOR THOSE track_info THAT FAILED.
        lookup.update(
            await lookup_audio_features(
                [
                    t.spotify_id
                    for t in has_ids
                    if t.isrc not in lookup
                    if t.spotify_id is not None and t.spotify_id not in lookup
                ]
            )
        )

        ensured: list[schema.Track] = []

        for track_info in has_ids:
            features = lookup.get(track_info.isrc) if track_info.isrc else None
            if features is None and track_info.spotify_id:
                features = lookup.get(track_info.spotify_id)

            if features is None:
                _LOGGER.warning("music.ensure_track_full.no_valid_ids_on_reccobeats", track=track_info)
                continue

            try:
                ensured.append(
                    schema.Track.model_validate(
                        {
                            **track_info.model_dump(),
                            **features.model_dump(
                                include={
                                    "acousticness",
                                    "danceability",
                                    "energy",
                                    "instrumentalness",
                                    "liveness",
                                    "loudness",
                                    "speechiness",
                                    "tempo",
                                    "valence",
                                    "mode",
                                }
                            ),
                        }
                    )
                )
            except pydantic.ValidationError:
                _LOGGER.exception("music.ensure_track_full.validation", track=track_info, features=features)

        return ensured

    # ── CORE PROTOCOL MEMBERS ─────────────────────────────────────────────────────────

    async def fetch(self, seed: BirthSeed, *, secrets: TrainerSecrets | None = None) -> schema.MusicPayload:
        if secrets is None:
            raise MusicLinkRequired("Trainer has no linked Last.fm account.")

        lastfm = {
            "session_key": await secrets.get(seed.trainer_id, trainer_types.LASTFM_SESSION_KEY),
            "username": await secrets.get(seed.trainer_id, trainer_types.LASTFM_USERNAME),
        }

        if lastfm["username"] is None:
            raise MusicLinkRequired("Trainer has no linked Last.fm account.")

        tasks: dict[str, asyncio.Task[niquests.Response]] = {}

        async with asyncio.TaskGroup() as g:
            tasks["7d"] = g.create_task(self.lastfm.user_top_tracks(lastfm["username"], period="7day", limit=200))
            tasks["1m"] = g.create_task(self.lastfm.user_top_tracks(lastfm["username"], period="1month", limit=200))

        r = tasks.pop("7d").result()
        top_7d = lastfm_schema.TracksPage.model_validate(r.json().get("toptracks"))

        r = tasks.pop("1m").result()
        top_1m = lastfm_schema.TracksPage.model_validate(r.json().get("toptracks"))

        if not top_1m.track:
            raise MusicListeningUnavailable("Linked Last.fm account has no usable listening history.")

        # ENSURE TRACKS HAVE VALID MBIDs and INFO
        parsed = await self.resolve_track_info(top_1m.track)

        # FETCH AUDIO FEATURES (and filter/log ones that fail)
        tracks = await self.ensure_full_track(parsed)

        # PAYLOAD
        meta: dict[str, Any] = {}

        if (coverage := (round(len(tracks) / len(parsed), 4))) < 0.5:
            meta = {
                "notes": {
                    "level": providers_schema.ProviderNoteLevelT.WARNING,
                    "code": "music.thin_stat_coverage",
                    "message": f"Music stats may be thin - only {coverage * 100:.2f}% tracks had audio analysis.",
                }
            }

        payload = schema.MusicPayload.model_validate(
            {
                "tracks": tuple(tracks),
                "last7d": sum(track.playcount for track in top_7d.track),
                "last1m": sum(track.playcount for track in top_1m.track),
                "meta": meta,
            }
        )

        _LOGGER.info(
            "music.fetch.summary",
            provider=self.name,
            top_7d=len(top_7d.track),
            top_1m=len(top_1m.track),
            parsed=len(parsed),
            tracks=len(tracks),
            last7d=payload.last7d,
            last1m=payload.last1m,
        )

        return payload

    async def synthesize(self, seed: BirthSeed, payload: schema.MusicPayload) -> Affinity:
        """Translate captured music payload to Affinity components."""
        rng = seed.rng(f"provider.{self.name}.moves")

        # RAW DATA
        signals = self.derive_signals(payload)

        # INTENSITY SKEW
        intensity = self.calculate_intensity(last7d=payload.last7d, last1m=payload.last1m)

        # RANKED ELEMENTS BASED ON THE DATA
        rankings, synth_notes = self.determine_element_scores(payload.tracks)
        elements = filter_element_types(rankings)

        # BALANCE SIGNAL DATA FOR BASE STAT TRANSLATION
        normalized = self.balance_for_bst(signals)
        base_stats = normalized.scaled(elements=elements)

        # LOAD MOVES
        all_moves = self.selectable_moves()

        return Affinity(
            identity=Identity(name="__", elements=elements, base=base_stats),
            visual_notes=self.visual_notes(payload, signals=signals, intensity=intensity),
            intensity=intensity,
            provider_id=self.name,
            element_rankings=rankings,
            moves=pick_starter_moves(moves=all_moves, rankings=rankings, elements=elements, k=10, rng=rng),
            provider_notes=(*(note.as_warning() for note in payload.meta.notes), *synth_notes),
        )

    # ── PROTOCOL HELPERS ──────────────────────────────────────────────────────────────

    def derive_signals(self, payload: schema.MusicPayload) -> dict[str, Signal]:
        """Build play-weighted ReccoBeats signals from tracks that have audio features."""
        AUDIO_DEFAULTS: dict[str, float] = {
            "tempo": 120.0,
            "duration": 220.0,
            "loudness": -7.0,
            "energy": 0.55,
            "acousticness": 0.12,
            "instrumentalness": 0.02,
            "valence": 0.45,
            "danceability": 0.55,
            "liveness": 0.12,
            "speechiness": 0.06,
        }

        totals: dict[str, float] = defaultdict(float)
        play_weight: dict[str, float] = defaultdict(float)

        for track in payload.tracks:
            track_values = {
                "tempo": track.tempo,
                "duration": track.duration or 0,
                "loudness": track.loudness,
                "energy": track.energy,
                "acousticness": track.acousticness,
                "instrumentalness": track.instrumentalness,
                "valence": track.valence,
                "danceability": track.danceability,
                "liveness": track.liveness,
                "speechiness": track.speechiness,
            }

            for attr, value in track_values.items():
                if attr == "duration" and value == 0:
                    continue

                totals[attr] += float(value) * track.plays
                play_weight[attr] += track.plays

        raws = {
            attr: totals[attr] / play_weight[attr] if play_weight[attr] else AUDIO_DEFAULTS[attr]
            for attr in AUDIO_DEFAULTS
        }

        # fmt: off
        # ruff: noqa: E501
        return {
            sig.name: sig
            for sig in (
                Signal(name="tempo",            attr="tempo",            raw=raws["tempo"],            min=  60.00, med= 120.00, max= 180.00),
                Signal(name="duration",         attr="duration",         raw=raws["duration"],         min= 120.00, med= 220.00, max= 420.00, axis="log10"),
                Signal(name="loudness",         attr="loudness",         raw=raws["loudness"],         min= -18.00, med=  -7.00, max=  -3.00),
                Signal(name="energy",           attr="energy",           raw=raws["energy"],           min=   0.00, med=   0.55, max=   1.00),
                Signal(name="acousticness",     attr="acousticness",     raw=raws["acousticness"],     min=   0.01, med=   0.12, max=   0.95, axis="log10"),
                Signal(name="instrumentalness", attr="instrumentalness", raw=raws["instrumentalness"], min=  0.001, med=   0.02, max=   0.95, axis="log10"),
                Signal(name="valence",          attr="valence",          raw=raws["valence"],          min=   0.00, med=   0.45, max=   1.00),
                Signal(name="danceability",     attr="danceability",     raw=raws["danceability"],     min=   0.00, med=   0.55, max=   1.00),
                Signal(name="liveness",         attr="liveness",         raw=raws["liveness"],         min=   0.01, med=   0.12, max=   0.85, axis="log10"),
                Signal(name="speechiness",      attr="speechiness",      raw=raws["speechiness"],      min=   0.01, med=   0.06, max=   0.66, axis="log10"),
            )
        }
        # fmt: on

    def calculate_intensity(self, *, last7d: int, last1m: int) -> float:
        """
        Map recent (7-day) vs. baseline play rates to [0, 1] via log-ratio sigmoid.

        `last1m` is the cumulative 30-day count (which includes the last 7 days),
        so we subtract the week out to get a disjoint 23-day baseline. The score
        compares the recent daily pace against that baseline:
             0.5 -> recent pace matches baseline (steady)
            >0.5 -> trending up
            <0.5 -> cooling off
        """
        prior_plays = last1m - last7d

        if prior_plays <= 0:
            # No baseline to compare against: hot if there's any recent activity,
            # neutral if there's nothing at all.
            return 1.0 if last7d else 0.5

        ratio = (last7d / 7) / (prior_plays / 23)
        z = math.log(ratio) if ratio > 0 else -10.0
        return round(1.0 / (1.0 + math.exp(-z)), ndigits=4)

    def determine_element_scores(
        self,
        tracks: tuple[schema.Track, ...],
    ) -> tuple[dict[VibemonTypeT, float], tuple[generation_types.ProviderWarning, ...]]:
        """Score Vibemon types from play-weighted genre/tag rules and optional audio mood."""
        genre_rules = utils.load_rules("classify_genre.json")
        mood_rules = utils.load_rules("classify_mood.json")
        instrument_rules = utils.load_rules("classify_instrument.json")

        scores: dict[VibemonTypeT, float] = defaultdict(float)
        synth_notes: list[generation_types.ProviderWarning] = []
        total_plays = 0

        for track in tracks:
            total_plays += track.plays

            labels = {
                utils.normalize_classify_label(name)
                for name in (*track.genres, *track.tags)
                if utils.normalize_classify_label(name)
            }

            for label in labels:
                hits = 0

                if genre_matches := [w for _, w, pattern in genre_rules if pattern.search(label)]:
                    hits |= 1

                    for type_weights in genre_matches:
                        for vtype, weight in type_weights:
                            scores[vtype] += (weight / len(genre_matches)) * track.plays

                for _, type_weights, pattern in mood_rules:
                    if pattern.search(label):
                        hits |= 2

                        for vtype, weight in type_weights:
                            scores[vtype] += weight * track.plays * 0.5

                for _, type_weights, pattern in instrument_rules:
                    if pattern.search(label):
                        hits |= 4

                        for vtype, weight in type_weights:
                            scores[vtype] += weight * track.plays * 0.3

                if not hits:
                    synth_notes.append(
                        generation_types.ProviderWarning(
                            level=generation_types.ProviderWarningLevel.INFO,
                            code="music.unclassified_tags",
                            message=f"The label '{label}' does not match any genre, mood, or instrument ({track.plays} plays)",
                        )
                    )

            brightness = Signal(
                name="valence",
                attr="valence",
                raw=track.valence,
                min=0.00,
                med=0.45,
                max=1.00,
            ).center

            if brightness > 0.5:
                boost = (brightness - 0.5) * 2 * track.plays * 0.25

                scores[VibemonTypeT.FAIRY] += boost * 0.40
                scores[VibemonTypeT.NORMAL] += boost * 0.35
                scores[VibemonTypeT.ELECTRIC] += boost * 0.15
            else:
                dim = (0.5 - brightness) * 2 * track.plays * 0.25
                scores[VibemonTypeT.GHOST] += dim * 0.30
                scores[VibemonTypeT.DARK] += dim * 0.25
                scores[VibemonTypeT.WATER] += dim * 0.25
                scores[VibemonTypeT.PSYCHIC] += dim * 0.10

            if track.is_major_key:
                type_weights = {VibemonTypeT.FAIRY: 0.25, VibemonTypeT.ELECTRIC: 0.20, VibemonTypeT.NORMAL: 0.15}
            else:
                type_weights = {VibemonTypeT.DARK: 0.25, VibemonTypeT.GHOST: 0.20, VibemonTypeT.PSYCHIC: 0.15}

            for vtype, weight in type_weights.items():
                scores[vtype] += weight * track.plays * 0.25

        if total_plays > 0:
            for t in list(scores):
                scores[t] /= total_plays

        if not any(v > 0 for v in scores.values()):
            return {VibemonTypeT.NORMAL: 1.0}, tuple(synth_notes)

        return dict(scores), tuple(synth_notes)

    def balance_for_bst(self, signals: dict[str, Signal]) -> providers_schema.BaseStatCenters:
        """Route play-weighted audio signals to base-stat centers via composite mixes."""
        groove = Signal.mix(signals["danceability"] * 0.7, signals["valence"] * 0.3, mode="center")
        heaviness = clamp(1.0 - signals["acousticness"].center, minimum=0.0, maximum=1.0)
        intensity = Signal.mix(signals["energy"] * 0.7, signals["loudness"] * 0.3, mode="center")
        production = clamp(0.6 * heaviness + 0.4 * signals["instrumentalness"].center, minimum=0.0, maximum=1.0)

        return providers_schema.BaseStatCenters(
            hp=signals["duration"].center,
            attack=intensity,
            defense=production,
            sp_attack=signals["valence"].center,
            sp_defense=groove,
            speed=signals["tempo"].center,
        )

    def visual_notes(
        self,
        payload: schema.MusicPayload,
        *,
        signals: dict[str, Signal],
        intensity: float,
    ) -> str:
        """Map play-weighted listening signals to a short creature-visual line (pure, replay-safe)."""
        parts: list[str] = []

        if rule_phrase := self._top_rule_visual(payload):
            parts.append(rule_phrase)

        for phrase in self._signal_visuals(signals, intensity=intensity):
            if len(parts) >= 3:
                break
            if phrase not in parts:
                parts.append(phrase)

        return "; ".join(parts) if parts else const.DEFAULT_VISUAL_NOTES

    def _top_rule_visual(self, payload: schema.MusicPayload) -> str | None:
        """Return the visual cue for the highest play-weighted classify rule match."""
        genre_rules = utils.load_rules("classify_genre.json")
        mood_rules = utils.load_rules("classify_mood.json")
        instrument_rules = utils.load_rules("classify_instrument.json")
        weights: dict[tuple[const.RuleCategoryT, str], float] = defaultdict(float)

        for track in payload.tracks:
            labels = {label for name in (*track.genres, *track.tags) if (label := utils.normalize_classify_label(name))}
            matched: set[tuple[const.RuleCategoryT, str]] = set()

            for label in labels:
                for name, _, pattern in genre_rules:
                    if pattern.search(label):
                        matched.add(("genre", name))

                for name, _, pattern in mood_rules:
                    if pattern.search(label):
                        matched.add(("mood", name))

                for name, _, pattern in instrument_rules:
                    if pattern.search(label):
                        matched.add(("instrument", name))

            for key in matched:
                weights[key] += track.plays

        candidates = [(weight, const.RULE_VISUALS[key]) for key, weight in weights.items() if key in const.RULE_VISUALS]
        if not candidates:
            return None

        return max(candidates, key=lambda item: (item[0], item[1]))[1]

    def _signal_visuals(
        self,
        signals: dict[str, Signal],
        *,
        intensity: float,
    ) -> tuple[str, ...]:
        """Rank signal-derived visual phrases by deviation from neutral (0.5)."""
        candidates: list[tuple[float, str]] = []

        def add(center: float, *, high: float, low: float, high_phrase: str, low_phrase: str) -> None:
            if center >= high:
                candidates.append((center - 0.5, high_phrase))
            elif center <= low:
                candidates.append((0.5 - center, low_phrase))

        add(
            signals["valence"].center,
            high=0.58,
            low=0.42,
            high_phrase="sun-warmed markings and a bright open palette",
            low_phrase="muted dusk palette and downcast soft edges",
        )
        add(
            signals["energy"].center,
            high=0.65,
            low=0.40,
            high_phrase="crackle-edged markings and hard high-contrast accents",
            low_phrase="soft low-contrast tones and sleepy muted washes",
        )
        add(
            signals["acousticness"].center,
            high=0.62,
            low=0.22,
            high_phrase="warm organic grain and unpolished matte texture",
            low_phrase="synthetic sheen and studio-polished gloss",
        )
        add(
            signals["danceability"].center,
            high=0.65,
            low=0.35,
            high_phrase="rhythmic stripe markings in syncopated bands",
            low_phrase="still unhurried plain tones",
        )
        add(
            signals["instrumentalness"].center,
            high=0.55,
            low=0.15,
            high_phrase="wordless quiet patterning and instrument-etched line markings",
            low_phrase="chatty expressive speckling and bright accent spots",
        )
        add(
            signals["liveness"].center,
            high=0.58,
            low=0.25,
            high_phrase="raw frayed edges and unfinished live-wire texture",
            low_phrase="clean studio-smooth finish",
        )
        add(
            signals["tempo"].center,
            high=0.65,
            low=0.35,
            high_phrase="quick staccato streak markings and crisp bright edging",
            low_phrase="slow languid gradient washes",
        )

        if intensity >= 0.65:
            candidates.append((intensity - 0.5, "freshly-charged vivid saturation"))
        elif intensity <= 0.35:
            candidates.append((0.5 - intensity, "settled unhurried stillness"))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return tuple(phrase for _, phrase in candidates)
