# Vibemon XP & Evolution

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | High |
| **Complexity** | Medium |
| **Area** | Meta-Progression |
| **Related** | [mon-event-history.md](mon-event-history.md), [vibe-gold-economy.md](vibe-gold-economy.md), [achievement-system.md](achievement-system.md) |

## Summary

Vibemon gain experience (XP) through battle performance, advancing through evolution tiers that unlock stats, moves, and visuals. XP gains and tier promotions are recorded as events in the [mon event history](mon-event-history.md) so progression is auditable and renderable on a timeline.

## Problem

Battle wins feel isolated. Without an experience curve there is no structured way to reward sustained play, and a Vibemon's growth has no visible arc.

## Concept

Round-based XP with participation credit feeds tier thresholds. Every XP-relevant moment (battle result, level up, move learned, evolution) emits a history event, so the progression system and the timeline view share one source of truth.

## Design

### XP mechanics

- **Round-based XP**: XP is distributed per round won (fainting an opponent), not just at the end of a battle.
- **Participation bonus**: Any Vibemon that appeared in battle receives a share of the total XP.
- **Alumni system**: Released Vibemon continue to exist in an Alumni Roster, potentially gaining passive XP or being recruitable for special missions.

### Evolution tiers

| Stage | Threshold | Rewards |
|-------|-----------|---------|
| **Novice** | 0 XP | Base stats, basic moves |
| **Adept** | 1,000 XP | +10% stats, 1 new move slot |
| **Expert** | 3,000 XP | +20% stats, title change |
| **Master** | 7,500 XP | +30% stats, visual upgrade |

### Event emission

Each mechanic maps onto history events (see [mon-event-history.md](mon-event-history.md)):

- Battle round/result → `battle` event with XP awarded per participant.
- Threshold crossed → `level_up`, then `evolution_attempt` / `evolution`.
- New move slot → `move_learned` (kept or rejected) / `move_forgotten`.

## Open Questions

- Alumni passive XP vs. cosmetic-only alumni — which ships in v1?
- Do wild Vibemon accrue XP from wild-vs-wild battles, or is XP owned-only?
- Is `level` a separate scalar from tier (Rare Candy implies levels), or are tiers the only granularity?

## Anti-Goals

- No full type-effectiveness matrix dependency — tier rewards work with the minimal move bonus model.
