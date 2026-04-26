# Pokémon Move Balance Reference Tables

Official game conventions for move generation. Use as ground truth for balance decisions.

---

## Power / PP / Accuracy Correlation

| Power     | Typical PP | Typical Accuracy | Notes |
|-----------|-----------|-----------------|-------|
| None (Status) | 10–20 | 1.0 or 0.9 | PP depends on utility level |
| 10–30     | 25–40 | 1.0 | Chip damage, almost always hits |
| 40–60     | 20–25 | 1.0 | Early-game bread and butter |
| 65–80     | 15–20 | 1.0 or 0.95 | Standard mid moves |
| 80–100    | 10–15 | 0.9–1.0 | Workhorses (Flamethrower, Surf) |
| 100–110   | 10    | 0.9–1.0 | Reliable high power |
| 110–120   | 5–10  | 0.7–0.9 | Tradeoff: power vs accuracy |
| 120–150   | 5     | 0.7–0.9 | Rare, signature-tier |
| 150+      | 5     | 0.9 | Always has major drawback |

**Key real-world anchors:**
- Tackle: 40 power, 100%, 35 PP
- Flamethrower: 90 power, 100%, 15 PP, 10% burn
- Hyper Beam: 150 power, 90%, 5 PP, recharge next turn
- Ice Beam: 90 power, 100%, 10 PP, 10% freeze
- Thunder: 110 power, 70%, 10 PP, 30% paralysis
- Earthquake: 100 power, 100%, 10 PP
- Focus Blast: 120 power, 70%, 5 PP, 10% Sp. Def drop
- Swords Dance: Status, 100%, 20 PP, +2 Attack self

---

## Secondary Effect Chance Standards

| Chance | Use Case |
|--------|----------|
| `1.0`  | STATUS category moves; guaranteed effects |
| `0.5`  | Effect is central to the move's identity (e.g., Scald's burn) |
| `0.3`  | Standard secondary on a damage move (burn, paralysis, flinch on mid-power) |
| `0.2`  | Secondary on a very powerful move |
| `0.1`  | Rare secondary (flinch on 80+ power moves, freeze chance) |

---

## Stat Change Conventions

| Delta | Meaning |
|-------|---------|
| +1 / -1 | Single stage — common, mild |
| +2 / -2 | Two stages — impactful, less common |
| +3 / -3 | Three stages — almost never; reserved for extreme moves |

Multi-stat changes are possible but rare. Examples:
- Amnesia: +2 Sp. Defense (self)
- Shell Smash: +2 Atk, +2 Sp. Atk, +2 Speed, -1 Def, -1 Sp. Def (self)
- Sticky Web: -1 Speed (target)

---

## Type → Category Tendencies

Most types have a "natural" category. Deviating is fine but should feel intentional.

| Type      | Natural Category | Common Cross |
|-----------|-----------------|--------------|
| NORMAL    | Physical        | Special (hyper beam, etc.) |
| FIRE      | Special         | Physical (flare blitz, etc.) |
| WATER     | Special         | Physical (waterfall, etc.) |
| ELECTRIC  | Special         | Physical (wild charge, etc.) |
| GRASS     | Special         | Physical (wood hammer, etc.) |
| ICE       | Special         | Physical (ice punch, etc.) |
| FIGHTING  | Physical        | — |
| POISON    | Physical        | Special (sludge bomb, etc.) |
| GROUND    | Physical        | — |
| FLYING    | Physical        | Special (air slash, etc.) |
| PSYCHIC   | Special         | — |
| BUG       | Physical        | Special (bug buzz, etc.) |
| ROCK      | Physical        | — |
| GHOST     | Physical        | Special (shadow ball, etc.) |
| DRAGON    | Special         | Physical (outrage, etc.) |
| DARK      | Physical        | Special (dark pulse, etc.) |
| STEEL     | Physical        | Special (flash cannon, etc.) |
| FAIRY     | Special         | Physical (play rough, etc.) |

---

## Status Move PP by Utility

| Utility Level | Example | PP |
|---------------|---------|-----|
| Very high (team staple) | Stealth Rock, Swords Dance | 20 |
| High (reliable condition) | Will-O-Wisp, Thunder Wave | 15 |
| Niche or situational | Curse, Trick Room | 10 |
| High-risk/reward | Sleep Powder (70% acc) | 15 |

---

## Level Requirement Guidelines

These are soft guidelines for when a monster learns the move naturally:

| Power / Utility          | Level Range |
|--------------------------|-------------|
| Status (utility/support) | 1–25 |
| Weak damage (≤50 power)  | 1–20 |
| Mid damage (60–80 power) | 15–35 |
| Strong damage (80–100)   | 30–45 |
| Very strong (100–120)    | 40–55 |
| Signature / 120+         | 50–65 |

---

## Common Effect Combinations by Theme

| Theme             | Suggested Status | Suggested Stat Changes |
|-------------------|-----------------|------------------------|
| Fire / Volcanic   | BURN            | -1 Sp. Defense (target) |
| Ice / Blizzard    | FREEZE          | -1 Speed (target) |
| Electric / Storm  | PARALYSIS       | -1 Speed or -1 Accuracy |
| Toxic / Poison    | POISON or BAD_POISON | -1 Defense |
| Sleep / Dream     | SLEEP           | — |
| Dark / Shadow     | — (no status)   | -1 Accuracy or -1 Sp. Defense |
| Fighting / Force  | — (no status)   | +1 Attack self, -1 Defense target |
| Psychic / Mind    | — or PARALYSIS  | -2 Sp. Defense or -1 Speed |
| Rock / Earth      | — (no status)   | -1 Speed (target) |
| Fairy / Enchant   | — or SLEEP      | -2 Attack (target) |
