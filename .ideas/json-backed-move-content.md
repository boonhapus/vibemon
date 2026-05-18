# JSON-Backed Move Content

**Status:** Accepted direction; implementation tracked in roadmap

## Why this exists

Move definitions currently live in Python modules. Moving content to validated JSON improves:
- frontend inspection and tooling,
- content safety for plugins,
- auditability and migration control,
- long-term localization readiness.

## Decision boundaries

- Battle engine continues consuming typed `Move`/`BattleMove` objects.
- Raw JSON must be parsed and validated in a content loader layer, not in battle runtime code.
- Provider-authored executable code is out of scope.
- `script_id` remains a backend-owned first-party escape hatch only.

## Canonical task tracker

Implementation tasks are maintained in:
- `.plans/ROADMAP.md` -> `Move Content Externalization (Deferred Build Track)`

## Scope notes

Near-term scope is externalized move data + validation + incremental migration.
Localization keys and full i18n plumbing are intentionally deferred until frontend requirements require them.
