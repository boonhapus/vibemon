# Mon Event History

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | High |
| **Complexity** | Medium |
| **Area** | Core Data Model |
| **Related** | [vibe-gold-economy.md](vibe-gold-economy.md), [achievement-system.md](achievement-system.md) |

## Summary

Every Vibemon — owned, wild, or expired — accumulates an append-only event history from birth onward. The history powers a timeline view for any mon, and doubles as the source of truth for XP accrual and battle records instead of bolting counters onto the entity.

## Problem

A Vibemon's state today is a snapshot: disposition (`owned` / `wild` / `expired`), stats, moves. There is no record of *how it got there* — no battle record, no XP ledger, no trail from birth through adoption to release or expiry. Adding XP and win/loss tracking as plain columns would lose the narrative and make retroactive features (timelines, achievements, alumni) impossible.

## Concept

An append-only event ledger keyed by Vibemon ID. Each event has a type, timestamp, and type-specific payload. Derived values (current XP, level, battle record) are projections over the ledger — recomputable, never hand-edited. Disposition transitions (`owned` / `wild` / `expired`) become consequences of events rather than parallel state.

## Design

### Core event catalog

| Event | Payload sketch | Notes |
|-------|---------------|-------|
| `birth` | provider, seed/snapshot ref, location | First event for every mon; anchors the timeline. |
| `adoption` | trainer id, crew slot, encounter ref | Wild → owned. |
| `release` | trainer id, reason (crew full, voluntary) | Owned → wild (or alumni). |
| `battle` | battle id, format (`owned_vs_trainer` / `wild_vs_wild` / `wild_vs_trainer`), result, rounds, XP awarded | One event per participant per battle. |
| `level_up` | new level, source (`battle` / `item`) | Distinguish candy from earned. |
| `move_learned` | move id, outcome (`kept` / `rejected`), replaced move | Rejected offers still recorded. |
| `move_forgotten` | move id, reason | |
| `evolution_attempt` | target tier, success flag, reason if failed | |
| `evolution` | from tier → to tier, stat/visual changes | |
| `expire` | cause (wild expiration window, other) | Terminal for wild mons. |

### Candidate additional events

Events worth considering beyond the core set:

| Event | Why |
|-------|-----|
| `tier_promotion` | If tiers and levels are separate scalars, threshold crossings (Novice → Adept) deserve their own event distinct from `level_up`. |
| `candidate_rejected` | Adoption candidate review already has a rejected/expired path (`win_no_adopt`); a mon that was *almost* adopted is timeline-worthy. |
| `encounter` | Wild mon sighted/engaged by a trainer but battle never started, or trainer fled. Gives wild mons a life story between birth and adoption/expiry. |
| `flee` | Mon (or trainer) fled an in-progress battle — different from a loss. |
| `item_used` | Rare Candy, future consumables targeted at a mon. Source attribution for `level_up`. |
| `rename` | Nickname changes, if/when supported. |
| `crew_change` | Moved between crew slots / formation changes (see crew-clock idea) without full release. |
| `heal` / `faint_recovery` | If fainting persists outside battle scope. |
| `alumni_recruited` | Released mon recalled for a special mission (alumni system). |
| `achievement_earned` | Achievements attributed to a specific mon rather than the trainer. |
| `migration` | Wild mon relocated (geolocation/simulation features). |
| `rebalance` | Dev-tuning replay altered derived stats from the frozen BirthSnapshot. Flagged as a system event, hidden from player timelines by default. |

### Invariants

- Ledger is append-only; corrections are new events, never edits.
- `birth` is always first; `expire` (wild) is terminal — no events after, except system events like `rebalance`.
- Disposition is derivable: latest of `birth`/`adoption`/`release`/`expire` determines `wild`/`owned`/`expired`.
- Battle XP totals on the mon must equal the sum of `battle` event XP plus `item_used` adjustments.

### Timeline view

Any mon's detail page renders the ledger chronologically: owned mons show their journey with a trainer; wild mons show sightings, wild-vs-wild battles, and eventual adoption or expiry. System events (`rebalance`) are filtered out of the player-facing view.

## Implementation

1. **Schema**: single `vibemon_event` table (mon id, type, occurred_at, JSON payload) — start permissive, tighten payloads per type as they stabilize.
2. **Emit on existing flows first**: birth (generation), adoption, release, expiry are already implemented flows — wire emission there before XP exists.
3. **Battle events** land with battle-result tracking; XP projection is implemented in `app/domains/vibemon/progression/`.
4. **Backfill**: existing mons get a synthetic `birth` event from their BirthSnapshot; adoption state backfilled from current disposition where derivable.
5. **Timeline UI** last, once a few event types exist.

## Open Questions

- One ledger table with JSON payloads vs. typed tables per event family?
- Do wild-vs-wild battles run as a background simulation, and at what volume — does the ledger need partitioning/retention for wild mons that never get adopted?
- Are rejected move offers (`move_learned` with `rejected`) player-visible or internal only?
- Event versioning: payload schemas will evolve — version field per event, or migrate-on-read?

## Success Criteria

- Any mon (owned, wild, expired) renders a complete, ordered timeline from birth.
- Current XP, level, and battle record are reproducible purely from the ledger.

## Anti-Goals

- Not a general analytics/event bus — player-meaningful mon lifecycle only (PostHog idea covers analytics).
- Not event sourcing for the whole entity: aesthetics, brand, and base stats stay snapshot-based; the ledger records *changes*, it does not replace BirthSnapshot.
