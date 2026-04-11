# P3-T2 — Limbs, Eyes, Mouth & Texture Rendering

**Phase:** 3 — Visual Rendering
**Dependencies:** P3-T1
**Depends on this:** P3-T3

---

## Objective

Extend the blob renderer with limb extrusion, facial features, and texture overlays so each creature has distinct visual character driven by its stats.

## Tasks

1. **Implement limb generation in `blobRenderer.ts`**
   - `generateLimbs(hullPoints, dna, rng)` → array of SVG path strings
   - Select hull points in the lower-lateral region (bottom 40%, left/right sides)
   - Limb styles:
     - `"stubby"` — small sub-blob at 60% parent radius
     - `"elongated"` — tapered ellipse extending 1.5× body radius outward
     - `"wing"` — mirrored curved path pair with reduced opacity (0.6)
   - Limb count from `dna.limbCount` (0, 1, or 2)

2. **Implement eye rendering**
   - `generateEyes(hullPoints, dna, rng)` → SVG elements (as string or structured data)
   - Anchor position: centroid of the topmost 20% of hull points
   - Two eyes offset by `±eyeSize × radius`; cyclops centred
   - Eye shapes (SVG path templates):
     - `"circle"` — `<circle>`
     - `"slit"` — narrow vertical ellipse
     - `"diamond"` — rotated square path
     - `"compound"` — cluster of 3 small circles

3. **Implement mouth rendering**
   - `generateMouth(hullPoints, dna)` → SVG path string or null
   - Anchor: bottom-centre of hull
   - Styles:
     - `"none"` — return null
     - `"line"` — simple horizontal arc
     - `"open"` — open ellipse
     - `"fanged"` — open with two triangular fangs

4. **Implement texture overlay**
   - `generateTexture(dna)` → SVG `<pattern>` element definition
   - Patterns at 15–25% opacity over the body path:
     - `"none"` — no pattern
     - `"dots"` — scattered small circles
     - `"stripes"` — diagonal lines
     - `"scales"` — overlapping arcs
     - `"cracks"` — jagged line network
   - Pattern applied via `fill="url(#texture-{uid})"`

5. **Write visual regression tests**
   - Snapshot SVG output for known VisualDNA inputs
   - Verify limb count matches `dna.limbCount`
   - Verify eye count matches `dna.eyeCount`

## Acceptance Criteria

- A Vibemon with `limbCount=2, eyeCount=2, mouthStyle="fanged", texturePattern="scales"` renders all features
- A Vibemon with `limbCount=0, eyeCount=1, mouthStyle="none", texturePattern="none"` renders a clean cyclops blob
- All SVG output is valid and renderable

## Files Modified

```
frontend/src/lib/utils/blobRenderer.ts
```
