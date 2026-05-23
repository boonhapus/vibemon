# Project Architecture

Vibemon uses a domain-first backend layout. Code is grouped by game concept first, then by adapters around those concepts.

## Target Layout

The tree below illustrates the package structure, file roles, and placement conventions
the codebase follows. It is **not an exhaustive directory listing** — helper modules,
internal constants files, provider-scoped data, and other support modules may exist in
any package without being shown here. What matters is the pattern: each domain owns its
types, entities, and schemas; workflows, providers, storage, and scripts each have their
own package root. The [File Naming Conventions](#file-naming-conventions) section is the
authoritative guide for what each file role means.

```text
vibemon/backend/app/
  domains/
    vibemon/
      entity.py
      identity.py
      lifecycle.py
      disposition.py
      assets.py
      brand.py
      history.py
      strength.py
      strength_formulas.py
      schema.py
      types.py
    trainer/
      entity.py
      party.py
      credits.py
    adoption/
      candidate.py
      policy.py
      schema.py
      types.py
    move/
      entity.py
      catalog.py
      types.py
    battle/
      entity.py
      actions.py
      events.py
      engine.py
      turn.py
      hooks.py
      const.py
      scripts.py
      mechanics/
    generation/
      seed.py
      snapshot.py
      affinity.py
      birth.py
    encounter/
      wild_pool.py
      wild_encounter.py
      geography.py
      tuning.py
      types.py

  app/
    _workflow_support.py
    generate_candidate.py
    generate_wild_supply.py
    adopt_candidate.py
    reject_candidate.py
    release_vibemon.py
    pick_wild_encounter.py
    prepare_wild_encounter_reveal.py
    record_wild_encounter.py
    expire_wild.py
    prune_expired_assets.py
    resolve_timeouts.py
    read_model.py

  providers/
    base.py
    helpers.py
    api_hooks.py
    climate/
      provider.py
      api.py
      const.py
      data/

  storage/
    database/
      models.py
      mapper.py
      move_catalog.py
      repositories.py
    blob/
      monstore.py
      assets.py
      const.py

  genai/
    client.py
    sprites.py
    structured_output.py
    utils.py
    _image.py
    prompts/

  core/
    ids.py
    math.py
    time.py
    types.py
    errors.py
    schema.py

vibemon/scripts/
  generate_candidate.py
  generate_wild_supply.py
  adopt_candidate.py
  reject_candidate.py
  release_vibemon.py
  pick_wild_encounter.py
  christen_vibemon.py
  manifest_vibemon.py
```

## Ownership

`domains/` owns game concepts and rules. Domain modules should not import workflow modules, storage adapters, HTTP adapters, or scripts.

`app/` owns headless workflows. A workflow takes IDs, domain objects, or simple command objects and returns domain objects or read models. It does not parse CLI arguments or assume HTTP.

`providers/` translates external or user-context signals into domain-defined generation inputs. Provider code may import domain types; generation domains must not import provider infrastructure.

`storage/database/` owns ORM models, database mapping, and repositories. `storage/blob/` owns object storage and asset bytes. Domains do not import concrete storage adapters.

`app/_workflow_support.py` holds shared helpers used by multiple workflows (read model assembly, state transitions, encounter adjustment plumbing). It is not a workflow itself and should not grow domain logic.

`providers/api_hooks.py` holds HTTP client middleware (logging, rate limiting) used by provider API clients. It is infrastructure for providers, not domain translation.

`genai/` owns AI client adapters and prompt rendering utilities. `genai/utils.py` handles prompt template loading; `genai/_image.py` wraps low-level image generation APIs.

`vibemon/scripts/` is the near-term frontend surface. Scripts should parse CLI arguments, call exactly one workflow or script-owned lifecycle realization operation, and print useful output.
The subprocess contract for frontend/dev tooling lives in `docs/development/SCRIPT_FRONTEND_CONTRACT.md`.

## File Naming Conventions

Each domain (and where useful, adapter packages) follows a small, recurring set of file roles. Pick the role by what the file *is*, not what it talks about.

`types.py` holds the **domain vocabulary** — enums, `Literal` unions, and `type` aliases the domain speaks in. No behavior, no state, no I/O. These are the names other modules import to describe shape.

> Examples: `VibemonTypeT`, `TierT`, and `BaseStatT` in `domains/vibemon/types.py`; `CandidateReviewStatusT` in `domains/adoption/types.py`; `StatStageNameT` in `domains/move/types.py`.

`entity.py` holds **live domain objects** — Pydantic models that carry identity, invariants, and behavior. Usually mutable (extend `Schema`), and own the domain methods that other layers call.

> Examples: `Vibemon` and `Aesthetic` in `domains/vibemon/entity.py`; `Move` in `domains/move/entity.py`; `Trainer` in `domains/trainer/entity.py`.

`schema.py` holds **frozen read-model projections** intended for serialization and API output. Extends `FrozenSchema`. Stateless, safe to hand outward. Schema files must not contain objects that carry mutable runtime state.

> Examples: `PublicVibemon` and `TypeDefenseSummary` in `domains/vibemon/schema.py`; `CandidateReviewRead` in `domains/adoption/schema.py`.

`const.py` holds **static lookup tables and pinned values** — module-scope dicts, frozensets, version constants, and external code enums that bridge external/system vocab to the domain's own `types.py`. No behavior. Use this instead of scattering literals through `types.py` or `entity.py`.

> Examples: `POSE_TO_ASSET` mapping and `ASSET_VERSION` in `storage/blob/const.py`; `WeatherCode` (WMO Code 4677) in `providers/climate/const.py`.

**Key distinction:** `types.py` is the vocabulary the domain *speaks in*; `const.py` is the fixed mapping/values (often translating to or from externals). `entity.py` is behavior + state; `schema.py` is a frozen outward projection.

## Vocabulary Boundaries

`adoption/` owns ownership acquisition. Candidate review is an adoption path, not a top-level domain.

`lifecycle` means presentation readiness only: born, christened, manifested. Lifecycle is not ownership, generation, or candidate workflow. Asset realization is script-driven for now.

`core/` is only for genuinely shared primitives such as IDs, time helpers, errors, and base schema classes.

## Rules Of Thumb

- New gameplay concept: add a package under `domains/`.
- New orchestration: add a module under `app/`.
- New external context source: add a provider under `providers/`.
- New persistence concern: add an adapter under `storage/`.
- New user-facing command: add a thin script under `vibemon/scripts/`.
- Gameplay numbers and owned raw content should live beside the owning domain or provider.
