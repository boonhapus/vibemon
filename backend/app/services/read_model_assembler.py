"""Service-internal read-model assembly for Vibemon public responses."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import datetime as dt

from app import const, models, schema, types
from app.balance.element_chart import TYPE_AFFINITIES, get_element_effectiveness
from app.data_store import types as ds_types
from app.domain import read_models

type AssetUrler = Callable[[str, dt.timedelta], Awaitable[str]]


class ReadModelAssembler:
    """Build PublicVibemon payloads from loaded ORM rows."""

    def __init__(
        self,
        *,
        schema_loader: Callable[[models.Vibemon], Awaitable[schema.Vibemon]],
        asset_urler: AssetUrler,
    ) -> None:
        self._schema_loader = schema_loader
        self._asset_urler = asset_urler

    async def assemble(
        self,
        row: models.Vibemon,
        *,
        reviewing_trainer_id: types.TrainerIdT | None = None,
    ) -> schema.PublicVibemon:
        vibemon = await self._schema_loader(row)
        assets = await self._public_assets(row.assets)
        review = _visible_review(row.candidate_reviews, reviewing_trainer_id)
        aesthetic = vibemon.aesthetic
        return schema.PublicVibemon(
            id=vibemon.id,
            nickname=vibemon.nickname,
            name=vibemon.name,
            identity=vibemon.identity,
            moves=vibemon.moves,
            level=vibemon.level,
            xp=vibemon.xp,
            evo_stage=vibemon.evo_stage,
            lifecycle=vibemon.lifecycle,
            disposition=types.VibemonDispositionT(row.disposition) if row.disposition else None,
            trainer_id=row.trainer_id,
            team_slot=row.team_slot,
            primary_color=aesthetic.primary_color if aesthetic else None,
            secondary_color=aesthetic.secondary_color if aesthetic else None,
            background_color=aesthetic.background_color if aesthetic else None,
            assets=assets,
            candidate_review=review,
            type_matchup=_type_matchup(vibemon),
        )

    async def _public_assets(self, assets: list[models.VibemonAsset]) -> tuple[schema.PublicAsset, ...]:
        public = []
        for asset in sorted(assets, key=lambda item: item.kind):
            public.append(
                schema.PublicAsset(
                    kind=ds_types.AssetKind(asset.kind),
                    url=await self._asset_urler(asset.object_key, const.PUBLIC_ASSET_URL_TTL),
                    content_type=asset.content_type,
                    byte_size=asset.byte_size,
                    sha256=asset.sha256,
                )
            )
        return tuple(public)


def _visible_review(
    reviews: list[models.CandidateReview],
    reviewing_trainer_id: types.TrainerIdT | None,
) -> schema.CandidateReviewRead | None:
    if reviewing_trainer_id is None:
        return None
    for review in reviews:
        if review.trainer_id == reviewing_trainer_id:
            status = types.CandidateReviewStatusT(review.status)
            resolution = types.CandidateReviewStatusT(review.resolution) if review.resolution else None
            return schema.CandidateReviewRead(
                id=review.id,
                trainer_id=review.trainer_id,
                status=status,
                shown_at=review.shown_at,
                timeout_at=review.timeout_at,
                resolved_at=review.resolved_at,
                resolution=resolution,
                status_label=read_models.candidate_review_status_label(status),
                resolved_label=read_models.candidate_review_status_label(resolution) if resolution else None,
            )
    return None


def _type_matchup(vibemon: schema.Vibemon) -> schema.TypeMatchupSummary:
    all_types = tuple(types.VibemonTypeT)
    weak_to: list[types.VibemonTypeT] = []
    resists: list[types.VibemonTypeT] = []
    immune_to: list[types.VibemonTypeT] = []
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
    return schema.TypeMatchupSummary(
        defense=schema.TypeDefenseSummary(
            weak_to=tuple(weak_to),
            resists=tuple(resists),
            immune_to=tuple(immune_to),
        ),
        coverage=schema.TypeCoverageSummary(
            move_types=move_types,
            strong_against=tuple(strong_against),
            ineffective_against=tuple(ineffective_against),
        ),
    )
