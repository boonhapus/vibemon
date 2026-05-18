# Vibemon Roadmap

**Status:** Draft  
**Last updated:** May 18, 2026

This roadmap translates the backend architecture review and domain decisions into implementation phases and future grilling topics.

## Immediate Implementation

### Phase 1: Service Foundation

- [x] Add `app/services/`.
- [x] Add `VibemonService` with injected provider, GenAI, asset/object-store, clock, and random dependencies.
- [x] Keep HTTP/API framework choices deferred.
- [x] Wrap existing lifecycle functions first; do not rewrite lifecycle internals as part of the first service slice.

### Phase 2: Candidate Review and Disposition

- [x] Add persisted Vibemon disposition: `owned`, `wild`, and non-playable `expired`.
- [x] Allow missing gameplay disposition only while an active candidate review exists.
- [x] Add candidate-review metadata for shown candidates.
- [x] Keep `trainer_id` as ownership only; candidate review records the reviewing trainer separately.
- [x] Implement candidate generation, adoption, rejection, and timeout resolution.
- [x] Enforce 24-hour candidate review timeout from `shown_at`.
- [x] Generate up to three candidates per trainer per day, sequentially, with one active generation job at a time.
- [x] Consume generation credit only after a christened candidate is successfully shown.

### Phase 3: Party Ownership Rules

- [x] Treat the six-slot party as the trainer's full owned roster.
- [x] Defer storage/box ownership.
- [x] Make full-party adoption an atomic release/adopt slot swap.
- [x] Preserve progression, moves, history, and assets on release.

### Phase 4: Read Models

- [x] Add public Vibemon read models suitable for future API routes.
- [x] Include identity, stats, lifecycle, disposition, ownership, party slot, colors, and asset URLs.
- [x] Include candidate-review state only for the reviewing trainer.
- [x] Persist asset refs/object keys; return fetchable URLs in read models.

## Immediate Next Slice

- Recreate/reset local development data after schema changes; no backwards-compatible migration path is needed before users exist.
- Harden generation credit holds and adoption swaps for real concurrent requests. **Progress 2026-05-18:** service reads now request row locks for trainer, pending-review, credit-day, owned-party, release, and encounter-adjustment rows; full-party adoption no longer mutates the released Vibemon before candidate manifestation succeeds. Crash hold expiry remains unresolved.
- ~~Add focused tests for one-active-generation enforcement, adoption-after-timeout rejection, and full-party swap behavior.~~ Done; also covered manifest-failure rollback behavior for full-party swaps.
- ~~Replace or simplify script callers so candidate generation goes through `VibemonService`.~~ Done; admins/testers bypass via `bypass_credits=True`.

## Deferred Implementation

### Wild Pool and Encounters

- Wild Pool is scoped by birth latitude/longitude using geohash precision 5.
- Sparse buckets expand to neighboring buckets before new encounter supply is generated.
- Encounter supply generation creates christened Wild Vibemon directly.
- Wild encounter queries must exclude under-review and expired Vibemon.
- Encounter services must revalidate disposition before final selection.

### Manifestation and Latency Hiding

- Rejected candidates and encounter-supply generations enter the Wild Pool as christened.
- Manifest lazily during prewarm or encounter preparation.
- Hide cold manifestation behind an Encounter Reveal, such as a silhouette slide-in.

### Wild Expiration

- Wild Vibemon expire after 30 days since last actual encounter.
- Any real player encounter resets expiration globally.
- Expiration marks the Vibemon `expired`; asset cleanup is separate retention work.
- Expired is terminal for normal gameplay.

### Encounter Weighting

- Encounter adjustments are trainer-specific.
- Candidate rejection and timeout start at `0.00x` encounter weight.
- Run starts at `0.30x`, defeat at `0.50x`, win without adoption at `0.75x`.
- Adjustments continuously decay to `1.00x` over a random 1-3 day window.
- Latest outcome replaces previous active adjustment for the same trainer/Vibemon pair.

### Strength Matching

- Member Strength is actual level-scaled stat total.
- Party Strength is average member strength plus 25% of max member strength plus 10% of total member strength.
- PvP compares Party Strength directly.
- Wild 6v1 matching compares wild Member Strength against 45% of trainer Party Strength.
- Wild matching initially accepts 70%-140% of that target, weighted toward the target.
- Keep all coefficients as centralized code constants.

### Catch

- Catch is deferred for later design.
- Reserve language only; do not add catch APIs or service placeholders in the first slice.
- Future Catch is valid only during battle and only against Wild Vibemon.
- Catching mechanics are not influenced by win, defeat, or run unless a later design explicitly changes that.

## Unresolved Decisions

<!-- /grill-with-docs: Resume here. Ask one question at a time, update docs/CONTEXT.md and docs/adr/ as decisions are resolved, and prefer codebase exploration over asking when the answer is discoverable. -->

## Next Grill Areas

### 1. Persistence Shape

Questions to resolve:

- Should candidate review be a separate table or a status table tied to Vibemon history?
- What exact fields belong on `vibemon`: `disposition`, `wild_entered_at`, `last_encountered_at`, `expired_at`, `party_slot`, `trainer_id`?
- Should generation credits be derived from event history or stored as daily counters?
- What database constraints enforce candidate-review/disposition invariants?
- How should local development data be reset after schema changes?

### 2. Service API Surface

Questions to resolve:

- What are the exact `VibemonService` methods and request/response types?
- Should candidate generation be synchronous for the first implementation or job-backed from the start?
- Where do idempotency keys belong for generation, adoption, rejection, timeout, and release?
- How should service methods expose domain failures: exceptions, result objects, or typed error codes?

### 3. Transaction and Concurrency Rules

Questions to resolve:

- Which service operations need row locks or conditional updates?
- How should full-party adoption swaps avoid race conditions?
- How should generation-credit holds expire if a worker crashes?
- How should timeout resolution race with adoption/rejection?

### 4. Asset Lifecycle Split

Questions to resolve:

- Should `manifested` continue to mean full sheet plus all nine poses, or should battle-ready and emote-ready split later?
- Which assets are required for candidate review, wild encounter reveal, battle, and owned presentation?
- How should failed monstore writes and partial asset uploads recover?
- What asset cleanup retention should apply after Expired?

### 5. Wild Encounter Design

Questions to resolve:

- What exactly counts as an Actual Encounter?
- When is last encounter timestamp updated: selection, reveal start, battle start, or battle completion?
- How many neighboring geohash buckets should sparse expansion search?
- What minimum pool size triggers new encounter supply generation?
- How should encounter selection combine geography, strength, freshness, and trainer-specific adjustments?

### 6. Generation Credits and Product Rules

Questions to resolve:

- When does the daily credit window reset: UTC, trainer-local timezone, or rolling 24 hours?
- Can credits accumulate or are they capped at three?
- Should admins/testers bypass credits? **Decided 2026-05-18: yes; exposed as `bypass_credits=True` on `VibemonService.generate_candidate` for script/admin callers.**
- Should encounter supply generation consume any trainer credit? Current assumption: no.

### 7. Battle and Catch Boundary

Questions to resolve:

- What does Catch eventually do during battle?
- Is Catch a battle action like move/switch/item/run?
- Does Catch consume turn priority or end the battle?
- What player-facing states exist when a Catch fails because another trainer adopted the mon first?

### 8. API and Frontend Readiness

Questions to resolve:

- What screens consume candidate-review state?
- How should candidate timeout be shown after the fact?
- What read models need private trainer-specific fields versus public fields?
- What URLs need signing, and how long should signed asset URLs live?

## Reference Docs

- [Backend Architecture Review](./backend-architecture-review.md)
- [Domain Context](../docs/CONTEXT.md)
- [Architecture Decision Records](../docs/adr/)
