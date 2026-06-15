# Provider intensity means rarity, and seeds evolution

**Status:** accepted

## Context

Every provider returns an `Affinity.intensity` in `[0, 1]`. It was used only as a *merge weight* in `Affinity.merge` (`weight = int(intensity * 100)`), deciding which provider dominates the blended stats, typing, and moves. But the four implemented providers each computed intensity to mean something different:

- **celestial** — true rarity (angular bodies + eclipse season + tight aspects + lunation extremes).
- **climate** — a 0.5-centered weather anomaly; a record-*cold* day scored *low*, and only hot/stormy days climbed.
- **music** — recency momentum (recent vs. baseline play pace), not rarity at all.
- **biome** — a hard-coded constant `0.5`.

Because the numbers shared a scale but not a meaning, combining them in merge compared apples to oranges, and intensity could not honestly answer "how rare is this birth?" Separately, the metric was *not* wired into the evolution seed: `Affinity.merge` drew `evo_seed` from a fixed `[24, 41, 34, 1]` distribution regardless of intensity, so BST (which follows `evo_seed` via `BST_SCALING_MATRIX`) carried no rarity signal either.

The product intent: **a high intensity should mean a rare birth, and rarity should fuel a stronger evolution line and BST.**

## Decision

**1. One shared definition.** Intensity is *calibrated rarity*: monotonic, in `[0, 1]`, with a soft floor around `0.2–0.3` (a common reading), climbing toward `1.0` for genuinely rare readings. There is **no** special "0.5 = typical" anchor — rarity is one-directional, not centered. celestial already behaved this way and is the reference shape (categorical base + additive bonuses for rare conditions).

Per-provider implementations (`provider.calculate_intensity`):

- **celestial** — unchanged (reference model); trimmed a dead `max(..., 0.0)`.
- **climate** — symmetric tail distance against the fetched ~6-week window. Temperature is two-tailed (record cold is as rare as record heat); precipitation, wind, CAPE, and low-visibility are one-tailed (only their intense excess is rare; a calm/dry/clear day is common). Aggregate tail distance → shifted sigmoid, so a typical day lands on the `~0.30` floor.
- **music** — replaced momentum with *sonic-palette distinctiveness*: RMS distance of the play-weighted audio-feature profile from the median listener (`Signal.center == 0.5`), over a fixed palette feature set, through a shifted sigmoid. No new API calls; `synthesize` stays pure.
- **biome** — replaced the constant with a per-land-cover rarity base (approximating global land-area share) plus additive bonuses for high altitude and water adjacency, clamped — celestial's shape.

**2. Rarity seeds evolution.** `EvolutionStageT.random_seed` gains an `intensity` parameter and applies an exponential tilt on each line's strength rank (`_EVO_SEED_RARITY_TILT = 0.6`). At `intensity = 0.5` the draw reproduces the historical `[24, 41, 34, 1]` distribution exactly (zero behavior change at neutral); higher rarity shifts mass to the longer/stronger lines (STAGE_3, PSEUDO_LEGENDARY), lower rarity concentrates on BASE. `Affinity.merge` computes a **merged rarity** — the intensity-weighted mean of contributing providers' intensities (the same weights it already uses for stat blending) — and passes it in. BST follows automatically through the existing `apply_evo_seed_bst_bias` / `BST_SCALING_MATRIX`.

Resulting evolution-line distribution:

| intensity | BASE | STAGE_2 | STAGE_3 | PSEUDO |
| :--- | :--- | :--- | :--- | :--- |
| 0.0 (common) | 0.42 | 0.39 | 0.18 | 0.003 |
| 0.5 (neutral) | 0.24 | 0.41 | 0.34 | 0.010 |
| 1.0 (rare) | 0.11 | 0.34 | 0.52 | 0.028 |

## Considered alternatives

- **Pure rarity with a true `0.0` floor.** Cleaner semantically, but a mundane all-providers birth yields near-zero merge weights and risks the `ZeroDivisionError` path in `Affinity.merge`. Rejected in favor of a soft floor (matches celestial, keeps merge weights non-degenerate).
- **Keep climate's 0.5-centered anomaly, fix only symmetry.** Rejected — it does not actually mean rarity; a record-cold day still sits far from "intense."
- **Music via global artist obscurity.** Truest to "rare taste," but requires new fetch-time API calls per artist and a payload-schema change. Deferred; audio-profile extremity uses already-captured data and keeps `synthesize` pure.
- **Music via genre/tag eclecticism (entropy).** Conflates "diverse" with "rare"; a niche mono-genre listener would score low. Rejected.
- **Merge rarity as max (not weighted mean) of provider intensities.** Too swingy when one provider maxes easily; the weighted mean still lets a single extraordinary signal lift the birth without letting it dominate outright.

## Consequences

- RNG-derived `evo_seed` (and therefore BST) for **new** births changes vs. the old fixed distribution, except at exactly `intensity = 0.5`. Pre-launch, so acceptable; existing `BirthSnapshot` payloads remain replayable.
- The merged-rarity → evolution-line mapping assumes the four providers share a calibrated scale. The mappings are calibrated by construction, **not** validated against a real birth distribution. Run the `provider-balance-analysis` skill on sampled births before relying on a given intensity meaning the same "rare" across providers.
- `_EVO_SEED_RARITY_TILT` (in `app/domains/vibemon/types.py`) is the single dial for how strongly rarity bends evolution; the tilt is deliberately gentle (even a maxed birth is only ~2.8% pseudo-legendary).
- Deferred: replacing music's distinctiveness proxy with true global artist obscurity, if/when fetch gains listener-count data.
