"""Rehearse a pure automated battle between two Vibemon."""

from typing import Annotated
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.domains.battle import entity as battle_entity
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

app = cyclopts.App(
    help=(
        "Rehearse a deterministic 1v1 Vibemon battle.\n\n"
        "Pass existing Vibemon IDs when you want specific combatants; omit either side to sample from the database.\n"
        "Examples:\n"
        "  simulate_battle.py\n"
        "  simulate_battle.py --vibemon-a 0198... --vibemon-b 0198...\n"
        "  simulate_battle.py --seed 42 --name-a Ada --name-b Lin\n"
        "  simulate_battle.py --move-policy best_damage"
    )
)


@app.default
def simulate_battle(
    *,
    vibemon_a: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(
            name="--vibemon-a",
            group=COMMON_OPTIONS,
            help="Existing Vibemon UUID for side A; random database pick if omitted.",
        ),
    ] = None,
    vibemon_b: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(
            name="--vibemon-b",
            group=COMMON_OPTIONS,
            help="Existing Vibemon UUID for side B; random database pick if omitted.",
        ),
    ] = None,
    trainer_a: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(
            name="--trainer-a",
            group=COMMON_OPTIONS,
            help="Trainer UUID for side A; random if omitted.",
        ),
    ] = None,
    trainer_b: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(
            name="--trainer-b",
            group=COMMON_OPTIONS,
            help="Trainer UUID for side B; random if omitted.",
        ),
    ] = None,
    name_a: Annotated[
        str,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer display name for side A."),
    ] = "trainer-a",
    name_b: Annotated[
        str,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer display name for side B."),
    ] = "trainer-b",
    seed: Annotated[
        int | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Random seed for deterministic battle rolls."),
    ] = 1,
    move_policy: Annotated[
        _common.BattleMovePolicyT,
        cyclopts.Parameter(
            name="--move-policy",
            group=COMMON_OPTIONS,
            help="Automated move selector: first_available, best_damage, stab_first, status_aware, or random.",
        ),
    ] = "first_available",
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
    asset_store_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Asset store URL override; defaults to VIBEMON_STORAGE__ASSETS.",
        ),
    ] = None,
) -> None:
    storage = _common.load_script_settings(database_url=database_url, asset_store_url=asset_store_url)
    asyncio.run(
        _run(
            vibemon_a_id=vibemon_a,
            vibemon_b_id=vibemon_b,
            trainer_a_id=trainer_a or uuid.uuid7(),
            trainer_b_id=trainer_b or uuid.uuid7(),
            trainer_a_name=name_a,
            trainer_b_name=name_b,
            database_url=storage.storage.database,
            asset_store_url=storage.storage.assets,
            rng_seed=seed,
            move_policy=move_policy,
        )
    )


async def _run(
    *,
    vibemon_a_id: uuid.UUID | None,
    vibemon_b_id: uuid.UUID | None,
    trainer_a_id: uuid.UUID,
    trainer_b_id: uuid.UUID,
    trainer_a_name: str,
    trainer_b_name: str,
    database_url: str,
    asset_store_url: str,
    rng_seed: int | None,
    move_policy: _common.BattleMovePolicyT,
) -> None:
    _common.ensure_local_blob_dir(asset_store_url)
    async with _common.session_scope(database_url=database_url) as sess:
        vibemon_a, selected_vibemon_a_id = await _load_selected_battle_vibemon(sess, vibemon_a_id)
        vibemon_b, selected_vibemon_b_id = await _load_selected_battle_vibemon(
            sess,
            vibemon_b_id,
            exclude_ids={selected_vibemon_a_id},
        )

    result = _common.simulate_battle(
        vibemon_a,
        vibemon_b,
        trainer_a_id=trainer_a_id,
        trainer_b_id=trainer_b_id,
        trainer_a_name=trainer_a_name,
        trainer_b_name=trainer_b_name,
        rng_seed=rng_seed,
        move_policy=move_policy,
    )
    _common.dump(
        {
            "experience": "battle",
            "vibemon_a_id": str(selected_vibemon_a_id),
            "vibemon_b_id": str(selected_vibemon_b_id),
            **result,
        }
    )


async def _load_selected_battle_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID | None,
    *,
    exclude_ids: set[uuid.UUID] | None = None,
) -> tuple[battle_entity.BattleVibemon, uuid.UUID]:
    if vibemon_id is None:
        try:
            selected_vibemon_id, vibemon = await _common.load_random_battle_vibemon(sess, exclude_ids=exclude_ids)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        return vibemon, selected_vibemon_id
    return await _common.load_battle_vibemon(sess, vibemon_id), vibemon_id


if __name__ == "__main__":
    app()
