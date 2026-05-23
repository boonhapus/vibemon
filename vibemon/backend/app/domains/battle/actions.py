from __future__ import annotations

from typing import Annotated, Literal

import pydantic

from app.core.ids import TrainerIdT
from app.core.schema import FrozenSchema


class TargetRef(FrozenSchema):
    """A concrete active battle slot."""

    trainer: TrainerIdT
    slot: int = 0


class MoveAction(FrozenSchema):
    """Use a move from an active slot."""

    kind: Literal["move"] = "move"
    trainer: TrainerIdT
    slot: int = 0
    move_name: str
    targets: tuple[TargetRef, ...] = ()


class SwitchAction(FrozenSchema):
    """Switch an active slot to a bench member."""

    kind: Literal["switch"] = "switch"
    trainer: TrainerIdT
    slot: int = 0
    bench_index: int


class ItemAction(FrozenSchema):
    """Use a trainer item."""

    kind: Literal["item"] = "item"
    trainer: TrainerIdT
    item_id: str
    target: TargetRef | None = None


class RunAction(FrozenSchema):
    """Attempt to run from battle."""

    kind: Literal["run"] = "run"
    trainer: TrainerIdT


type BattleAction = Annotated[
    MoveAction | SwitchAction | ItemAction | RunAction,
    pydantic.Discriminator("kind"),
]
