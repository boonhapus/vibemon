"""Provider move-content JSON loader."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import pydantic

from app import schema


@dataclass(frozen=True, slots=True)
class MoveContentIssue:
    provider: str
    code: str
    message: str
    move_id: str | None = None
    move_name: str | None = None
    index: int | None = None


@dataclass(frozen=True, slots=True)
class MoveContentLoadResult:
    provider: str
    source: Path
    moves: tuple[schema.Move, ...]
    issues: tuple[MoveContentIssue, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.issues)


def _issue(
    provider: str,
    code: str,
    message: str,
    *,
    move_id: str | None = None,
    move_name: str | None = None,
    index: int | None = None,
) -> MoveContentIssue:
    return MoveContentIssue(
        provider=provider,
        code=code,
        message=message,
        move_id=move_id,
        move_name=move_name,
        index=index,
    )


def _format_pydantic_error(exception: pydantic.ValidationError) -> str:
    parts: list[str] = []
    for error in exception.errors():
        loc = ".".join(str(item) for item in error.get("loc", ()))
        msg = str(error.get("msg", "validation error"))
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) if parts else str(exception)


def _parse_root(data: Mapping[str, Any], source: Path) -> tuple[str, list[dict[str, Any]]]:
    unknown_root_fields = set(data) - {"version", "provider", "moves"}
    if unknown_root_fields:
        unknown = ", ".join(sorted(unknown_root_fields))
        raise ValueError(f"{source}: unknown top-level fields: {unknown}")

    version = data.get("version")
    if version != 1:
        raise ValueError(f"{source}: unsupported move content version={version!r}; expected 1")

    provider = data.get("provider")
    if not isinstance(provider, str) or not provider:
        raise ValueError(f"{source}: provider must be a non-empty string")

    raw_moves = data.get("moves")
    if not isinstance(raw_moves, list):
        raise ValueError(f"{source}: moves must be a list")

    move_dicts: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_moves):
        if not isinstance(raw, dict):
            raise ValueError(f"{source}: moves[{idx}] must be an object")
        move_dicts.append(raw)
    return provider, move_dicts


def load_provider_moves(source: str | Path) -> MoveContentLoadResult:
    """Load one provider move JSON file with strict per-move validation."""
    path = Path(source)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: failed to parse move content JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path}: root must be an object")

    provider, raw_moves = _parse_root(payload, path)
    issues: list[MoveContentIssue] = []
    moves: list[schema.Move] = []
    seen_ids: dict[str, tuple[int, str]] = {}
    seen_names: dict[str, tuple[int, str]] = {}

    for index, raw_move in enumerate(raw_moves):
        move_id = raw_move.get("id") if isinstance(raw_move.get("id"), str) else None
        move_name = raw_move.get("name") if isinstance(raw_move.get("name"), str) else None

        try:
            move = schema.Move.model_validate(raw_move)
        except pydantic.ValidationError as exc:
            issues.append(
                _issue(
                    provider,
                    "invalid_move",
                    _format_pydantic_error(exc),
                    move_id=move_id,
                    move_name=move_name,
                    index=index,
                )
            )
            continue

        assert move.id is not None
        if not move.id.startswith(f"{provider}."):
            issues.append(
                _issue(
                    provider,
                    "provider_mismatch",
                    f"move id {move.id!r} must be scoped to provider {provider!r}",
                    move_id=move.id,
                    move_name=move.name,
                    index=index,
                )
            )
            continue

        if (existing := seen_ids.get(move.id)) is not None:
            existing_idx, existing_name = existing
            issues.append(
                _issue(
                    provider,
                    "duplicate_move_id",
                    f"duplicate move id {move.id!r} with moves[{existing_idx}] ({existing_name!r})",
                    move_id=move.id,
                    move_name=move.name,
                    index=index,
                )
            )
            continue

        canonical_name = move.canonical_name
        if (existing_name := seen_names.get(canonical_name)) is not None:
            existing_idx, existing_id = existing_name
            issues.append(
                _issue(
                    provider,
                    "duplicate_canonical_name",
                    (f"canonical name collision {canonical_name!r} with moves[{existing_idx}] (id={existing_id!r})"),
                    move_id=move.id,
                    move_name=move.name,
                    index=index,
                )
            )
            continue

        seen_ids[move.id] = (index, move.name)
        seen_names[canonical_name] = (index, move.id)
        moves.append(move)

    return MoveContentLoadResult(provider=provider, source=path, moves=tuple(moves), issues=tuple(issues))
