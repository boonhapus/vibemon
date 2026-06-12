# Vibemon Codebase Structure

Index and high-level map of everything under `vibemon/`. This document describes **what lives where** in the current tree — not rollout plans, tuning numbers, or domain vocabulary (see [development/CONTEXT.md](development/CONTEXT.md) and [development/ARCHITECTURE.md](development/ARCHITECTURE.md) for those).

## Top level

```text
vibemon/
  backend/     Python Litestar API, domains, workflows, providers, storage
  frontend/    SvelteKit static SPA (trainer onboarding, crew UI)
  tools/         Standalone dev utilities (sprite cutout)
```

| Package | Stack | Role |
|---------|-------|------|
| `backend` | Python 3.14+, Litestar, SQLAlchemy async, pydantic-ai | Game rules, generation, persistence, HTTP API |
| `frontend` | Svelte 5, SvelteKit, Vite 8, TypeScript | Player-facing scenes and API clients |
| `tools` | Python 3.12+ (isolated venv) | Local asset-processing helpers outside the main API |

---

## Backend (`vibemon/backend/`)

Python package root is `app/`. Run via `uv run dev` (see `scripts/dev_stack.py`) or `uvicorn`. Configuration loads from `VIBEMON_*` env vars in `app/settings.py` (database, asset store, cache, API secrets, model strings).

### `app/core/`

Shared primitives with no game semantics: ID helpers (`ids.py`), time/clock (`time.py`), math (`math.py`), base Pydantic schema classes (`schema.py`), structured errors (`errors.py`), logging setup (`logging.py`), loop utilities (`loop.py`), and generic types (`types.py`).

### `app/domains/`

Game concepts and rules. Domain modules **do not** import workflows, HTTP, storage adapters, or scripts. Each package follows recurring file roles (see ARCHITECTURE.md): `types.py` (vocabulary), `entity.py` (behavior + state), `schema.py` (frozen read models), `const.py` (lookup tables).

| Package | Purpose |
|---------|---------|
| **`vibemon/`** | Core creature: `entity.py` (`Vibemon`, `Aesthetic`), identity/stats (`identity.py`, `strength.py`, `strength_formulas.py`), disposition (`disposition.py`), lifecycle readiness (`lifecycle.py`), history, brand, asset kind enums (`assets.py`), public schemas (`schema.py`, `types.py`). |
| **`trainer/`** | Player entity: registration fields, crew roster (`crew.py`), generation credits (`credits.py`), trainer asset kinds (`assets.py`, `const.py`), validation (`validation.py`), schemas for API output. |
| **`adoption/`** | Ownership acquisition: candidate review state (`candidate.py`), adoption policy (`policy.py`), review schemas and types. |
| **`generation/`** | Birth pipeline inputs: `BirthSeed` (`seed.py`), provider snapshots (`snapshot.py`), affinity merge (`affinity.py`), birth orchestration (`birth.py`), provider ports (`ports.py`, `providers.py`), generation types. |
| **`move/`** | Move entities (`entity.py`), catalog resolution (`catalog.py`), universal moves data (`data/universal_moves.json`, `universal.py`), move/stat vocabulary (`types.py`). |
| **`battle/`** | Turn-based combat: `GameEngine` (`engine.py`), battle entities (`entity.py`), actions, events, turn resolution (`turn.py`), AI (`ai.py`), constants. **`mechanics/`** subpackage: accuracy, damage, effects, stats, status, targeting, turn order. |
| **`encounter/`** | Wild encounter supply: geography weighting (`geography.py`), wild pool (`wild_pool.py`), encounter picking (`wild_encounter.py`), tuning knobs (`tuning.py`), wild stat helpers (`wild_stats.py`), types. |

### `app/workflows/`

Headless orchestration: takes IDs or domain objects, returns domain objects or read models. No CLI or HTTP parsing. Shared helpers are split across focused modules (`birth_persist.py`, `public_projection.py`, `wild_disposition.py`, etc.); sprite/image processing lives in `sprite_postprocess.py` and `rmbg.py`, with `asset_realization.py` as the lifecycle seam.

| Module | Responsibility |
|--------|----------------|
| `candidate.py` | Generate, adopt, and reject candidates (trainer onboarding). |
| `materialize_vibemon.py` | Asset realization: reference, sprite sheet, christen steps onto monstore. |
| `generate_wild_supply.py` | Seed wild encounter pool. |
| `wild_encounter.py` | Pick encounters, record outcomes, expire wild rows. |
| `release_vibemon.py` | Release owned Vibemon back to wild. |
| `resolve_timeouts.py` | Candidate review timeouts and stale credit holds. |
| `prune_expired_assets.py` | Remove expired blob assets. |
| `rebalance_vibemon.py` | Replay birth to rebalance existing persisted Vibemon. |
| `battle_play.py` | Load battle combatants, start wild battles, submit turns. |

### `app/providers/`

External-context plugins that translate real-world signals into generation inputs. Each provider subclasses `VibeProvider` in `base.py`. Registry and requirement checks live in `catalog.py` and `catalog_schema.py`. Shared HTTP helpers in `helpers.py`; cross-provider types in `types.py` and `schema.py`. API client middleware in `_api/` (hooks, policy, session).

| Provider | Role |
|----------|------|
| **`climate/`** | Weather and atmosphere from coordinates/time. `openmeteo/` client, `data/` reference tables, `const.py` (WMO codes). |
| **`biome/`** | Land cover, elevation, water proximity. `data/moves.json`, raster helpers under `raster/`, water queries under `water/`. |
| **`celestial/`** | Astrological chart: ephemeris engine (`ephemeris/`), houses, aspects, eclipse logic, `data/moves.json`. |
| **`music/`** | Listening history and audio features. `lastfm/` (OAuth routes mounted at `/lastfm`), `musicbrainz/`, `reccobeats/`, classification data in `data/`, `utils.py`. |
| **`video/`** | Watch-history provider (Letterboxd-style signals). |
| **`books/`** | Reading-history provider. |
| **`fitness/`** | Activity/fitness signal provider. |

Provider move catalogs are versioned JSON beside each provider (`data/moves.json`). Universal moves live in `domains/move/data/`.

### `app/storage/`

Persistence adapters. Domains do not import these directly from workflow code paths that should stay pure — workflows and HTTP deps wire them in.

| Area | Contents |
|------|----------|
| **`database/`** | SQLAlchemy models (`models.py`), async engine (`engine.py`), domain↔ORM mapping (`mapper.py`), per-aggregate repositories (`vibemon_repo.py`, `trainer_repo.py`, `candidate_review_repo.py`, etc.), read-model assembly (`read_model.py`), move catalog DB helpers (`move_catalog.py`), custom column types (`types.py`), repair utilities (`repair.py`). |
| **`blob/`** | Object store via obstore: `MonStore` (`monstore.py`), asset key helpers (`assets.py`, `const.py`). |
| **`cache/`** | Redis or SQLite HTTP cache (`redis.py`), provider prefetch timestamps (`provider_prefetch.py`). |
| **`secrets/`** | Encrypted trainer API tokens (`repository.py`). |
| **`bootstrap.py`** | Post-init seeding: canonical trainer reference sprite from frontend static tree. |

### `app/http/`

Litestar application (`app.py`): CORS, lifespan (DB init), route registration, Last.fm ASGI mount. Dependencies in `deps.py` (DB session, cookie session). Error mapping in `errors.py`. Battle read helpers in `battle_read.py`.

**Routes** (`routes/`):

| Router | Endpoints (summary) |
|--------|---------------------|
| `health.py` | Liveness/readiness. |
| `assets.py` | `GET /api/assets/{key}` — stream monstore blobs. |
| `trainers.py` | Registration, session cookie, username check, trainer reference upload, crew read. |
| `candidates.py` | Candidate generate/adopt/reject/refresh (onboarding hatch flow). |
| `providers.py` | Provider catalog list, prefetch triggers for configuration UI. |

**Schemas** (`schemas/`): HTTP request/response DTOs for candidates, crew, providers — separate from domain `schema.py` read models where shaping differs.

### `app/genai/`

AI adapters and prompt rendering. Not sprite matte normalization (that is workflow asset code).

| Area | Contents |
|------|----------|
| `google.py` | pydantic-ai builders for Google text/image models. |
| `prompts.py` | Template loading and metadata for `.mdc` / Jinja prompts. |
| `vibemon_assets.py` | Vibemon-facing generator: species names, reference images, sprite sheets, battle cries, trainer reference facing. |
| `static_assets.py` | Generation for shipped static sprites (trainer, hatchling silhouette). |
| `sprite_facing.py` | Detect left/right facing on reference uploads. |
| `style_bible.py` | Style-bible reference paths and helpers. |
| **`prompts/`** | Prompt library: species name, sprite reference/sheet/facing, trainer reference, battle cry; element Jinja snippets; role and tier visual/sonic templates; `_style/rendering.j2`. |
| **`style_bible/`** | Canonical reference PNGs used as generation anchors. |

### `app/_compat/`

Third-party compatibility shims (e.g. `httpx.py` annotation fixes for Python 3.14).

### `scripts/`

CLI rehearsal surface — **not** a second application layer. Orchestrates workflows for manual UX exercise. Shared CLI plumbing in `_common.py`. See `scripts/README.md`.

| Script | Role |
|--------|------|
| `dev_stack.py` | Run backend + frontend together (`uv run dev`). |
| `init_db.py` | Create tables from models. |
| `db_shell.py` | Ad-hoc SQL / interactive DB shell. |
| `generate_vibemon.py` | Create Vibemon at a lifecycle stage (candidate/wild/owned). |
| `generate_static_assets.py` | Regenerate shipped static sprites via genai. |
| `manifest_vibemon.py` | Asset manifest utilities. |
| `link_lastfm.py` | Last.fm account linking helper. |
| `simulate_adoption.py` | Adoption flow rehearsal. |
| `simulate_battle.py` | Battle simulation rehearsal. |
| `simulate_wild_encounter.py` | Wild encounter rehearsal. |

### `tests/`

Pytest tree mirroring `app/` layout: `domains/`, `providers/`, `workflows/`, `http/`, `storage/`, `app/`, plus `fixtures/` (including biome raster samples) and `scripts/`. Config in `pyproject.toml` (`asyncio_mode = auto`).

---

## Frontend (`vibemon/frontend/`)

SvelteKit app with **static adapter** (`prerender = true` on root layout). Dev server defaults to HTTPS on port 5173 when `.certs/` exist (`pnpm certs`). Vite allows monorepo paths outside the package for linked assets.

### `src/routes/`

SvelteKit file-based routing.

| Route | Page |
|-------|------|
| `/` | Placeholder landing (`+page.svelte`). |
| `(onboarding)/register` | Trainer registration scene. |
| `(onboarding)/hatch` | Candidate hatch / review flow (shared onboarding layout). |
| `/deck/crew` | Crew roster scene. |
| `deck/+page.ts` | Deck route redirect/setup. |

The `(onboarding)/+layout.svelte` layout owns the full trainer onboarding shell: reference camera, hatch controls, candidate panel, provider settings modals, adopt nickname flow, and suspense choreography.

### `src/lib/domains/`

Feature-aligned UI modules. Each domain folder holds Svelte components and thin API clients.

| Folder | Contents |
|--------|----------|
| **`trainer/`** | Onboarding scenes (`TrainerRegistrationScene`, `TrainerConfigurationScene`), reference sprite + camera (`TrainerReference`, `TrainerReferenceCamera`), hatch UI (`HatchControls`, `HatchCandidatePanel`, `HatchlingSilhouette`), settings modals, BST chart, adopt nickname modal; API modules (`trainerApi.ts`, `hatchApi.ts`, `providerApi.ts`); stores (`trainerRegisterStore`, `providerConfigModalStore`); onboarding state machine (`trainerOnboardingUi.ts`, `hatchSuspense.ts`); username validation. |
| **`crew/`** | Crew scene and nav button (`CrewScene`, `CrewNavButton`). |
| **`game/`** | Cross-cutting game asset paths (`gearSpritePaths.ts` for camera, vibe-deck, vibe-cart facings). |

### `src/lib/ui/`

Shared game chrome and primitives: scene frame, modals, panels, toast system, film grain, dialog box, element badges, trainer name input, free-form buttons, banded background. Design tokens in `tokens.css`. Element type helpers in `elementTypes.ts`.

### `src/app.css`

Global styles; imports UI tokens. Root typography and color scheme.

### `static/`

Shipped binary assets served as-is (also referenced by backend bootstrap for canonical trainer sprite).

```text
static/game/
  backgrounds/   Scene backdrops (e.g. trainer-field.png)
  icons/         Gear HUD icons (vibe-deck, vibe-cart); standard app chrome uses Lucide in the frontend
  sprites/       Trainer, gear, hatchling silhouette; left/right facing variants
```

### `asset-prompts/`

Human- and genai-facing prompt specs for static assets. Base style markdown (`base-style.md`, icon/sprite variants) plus per-asset `.mdc` files under `game/icons/` and `game/sprites/` that pair with backend `genai/prompts/`.

### `scripts/`

Frontend-only Node scripts: `generate-dev-cert.mjs` (HTTPS dev certs), `normalize-blank-lines.mjs` (format helper).

---

## Tools (`vibemon/tools/`)

### `cutout/`

Standalone package `vibemon-cutout` — bbox-guided background removal for sprites (rembg/onnxruntime). Local web UI (`server.py`, `web.py`, `static/`) and CLI (`cli.py`). Separate `pyproject.toml` and venv; not imported by the main backend at runtime. Used during asset authoring workflows.

---

## How the pieces connect

```text
┌─────────────────┐     HTTP (session cookie)      ┌──────────────────┐
│  frontend/      │ ─────────────────────────────► │  backend/http/   │
│  SvelteKit      │     /api/trainers, candidates  │  Litestar        │
└────────┬────────┘     /api/providers, assets     └────────┬─────────┘
         │                                                    │
         │ static/game/sprites                                │ workflows/
         ▼                                                    ▼
┌─────────────────┐                              ┌──────────────────┐
│  static/        │ ◄── bootstrap seed ──────────│  domains/        │
│  asset-prompts  │     genai/static_assets      │  providers/      │
└─────────────────┘                              └────────┬─────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────┐
                                               │  storage/        │
                                               │  database + blob │
                                               └──────────────────┘
```

**Typical onboarding path:** `register` → trainer session → upload reference → `hatch` calls candidate routes → workflows run birth + materialize → blobs in monstore → frontend loads sprites via `/api/assets/{key}` or static paths for gear.

**Typical generation path:** `BirthSeed` (time + geo + trainer) → providers fetch payloads → affinities merge in `generation/birth.py` → `Vibemon` entity → optional genai asset passes → persist via mapper/repositories.

---

## Related documentation

| Document | Topic |
|----------|-------|
| [development/CONTEXT.md](development/CONTEXT.md) | Canonical domain vocabulary |
| [development/VOICE.md](development/VOICE.md) | Player-facing copy and tone quick reference |
| [development/COLORS.md](development/COLORS.md) | Locked palette quick reference |
| [development/ARCHITECTURE.md](development/ARCHITECTURE.md) | Layer ownership and file naming conventions |
| [development/SCRIPT_FRONTEND_CONTRACT.md](development/SCRIPT_FRONTEND_CONTRACT.md) | Script subprocess contract for tooling |
| [development/DESIGN.md](development/DESIGN.md) | Product and UX design notes |
| [development/GEAR.md](development/GEAR.md) | Vibe Deck, Vibe Cart, Cart Folio visual spec |
