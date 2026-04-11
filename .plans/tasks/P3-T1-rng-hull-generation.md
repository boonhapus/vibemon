# P3-T1 — Seeded RNG & Blob Hull Generation

**Phase:** 3 — Visual Rendering
**Dependencies:** P1-T7 (frontend exists)
**Depends on this:** P3-T2, P3-T3

---

## Objective

Implement the deterministic client-side RNG and the core blob shape generation algorithm that creates the creature's body silhouette from VisualDNA parameters.

## Important

Use **Svelte 5 syntax only**: `$state()`, `$derived()`, `$props()`.

## Tasks

1. **Create `frontend/src/lib/utils/seededRandom.ts`**
   - Implement Mulberry32 PRNG: takes a seed integer, returns a `() => number` function producing values in [0, 1)
   - Must be fully deterministic: same seed → same sequence

2. **Create `frontend/src/lib/utils/blobRenderer.ts`**

3. **Implement `generateHullPoints(dna: VisualDNA, seed: number): Point[]`**
   - Base radius = 75px in a 200×220 viewBox centred at (100, 110)
   - For each of `dna.nPoints` control points:
     - Base angle evenly distributed around the circle
     - Angle jitter: `(rng() - 0.5) × (π / nPoints) × 0.6`
     - Radius: `BASE_RADIUS × (1 - spikiness/2 + rng() × spikiness)`
   - Return array of `{x, y}` points

4. **Implement `smoothClosedPath(pts: Point[]): string`**
   - Catmull-Rom → Cubic Bézier conversion for a smooth closed SVG path
   - Control points: `cp1 = p1 + (p2 - p0) / 6`, `cp2 = p2 - (p3 - p1) / 6`
   - Wrap indices cyclically
   - Return SVG path string starting with `M` and ending with `Z`

5. **Write unit tests**
   - Same seed + same VisualDNA → identical hull points
   - Different seeds → different hull points
   - `smoothClosedPath` produces valid SVG path string with correct number of `C` commands
   - Hull points stay within the 200×220 viewBox for all spikiness values

## Acceptance Criteria

- `seededRandom(42)()` always returns the same number
- `generateHullPoints` produces `nPoints` points inside the viewBox
- `smoothClosedPath` returns a valid, closed SVG path

## Files Created

```
frontend/src/lib/utils/seededRandom.ts
frontend/src/lib/utils/blobRenderer.ts
frontend/src/lib/types.ts  (add Point type if not present)
tests/blobRenderer.test.ts
```
