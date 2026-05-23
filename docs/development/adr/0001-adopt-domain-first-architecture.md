# Adopt Domain-First Architecture

## Status

Accepted.

## Context

Vibemon needs a package structure that gives gameplay concepts, headless workflows, providers, storage adapters, and script-driven frontend work clear homes. The prior architecture mixed these concerns through broad service modules, a singular `domain` package, and active ADRs that described now-obsolete boundaries.

## Decision

Adopt the domain-first architecture described in `docs/development/ARCHITECTURE.md` and implemented under `vibemon/backend/app`.

- `domains/` owns game concepts and rules.
- `app/` owns transport-ignorant workflow modules.
- `providers/` translates external or user-context signals into generation inputs.
- `storage/database/` owns ORM models, mapping, and repositories.
- `storage/blob/` owns object/blob storage and asset byte references.
- `genai/` owns AI client adapters and prompt rendering utilities.
- `vibemon/scripts/` is the near-term user-facing frontend surface.

## Consequences

Older ADRs have been archived and are no longer active constraints. Useful vocabulary and domain constraints should be copied forward into `CONTEXT.md` or new decision notes as needed.
