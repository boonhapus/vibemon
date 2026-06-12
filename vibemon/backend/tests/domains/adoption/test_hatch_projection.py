"""Tests for hatch review read-model assembly."""

import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.adoption import hatch_projection
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.assets import AssetKind, SpriteAnchor
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.schema import (
    PublicAsset,
    PublicVibemon,
    TypeCoverageSummary,
    TypeDefenseSummary,
    TypeMatchupSummary,
)
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT
from app.storage.database import candidate_review_repo, models
from app.workflows import candidate_action
from app.workflows.candidate import generate_candidate
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


def _empty_matchup() -> TypeMatchupSummary:
    return TypeMatchupSummary(
        defense=TypeDefenseSummary(weak_to=(), resists=(), immune_to=()),
        coverage=TypeCoverageSummary(move_types=(), strong_against=(), ineffective_against=()),
    )


def _public_vibemon(
    *,
    evo_seed: EvolutionStageT = EvolutionStageT.BASE,
) -> PublicVibemon:
    anchor = SpriteAnchor(anchor_x=0.5, baseline_y=0.92, content_box=(0.2, 0.1, 0.8, 0.95))
    return PublicVibemon(
        id=uuid.uuid7(),
        name="Sproutling",
        nickname="Sprout",
        identity=Identity(
            name="Sproutling",
            elements=(VibemonTypeT.GRASS,),
            visual_notes="",
            provider_visual_notes="",
            base=BaseStats(hp=45, attack=49, defense=49, sp_attack=65, sp_defense=65, speed=45),
            evo_seed=evo_seed,
        ),
        moves=(
            Move(
                id="climate.leaf_slap",
                name="Leaf Slap",
                type=VibemonTypeT.GRASS,
                category=MoveCategoryT.PHYSICAL,
                power=40,
                accuracy=None,
                flavor_text="A leafy smack.",
            ),
        ),
        level=1,
        xp=0,
        evo_stage=evo_seed,
        lifecycle=VibemonLifecycleT.CHRISTENED,
        disposition=None,
        assets=(
            PublicAsset(
                kind=AssetKind.REFERENCE,
                url="https://example.test/reference.png",
                selected_revision=1,
                max_revision=1,
                content_type="image/png",
                byte_size=128,
                sha256="abc123",
                anchor=anchor,
            ),
        ),
        birth_providers=("climate",),
        candidate_review=None,
        type_matchup=_empty_matchup(),
    )


def test_assemble_hatch_candidate_maps_core_fields() -> None:
    public = _public_vibemon()

    payload = hatch_projection.assemble_hatch_candidate(public, reference_facing="right")

    assert payload.id == public.id
    assert payload.name == "Sproutling"
    assert payload.nickname == "Sprout"
    assert payload.elements == ("grass",)
    assert payload.bst == public.identity.bst
    assert payload.power_pips > 0
    assert payload.reference_url == "https://example.test/reference.png"
    assert payload.reference_facing == "right"
    assert payload.providers == ("climate",)
    assert payload.display.anchor_x == 0.5
    assert payload.display.baseline_y == 0.92
    assert payload.display.size_class == "small"
    assert payload.moves[0].name == "Leaf Slap"
    assert payload.moves[0].combat_hints == ("Never misses.",)


def test_assemble_hatch_candidate_three_stage_line_is_small_at_hatch() -> None:
    public = _public_vibemon(evo_seed=EvolutionStageT.STAGE_3).model_copy(
        update={"evo_stage": EvolutionStageT.BASE},
    )

    payload = hatch_projection.assemble_hatch_candidate(public)

    assert payload.evolution_line.form_count == 3
    assert payload.display.size_class == "small"


def test_assemble_hatch_candidate_marks_deep_evolution_line() -> None:
    public = _public_vibemon(evo_seed=EvolutionStageT.PSEUDO_LEGENDARY).model_copy(
        update={"evo_stage": EvolutionStageT.BASE},
    )

    payload = hatch_projection.assemble_hatch_candidate(public)

    assert payload.evo_seed == int(EvolutionStageT.PSEUDO_LEGENDARY)
    assert payload.evolution_line.form_count == 3
    assert payload.evolution_line.line_rarity == "deep"
    assert payload.display.size_class == "large"


@pytest.mark.asyncio
async def test_candidate_action_read_uses_stored_review_facing(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 6, 11, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="hatcher"))
    await sess.flush()

    candidate = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=BirthSeed(
            timestamp=now,
            geo_coords=(41.8781, -87.6298),
            trainer_id=trainer_id,
            providers=[FakeProvider()],
        ),
        christen=False,
    )
    review = await candidate_review_repo.load_pending_candidate_review(sess, trainer_id=trainer_id)
    assert review is not None
    review.reference_facing = "right"
    await sess.flush()

    payload = await candidate_action.candidate_action_read(
        sess,
        trainer_id=trainer_id,
        vibemon_id=candidate.id,
    )

    assert payload.crew_count == 0
    assert payload.candidate.id == candidate.id
    assert payload.candidate.reference_facing == "right"
    assert payload.candidate.candidate_review is not None
    assert payload.candidate.candidate_review.status is CandidateReviewStatusT.PENDING
