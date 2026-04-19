# Pokémon Mechanics: Critical Hit Stages

The Critical Hit (Crit) Stage is an internal modifier that determines the probability of an attack dealing 1.5x damage and ignoring defensive stat buffs. Unlike standard stats, Crit Stages cannot be lowered and start at a baseline of 0.

## 1. Probability Table (Gen VI – Present)

| Stage | Crit Ratio | Probability |
| :--- | :--- | :--- |
| **0** | 1/24 | 4.17% |
| **1** | 1/8 | 12.5% |
| **2** | 1/2 | 50.0% |
| **3+** | 1/1 | 100% (Guaranteed) |

## 2. Common Modifiers

Stages are cumulative. You can reach "Guaranteed Crit" status by stacking any combination of the following to reach a total of +3.

### Move Modifiers
* **High-Crit Ratio Moves (+1):** (e.g., *Leaf Blade*, *Stone Edge*, *Slash*, *Shadow Claw*)
* **Fixed-Crit Moves (Max):** Moves like *Surging Strikes* or *Flower Trick* bypass the stage system and always result in a Stage 3+ hit.

### Item Modifiers
* **Scope Lens / Razor Claw (+1):** Boosts the stage of every move used by the holder.
* **Lansat Berry (+2):** Increases stage by +2 when the user's HP falls below 1/4.
* **Leek / Lucky Punch (+2):** Specific to Farfetch'd/Sirfetch'd and Chansey respectively.

### Abilities & Status
* **Super Luck (+1):** Increases the user's crit stage by +1 permanently.
* **Focus Energy (+2):** A status move that increases the user's crit stage by +2 until they switch out.
* **Dire Hit (+2):** An item used in-battle that mimics the effect of Focus Energy.

## 3. Calculation Examples

* **Standard Move + Scope Lens:** 0 (Base) + 1 (Item) = **Stage 1** (12.5% chance)
* **Slash (High-Crit) + Super Luck:** 1 (Move) + 1 (Ability) = **Stage 2** (50% chance)
* **Focus Energy + Scope Lens:** 2 (Status) + 1 (Item) = **Stage 3** (100% chance)