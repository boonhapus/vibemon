"""HTTP tests for wild battle routes."""

from collections.abc import AsyncGenerator
import datetime as dt
import io
import uuid

from litestar import Litestar
from litestar.testing import AsyncTestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
import pytest
import sqlalchemy as sa

from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.move.entity import EffectGroup, MoveBehavior
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.sprite import types as sprite_types
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.types import VibemonLifecycleT
from app.genai import vibemon_assets as genai_assets
from app.http.app import create_app
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import models
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.fixture
def http_app() -> Litestar:
    return create_app()


@pytest.fixture
async def client(http_app: Litestar) -> AsyncGenerator[AsyncTestClient[Litestar]]:
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


def _png_bytes() -> bytes:
    payload = io.BytesIO()
    Image.new("RGB", (16, 16), "#ffffff").save(payload, format="PNG")
    return payload.getvalue()


class _FakeAssetGenerator:
    async def detect_trainer_reference_facing(self, reference_png: bytes) -> sprite_types.SpriteFacing:
        return sprite_types.SpriteFacing.RIGHT

    async def detect_vibemon_reference_facing(
        self, reference_png: bytes, *, vibemon_name: str
    ) -> sprite_types.SpriteFacing:
        return sprite_types.SpriteFacing.RIGHT

    async def generate_name(self, identity: object, moves: object) -> str:
        return "Testling"

    async def generate_reference_image(self, vibemon: object) -> bytes:
        return _png_bytes()

    async def generate_battle_cry_audio(self, vibemon: object) -> bytes:
        return b"mp3"

    async def generate_sprite_sheet_image(self, vibemon: object, reference_image: bytes) -> bytes:
        return _png_bytes()


@pytest.fixture(autouse=True)
def fake_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(genai_assets, "get_default_asset_generator", lambda: _FakeAssetGenerator())
    get_default_monstore.cache_clear()


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.providers.registry.build_provider_instances",
        lambda provider_names=None: [FakeProvider()],
    )


def _move_row(*, content_id: str, name: str, power: int = 120) -> models.Move:
    return models.Move(
        id=uuid.uuid7(),
        content_id=content_id,
        name=name,
        flavor_text="Test move.",
        type=VibemonTypeT.NORMAL.value,
        category=MoveCategoryT.PHYSICAL.value,
        power=power,
        accuracy=1.0,
        pp=20,
        priority=0,
        target=MoveTargetT.SINGLE.value,
        level_requirement=1,
        effects=[EffectGroup(effects=(), trigger="on_hit", chance=1.0).model_dump(mode="json")],
        behavior=MoveBehavior().model_dump(mode="json"),
    )


async def _register(client: AsyncTestClient[Litestar], username: str = "Battler") -> str:
    response = await client.post("/api/trainers/register", json={"username": username})
    assert response.status_code == 201
    return response.json()["id"]


async def _insert_wild(sess: AsyncSession) -> uuid.UUID:
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    wild_id = uuid.uuid7()
    seed = models.BirthSeed(timestamp=now, geo_coords=[41.0, -87.0], trainer_id=TEST_TRAINER_ID)
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    wild = models.Vibemon(
        id=wild_id,
        nickname=None,
        xp=0,
        level=3,
        evo_stage=1,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.WILD.value,
        crew_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=now,
    )
    wild.identity = models.Identity(
        name="Fodder",
        visual_notes=None,
        elements=["normal"],
        base_hp=20,
        base_attack=10,
        base_defense=20,
        base_sp_attack=10,
        base_sp_defense=20,
        base_speed=10,
        evo_seed=1,
        is_radiant=False,
        generated_at=now,
    )
    tap = _move_row(content_id="test.tap", name="Tap", power=1)
    wild.moves = [
        models.VibemonMove(
            vibemon_id=wild_id,
            move_content_id=tap.content_id,
            active_slot=0,
            move=tap,
        )
    ]
    sess.add(wild)
    await sess.flush()
    return wild_id


async def _seed_battle_pair(client: AsyncTestClient[Litestar], http_app: Litestar) -> tuple[str, str]:
    await _register(client)
    generated = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert generated.status_code == 201
    hero_id = generated.json()["candidate"]["id"]
    adopted = await client.post(f"/api/candidates/{hero_id}/adopt", json={"nickname": "Hero"})
    assert adopted.status_code == 201

    factory = http_app.state.session_factory
    async with factory() as sess:
        wild_id = await _insert_wild(sess)
        await sess.commit()

    started = await client.post(
        "/api/battles",
        json={"hero_vibemon_id": hero_id, "wild_vibemon_id": str(wild_id)},
    )
    assert started.status_code == 201, started.text
    return hero_id, started.json()["battle_id"]


async def test_battle_happy_path_start_turn_finish(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)

    state = await client.get(f"/api/battles/{battle_id}")
    assert state.status_code == 200
    payload = state.json()
    assert payload["player"]["stat_stages"] == {}
    assert payload["player"]["moves"][0]["effectiveness"] == 1.0
    assert payload["player"]["moves"][0]["category"] in {"physical", "special", "status"}
    assert payload["player"]["moves"][0]["id"]
    assert payload["player"]["moves"][0]["accuracy"] is not None
    assert isinstance(payload["player"]["moves"][0]["flavor_text"], str)
    assert isinstance(payload["player"]["moves"][0]["combat_hints"], list)
    assert payload["weather"] == "clear"

    move_name = payload["player"]["moves"][0]["name"]
    turn_payload = None
    for _ in range(20):
        turn = await client.post(
            f"/api/battles/{battle_id}/turn",
            json={"move_name": move_name},
        )
        assert turn.status_code == 201
        turn_payload = turn.json()
        if turn_payload["state"]["concluded"]:
            break
    assert turn_payload is not None
    assert turn_payload["state"]["concluded"] is True

    finish = await client.post(f"/api/battles/{battle_id}/finish")
    assert finish.status_code == 201
    progression = finish.json()["progression"]
    assert progression is not None
    assert progression["new_xp"] > progression["previous_xp"]
    assert progression["new_level"] >= progression["previous_level"]
    assert 0.0 <= progression["xp_bar_ratio"] <= 1.0
    assert progression["leveled_up"] == (progression["new_level"] > progression["previous_level"])
    if progression["leveled_up"]:
        assert isinstance(progression["stat_deltas"], list)
        assert progression["stat_deltas"]
        assert progression["stat_deltas"][0]["stat"] == "hp"


async def test_battle_run_concludes_without_progression(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)

    fled = await client.post(f"/api/battles/{battle_id}/run")
    assert fled.status_code == 201
    fled_payload = fled.json()
    assert fled_payload["state"]["fled"] is True
    assert "You slip away." in fled_payload["messages"]

    finish = await client.post(f"/api/battles/{battle_id}/finish")
    assert finish.status_code == 201
    assert finish.json()["progression"] is None


async def test_battle_turn_rejects_invalid_move(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)

    response = await client.post(f"/api/battles/{battle_id}/turn", json={"move_name": "Missing Move"})
    assert response.status_code == 400
    assert "Missing Move" in response.json()["detail"]


async def test_battle_turn_rejects_concluded_battle(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)
    await client.post(f"/api/battles/{battle_id}/run")

    response = await client.post(
        f"/api/battles/{battle_id}/turn",
        json={"move_name": "Tap"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Battle is already over."


async def test_battle_switch_rejects_out_of_range_bench(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)

    response = await client.post(
        f"/api/battles/{battle_id}/switch",
        json={"bench_index": 5},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "That crew member is not in this battle."


async def test_battle_finish_is_not_idempotent(client: AsyncTestClient[Litestar], http_app: Litestar) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)
    await client.post(f"/api/battles/{battle_id}/run")

    first = await client.post(f"/api/battles/{battle_id}/finish")
    assert first.status_code == 201

    second = await client.post(f"/api/battles/{battle_id}/finish")
    assert second.status_code == 401
    assert second.json()["detail"] == "Battle session not found."


async def test_battle_win_finish_records_encounter_outcome_once(
    client: AsyncTestClient[Litestar], http_app: Litestar
) -> None:
    _, battle_id = await _seed_battle_pair(client, http_app)

    state = await client.get(f"/api/battles/{battle_id}")
    wild_id = uuid.UUID(state.json()["wild_vibemon_id"])
    move_name = state.json()["player"]["moves"][0]["name"]

    for _ in range(20):
        turn = await client.post(f"/api/battles/{battle_id}/turn", json={"move_name": move_name})
        assert turn.status_code == 201
        if turn.json()["state"]["concluded"]:
            break

    finish = await client.post(f"/api/battles/{battle_id}/finish")
    assert finish.status_code == 201

    factory = http_app.state.session_factory
    async with factory() as sess:
        adjustments = (
            (
                await sess.execute(
                    sa.select(models.EncounterAdjustment).where(models.EncounterAdjustment.vibemon_id == wild_id)
                )
            )
            .scalars()
            .all()
        )
        history = (
            (await sess.execute(sa.select(models.VibemonHistory).where(models.VibemonHistory.vibemon_id == wild_id)))
            .scalars()
            .all()
        )

    assert len(adjustments) == 1
    assert adjustments[0].source == WildEncounterOutcomeT.WIN_NO_ADOPT.value
    assert len(history) == 1
    assert history[0].event_type == VibemonHistoryEventT.WILD_ENCOUNTER_COMPLETED.value
