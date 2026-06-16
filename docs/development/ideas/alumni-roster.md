# Alumni Roster

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Low |
| **Complexity** | Low |
| **Area** | Meta-Progression |
| **Related** | [mon-event-history.md](mon-event-history.md) |

## Summary

A read-only "former crew" roster: every Vibemon that was once owned by a trainer and later released stays viewable as an alumnus. Pure lens over data that already persists — released mons keep their rows; only their disposition flips.

## Problem

Releasing an invested mon makes it feel like it vanished. There is no surface for "mons that used to be mine," so player attachment and history are lost at release.

## Concept

Filter/query over already-persisted released mons keyed by their former `trainer_id` (recoverable from history events: `adoption` → `release`). No new mechanic, no background process — a view.

## Anti-Goals (lifted out of the XP doc deliberately)

- **No passive XP.** Alumni do not level on their own. That would need a background write path with no battle to anchor it — explicitly cut.
- **No mission recruitment.** "Recall an alumnus for a special mission" depends on a missions system that does not exist; cut.

## Open Questions

- Does release sever `trainer_id` immediately (current behavior)? If so, the former-owner link must come from the history ledger rather than a live FK.
- Expired (wild-expiration) mons: alumni or excluded?
