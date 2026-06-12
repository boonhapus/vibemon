# Generative Aesthetics & Showcase

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Low |
| **Complexity** | Medium |
| **Area** | Visual Identity & Pride |
| **Related** | [vibe-gold-economy.md](vibe-gold-economy.md), [achievement-system.md](achievement-system.md), [sprite-anatomy-system.md](sprite-anatomy-system.md) |

## Summary

Make **Vibemon** feel alive beyond static sprite sheets: dynamic idle and battle motion, an Alumni Roster that memorializes the trainer journey, and cosmetic customization purchased with **Vibe Gold** — all without battle power creep.

## Problem

Static sprite sheets are a strong start, but the product lacks interactive visuals and a durable way to celebrate a trainer's history. Journey milestones and released **Vibemon** deserve a showcase, not a discard pile.

## Concept

Three layers of pride and polish:

1. **AI-animated sprites** — breathing idle loops, battle reactions, and optional elemental auras.
2. **Alumni Roster** — every **Vibemon** ever owned, with stats, trophies, and social export.
3. **Aesthetic customization** — palette, audio, and frame cosmetics sold for VG.

## Design

### AI-animated sprites

Move beyond static PNGs to dynamic idle and battle animations.

- **Idle animations**: AI video generation or procedural transforms for breathing, swaying, or floating on the center pose.
- **Battle reactions**: animations for taking damage, attacking, or fainting.
- **Elemental auras**: purchasable overlays (Fire, Sparkles, Dark) tied to type and role.

### Alumni Roster (showcase)

A dedicated UI for all **Vibemon** ever owned, including released or traded ones.

- **Trophies & titles**: milestones (e.g., "First Mythical," "Champion of Route 7").
- **Stat tracking**: total wins, damage dealt, and XP across the **Vibemon**'s history.
- **Export for socials**: share button that generates a polished Trainer Card with crew aesthetics and stats.

### Aesthetic customization

Non-pay-to-win items in the shop for **Vibe Gold**.

- **Shiny Spray**: permanent palette-swap overlay.
- **Battle Cry Remix**: re-prompt the generative audio engine for a new style.
- **Showcase frames**: rare borders for Alumni Roster or Trainer Card.

## Open Questions

- AI video vs. CSS/procedural idle for v1 cost and quality bar?
- Alumni stats: authoritative from backend battle log or aggregated client-side?
- Share export format: static image, short video, or both?
