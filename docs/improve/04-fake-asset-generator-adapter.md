# 04 — VibemonAssetGenerator: turn hypothetical seam real with a fake adapter

**Status:** implemented — `app/genai/fake_assets.py`, selected via `genai.fake_assets` (`VIBEMON_GENAI__FAKE_ASSETS=1`)
**Priority:** highest (do with 02; cheap)
**Vocabulary:** module / interface / seam / adapter / depth / locality per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/workflows/materialize_vibemon.py` — defines the `VibemonAssetGenerator` protocol (name generation, reference image, sprite sheet, cry)
- `vibemon/backend/app/genai/vibemon_assets.py` — sole adapter (`get_default_asset_generator()`, hard-coded Google client)

## Problem

One adapter = hypothetical seam. The protocol exists and is injected into `MaterializeVibemon`, but only the Google genai client satisfies it. Consequences:

- Tests of **Manifest** / **Christen** can't run without the real genai path or ad-hoc mocks built per-test.
- The seam is invisible to callers — nothing demonstrates that the generator is swappable, so nobody designs against the protocol; they design against the Google client's behaviour.
- The same applies to the adjacent `AssetStore` protocol (monstore wrapper, also single-adapter), worth handling in the same pass.

## Solution

Ship a deterministic fake adapter as a real second adapter (not a test-local mock):

- canned species name (seeded from vibemon id for determinism)
- solid-color or simple-pattern reference image and sprite sheet at correct dimensions/grid, using the **Aesthetic** primary color as matte so downstream `sprite_postprocess` paths still exercise
- silent or tone-burst cry

Place it where production code can also use it (e.g. `app/genai/fake_assets.py` or alongside the protocol) so scripts can run offline (`--fake-assets`), not just tests. Optionally do the same for `AssetStore` with an in-memory store.

Two adapters = real seam. Zero interface change.

## Benefits

- The whole Lifecycle realization pipeline (plan 02) becomes testable offline and fast — interface-level tests for christen/manifest without genai keys or network.
- Script frontend gets an offline mode for development.
- Cheapest item on the list: one small new adapter, no API change, immediate payoff.

## Notes / dependencies

- Pairs with plan 02; can also land standalone first (it makes 02's refactor safer by enabling tests before restructuring).
- Fake sheet must satisfy `sprite_postprocess` validation (grid dims, matte) — that constraint documents the implicit contract noted in plan 02.
- No ADR conflicts.
