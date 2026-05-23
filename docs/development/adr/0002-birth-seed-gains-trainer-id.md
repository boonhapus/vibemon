# `BirthSeed` gains `trainer_id`

**Status:** proposed

## Context

`BirthSeed` (`app/domains/generation/seed.py`) carried only `timestamp`, `geo_coords`, and `providers`. Two consequences:

1. Two trainers birthing at the same coordinate and microsecond produced identical RNG seeds. Latent collision risk that hadn't bitten in practice yet.
2. Per-trainer providers were architecturally blocked. `SoundProvider` (see `plans/sound-provider-plan.md`) needs the trainer's Spotify refresh token to fetch personal listening data; without `trainer_id` on the seed, there is no clean way to thread trainer identity into `provider.fetch(seed)`.

## Decision

Add `trainer_id: uuid.UUID` to `BirthSeed` and fold it into `_rng_seed_material` so it participates in deterministic RNG derivation.

## Considered alternatives

- **Pass trainer context via a sidecar bag** (`BirthSeed.provider_context: dict[str, Any]` keyed by provider name). Keeps trainer out of the seed proper, but conflates per-provider config with per-birth identity. Rejected — trainer identity is genuinely seed material, not provider configuration.
- **Resolve trainer at `fetch()` time via thread-local / contextvar.** Adds invisible coupling and breaks the seed's `FrozenSchema` self-containment. Rejected.
- **Leave `BirthSeed` unchanged; ship sound as market-mode-only.** Rejected when sound was scoped to personal-mode-only — see sound-provider-plan.md.

## Consequences

- Every existing `BirthSeed` construction site must pass `trainer_id`. Migration scope: `app/workflows/`, test fixtures, any script frontends.
- `rng_seed` and `rng_seed_for(namespace)` outputs **change** for the same `(timestamp, geo_coords)` pair. Existing Vibemon `BirthSnapshot` payloads remain replayable (snapshot stores raw payload), but RNG-derived outputs (move starter selection, evo seed, radiant roll) for *new* births differ from what the old seed would have produced. Acceptable: the change is pre-launch.
- Other providers (climate, geography) can ignore `trainer_id` entirely. No fetch-shape change for them.
- The dupe-birth latent risk closes as a side effect.
