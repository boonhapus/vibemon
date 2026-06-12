# 02 — Lifecycle realization: deep module for Christen/Manifest behind a small interface

**Status:** proposed
**Priority:** highest (do with 04)
**Vocabulary:** module / interface / seam / depth / locality / leverage per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/workflows/asset_realization.py` (~140 LOC) — public facade
- `vibemon/backend/app/workflows/materialize_vibemon.py` (~269 LOC) — class with DI protocols
- `vibemon/backend/app/workflows/sprite_postprocess.py` (~230 LOC) — PNG normalization, sheet validation, pose extraction
- `vibemon/backend/app/workflows/rmbg.py` (~600 LOC) — custom background removal (flood fill, defringe, component keep)
- `vibemon/backend/app/workflows/pixelsnap.py` (~43 LOC) + `_pixelsnap_palette.py` (~28 LOC)
- `vibemon/backend/app/workflows/reference_facing.py` (~10 LOC)
- `vibemon/backend/app/workflows/trainer_reference.py` (~76 LOC)

## Problem

Understanding one **Lifecycle** transition (**Christen** or **Manifest**) requires reading seven files. Friction in detail:

- **Implicit ordering:** christen before manifest; refresh updates display assets, not the base reference. Nothing in the interface encodes this — callers must know.
- **Implicit contracts:** `sprite_postprocess.extract_sprites` takes a numpy RGB array, a matte color (sourced from the **Aesthetic** primary color in `brand.py`), and grid dimensions. None of this is domain language; all of it is caller knowledge.
- **Deceptive naming:** `asset_realization.py` is a facade over a class; `sprite_postprocess.py` is a bag of pure functions; `rmbg.py` is a serious algorithm with no domain vocabulary.
- **Leaky seam:** `asset_realization` imports `pixelsnap`, `sprite_postprocess`, and `MaterializeVibemon`; `materialize_vibemon` imports `sprite_postprocess`; `sprite_postprocess` imports `pixelsnap` and `rmbg`. The image pipeline is criss-crossed rather than layered.
- Callers don't distinguish three genuinely different operations: generate a new reference (genai), reprocess a stored reference (chroma/cleanup), remanifest a sheet from a stored reference.

## Solution

One deep Lifecycle realization module whose public interface is the transitions themselves:

- `christen(vibemon)` — finalize name and preview presentation
- `manifest(vibemon)` — produce full battle/presentation **Assets** (sheet, **Poses**, cry)
- plus the small number of genuinely distinct re-entry operations (reprocess display, remanifest) named explicitly

The ~900 LOC image pipeline (`rmbg`, `pixelsnap`, `sprite_postprocess`) becomes private implementation — callers never see numpy arrays, mattes, or grid dimensions. Ordering invariants (christen-before-manifest) are enforced inside the module via the **Transition Policy**, not by caller discipline.

This is the largest depth win available: the biggest implementation in the codebase behind a two-verb interface.

## Benefits

- **Depth/leverage:** ~1,400 LOC of behaviour behind a handful of transition verbs.
- **Locality:** sprite bugs, matte handling, palette snapping all concentrate in one place; the **Pixelsnap asset convention** has one home.
- **Tests:** tests exercise transitions (did christen produce a name + preview? did manifest produce the expected **Asset Kinds**?), not PNG plumbing. Pure-function tests for `rmbg`/`postprocess` can remain as implementation tests, but the interface tests stop needing fixture archaeology.

## Notes / dependencies

- **Do together with plan 04** (fake `VibemonAssetGenerator` adapter) — that's what makes the deepened module testable offline.
- Interior layering suggestion: facade → generation (genai adapter) → pipeline (pure image steps) → storage (Monstore writes). Decide exact shape in grilling.
- No ADR conflicts.
