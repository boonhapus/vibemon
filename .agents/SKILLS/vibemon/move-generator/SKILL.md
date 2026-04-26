---
name: move-generator
description: >
  Generates thematic, balanced Vibemon moves as Python dataclass instances, ready to
  copy-paste into the codebase. Triggers on phrases like "generate moves", "create
  Vibemon moves", "I need moves with a [theme] theme", or anything describing move
  creation for Vibemon.
metadata:
  version: 1.0.0
---

# Vibemon Move Generator

Generates thematic, convention-accurate Vibemon moves as ready-to-use Python dataclass instances.

---

## Step 1 — Gather Inputs

Ask these two questions **together in a single message** (use the `ask_user_input` tool if available):

1. **Theme** — What is the theme of these moves? (e.g., "volcanic eruption", "ancient runes", "deep sea", "cyberpunk electricity")
2. **Count** — How many moves should be generated? (typical range: 1–20)

If the user has already answered either question in the conversation, do not re-ask it.

---

## Step 2 — Plan the Move Set

Before writing any code, silently plan the batch so the set feels cohesive and balanced:

- **Type coverage**: lean into the theme's most natural type(s), but allow 1–2 surprises
- **Category spread**: aim for roughly 50% Physical/Special, 20–30% Status across batches of 5+
- **Power tier spread**: include weak, mid, and strong moves; avoid making everything high-power
- **Effect variety**: vary which moves have effects; not every move needs one

See `references/balance-tables.md` for official stat ranges and effect chance conventions.

---

## Step 3 — Generate Each Move

For every move, follow these rules:

### Naming
- Name should feel like an official Pokémon move: 1–3 words, evocative, thematic
- Avoid names that are too generic ("Fire Attack") or too wordy ("Massive Burning Inferno Blast")

### Flavor Text
- One sentence, written in the style of official Pokédex/move descriptions
- Present tense, vivid, references the move's visual effect
- Example: *"The user hurls a superheated boulder that sears the target on impact."*

### Type
Must be one of the 18 canonical types. Match the theme as naturally as possible.

### Category
- **PHYSICAL**: Contact moves, claws, tackles, physical force — uses Attack/Defense
- **SPECIAL**: Energy/elemental projection — uses Sp. Attack/Sp. Defense  
- **STATUS**: No damage; inflicts conditions, boosts, or debuffs

### Power (`int | None`)
Follow these official conventions:

| Power Range | Tier        | Notes                              |
|-------------|-------------|-------------------------------------|
| `None`      | Status      | Required for STATUS moves           |
| 10–40       | Very Weak   | High PP (25–35), often with effect  |
| 40–60       | Weak        | High PP (20–25)                     |
| 60–80       | Mid         | Standard PP (10–20)                 |
| 80–100      | Strong      | Lower PP (5–15)                     |
| 100–120     | Very Strong | Low PP (5–10), often has a drawback |
| 120–150+    | Signature   | Very low PP (5), rare effects       |

### Accuracy (`float | None`)
- `1.0` = 100% — default for most moves
- `0.9` = 90% — moves with high power or great effects
- `0.85` = 85% — strong moves (e.g., Blizzard tier)
- `0.7` = 70% — high-risk moves (e.g., Focus Blast, Stone Edge)
- `None` = never misses (e.g., Swift, Aerial Ace equivalents)

### PP (`int`)
Use standard PP values: 5, 10, 15, 20, 25, 30, 35, 40. Match to power tier (see table above).

### Effect (`MoveEffect | None`)
- Decide freely based on category and theme — do not force an effect if it doesn't fit
- **STATUS moves**: must have an effect (that's their purpose)
- **PHYSICAL/SPECIAL**: include an effect when thematically natural (burning fire move, paralyzing lightning, etc.)
- Effect chance conventions:
  - `1.0` — guaranteed (STATUS moves)
  - `0.3` — standard secondary chance (30% burn, paralysis, etc.)
  - `0.1` — rare secondary (flinch on powerful moves)
  - `0.5` — moderate (move's secondary is a core part of its identity)
- Stat changes use `int` deltas: `+1`, `+2`, `-1`, `-2` (rarely ±3)
- `target_self=True` for self-buffs; `target_self=False` (default) for debuffs on the target

### Level Requirement (`int`)
- 1 for basic/early moves
- 10–20 for mid-power moves
- 30–50 for strong moves
- 50+ for signature or extremely powerful moves

---

## Step 4 — Output Format

Output all moves as **Python dataclass instances**, ready to copy-paste. Always include the full import block at the top, followed by each move as a named variable.

```python
from dataclasses import dataclass
from typing import Literal

# --- (paste your MoveEffect and Move dataclass definitions here) ---

# Generated Moves — Theme: Volcanic Fury

magma_surge = Move(
    name="Magma Surge",
    flavor_text="The user unleashes a torrent of molten rock that scorches the target.",
    type=FIRE,
    category=SPECIAL,
    power=85,
    accuracy=0.9,
    pp=10,
    effect=MoveEffect(
        status_inflict=BURN,
        stat_changes={},
        target_self=False,
        chance=0.3,
    ),
    level_requirement=36,
)
```

- Use `snake_case` variable names derived from the move name
- Include a comment header: `# Generated Moves — Theme: <theme>`
- Omit fields that match their defaults (`accuracy=1.0`, `pp=10`, `effect=None`, `level_requirement=1`) **only if** the value is the dataclass default — otherwise always include them
- After the code block, include a brief **Move Summary Table** in Markdown for quick human scanning:

| Name | Type | Cat | Power | Acc | PP | Effect |
|------|------|-----|-------|-----|----|--------|
| Magma Surge | FIRE | Special | 85 | 90% | 10 | 30% Burn |

---

## Quality Checklist

Before outputting, verify each move:
- [ ] Name is 1–3 words and feels like an official Pokémon move name
- [ ] Flavor text is one vivid sentence in Pokédex style
- [ ] Power/PP/Accuracy are internally consistent with the balance tables
- [ ] STATUS moves have `power=None` and a non-None `effect`
- [ ] Effect chances use standard values (0.1, 0.3, 0.5, 1.0)
- [ ] The full batch has variety in category, power tier, and effect type
- [ ] Level requirements scale with power

---

## Reference Files

- `references/balance-tables.md` — Official stat ranges, PP conventions, effect chance norms, type-category tendencies. **Read this before generating any moves** if you are uncertain about balance values.
