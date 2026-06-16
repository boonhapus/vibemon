# Vibe Gold & World Economy

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | High |
| **Area** | Economy |
| **Related** | [geolocation-traversal-and-simulation.md](geolocation-traversal-and-simulation.md), [achievement-system.md](achievement-system.md) |

## Summary

**Vibe Gold (VG)** is a wagering and shop currency that adds competitive risk and purchasable utility on top of the XP loop. Trainers stake VG on battles and spend it on consumables and travel items.

## Problem

Battles have no stakes beyond the result itself, and there is no sink/source loop to reward competitive risk-taking or gate utility features like simulated travel.

## Concept

Two coupled systems: pre-battle **wagering** with escrow and a fairness hint, and a **shop** that recycles VG into consumables and utility items.

## Design

### Wagering

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

Items applied to a specific Vibemon (e.g., Rare Candy) should emit an `item_used` event in the [mon event history](mon-event-history.md) so candy-driven level ups are distinguishable from battle-earned ones.

## Open Questions

- Win-probability engine: show exact % or qualitative bands?
- Shop inventory rotation vs. static catalog at launch?
- VG sources beyond wagering — battle payouts, achievements, daily play?
