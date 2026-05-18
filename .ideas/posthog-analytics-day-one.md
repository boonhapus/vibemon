# PostHog Analytics from Day One

## Premise
Frontend decisions must be driven by observed user behavior, not intuition. Instrument from the first commit so we never ship a feature blind. Retrofitting analytics after launch loses the early-adopter signal — the most valuable cohort for shaping the product.

## Why PostHog
- **Single platform**: product analytics + session replay + feature flags + experiments + surveys + error tracking. No glue code between Mixpanel/LaunchDarkly/Sentry/Hotjar.
- **Self-host option**: PII control if Vibemon ever stores trainer identity beyond pseudonyms.
- **Open source core**: not locked into a vendor's pricing whim.
- **Autocapture**: pageviews + clicks captured without manual instrumentation; bespoke events layered on top.
- **Reverse proxy support**: dodge adblockers via first-party domain (`/ph/` route).

## Scope: What to Track

### Autocapture (free signal)
- Page navigation, click targets, form interactions.
- Set up `data-attr` taxonomy on key elements (e.g. `data-attr="battle-attack-btn"`).

### Custom Events (intentional)
Battle loop:
- `battle_started` — opponent type, trainer level, party composition
- `move_selected` — move id, type, party slot, turn number
- `battle_ended` — outcome (win/lose/flee), turns, damage dealt/taken
- `vibemon_fainted` — which vibemon, at what turn, vs what type

Progression:
- `vibemon_caught` — species, level, location
- `vibemon_evolved` — from/to species, trigger
- `move_learned` — move, vibemon, source (level-up/tm/tutor)
- `team_composition_changed` — party diff

Engagement:
- `session_started` / `session_ended` — duration, screens visited
- `feature_discovered` — first interaction with a new system
- `dead_end_reached` — user stuck in menu loop, repeated back-button hits

### Identification
- Pseudonymous `distinct_id` from first session (no login required).
- Merge identities later if/when auth lands (`posthog.identify`).
- Group analytics: trainer → team → battles (PostHog groups).

## Why This Matters for Vibemon Specifically

1. **Move balance** — telemetry on move usage + win rate is the only way to validate the type/affinity system. The roadmap commits to data-driven balance; without instrumentation it's vibes.
2. **Generative content QA** — when genai produces a Vibemon, we need to know if players actually use it, evolve it, or release it. PostHog funnels answer this.
3. **Asset weight** — session replay + performance events surface which sprites/animations cause jank on real devices.
4. **Difficulty curve** — battle outcome distributions by trainer level expose grind walls.

## Implementation Plan

### Phase 0: Setup (before first feature ships)
- Add `posthog-js` to frontend.
- Init in app root with reverse proxy config.
- Wire env vars: `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST`.
- Add `.env.example` entry; document opt-out flag for dev.
- Configure session replay with input masking (privacy default).

### Phase 1: Event Taxonomy
- Create `frontend/src/analytics/events.ts` — typed event names + payload shapes.
- Single `track(event, props)` wrapper so we can swap providers later.
- Lint rule / type system enforces no raw `posthog.capture` calls outside the module.

### Phase 2: Battle Instrumentation
- Hook into existing battle state machine — emit events at each transition.
- Backend events too? PostHog supports server-side capture; use for authoritative battle outcomes if frontend can be tampered with.

### Phase 3: Feature Flags
- Gate new vibemon species, move sets, and UI experiments behind PostHog flags.
- Default: 0% rollout, internal users via cohort.
- Replace ad-hoc env toggles.

### Phase 4: Experiments
- A/B test concrete questions: catch rate UI, evolution prompts, move tutor pricing.
- Define guardrail metrics (session length, churn) before shipping any experiment.

## Open Questions
- Self-host vs. PostHog Cloud? Cloud is fine for MVP; revisit at scale or if PII enters the model.
- Backend events: send via PostHog Python SDK from FastAPI, or push from frontend only?
- Cost ceiling: free tier covers 1M events/month — battle events at scale could blow this. Sample non-critical events.
- Privacy policy text — needed before public launch even with pseudonymous IDs.
- Mobile/native plans? PostHog has SDKs but event taxonomy should be platform-agnostic now.

## Anti-Goals
- Vanity metrics. DAU without context is noise.
- Tracking everything. Bloated event streams hide signal; curate.
- Decisions in a vacuum. Pair quantitative (PostHog) with qualitative (playtests, surveys) — PostHog surveys can host both.

## Success Criteria
- Every roadmap feature ships with at least one tracked event proving it's used.
- No balance change merged without supporting telemetry.
- Feature flags are the default rollout mechanism, not direct merges to main.
