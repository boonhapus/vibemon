from __future__ import annotations

from typing import Protocol


class MoveUseResult(Protocol):
    """Marker protocol for future move-use results."""


class MoveScript(Protocol):
    """First-party executable behavior for exceptional moves."""

    def modify_priority(self, ctx: object, use: object) -> int: ...

    def before_move(self, ctx: object, use: object) -> MoveUseResult: ...

    def modify_power(self, ctx: object, use: object, target: object) -> int | None: ...

    def on_hit(self, ctx: object, hit: object) -> None: ...

    def after_move(self, ctx: object, use: object) -> None: ...


class MoveScriptRegistry:
    """Stable id registry for first-party move scripts."""

    def __init__(self) -> None:
        self._scripts: dict[str, MoveScript] = {}

    def register(self, script_id: str, script: MoveScript) -> None:
        self._scripts[script_id] = script

    def get(self, script_id: str | None) -> MoveScript | None:
        if script_id is None:
            return None
        return self._scripts.get(script_id)
