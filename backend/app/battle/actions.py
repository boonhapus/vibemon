from __future__ import annotations

from typing import Annotated, Literal

import pydantic

from app import schema, types


class TargetRef(schema._Static):
    """A concrete active battle slot."""

    trainer: types.TrainerIdT
    slot: int = 0


class MoveAction(schema._Static):
    """Use a move from an active slot."""

    kind: Literal["move"] = "move"
    trainer: types.TrainerIdT
    slot: int = 0
    move_name: str
    targets: tuple[TargetRef, ...] = ()


class SwitchAction(schema._Static):
    """Switch an active slot to a bench member."""

    kind: Literal["switch"] = "switch"
    trainer: types.TrainerIdT
    slot: int = 0
    bench_index: int


class ItemAction(schema._Static):
    """Use a trainer item."""

    kind: Literal["item"] = "item"
    trainer: types.TrainerIdT
    item_id: str
    target: TargetRef | None = None


class RunAction(schema._Static):
    """Attempt to run from battle."""

    kind: Literal["run"] = "run"
    trainer: types.TrainerIdT


type BattleAction = Annotated[
    MoveAction | SwitchAction | ItemAction | RunAction,
    pydantic.Discriminator("kind"),
]
