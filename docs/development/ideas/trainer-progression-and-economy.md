# Trainer Progression & World Economy

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | High |
| **Complexity** | High |
| **Area** | Meta-Progression & Economy |
| **Related** | [geolocation-traversal-and-simulation.md](geolocation-traversal-and-simulation.md), [achievement-system.md](achievement-system.md), [generative-aesthetics-and-showcase.md](generative-aesthetics-and-showcase.md) |

## Summary

Introduce a unified XP loop, **Vibe Gold** wagering, and a shop so trainers have long-term goals beyond individual battles. Performance in battle and competitive risk feed meta-progression through evolution tiers and purchasable utility items.

## Problem

Players need long-term goals beyond individual battles. Without a shared economy and experience curve, battle wins feel isolated and there is no structured way to reward sustained play or competitive risk-taking.

## Concept

Three coupled systems:

1. **Experience & evolution** — round-based XP, participation credit, and tier thresholds that unlock stats, moves, and visuals.
2. **Vibe Gold & wagering** — optional pre-battle stakes with escrow and a win-probability hint so trainers can assess fairness.
3. **Shop** — consumables and utility purchased with VG, including items that gate simulated travel and encounter boosts.

## Design

### Experience & evolution

**Vibemon** gain experience (XP) through battle performance.

**XP mechanics**

- **Round-based XP**: XP is distributed per round won (fainting an opponent), not just at the end of a battle.
- **Participation bonus**: Any **Vibemon** that appeared in battle receives a share of the total XP.
- **Alumni system**: Released **Vibemon** continue to exist in an Alumni Roster, potentially gaining passive XP or being recruitable for special missions.

**Evolution tiers**

| Stage | Threshold | Rewards |
|-------|-----------|---------|
| **Novice** | 0 XP | Base stats, basic moves |
| **Adept** | 1,000 XP | +10% stats, 1 new move slot |
| **Expert** | 3,000 XP | +20% stats, title change |
| **Master** | 7,500 XP | +30% stats, visual upgrade |

### Vibe Gold (VG) & wagering

A risk-reward layer for competitive play.

**Wagering**

- Before a battle, trainers can negotiate stakes (Vibe Gold).
- **Asymmetrical stakes** are allowed (e.g., 500 VG vs 100 VG).
- **Win probability engine**: the system calculates win probability from crew BST, levels, and type advantages so trainers can assess wager fairness.
- **Escrow**: VG is locked at battle start and awarded to the winner.

### In-game shop

Items categorized into consumables and utility.

| Item | Cost (VG) | Effect |
|------|-----------|--------|
| **Rare Candy** | 1,000 | Increases **Vibemon** level by 1. |
| **Teleport Capsule** | 200 | Return to home base instantly. |
| **Mythical Increaser** | 5,000 | Boosts Mythical encounter odds for 4 hours. |
| **Simulation Voucher** | 2,500 | One **Simulated Travel** session (see [geolocation idea](geolocation-traversal-and-simulation.md)). |

## Open Questions

- Alumni passive XP vs. cosmetic-only alumni — which ships in v1?
- Win-probability engine: show exact % or qualitative bands?
- Shop inventory rotation vs. static catalog at launch?
