"""Public Vibemon read model: owns row → PublicVibemon end to end.

Presentation shaping lives here — which fields are public, reviewing-trainer
visibility, type matchups, and signed asset URLs. `mapper` stays the storage
adapter (ORM ↔ domain); this module imports it, not the reverse (ADR-0001).
"""

import datetime as dt

from app.core.ids import TrainerIdT
from app.domains.adoption import schema as adoption_schema
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.generation.types import ProviderWarning
from app.domains.move.catalog import TYPE_AFFINITIES, get_element_effectiveness
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.assets import AssetKind, SpriteAnchor
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.progression import learnset
from app.domains.vibemon.schema import (
    PublicAsset,
    PublicVibemon,
    TypeCoverageSummary,
    TypeDefenseSummary,
    TypeMatchupSummary,
)
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import mapper, models

PUBLIC_ASSET_URL_TTL = dt.timedelta(minutes=15)


async def public_vibemon(
    row: models.Vibemon,
    *,
    reviewing_trainer_id: TrainerIdT | None = None,
) -> PublicVibemon:
    """Assemble the public read model for one loaded Vibemon row."""
    vibemon = await mapper.vibemon_from_row(row)
    assets = await _public_assets(row.assets)
    review = _visible_review(row.candidate_reviews, reviewing_trainer_id)
    aesthetic = vibemon.aesthetic
    birth_providers = tuple(learnset.birth_provider_names(BirthSnapshot(provider_payloads=dict(row.birth_snapshot.provider_payloads))))
    return PublicVibemon(
        id=vibemon.id,
        nickname=vibemon.nickname,
        name=vibemon.name,
        identity=vibemon.identity,
        moves=vibemon.moves,
        level=vibemon.level,
        xp=vibemon.xp,
        growth_rate=vibemon.growth_rate,
        evo_stage=vibemon.evo_stage,
        lifecycle=vibemon.lifecycle,
        disposition=VibemonDispositionT(row.disposition) if row.disposition else None,
        trainer_id=row.trainer_id,
        crew_slot=row.crew_slot,
        primary_color=aesthetic.primary_color if aesthetic else None,
        secondary_color=aesthetic.secondary_color if aesthetic else None,
        background_color=aesthetic.background_color if aesthetic else None,
        assets=assets,
        birth_providers=birth_providers,
        candidate_review=review,
        type_matchup=type_matchup(vibemon),
    )


async def _public_assets(assets: list[models.VibemonAsset]) -> tuple[PublicAsset, ...]:
    public = []
    for asset in sorted(assets, key=lambda item: item.kind):
        public.append(
            PublicAsset(
                kind=AssetKind(asset.kind),
                url=await _sign_asset_url(asset.object_key, PUBLIC_ASSET_URL_TTL),
                selected_revision=asset.selected_revision,
                max_revision=asset.max_revision,
                content_type=asset.content_type,
                byte_size=asset.byte_size,
                sha256=asset.sha256,
                anchor=SpriteAnchor.model_validate(asset.display_anchor) if asset.display_anchor else None,
            )
        )
    return tuple(public)


async def _sign_asset_url(key: str, expires_in: dt.timedelta) -> str:
    return await get_default_monstore().url(key, expires_in)


def _visible_review(
    reviews: list[models.CandidateReview],
    reviewing_trainer_id: TrainerIdT | None,
) -> adoption_schema.CandidateReviewRead | None:
    if reviewing_trainer_id is None:
        return None
    for review in reviews:
        if review.trainer_id == reviewing_trainer_id:
            status = CandidateReviewStatusT(review.status)
            resolution = CandidateReviewStatusT(review.resolution) if review.resolution else None
            return adoption_schema.CandidateReviewRead(
                id=review.id,
                trainer_id=review.trainer_id,
                status=status,
                shown_at=review.shown_at,
                timeout_at=review.timeout_at,
                resolved_at=review.resolved_at,
                resolution=resolution,
                status_label=adoption_schema.candidate_review_status_label(status),
                resolved_label=adoption_schema.candidate_review_status_label(resolution) if resolution else None,
                provider_notes=_provider_notes(review.provider_notes),
            )
    return None


def _provider_notes(raw: list[dict[str, str]]) -> tuple[ProviderWarning, ...]:
    return tuple(ProviderWarning.model_validate(item) for item in raw)


def type_matchup(vibemon: Vibemon) -> TypeMatchupSummary:
    all_types = tuple(VibemonTypeT)
    weak_to: list[VibemonTypeT] = []
    resists: list[VibemonTypeT] = []
    immune_to: list[VibemonTypeT] = []
    for attack_type in all_types:
        modifier = get_element_effectiveness(attack_type, vibemon.elements)
        if modifier == 0.0:
            immune_to.append(attack_type)
        elif modifier > 1.0:
            weak_to.append(attack_type)
        elif 0.0 < modifier < 1.0:
            resists.append(attack_type)

    move_types = tuple(dict.fromkeys(move.type for move in vibemon.moves))
    strong_against = sorted(
        {covered for move_type in move_types for covered in TYPE_AFFINITIES[move_type].covers},
        key=lambda value: value.value,
    )
    ineffective_against = sorted(
        {
            defender_type
            for defender_type in all_types
            if move_types
            and all(get_element_effectiveness(move_type, (defender_type,)) < 1.0 for move_type in move_types)
        },
        key=lambda value: value.value,
    )
    return TypeMatchupSummary(
        defense=TypeDefenseSummary(
            weak_to=tuple(weak_to),
            resists=tuple(resists),
            immune_to=tuple(immune_to),
        ),
        coverage=TypeCoverageSummary(
            move_types=move_types,
            strong_against=tuple(strong_against),
            ineffective_against=tuple(ineffective_against),
        ),
    )
