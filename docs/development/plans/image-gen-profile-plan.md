# Image Generation Profile Plan

Per-asset control of **model**, **resolution**, and **aspect ratio** for every Gemini image call — static game art, style bibles, and per-Vibemon monstore sprites. Replaces the global `2K` default in `GeminiImageAgent` and the env-only `VIBEMON_GENAI__IMAGE` selector for mon generation, so cost and model lane are version-controlled in `.mdc` frontmatter (DESIGN §5.1).

Primary migration target: **`gemini-3.1-flash-image`** (GA replacement for `gemini-2.5-flash-image`, which retires **2026-10-02**).

---

## Problem

Two prompt systems exist today; neither passes resolution or aspect ratio to the image client.

| System | Location | Model source | Resolution / aspect |
| :--- | :--- | :--- | :--- |
| Static game assets | `vibemon/frontend/asset-prompts/game/*.mdc` | Frontmatter `model:` | **None** — client hardcodes `2K` / `1:1` |
| Mon / trainer GenAI | `vibemon/backend/app/genai/prompts/*.mdc` | `VIBEMON_GENAI__IMAGE` env | **None** — same hardcoded default |

```python
# vibemon/backend/app/genai/google.py — today every call unless overridden
builtin_tools=[pydantic_ai.ImageGenerationTool(size="2K", aspect_ratio="1:1")]
```

Static assets pass only `record.model` via `generate_static_assets.py`. Mon generation (`VibemonAssetGenerator`) never passes `builtin_tools`. On **2.5-flash**, `2K` is ignored (1K cap, $0.039 flat). On **3.1-flash**, `2K` is honored ($0.101/image) — a silent **+159%** cost vs 1K references with no benefit after pixelsnap.

Mons have **no per-species `.mdc` provenance** — only shared templates plus whatever env default was live at christen time.

---

## Goal

1. Every image-generating prompt record declares `model`, `resolution`, and `aspect_ratio` in YAML frontmatter.
2. The image client receives that profile on **every** call (static script, mon pipeline, trainer regenerate).
3. Style bibles and static art are re-approved on the new model lane before bulk mon remanifest.
4. Full inventory QA covers **every sprite surface** in the product.

---

## Target schema

Add to all **image-generating** `.mdc` frontmatter:

```yaml
---
model: gemini-3.1-flash-image
resolution: 1K          # 512 | 1K | 2K | 4K  (uppercase K required by Gemini API)
aspect_ratio: "1:1"     # Gemini imageConfig values: 1:1, 16:9, 9:16, …
---
```

### Recommended profiles (locked defaults)

| Asset class | Model | Resolution | Aspect | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Style bibles (trainer, hatchling) | `gemini-3.1-flash-image` | **1K** | **1:1** | Display snaps to 128px long edge |
| Gear sprites | 3.1-flash | **1K** | **1:1** | Left/right poses derived — no extra gen |
| Gear HUD icons | 3.1-flash | **1K** | **1:1** | Snaps to 96px grid |
| Scene backgrounds | 3.1-flash | **1K** | **16:9** | Matches 320×180 scene layer |
| Mon reference | 3.1-flash | **1K** | **1:1** | Model input + showcase; snaps 384/128 |
| Mon sprite sheet | 3.1-flash | **2K** | **1:1** | Nine-cell grid needs native room — **only** sheet uses 2K |
| Per-trainer reference | 3.1-flash | **1K** | **1:1** | `trainer-reference.mdc` |

**Decision point (before full background regen):** keep `gemini-3-pro-image` for hero bases (`title.png`, `hatch.png`) if 3.1-flash loses painterly depth; all variants can follow their base's model.

`VIBEMON_GENAI__IMAGE` remains a **migration fallback** when frontmatter omits fields; remove fallback once all templates migrated. Fix `.env.example` — it currently lists `gemini-2.0-flash`, which is not an image model.

---

## Pricing reference (Google API, standard tier)

| Model | 1K | 2K |
| :--- | ---: | ---: |
| `gemini-2.5-flash-image` | $0.039 | *(1K only)* |
| `gemini-3.1-flash-image` | $0.067 | $0.101 |
| `gemini-3-pro-image` | $0.134 | $0.134 |

Batch API ≈ 50% off. Positions extracted from sheets, pose mirroring, and `@128` / `@96` derivatives incur **no** API cost.

---

## Implementation

### Phase 0 — Plumbing

**Files:** `app/genai/google.py`, `app/genai/static_assets.py`, `app/genai/prompts.py`, `app/genai/vibemon_assets.py`, `scripts/generate_static_assets.py`, tests.

1. Add frozen `ImageGenProfile(model, resolution, aspect_ratio)` dataclass.
2. `GeminiImageAgent.run(..., profile: ImageGenProfile | None)` — build `ImageGenerationTool` from profile; **remove** blind `2K` default (fallback: env-derived profile at **1K** during migration, not 2K).
3. Extend `AssetPromptRecord` + `parse_asset_prompt()` with `resolution`, `aspect_ratio` (optional initially, required after Phase 1).
4. Extend `RenderedPrompt` — parse image profile from backend template frontmatter.
5. `VibemonAssetGenerator` — pass profile from `prompts.render(...)` into `generate_reference_image`, `generate_sprite_sheet_image`, `generate_trainer_reference`.
6. `generate_static_assets._generate_raw_image` — pass profile from record.
7. Manifest rows — add `resolution`, `aspect_ratio` to `manifest.json`.
8. Tests in `test_static_assets.py` + one test that image call receives correct `ImageGenerationTool` args.

### Phase 1 — Static `.mdc` migration

Update all **27** records under `vibemon/frontend/asset-prompts/game/` (28 after adding missing camera icon). Set recommended profiles above; bump `generated:`; set `status: draft` until re-approved.

**Fix frontmatter ↔ disk path drift:**

| `.mdc` | Frontmatter `asset:` | On disk |
| :--- | :--- | :--- |
| `backgrounds/crew-showcase.mdc` | `crew-showcase--day.png` | `crew-showcase.png` |
| `backgrounds/hatch.mdc` | `hatch--dawn.png` | `hatch.png` |
| `backgrounds/title.mdc` | `title--day.png` | `title.png` |

**Gap:** `static/game/icons/camera.png` exists; add `icons/camera.mdc` (mirror `vibe-deck` pattern: `reference_asset`, `depends_on`).

Document schema in `docs/development/ASSET-PROMPTS.md` (referenced from DESIGN §5.1).

### Phase 2 — Backend prompt migration

| Template | Image gen? | Profile |
| :--- | :--- | :--- |
| `sprite-reference.mdc` | Yes | 1K / 1:1 / 3.1-flash |
| `sprite-sheet.mdc` | Yes | **2K** / 1:1 / 3.1-flash |
| `trainer-reference.mdc` | Yes | 1K / 1:1 / 3.1-flash |
| `species-name.mdc` | No (text) | — |
| `battle-cry.mdc` | No (ElevenLabs) | — |
| `sprite-facing.mdc` | No (text vision) | — |

### Phase 3 — Mon provenance (older assets)

Per-species `.mdc` files are not scalable (identity is data-driven). Instead:

1. At christen/manifest, persist on `Vibemon.aesthetic` (or small JSON column):

   ```json
   {
     "reference": {
       "model": "gemini-3.1-flash-image",
       "resolution": "1K",
       "aspect_ratio": "1:1",
       "prompt": "sprite-reference.mdc",
       "prompt_version": "1.5.0"
     },
     "sheet": { "resolution": "2K", ... }
   }
   ```

2. `manifest_vibemon.py --regenerate` uses **current** template profile (remanifest = new model lane by design).
3. Existing mons keep old blobs until regenerated; backfill provenance as `"unknown"` or env-at-birth unless remanifested.

### Phase 4 — Style bible sync

`app/genai/style_bible.py` reads `trainer.png` from static and bundled `hatchling-silhouette.png`. After regen:

1. Regenerate via updated `trainer.mdc` + `hatchling-silhouette.mdc`.
2. Pixelsnap → `trainer@128.png`, `hatchling-silhouette@128.png`.
3. Sync hatchling canonical PNG into `backend/app/genai/style_bible/` (or refactor to always read static — follow-up).

**Gate:** no mon QA until style bibles pass — every `generate_reference_image` attaches both.

---

## Complete asset inventory

### A. Static sprites (`static/game/sprites/`) — 13 files, 5 image gen

| File | Source | `.mdc` | Runtime |
| :--- | :--- | :--- | :--- |
| `trainer.png` | Gen | `sprites/trainer.mdc` | Style bible; bootstrap seed |
| `trainer@128.png` | Derived (pixelsnap) | — | Register, crew formation default |
| `hatchling-silhouette.png` | Gen | `sprites/hatchling-silhouette.mdc` | Style bible |
| `hatchling-silhouette@128.png` | Derived | — | Placeholder: battle, crew, hatch, title |
| `camera.png` | Gen | `sprites/camera.mdc` | Trainer upload UI |
| `camera-left/right.png` | Derived (`derive_poses`) | — | `TrainerReferenceCamera` |
| `vibe-deck.png` | Gen | `sprites/vibe-deck.mdc` | Gear reference |
| `vibe-deck-left/right.png` | Derived | — | Future overworld |
| `vibe-cart.png` | Gen | `sprites/vibe-cart.mdc` | Gear reference |
| `vibe-cart-left/right.png` | Derived | — | — |

### B. Static icons (`static/game/icons/`) — 4 files, 3 image gen (after camera icon added)

| File | Source | `.mdc` | Runtime |
| :--- | :--- | :--- | :--- |
| `vibe-deck.png` | Gen | `icons/vibe-deck.mdc` | Source for `@96` |
| `vibe-deck@96.png` | Derived (trim/snap) | — | `CrewNavButton` |
| `vibe-cart.png` | Gen | `icons/vibe-cart.mdc` | — |
| `camera.png` | Gen (to add) | **missing** | — |

### C. Scene backgrounds — 20 PNGs, 20 `.mdc`s, all gen

| Scene | Variants |
| :--- | :--- |
| title | `title.png`, `--dawn`, `--dusk`, `--night` |
| hatch | `hatch.png`, `--day`, `--dusk`, `--night` |
| register | `register.png`, `--day`, `--dusk`, `--night` |
| crew-showcase | `crew-showcase.png`, `--dawn`, `--dusk`, `--night` |
| battle | `battle.png`, `--dawn`, `--dusk`, `--night` |

Consumed via `sceneBackgroundSrc()` on `/`, `/hatch`, `/register`, `/crew/*`, `/battle/*`, `/encounters`.

### D. Per-Vibemon monstore — 2 image gen calls per mon

| Blob | Source | Primary QA surface |
| :--- | :--- | :--- |
| `sprite/reference-raw.png` | Gen (`sprite-reference.mdc`) | Not shown directly |
| `sprite/reference.png` | Postprocess | Title grass, hatch reveal, crew fallback, battle fallback |
| `sprite/sheet.png` | Gen (`sprite-sheet.mdc`) | Grid source for 9 poses |
| `pose/battle-back.png` | Extract R1C1 | Battle **player** |
| `pose/battle-opponent.png` | Extract R1C3 | Battle **opponent** |
| `pose/battle-hero.png` | Extract R1C2 | Crew `sprite_url` (preferred) |
| `pose/emote-happy.png` | Extract R2C2 | Move-learn modal |
| `pose/emote-resting.png` | Extract R2C1 | Required at manifest; no UI yet |
| `pose/emote-frustrated.png` | Extract R2C3 | Required at manifest; no UI yet |
| `pose/emote-proud.png` | Extract R3C1 | Required at manifest; no UI yet |
| `pose/emote-confused.png` | Extract R3C2 | Required at manifest; no UI yet |
| `pose/emote-sad.png` | Extract R3C3 | Required at manifest; no UI yet |

Pose grid ↔ `PoseT` ↔ `sprite-sheet.mdc` cell labels (R1C1…R3C3) ↔ `extract_sprites()` — fixed contract; QA must verify no row/column swap.

Battle cry (`audio/cry-battle.mp3`) is ElevenLabs — out of scope.

### E. Per-trainer monstore

| Blob | Gen? | Surface |
| :--- | :--- | :--- |
| `REFERENCE_RAW` | Gen (`trainer-reference.mdc` + likeness) | — |
| `REFERENCE` | Postprocess | Register, crew when logged in |

Regenerated per trainer via `generate_trainer.py --regenerate` — not part of bulk static/mon regen unless explicitly run.

---

## Manual QA sequence (before full regen)

Each step gates the next. Costs assume 3.1-flash standard tier.

### Step 1 — Style bibles (~$0.13)

| Asset | Calls |
| :--- | ---: |
| `trainer.png` → `@128` | 1 |
| `hatchling-silhouette.png` → `@128` | 1 |

**Check:** outline weight vs `base-style.md`; `/register` default trainer; placeholder `@128` crisp at integer scale.

### Step 2 — Pilot mon (~$0.17)

One manifested mon: `manifest_vibemon.py --vibemon <uuid> --regenerate`

| Output | Route |
| :--- | :--- |
| `reference` | `/` title (if in pool), `/crew` |
| `battle-back` / `battle-opponent` | `/battle/<id>` |
| `battle-hero` | Crew formation / roster |
| `emote-happy` | Move-learn after level-up |
| All 9 poses + sheet | Visual grid review; chroma matte; snap profiles (192 battle / 384 emote) |

### Step 3 — Gear triad (~$0.34)

5 gen calls: camera, vibe-deck, vibe-cart sprites + vibe-deck + vibe-cart icons (+ camera icon once added). Run `derive_poses` after each canonical sprite.

**Check:** `/register` camera; crew nav `vibe-deck@96` aspect; styleguide specimens if present.

### Step 4 — Background spot-check (~$0.40)

6 gen calls — one base per scene: `hatch`, `register`, `title`, `crew-showcase`, `battle`, plus one phase variant (e.g. `title--night`).

**Check:** HUD contrast zones per prompt; `/`, `/hatch`, `/register`, `/crew`, `/battle`, `/encounters`.

### Step 5 — Sign-off

Only after Steps 1–4 pass:

```bash
# Full static (including approved)
uv run --project vibemon/backend python scripts/generate_static_assets.py --include-approved

# Bulk mon remanifest (batched)
uv run --project vibemon/backend python scripts/manifest_vibemon.py --regenerate --limit N
```

---

## Full regenerate cost estimate

### Static — 28 image API calls (after camera icon)

| Bucket | Count | Profile | Cost |
| :--- | ---: | :--- | ---: |
| Backgrounds | 20 | 3.1-flash 1K 16:9 | $1.34 |
| Sprites | 5 | 3.1-flash 1K 1:1 | $0.34 |
| Icons | 3 | 3.1-flash 1K 1:1 | $0.20 |
| **Static total** | **28** | | **≈ $1.88** |

vs today's mix (20× 3-pro + 7× 3-pro + 1× 2.5): **≈ $3.66** (~49% savings at 3.1-flash 1K).

Derived (free): 6 gear pose pairs, 2× `@128`, 1× `@96`.

### Per mon — 2 calls

| Step | Cost |
| :--- | ---: |
| Reference (1K) | $0.067 |
| Sheet (2K) | $0.101 |
| **Per mon** | **$0.168** |

| Mons | Remanifest |
| ---: | ---: |
| 10 | $1.68 |
| 25 | $4.20 |
| 50 | $8.40 |
| 100 | $16.80 |

### Combined examples

| Scope | ≈ Cost |
| :--- | ---: |
| Pilot QA (Steps 1–4) | $1.04 |
| Full static regen | $1.88 |
| Static + 25 mons | $6.08 |
| Static + 50 mons | $10.28 |
| Static + 100 mons | $18.68 |

Per-trainer `--regenerate`: +$0.067 each (not in totals above).

---

## QA checklist — every sprite surface

Sign-off matrix after full regen. For **each mon** in the wild pool, rows marked **mon** repeat.

| # | Surface | Route / trigger | Asset | Type |
| ---: | :--- | :--- | :--- | :--- |
| 1 | Title background | `/` | `backgrounds/title*` | static |
| 2 | Title grass mons ×4 | `/` | mon `reference` | mon |
| 3 | Hatch background | `/hatch` | `backgrounds/hatch*` | static |
| 4 | Hatch placeholder | pre-reveal | `hatchling-silhouette@128` | static |
| 5 | Hatch candidate | post-reveal | mon `reference` | mon |
| 6 | Register background | `/register` | `backgrounds/register*` | static |
| 7 | Trainer default | register, no upload | `trainer@128` | static |
| 8 | Trainer uploaded | after onboarding | monstore `REFERENCE` | trainer |
| 9 | Camera gear | register upload | `camera-left` | static |
| 10 | Crew showcase bg | `/crew` | `backgrounds/crew-showcase*` | static |
| 11 | Crew roster empty | empty slot | `hatchling-silhouette@128` | static |
| 12 | Crew roster filled | member card | mon REFERENCE/hero | mon |
| 13 | Crew formation trainer | formation scene | trainer monstore or `@128` | both |
| 14 | Crew formation mon | clock ring | mon REFERENCE/hero | mon |
| 15 | Crew nav icon | nav button | `vibe-deck@96` | static |
| 16 | Battle background | `/battle/*` | `backgrounds/battle*` | static |
| 17 | Battle player | in fight | `pose/battle-back` | mon |
| 18 | Battle wild | in fight | `pose/battle-opponent` | mon |
| 19 | Move-learn emote | level-up offer | `pose/emote-happy` | mon |
| 20 | Encounters bg | `/encounters` | `battle*` bg | static |
| 21 | Emote resting | manifest QA | `pose/emote-resting` | mon |
| 22 | Emote frustrated | manifest QA | `pose/emote-frustrated` | mon |
| 23 | Emote proud | manifest QA | `pose/emote-proud` | mon |
| 24 | Emote confused | manifest QA | `pose/emote-confused` | mon |
| 25 | Emote sad | manifest QA | `pose/emote-sad` | mon |
| 26 | Gear vibe-deck | asset review | `sprites/vibe-deck.png` | static |
| 27 | Gear vibe-cart | asset review | `sprites/vibe-cart.png` | static |
| 28 | Gear camera | asset review | `sprites/camera.png` | static |
| 29 | Icon vibe-deck | HUD | `icons/vibe-deck.png` | static |
| 30 | Icon vibe-cart | HUD | `icons/vibe-cart.png` | static |
| 31 | Icon camera | HUD | `icons/camera.png` | static |
| 32 | Sheet grid | manifest QA | `sprite/sheet.png` | mon |

---

## PR sequence

| PR | Scope | Exit criteria |
| :--- | :--- | :--- |
| **1** | Phase 0 plumbing | Tests green; profile injected when frontmatter present; default 1K not 2K |
| **2** | Phase 1 static `.mdc` + path fixes + camera icon mdc | All frontmatter valid; pilot regen trainer + hatchling only |
| **3** | Phase 2 backend prompts + Phase 3 mon provenance JSON | Pilot mon regenerate uses template profile; provenance persisted |
| **4** | Pilot QA (Steps 2–4) | Sign-off notes in PR |
| **5** | Full static `--include-approved` | PNGs committed; `status: approved` updated |
| **6** | Bulk `manifest_vibemon.py --regenerate` | Batched with `--limit`; QA checklist complete |

---

## Risks and open decisions

1. **Background model split** — all 3.1-flash 1K vs hero bases on 3-pro. Decide at Step 4 spot-check.
2. **Sheet must stay 2K** — 1K nine-cell sheets fail `validate_sprite_sheet` more often; do not downgrade.
3. **Frontmatter path drift** — fix in PR 2 before any regen or outputs land wrong.
4. **Hatchling dual path** — bundled copy under `genai/style_bible/` vs static; sync after every hatchling regen until refactored.
5. **2.5-flash retirement** — `trainer.mdc` is the only static record still on 2.5; migrate with style bible Step 1.

---

## Key code references

| Area | Path |
| :--- | :--- |
| Image client (hardcoded 2K) | `vibemon/backend/app/genai/google.py` |
| Static prompt parse | `vibemon/backend/app/genai/static_assets.py` |
| Static regen script | `vibemon/backend/scripts/generate_static_assets.py` |
| Mon image gen | `vibemon/backend/app/genai/vibemon_assets.py` |
| Mon manifest / regenerate | `vibemon/backend/app/workflows/materialize_vibemon.py`, `scripts/manifest_vibemon.py` |
| Pose extract grid | `vibemon/backend/app/workflows/sprite_postprocess.py` |
| Battle sprite resolver | `vibemon/backend/app/http/battle_read.py::_sprite_url` |
| Style bible loaders | `vibemon/backend/app/genai/style_bible.py` |
| Snap profiles | `vibemon/backend/app/domains/sprite/const.py` |
| Frontend asset prompts | `vibemon/frontend/asset-prompts/game/` |
| Backend gen prompts | `vibemon/backend/app/genai/prompts/` |
