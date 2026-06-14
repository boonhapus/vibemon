# 05 — Public projection: fold pass-through facade into a read-model module

**Status:** implemented — `ReadModelAssembler` + `read_model.py` folded into `public_projection.py`; the DI class (schema_loader/asset_urler, never varied) is gone and row → `PublicVibemon` (incl. Monstore URL signing) is one hop. `mapper.py` stays the ORM↔domain adapter.
**Priority:** medium (smaller win than 01–04)
**Vocabulary:** module / interface / seam / depth / locality per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/workflows/public_projection.py` (~24 LOC) — pass-through called from 10+ sites
- `vibemon/backend/app/storage/database/mapper.py` (~300+ LOC) — does the real row→schema work
- `read_model.ReadModelAssembler` — view assembly
- `get_default_monstore().url(...)` — asset URL signing

## Problem

`public_projection.public_vibemon` fails the deletion test: deleting it would not concentrate complexity, just relocate the three-line assembler construction to call sites. The real behaviour lives elsewhere, so answering "how does a Vibemon serialize for the HTTP response?" requires a three-hop chain: `public_projection` → `mapper.vibemon_from_row` → `ReadModelAssembler` (plus **Monstore** URL signing). Each hop is small; all are required.

## Solution

One read-model module that owns row → `PublicVibemon` end to end, including asset URL signing via **Monstore**. The assembler and the projection-specific parts of the mapping collapse into it; `mapper.py` stays a **Database Storage** adapter (ORM↔domain), while presentation shaping (which fields are public, reviewing-trainer visibility, signed URLs) lives in the read-model module. The projection chain becomes one hop.

## Benefits

- **Locality:** serialization changes, visibility rules, and URL-signing policy concentrate in one place with one obvious test home.
- **Leverage:** modest — callers already had a one-call interface; the gain is for maintainers, not callers. That's why this ranks below 01–04.

## Notes / dependencies

- Independent of other plans; safe to do anytime.
- Watch the seam direction: read-model module may import storage mapper, not vice versa (ADR-0001 layering).
