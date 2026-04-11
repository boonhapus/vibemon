# P3-T3 — VibemonRenderer Component & Animations

**Phase:** 3 — Visual Rendering
**Dependencies:** P3-T1, P3-T2
**Depends on this:** P4-T1

---

## Objective

Assemble the full SVG rendering pipeline into a Svelte 5 component and add idle animations (float and glow pulse).

## Tasks

1. **Create `frontend/src/lib/components/VibemonRenderer.svelte`**
   - Props via `$props()`: `dna: VisualDNA`, `seed: number`, `uid: string`, `flipped: boolean = false`
   - Reactive derivations via `$derived()`:
     - `hullPoints` from `generateHullPoints(dna, seed)`
     - `bodyPath` from `smoothClosedPath(hullPoints)`
     - `limbs` from `generateLimbs(...)`
     - `eyes` from `generateEyes(...)`
     - `mouth` from `generateMouth(...)`
   - HSL helper: `hsl([h, s, l])` → CSS `hsl(...)` string

2. **Assemble the SVG**
   - ViewBox `0 0 200 220`
   - CSS custom properties: `--cp`, `--cs`, `--ca`, `--ce`, `--ow` from VisualDNA
   - `transform: scaleX(-1)` when `flipped`
   - `transform: scale(dna.sizeScale)`
   - Layer order: glow filter defs → texture pattern defs → limbs (behind) → body path → texture overlay → eyes → mouth

3. **Add glow filter**
   - SVG `<filter>` with `<feGaussianBlur>` driven by `dna.glowIntensity × 6`
   - Unique filter ID using `uid` to prevent collisions when two Vibemons are on screen

4. **Implement idle float animation**
   - CSS `@keyframes float`: translateY ±6px
   - Period driven by `dna.animationSpeed` seconds
   - `ease-in-out infinite alternate`

5. **Implement glow pulse animation**
   - CSS `@keyframes` on the filter's `stdDeviation`
   - Period = `animationSpeed × 1.5` seconds

6. **Update the battle page to render both Vibemons**
   - Replace the raw JSON display with two `<VibemonRenderer>` instances
   - Player on the left (normal), enemy on the right (`flipped={true}`)
   - Display name and element type above each

7. **Test with varied VisualDNA**
   - Manually test with high-attack (spiky), high-defense (round), cyclops, dual-limbed variations
   - Verify the two creatures look visually distinct

## Acceptance Criteria

- Two animated, visually distinct blob creatures render side-by-side on `/battle`
- Enemy is mirrored horizontally
- Idle float animation runs smoothly
- Same seed + same VisualDNA always produces identical visual output

## Files Created

```
frontend/src/lib/components/VibemonRenderer.svelte
```

## Files Modified

```
frontend/src/routes/battle/+page.svelte
```
