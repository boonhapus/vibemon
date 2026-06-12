# PostHog Analytics from Day One

| | |
| --- | --- |
| **Status** | Adopted |
| **Priority** | High |
| **Complexity** | Low–Medium |
| **Area** | Infrastructure / Analytics |
| **Related** | [../plans/infrastructure-plan.md](../plans/infrastructure-plan.md) (operational plan) |

## Summary

Frontend decisions must be driven by observed user behavior, not intuition. Instrument from the first commit so we never ship a feature blind. Retrofitting analytics after launch loses the early-adopter signal — the most valuable cohort for shaping the product.

Operational rollout lives in `docs/development/plans/infrastructure-plan.md` (PostHog Cloud section). This document remains the rationale and event-taxonomy reference.

## Problem

Without day-one instrumentation we ship features blind, lose early-adopter cohort signal, and cannot validate move balance, generative content QA, asset performance, or difficulty curves with data. Ad-hoc env toggles and retrofitted `data-*` sweeps create noise without actionable funnels.

## Concept

PostHog as a single platform (analytics, replay, flags, experiments, surveys, error tracking) with a thin vertical-slice rollout: init SDK → `track()` wrapper → events co-located with behavior → optional `data-action` on the same PR. Named custom events are the source of truth; autocapture is exploratory only.

## Design

### Why PostHog
- **Single platform**: product analytics + session replay + feature flags + experiments + surveys + error tracking. No glue code between Mixpanel/LaunchDarkly/Sentry/Hotjar.
- **Self-host option**: PII control if Vibemon ever stores trainer identity beyond pseudonyms.
- **Open source core**: not locked into a vendor's pricing whim.
- **Autocapture**: pageviews + clicks captured without manual instrumentation; bespoke events layered on top.
- **Reverse proxy support**: dodge adblockers via first-party domain (`/ph/` route).

### Instrumentation ideology

**Do not** block PostHog on a repo-wide pass of `data-*` attributes. **Do** ship analytics in thin vertical slices: init SDK → `track()` wrapper → events co-located with behaviour → optional `data-action` on the same PR.

### Three layers (priority order)

| Layer | Purpose | Required before PH? |
|-------|---------|---------------------|
| **Custom events** (`track(name, props)`) | Funnels, KPIs, product decisions | Yes — source of truth |
| **Pageviews + sessions** (`$pageview`, SDK defaults) | Where users go, how long they stay | Yes — init + SvelteKit navigation hook |
| **`data-action` on key controls** | Stable autocapture labels, Playwright selectors | No — add alongside instrumentation, not before |

Autocapture alone is exploratory signal. It is noisy and brittle (button label changes break insights). **Named custom events win** for anything we will act on (adopt rate, release rate, generation failures).

### Sessions and clicks

- **Sessions** are derived automatically by PostHog from the event stream (idle timeout ≈ 30 minutes). Do not manually start/stop sessions unless we have a rare need for custom `session_*` events.
- **Clicks** can come from autocapture (`$autocapture`) or from explicit `track()` calls fired in the same handler as the action (preferred for CTAs).
- **Session replay** is enabled at init with input masking; it attaches to sessions without extra wiring.

### `data-action` convention (supplement only)

Use one attribute name on **high-value controls only** (~10–15 per major flow, not every element):

```html
<button data-action="candidate-adopt" …>Adopt</button>
```

Naming: kebab-case, `{domain}-{verb}` (e.g. `trainer-register`, `generation-start`, `crew-release-confirm`).

Apply when:

- The control is a primary CTA or funnel step.
- We want Playwright e2e selectors that match analytics semantics.
- Autocapture exploration is useful for that screen.

Skip when:

- `track()` already captures the outcome with richer props (`vibemon_id`, `providers`, error codes).
- The element is decorative or duplicated (type badges, slot indices).

Prefer plumbing `data-action` through shared primitives (e.g. optional prop on `MenuButton`) over sprinkling attributes on every scene.

### Where to emit events

Co-locate `track()` with **domain stores or API success/failure paths** — the same place real side effects happen:

- `trainerStore` — register, login, sign out
- `generationStore` — generation start/complete/fail, adopt, reject
- `crewStore` — release

Avoid: duplicate `track()` in both a button component and a store unless the store is the only caller.

### Identification (current product)

Trainer session cookies exist. After `GET /api/trainers/me` or successful register/login:

```typescript
posthog.identify(trainer.id, { username: trainer.username });
```

Use **trainer UUID** as `distinct_id`, not username (usernames may become mutable later). Call `posthog.reset()` on sign out.

Optional later: `posthog.group('trainer', trainer.id)` for crew-scoped analytics.

### Dev opt-out

No key or `VITE_POSTHOG_ENABLED=false` → analytics module no-ops. Local dev should default to off unless explicitly testing telemetry.

### Anti-patterns (explicit)

- Pre-PH sweep adding `data-*` to every Svelte component “for later”.
- Raw `posthog.capture()` outside the analytics module.
- Vanity autocapture on all DOM nodes (event volume + noise).
- Custom `session_started` / `session_ended` before proving built-in session metrics are insufficient.

### Scope: what to track

### Autocapture (exploratory signal)

- Page navigation and clicks on allowed elements (`button`, `a`, `[data-action]`).
- Restrict autocapture if volume grows: `dom_event_allowlist: ['click']`, `element_allowlist` as above.
- **`data-action`** replaces the older `data-attr` idea — one stable name, shared with e2e tests.

### Custom Events (intentional — primary)

**Shipped flows (instrument first):**

- `trainer_registered` / `trainer_logged_in` / `trainer_signed_out`
- `generation_started` — `providers[]`, `has_location`
- `generation_completed` / `generation_failed` — `vibemon_id?`, `duration_ms`, `code?`
- `candidate_adopted` / `candidate_rejected` — `vibemon_id`, `crew_count`
- `crew_member_released` — `vibemon_id`, `slot`

Battle loop (when battle ships):
- `battle_started` — opponent type, trainer level, crew composition
- `move_selected` — move id, type, crew slot, turn number
- `battle_ended` — outcome (win/lose/flee), turns, damage dealt/taken
- `vibemon_fainted` — which vibemon, at what turn, vs what type

Progression:
- `vibemon_caught` — species, level, location
- `vibemon_evolved` — from/to species, trigger
- `move_learned` — move, vibemon, source (level-up/tm/tutor)
- `crew_composition_changed` — crew diff

Engagement:
- `feature_discovered` — first interaction with a new system
- `dead_end_reached` — user stuck in menu loop, repeated back-button hits

Built-in session metrics and `$pageview` cover most “session_started / session_ended” needs; add custom session events only if dashboards prove a gap.

### Identification
- Anonymous `distinct_id` until first `identify()` (existing PostHog behaviour).
- **`posthog.identify(trainer.id)`** after register/login/me; **`posthog.reset()`** on sign out.
- Group analytics (optional later): trainer → crew → battles (PostHog groups).

### Why this matters for Vibemon specifically

1. **Move balance** — telemetry on move usage + win rate is the only way to validate the type/affinity system. The roadmap commits to data-driven balance; without instrumentation it's vibes.
2. **Generative content QA** — when genai produces a Vibemon, we need to know if players actually use it, evolve it, or release it. PostHog funnels answer this.
3. **Asset weight** — session replay + performance events surface which sprites/animations cause jank on real devices.
4. **Difficulty curve** — battle outcome distributions by trainer level expose grind walls.

## Implementation

Follow this order. **Do not** add a separate “data-ID migration” milestone before Phase 0.

### Phase 0: SDK shell
- Add `posthog-js` to frontend.
- `src/lib/analytics/` — `init.ts`, `track.ts`, `events.ts`; no-op when key missing or disabled.
- Init in root layout; **`afterNavigate` → `$pageview`** for SvelteKit client routes.
- Env: `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST`, `VITE_POSTHOG_ENABLED` in `.env.example`.
- Session replay with **`maskAllInputs: true`**.

### Phase 1: Vertical slice (setup → generate → crew)
- Typed events for shipped flows (see list above).
- `track()` in domain stores alongside API calls.
- `identify()` / `reset()` in trainer session lifecycle.
- **`data-action` only on CTAs touched in this PR** (or via `MenuButton` prop).
- Verification: funnel insight in PostHog UI for register → generate → adopt.

### Phase 2: Battle instrumentation
- Hook into battle state machine — emit events at each transition.
- Backend events optional: PostHog Python SDK for authoritative outcomes if frontend tampering matters.

### Phase 3: Feature Flags
- Gate new providers, species, UI experiments. Default 0% → internal cohort → percentage.
- Replace ad-hoc env toggles.

### Phase 4: Experiments
- A/B test concrete questions; define guardrail metrics (session length, churn) first.

## Open Questions
- Self-host vs. PostHog Cloud? **Cloud for v1** (see infrastructure plan). Revisit at scale or if PII enters the model.
- Backend events: send via PostHog Python SDK from FastAPI, or push from frontend only?
- Cost ceiling: free tier covers 1M events/month — battle events at scale could blow this. Sample non-critical events.
- Privacy policy text — needed before public launch even with pseudonymous IDs.
- Mobile/native plans? PostHog has SDKs but event taxonomy should be platform-agnostic now.

## Anti-Goals
- Vanity metrics. DAU without context is noise.
- Tracking everything. Bloated event streams hide signal; curate.
- **Upfront `data-*` sweeps** before the SDK or `track()` wrapper exists.
- Decisions in a vacuum. Pair quantitative (PostHog) with qualitative (playtests, surveys) — PostHog surveys can host both.

## Success Criteria
- Every roadmap feature ships with at least one tracked event proving it's used.
- No balance change merged without supporting telemetry.
- Feature flags are the default rollout mechanism, not direct merges to main.
