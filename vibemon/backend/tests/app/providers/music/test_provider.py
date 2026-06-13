"""Unit and integration tests for the music provider."""

from typing import Any
import collections
import datetime as dt
import json
import pathlib

import pytest

from app.core.errors import MusicListeningUnavailable
from app.core.math import clamp
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move import universal
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import BaseStats, Identity
from app.providers import schema as providers_schema
from app.providers.helpers import Signal
from app.providers.music import schema as music_schema
from app.providers.music.lastfm import schema as lastfm_schema
from app.providers.music.musicbrainz import schema as mb_schema
from app.providers.music.provider import MusicProvider
from tests.app.providers.music.conftest import FakeTrainerSecrets
from tests.conftest import TEST_TRAINER_ID

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

THIN_COVERAGE_THRESHOLD = 0.5
THIN_STAT_COVERAGE_NOTE_CODE = "music.thin_stat_coverage"
THIN_STAT_COVERAGE_NOTE_MESSAGE = "Music stats may be thin"
UNCLASSIFIED_TAGS_NOTE_CODE = "music.unclassified_tags"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _load_music_payload(name: str) -> music_schema.MusicPayload:
    return MusicProvider.parse_payload(_load_fixture(name))


def _sample_track(**overrides: object) -> music_schema.Track:
    track: dict[str, object] = {
        "mbid": "11111111-1111-1111-1111-111111111111",
        "isrc": "USRC17607839",
        "spotify_id": "spotify-track-1",
        "name": "Example",
        "artist": "Artist",
        "genres": [],
        "tags": [],
        "duration": 220.0,
        "plays": 1,
        "acousticness": 0.12,
        "danceability": 0.55,
        "energy": 0.55,
        "instrumentalness": 0.02,
        "liveness": 0.12,
        "loudness": -9.0,
        "mode": 1,
        "speechiness": 0.06,
        "tempo": 120.0,
        "valence": 0.45,
    }
    track.update(overrides)
    return music_schema.Track.model_validate(track)


def _music_payload(*tracks: music_schema.Track, **overrides: object) -> music_schema.MusicPayload:
    track_tuple = tracks or (_sample_track(),)
    return music_schema.MusicPayload(
        tracks=track_tuple,
        last7d=int(str(overrides.get("last7d", 0))),
        last1m=int(str(overrides.get("last1m", 0))),
        meta=overrides.get("meta", providers_schema.ProviderPayloadMeta()),
    )


def test_music_move_catalog_has_fifteen_moves_per_exposed_element(music_provider: MusicProvider) -> None:
    provider = music_provider
    exposed_types = set(provider.get_exposed_elements())
    move_counts = collections.Counter(move.type for move in provider.moves())
    assert move_counts == {element: 15 for element in exposed_types}


def test_music_selectable_moves_include_shared_universal_moves_once(music_provider: MusicProvider) -> None:
    provider = music_provider
    universal_ids = {move.id for move in universal.moves()}
    selectable_ids = [move.id for move in provider.selectable_moves(level=99)]
    assert universal_ids <= set(selectable_ids)
    assert len(selectable_ids) == len(provider.moves()) + len(universal.moves())


def test_derive_signals_uses_play_weighted_means() -> None:
    payload = _music_payload(
        _sample_track(tempo=100.0, plays=1),
        _sample_track(tempo=140.0, plays=3, mbid="22222222-2222-2222-2222-222222222222"),
    )

    signals = MusicProvider().derive_signals(payload)

    assert signals["tempo"].raw == pytest.approx(130.0)
    assert signals["duration"].axis == "log10"
    assert signals["acousticness"].axis == "log10"
    assert signals["loudness"].axis == "linear"


def test_derive_signals_falls_back_to_defaults_without_audio_fields() -> None:
    signals = MusicProvider().derive_signals(_music_payload())

    assert signals["tempo"].raw == 120.0
    assert signals["valence"].raw == 0.45
    assert signals["valence"].center == pytest.approx(0.5)


def test_visual_notes_empty_payload() -> None:
    provider = MusicProvider()
    payload = music_schema.MusicPayload(
        tracks=(),
        last7d=0,
        last1m=0,
    )
    signals = provider.derive_signals(payload)
    assert provider.visual_notes(payload, signals=signals, intensity=0.5) == "quiet neutral tones, plain and unmarked"


def test_visual_notes_play_weighted_labels_and_hot_pace() -> None:
    provider = MusicProvider()
    payload = _music_payload(
        _sample_track(plays=100, genres=["shoegaze"]),
        _sample_track(plays=40, genres=["dream pop"], mbid="22222222-2222-2222-2222-222222222222"),
        _sample_track(plays=25, genres=["indie rock"], mbid="33333333-3333-3333-3333-333333333333"),
        _sample_track(plays=10, genres=["metal"], mbid="44444444-4444-4444-4444-444444444444"),
    )
    signals = provider.derive_signals(payload)
    notes = provider.visual_notes(payload, signals=signals, intensity=0.72)

    assert "hazy soft-focus edges" in notes
    assert "shoegaze" not in notes
    assert "dream pop" not in notes
    assert "indie rock" not in notes
    assert "metal" not in notes
    assert "freshly-charged vivid saturation" in notes


def test_visual_notes_melancholic_low_energy() -> None:
    provider = MusicProvider()
    payload = _music_payload(_sample_track(valence=0.2, energy=0.25, plays=5))
    signals = provider.derive_signals(payload)
    notes = provider.visual_notes(payload, signals=signals, intensity=0.5)

    assert "muted dusk palette" in notes
    assert "soft low-contrast tones" in notes


def test_balance_for_bst_maps_music_signals() -> None:
    provider = MusicProvider()
    signals = provider.derive_signals(_music_payload(_sample_track()))
    centers = provider.balance_for_bst(signals)

    heaviness = clamp(1.0 - signals["acousticness"].center, minimum=0.0, maximum=1.0)
    intensity = Signal.mix(signals["energy"] * 0.7, signals["loudness"] * 0.3, mode="center")
    groove = Signal.mix(signals["danceability"] * 0.7, signals["valence"] * 0.3, mode="center")

    assert centers.hp == signals["duration"].center
    assert centers.attack == intensity
    expected_defense = clamp(
        0.6 * heaviness + 0.4 * signals["instrumentalness"].center,
        minimum=0.0,
        maximum=1.0,
    )
    assert centers.defense == expected_defense
    assert centers.sp_attack == signals["valence"].center
    assert centers.sp_defense == groove
    assert centers.speed == signals["tempo"].center


def test_derive_signals_skips_tracks_without_reccobeats() -> None:
    payload = _music_payload(_sample_track(energy=0.9, loudness=-5.0, plays=1))

    signals = MusicProvider().derive_signals(payload)

    assert signals["energy"].raw == pytest.approx(0.9)
    assert signals["loudness"].raw == pytest.approx(-5.0)


def test_payload_tracks_keeps_tag_only_tracks() -> None:
    info = music_schema.TrackInfo.model_validate(
        {
            "mbid": "11111111-1111-1111-1111-111111111111",
            "isrc": "USRC12500016",
            "spotify_id": None,
            "name": "Last Resort",
            "artist": "Papa Roach",
            "genres": ["nu metal"],
            "tags": ["nu metal"],
            "duration": 200.0,
            "plays": 5,
        }
    )
    full = music_schema.Track.model_validate(
        {
            **info.model_dump(),
            "spotify_id": "105Fwh9wijwT41rrfgSnrE",
            "acousticness": 0.1,
            "danceability": 0.5,
            "energy": 0.8,
            "instrumentalness": 0.0,
            "liveness": 0.1,
            "loudness": -6.0,
            "mode": 1,
            "speechiness": 0.05,
            "tempo": 130.0,
            "valence": 0.4,
        }
    )
    tag_only = music_schema.TrackInfo.model_validate(
        {
            **info.model_dump(),
            "mbid": "22222222-2222-2222-2222-222222222222",
            "name": "Limbs",
            "plays": 11,
        }
    )

    parsed = [info, tag_only]
    with_audio = [full]
    by_mbid = {track.mbid: track for track in with_audio}
    payload = [
        by_mbid[track_info.mbid].model_dump() if track_info.mbid in by_mbid else track_info.model_dump()
        for track_info in parsed
    ]

    assert len(payload) == 2
    assert payload[0]["energy"] == 0.8
    assert "energy" not in payload[1]
    assert payload[1]["genres"] == ["nu metal"]


def test_determine_element_scores_empty_tracks() -> None:
    scores, _notes = MusicProvider().determine_element_scores(())
    assert scores == {VibemonTypeT.NORMAL: 1.0}


def test_determine_element_scores_metal_tag() -> None:
    scores, _notes = MusicProvider().determine_element_scores((_sample_track(genres=["heavy metal"], plays=10),))
    assert scores.get(VibemonTypeT.STEEL, 0) > 0
    assert scores.get(VibemonTypeT.DARK, 0) > 0


def test_determine_element_scores_blues_rock_stacks_normalized() -> None:
    scores, _notes = MusicProvider().determine_element_scores((_sample_track(genres=["blues rock"], plays=10),))
    assert scores[VibemonTypeT.ROCK] > 0
    assert scores[VibemonTypeT.GROUND] > 0


def test_determine_element_scores_dance_matches_electronic() -> None:
    scores, _notes = MusicProvider().determine_element_scores((_sample_track(genres=["dance"], plays=1),))
    assert scores.get(VibemonTypeT.ELECTRIC, 0) >= 1.0


def test_determine_element_scores_multi_tag_track() -> None:
    scores, _notes = MusicProvider().determine_element_scores(
        (_sample_track(genres=["jazz", "sad", "piano"], plays=5),)
    )
    assert scores.get(VibemonTypeT.PSYCHIC, 0) > 0
    assert scores.get(VibemonTypeT.WATER, 0) > 0


def test_determine_element_scores_uses_genres_and_tags() -> None:
    scores, _notes = MusicProvider().determine_element_scores((_sample_track(genres=["metal"], tags=["sad"], plays=5),))
    assert scores.get(VibemonTypeT.STEEL, 0) > 0
    assert scores.get(VibemonTypeT.WATER, 0) > 0


def test_determine_element_scores_play_count_weighting() -> None:
    provider = MusicProvider()
    light, _ = provider.determine_element_scores((_sample_track(genres=["metal"], plays=1),))
    heavy, _ = provider.determine_element_scores((_sample_track(genres=["metal"], plays=100),))
    for t in VibemonTypeT:
        assert light.get(t, 0) == pytest.approx(heavy.get(t, 0), abs=0.001)


def test_determine_element_scores_across_tracks() -> None:
    provider = MusicProvider()
    scores, _notes = provider.determine_element_scores(
        (
            _sample_track(genres=["metal"], plays=10),
            _sample_track(genres=["jazz"], plays=10, mbid="22222222-2222-2222-2222-222222222222"),
        )
    )
    assert scores.get(VibemonTypeT.STEEL, 0) > 0
    assert scores.get(VibemonTypeT.PSYCHIC, 0) > 0


def test_calculate_intensity_balanced_pace() -> None:
    assert MusicProvider().calculate_intensity(last7d=70, last1m=300) == 0.5


def test_calculate_intensity_hot_week() -> None:
    intensity = MusicProvider().calculate_intensity(last7d=140, last1m=300)
    assert intensity > 0.65


def test_affinity_serializes_provider_notes() -> None:
    note = generation_types.ProviderWarning(
        level=generation_types.ProviderWarningLevel.WARNING,
        code=THIN_STAT_COVERAGE_NOTE_CODE,
        message=THIN_STAT_COVERAGE_NOTE_MESSAGE,
    )
    affinity = Affinity(
        identity=Identity(name="__", elements=(VibemonTypeT.NORMAL,), base=BaseStats()),
        provider_id="music",
        intensity=0.5,
        moves=(),
        provider_notes=(note,),
    )
    payload = affinity.model_dump(mode="json")
    assert payload["provider_notes"] == [
        {
            "level": "warning",
            "code": THIN_STAT_COVERAGE_NOTE_CODE,
            "message": THIN_STAT_COVERAGE_NOTE_MESSAGE,
        }
    ]


@pytest.mark.asyncio
async def test_synthesize_fixture_payload_is_deterministic(music_provider: MusicProvider) -> None:
    provider = music_provider
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = _load_music_payload("music_payload.json")
    first = await provider.synthesize(seed, payload)
    second = await provider.synthesize(seed, payload)
    assert first.model_dump(mode="json", exclude={"identity": {"generated_at"}}) == second.model_dump(
        mode="json", exclude={"identity": {"generated_at"}}
    )
    assert first.provider_id == "music"
    assert first.identity.elements
    assert first.visual_notes
    assert first.visual_notes != "???"
    assert first.visual_notes == second.visual_notes


@pytest.mark.asyncio
async def test_synthesize_emits_thin_coverage_note(music_provider: MusicProvider) -> None:
    provider = music_provider
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = _load_music_payload("music_payload.json").model_copy(
        update={
            "meta": providers_schema.ProviderPayloadMeta(
                notes=(
                    providers_schema.ProviderNote(
                        level=providers_schema.ProviderNoteLevelT.WARNING,
                        code=THIN_STAT_COVERAGE_NOTE_CODE,
                        message=THIN_STAT_COVERAGE_NOTE_MESSAGE,
                    ),
                )
            )
        }
    )
    affinity = await provider.synthesize(seed, payload)
    thin_notes = [note for note in affinity.provider_notes if note.code == THIN_STAT_COVERAGE_NOTE_CODE]
    assert len(thin_notes) == 1
    assert thin_notes[0].level == generation_types.ProviderWarningLevel.WARNING
    assert thin_notes[0].message == THIN_STAT_COVERAGE_NOTE_MESSAGE


@pytest.mark.asyncio
async def test_synthesize_emits_unclassified_tags_note(music_provider: MusicProvider) -> None:
    provider = music_provider
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = _music_payload(
        _sample_track(genres=["fnord"], tags=[], plays=100),
        _sample_track(genres=["metal"], tags=[], plays=50, mbid="22222222-2222-2222-2222-222222222222"),
    )
    affinity = await provider.synthesize(seed, payload)
    unclassified = [note for note in affinity.provider_notes if note.code == UNCLASSIFIED_TAGS_NOTE_CODE]
    assert len(unclassified) == 1
    assert unclassified[0].level == generation_types.ProviderWarningLevel.INFO
    assert "fnord" in unclassified[0].message


@pytest.mark.asyncio
async def test_fetch_raises_on_empty_history(
    music_provider: MusicProvider,
    trainer_secrets: FakeTrainerSecrets,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = music_provider

    async def _empty_top_tracks(_username: str, **_kwargs: object) -> object:
        return _Response({"toptracks": {"track": []}})

    class _Response:
        status_code = 200

        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def json(self) -> dict[str, object]:
            return self._payload

    monkeypatch.setattr(provider.lastfm, "user_top_tracks", _empty_top_tracks)

    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    with pytest.raises(MusicListeningUnavailable):
        await provider.fetch(seed, secrets=trainer_secrets)


@pytest.mark.asyncio
async def test_fetch_enriches_musicbrainz_and_reccobeats(
    music_provider: MusicProvider,
    trainer_secrets: FakeTrainerSecrets,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = music_provider

    async def _top_tracks(_username: str, *, period: str, **_kwargs: object) -> object:
        if period == "7day":
            return _json_response({"toptracks": {"track": []}})
        return _json_response(
            {
                "toptracks": {
                    "track": [
                        {
                            "name": "Metal Storm",
                            "mbid": "11111111-1111-1111-1111-111111111111",
                            "duration": "240000",
                            "playcount": "12",
                            "artist": {
                                "name": "Steel Horizon",
                                "mbid": "22222222-2222-2222-2222-222222222222",
                            },
                        }
                    ]
                }
            }
        )

    async def _audio_features(*ids: str):
        return _json_response(
            {
                "content": [
                    {
                        "isrc": "USRC17607839",
                        "href": "https://open.spotify.com/track/spotify-from-reccobeats",
                        "energy": 0.5,
                        "acousticness": 0.2,
                        "liveness": 0.1,
                        "valence": 0.4,
                        "danceability": 0.6,
                        "tempo": 120.0,
                        "instrumentalness": 0.0,
                        "loudness": -8.0,
                        "speechiness": 0.05,
                        "mode": 1,
                    }
                ]
            },
            ok=True,
        )

    def _json_response(payload: dict[str, object], *, ok: bool = True) -> object:
        class _Response:
            status_code = 200

            def __init__(self, body: dict[str, object], *, ok: bool) -> None:
                self._body = body
                self.ok = ok

            @staticmethod
            def raise_for_status() -> None:
                return None

            def json(self) -> dict[str, object]:
                return self._body

        return _Response(payload, ok=ok)

    async def _recording(mbid: str):
        return _json_response(
            {
                "id": mbid,
                "title": "Metal Storm",
                "isrcs": ["USRC17607839"],
                "length": 240_000,
                "genres": [{"id": "31be54b2-4d0c-42df-aa44-c496c7b4c3c3", "name": "metal"}],
                "tags": [{"name": "metal"}, {"name": "aggressive"}],
            }
        )

    monkeypatch.setattr(provider.lastfm, "user_top_tracks", _top_tracks)
    monkeypatch.setattr(provider.musicbrainz, "recording", _recording)
    monkeypatch.setattr(provider.reccobeats, "audio_features", _audio_features)

    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = await provider.fetch(seed, secrets=trainer_secrets)
    assert payload.tracks
    assert payload.tracks[0].genres == ["metal"]
    assert payload.tracks[0].tags == ["metal", "aggressive"]
    assert payload.last7d == 0
    assert payload.last1m == 12


def test_to_track_info_maps_genres_and_tags() -> None:
    recording = mb_schema.Recording.model_validate(
        {
            "id": "026fa041-3917-4c73-9079-ed16e36f20f8",
            "title": "Example",
            "genres": [{"id": "911c7bbb-172d-4df8-9478-dbff4296e791", "name": "pop"}],
            "tags": [{"name": "pop"}, {"name": "sexy"}],
        }
    )
    track = lastfm_schema.Track.model_validate({"name": "Example", "artist": {"#text": "Artist"}, "playcount": 3})

    info = music_schema.TrackInfo.combine(recording=recording, track=track)

    assert info.genres == ["pop"]
    assert info.tags == ["pop", "sexy"]


@pytest.mark.asyncio
async def test_resolve_falls_back_to_search_when_mbid_has_no_audio_ids(
    music_provider: MusicProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = music_provider

    lf_track = lastfm_schema.Track.model_validate(
        {
            "name": "Mr. Brightside",
            "mbid": "b5aa154a-6b20-475f-8fb2-6a232be05f36",
            "duration": "223000",
            "playcount": "4",
            "artist": {"name": "The Killers"},
        }
    )

    async def _recording(_mbid: str) -> object:
        class _Response:
            ok = True

            def json(self) -> dict[str, object]:
                if _mbid == "studio-recording-mbid":
                    return {
                        "id": "studio-recording-mbid",
                        "title": "Mr. Brightside",
                        "length": 223_000,
                        "isrcs": ["GBUM70300485"],
                        "genres": [{"id": "g1", "name": "rock"}],
                        "tags": [{"name": "indie rock", "count": 3}],
                        "artist-credit": [
                            {
                                "name": "The Killers",
                                "artist": {"id": "aaaa", "name": "The Killers"},
                            }
                        ],
                    }
                return {
                    "id": "b5aa154a-6b20-475f-8fb2-6a232be05f36",
                    "title": "Mr. Brightside",
                    "disambiguation": "live",
                    "isrcs": [],
                    "length": 223_000,
                }

        return _Response()

    async def _search_recording(**_kwargs: object) -> object:
        class _Response:
            ok = True

            def json(self) -> dict[str, object]:
                return {
                    "recordings": [
                        {
                            "id": "studio-recording-mbid",
                            "title": "Mr. Brightside",
                            "length": 223_000,
                            "isrcs": ["GBUM70300485"],
                            "artist-credit": [
                                {
                                    "name": "The Killers",
                                    "artist": {
                                        "id": "aaaa",
                                        "name": "The Killers",
                                    },
                                }
                            ],
                        }
                    ]
                }

        return _Response()

    monkeypatch.setattr(provider.musicbrainz, "recording", _recording)
    monkeypatch.setattr(provider.musicbrainz, "search_recording", _search_recording)

    resolved = await provider.resolve_track_info([lf_track])

    assert len(resolved) == 1
    assert resolved[0].mbid == "studio-recording-mbid"
    assert resolved[0].isrc == "GBUM70300485"
    assert resolved[0].genres == ["rock"]
    assert resolved[0].tags == ["indie rock"]


@pytest.mark.asyncio
async def test_rank_search_prefers_studio_recording_over_live(
    music_provider: MusicProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = music_provider
    lf_track = lastfm_schema.Track.model_validate(
        {
            "name": "Mr. Brightside",
            "duration": "223000",
            "playcount": "4",
            "artist": {"name": "The Killers"},
        }
    )

    async def _search_recording(**_kwargs: object) -> object:
        class _Response:
            ok = True

            def json(self) -> dict[str, object]:
                return {
                    "recordings": [
                        {
                            "id": "live-mbid",
                            "title": "Mr. Brightside",
                            "length": 223_000,
                            "disambiguation": "live, 2009-07: Royal Albert Hall, London, UK",
                            "isrcs": [],
                            "artist-credit": [
                                {
                                    "name": "The Killers",
                                    "artist": {"id": "aaaa", "name": "The Killers"},
                                }
                            ],
                        },
                        {
                            "id": "studio-mbid",
                            "title": "Mr. Brightside",
                            "length": 223_000,
                            "isrcs": ["GBUM70300485"],
                            "artist-credit": [
                                {
                                    "name": "The Killers",
                                    "artist": {"id": "aaaa", "name": "The Killers"},
                                }
                            ],
                        },
                    ]
                }

        return _Response()

    async def _recording(_mbid: str) -> object:
        class _Response:
            ok = True

            def json(self) -> dict[str, object]:
                return {
                    "id": _mbid,
                    "title": "Mr. Brightside",
                    "length": 223_000,
                    "isrcs": ["GBUM70300485"],
                    "genres": [{"id": "g1", "name": "rock"}],
                    "tags": [{"name": "alternative rock", "count": 2}],
                    "artist-credit": [
                        {
                            "name": "The Killers",
                            "artist": {"id": "aaaa", "name": "The Killers"},
                        }
                    ],
                }

        return _Response()

    monkeypatch.setattr(provider.musicbrainz, "search_recording", _search_recording)
    monkeypatch.setattr(provider.musicbrainz, "recording", _recording)

    resolved = await provider.rank_search(lf_track)

    assert resolved is not None
    assert resolved.mbid == "studio-mbid"
    assert resolved.isrc == "GBUM70300485"
    assert resolved.genres == ["rock"]
    assert resolved.tags == ["alternative rock"]


@pytest.mark.asyncio
async def test_ensure_full_track_falls_back_to_spotify_id(music_provider: MusicProvider) -> None:
    provider = music_provider
    track_info = music_schema.TrackInfo.model_validate(
        {
            "mbid": "11111111-1111-1111-1111-111111111111",
            "isrc": "USRC12500016",
            "spotify_id": "105Fwh9wijwT41rrfgSnrE",
            "name": "Example",
            "artist": "Artist",
            "genres": [],
            "duration": 200.0,
            "plays": 1,
        }
    )
    feature_row = {
        "isrc": "USRC12500016",
        "href": "https://open.spotify.com/track/105Fwh9wijwT41rrfgSnrE",
        "energy": 0.5,
        "acousticness": 0.2,
        "liveness": 0.1,
        "valence": 0.4,
        "danceability": 0.6,
        "tempo": 120.0,
        "instrumentalness": 0.0,
        "loudness": -8.0,
        "speechiness": 0.05,
        "mode": 1,
    }
    calls: list[tuple[str, ...]] = []

    async def _audio_features(*ids: str) -> object:
        calls.append(ids)

        class _Response:
            ok = True
            status_code = 200

            def json(self) -> dict[str, object]:
                if ids == ("USRC12500016",):
                    return {"content": []}
                return {"content": [feature_row]}

        return _Response()

    provider.reccobeats.audio_features = _audio_features  # type: ignore[method-assign]

    tracks = await provider.ensure_full_track([track_info])

    assert len(tracks) == 1
    assert calls == [("USRC12500016",), ("105Fwh9wijwT41rrfgSnrE",)]
