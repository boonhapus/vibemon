"""Replay existing Vibemon through current provider balance logic."""

from typing import Annotated
import asyncio
import enum
import json
import pathlib
import uuid

import cyclopts

from app.workflows import rebalance_vibemon as rebalance_workflow
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)


class DetailLevel(enum.StrEnum):
    SUMMARY = "summary"
    FULL = "full"


app = cyclopts.App(
    help=(
        "Rebalance existing Vibemon from persisted birth snapshots.\n\n"
        "The default run previews changes without writing them.\n"
        "Examples:\n"
        "  rebalance_vibemon.py\n"
        "  rebalance_vibemon.py --limit 20\n"
        "  rebalance_vibemon.py --detail full --output rebalance-report.json\n"
        "  rebalance_vibemon.py --vibemon 0198... --apply"
    )
)


@app.default
def rebalance_vibemon(
    *,
    vibemon: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Specific Vibemon UUID to rebalance; omitted selects all."),
    ] = None,
    limit: Annotated[
        int | None,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Maximum number of Vibemon to replay when no specific Vibemon is selected.",
        ),
    ] = None,
    apply: Annotated[
        bool,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Persist the rebalance; omitted runs a preview only."),
    ] = False,
    examples: Annotated[
        int,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Number of changed examples to include in the JSON output."),
    ] = 20,
    detail: Annotated[
        DetailLevel,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="How much before/after detail to include in output."),
    ] = DetailLevel.SUMMARY,
    include_unchanged: Annotated[
        bool,
        cyclopts.Parameter(group=COMMON_OPTIONS, negative="", help="Include unchanged rows when using full detail."),
    ] = False,
    output: Annotated[
        pathlib.Path | None,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Optional path to write the JSON report."),
    ] = None,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
) -> None:
    storage = _common.load_script_settings(database_url=database_url)
    asyncio.run(
        _run(
            vibemon_id=vibemon,
            limit=limit,
            apply=apply,
            examples=examples,
            detail=detail,
            include_unchanged=include_unchanged,
            output=output,
            database_url=storage.storage.database,
        )
    )


async def _run(
    *,
    vibemon_id: uuid.UUID | None,
    limit: int | None,
    apply: bool,
    examples: int,
    detail: DetailLevel,
    include_unchanged: bool,
    output: pathlib.Path | None,
    database_url: str,
) -> None:
    async with _common.session_scope(database_url=database_url) as sess:
        results = await rebalance_workflow.rebalance_existing_vibemons(
            sess,
            vibemon_id=vibemon_id,
            limit=limit,
            dry_run=not apply,
        )
    changed = [result for result in results if result.changed]
    report = _report(
        results,
        changed=changed,
        apply=apply,
        examples=examples,
        detail=detail,
        include_unchanged=include_unchanged,
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _common.dump(report)


def _report(
    results: tuple[rebalance_workflow.RebalanceSummary, ...],
    *,
    changed: list[rebalance_workflow.RebalanceSummary],
    apply: bool,
    examples: int,
    detail: DetailLevel,
    include_unchanged: bool,
) -> dict[str, object]:
    report: dict[str, object] = {
        "mode": "apply" if apply else "dry-run",
        "detail": detail.value,
        "selected": len(results),
        "changed": len(changed),
        "type_changed": sum(result.type_changed for result in results),
        "stats_changed": sum(result.stats_changed for result in results),
        "moves_changed": sum(result.moves_changed for result in results),
        "move_definitions_changed": sum(result.move_definitions_changed for result in results),
    }
    if detail is DetailLevel.FULL:
        report["changes"] = [_full_change(result) for result in changed]
        if include_unchanged:
            report["unchanged"] = [_full_change(result) for result in results if not result.changed]
        return report
    report["examples"] = [_summary_change(result) for result in changed[: max(0, examples)]]
    return report


def _summary_change(result: rebalance_workflow.RebalanceSummary) -> dict[str, object]:
    return {
        "vibemon_id": str(result.vibemon_id),
        "name": result.name,
        "before_elements": [element.value for element in result.before_elements],
        "after_elements": [element.value for element in result.after_elements],
        "before_bst": result.before_bst,
        "after_bst": result.after_bst,
        "bst_delta": result.bst_delta,
        "before_moves": list(result.before_moves),
        "after_moves": list(result.after_moves),
        "type_changed": result.type_changed,
        "stats_changed": result.stats_changed,
        "move_definitions_changed": result.move_definitions_changed,
        "moves_changed": result.moves_changed,
        "changed": result.changed,
    }


def _full_change(result: rebalance_workflow.RebalanceSummary) -> dict[str, object]:
    return {
        **_summary_change(result),
        "before": {
            "identity": result.before_identity.model_dump(mode="json"),
            "moves": [move.model_dump(mode="json") for move in result.before_moves_full],
        },
        "after": {
            "identity": result.after_identity.model_dump(mode="json"),
            "moves": [move.model_dump(mode="json") for move in result.after_moves_full],
        },
    }


if __name__ == "__main__":
    app()
