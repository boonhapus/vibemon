# Background Wild Simulation

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | High |
| **Area** | Simulation |
| **Related** | [mon-event-history.md](mon-event-history.md), [geolocation-traversal-and-simulation.md](geolocation-traversal-and-simulation.md) |

## Summary

A background process that runs wild-vs-wild battles among unowned Vibemon, letting the wild population gain XP, level, and evolve on its own between trainer encounters. The XP/evolution *engine* is already disposition-agnostic (implemented in `app/domains/vibemon/progression/`); this doc owns the missing *trigger* and the volume/retention problem it creates.

## Problem

Wild mons are static until a trainer encounters them. With a disposition-agnostic XP engine, wild mons *can* grow — but nothing makes them fight each other, so the wild world has no life of its own and adopted mons always start from `level=1` baseline.

## Concept

A scheduled sim pairs wild mons (by geography/pool), runs battles headlessly, and applies the same XP award as trainer battles. Wild mons evolve automatically (no cancel screen — no one to prompt).

## Open Questions

- **Volume/retention** (the concern flagged in [mon-event-history.md](mon-event-history.md)): per-battle event rows for wild mons that never get adopted could grow unbounded. Batched/lazy XP projection vs per-round rows? Partitioning/retention for un-adopted wild mons?
- Matchmaking: random within a geo pool, strength-banded, or tied to the geolocation simulation?
- Cadence and battle volume — how many wild battles per tick, and what drives the schedule?
- Do sim results need to be replayable/auditable, or is only the net XP/level outcome retained?

## Anti-Goals

- Not a player-visible real-time spectacle in v1 — a background population process.
