# P1-T5 — Visual DNA Generation & Name Generator

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T2, P1-T4
**Depends on this:** P1-T6

---

## Objective

Build the backend logic that converts merged `SourceData` and computed `VibemonStats` into a `VisualDNA` object and a procedural name. These drive all frontend rendering.

## Tasks

1. **Create `backend/app/engine/visual.py`**

2. **Implement `generate_visual_dna(merged, stats, seed) -> VisualDNA`**
   Apply the stat → visual parameter mapping table from the design doc:
   - `n_points` = `8 + floor(speed / 255 × 4)`
   - `spikiness` = `0.1 + (attack / 255) × 0.5`
   - `limb_count` = HP thresholds: <85 → 0, 85–170 → 1, >170 → 2
   - `limb_style` = speed > defense → "wing"/"elongated", else "stubby"
   - `eye_count` = sp_attack > 170 → 1 (cyclops), else 2
   - `eye_size` = `0.04 + (sp_defense / 255) × 0.08`
   - `eye_shape` = element lookup table
   - `mouth_style` = attack thresholds
   - `texture_pattern` = defense thresholds
   - `outline_weight`, `glow_intensity`, `size_scale`, `animation_speed` from formulas

3. **Implement `generate_palette(merged, stats, rng) -> tuple`**
   - Base hue from `merged.hue_primary` or `ELEMENT_BASE_HUES[element]`
   - ±15° seeded jitter
   - Saturation from sp_attack
   - Secondary hue = analogous (+30°), accent = near-complementary (+180°)
   - Eye colour always high-saturation accent
   - Define `ELEMENT_BASE_HUES` dict for all 9 elements

4. **Create `backend/app/engine/names.py`**
   - Define `SYLLABLES` dict with ~40 syllables per element (all 9 elements)
   - `generate_name(element, seed) -> str`
   - Pick 2–3 syllables using seeded RNG, capitalise, join
   - Ensure names are pronounceable (no triple consonant clusters)

5. **Write tests**
   - VisualDNA parameter ranges are within spec for edge-case stats (all 1s, all 255s, mixed)
   - Palette hues are in [0, 360), saturation/lightness in [0, 1]
   - Name generator is deterministic and produces 2–3 syllable names
   - Eye shape matches element lookup for each of the 9 elements

## Acceptance Criteria

- `generate_visual_dna` returns a valid `VisualDNA` for any legal `VibemonStats`
- All visual parameters fall within their documented ranges
- Names are deterministic, readable, and 4–10 characters long

## Files Created

```
backend/app/engine/
  visual.py
  names.py
tests/
  test_visual.py
  test_names.py
```
