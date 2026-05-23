# Move Interface vs Pokemon

## Status

Idea.

## Question

Vibemon moves are currently data-first: a `Move` has identity, type, category,
power, accuracy, PP, priority, target, level requirement, effect groups, and a
small declarative `behavior.conditions` surface. This note compares that surface
against mainline Pokemon-style move behavior so future battle work can choose
which gaps are deliberate.

## Current Vibemon Move Surface

Implemented:

- Stable global content id and canonical display-name collision checks.
- Type, category, power, accuracy, PP, priority, target, and level requirement.
- Declarative effects for status infliction, stat stages, drain, recoil,
  weather setting, and healing.
- Triggered effect groups for `on_use`, `on_hit`, and `after_damage`.
- A shared-chance roll per effect group.
- A small condition surface for priority deltas, currently used by turn order.
- Persistence as JSON-backed move definitions with global catalog uniqueness.

Recently removed:

- `script_id` and the first-party move script registry.
- Battle hook registries for damage, accuracy, and end-of-turn phases.
- Unimplemented condition override fields that implied accuracy/power/validity
  behavior the engine did not execute.

## Pokemon-Like Capabilities We Do Not Model

Move execution phases:

- Pre-move legality checks beyond target validity, PP, and simple status gates.
- Charging, recharging, semi-invulnerable turns, multi-turn lock-in, rampage,
  forced repeats, and delayed resolution.
- Interruptible moves such as flinch, protect-style blocking, substitute
  interactions, redirection, snatch/magic-coat-style interception, and pursuit-
  style timing.

Targeting:

- Doubles/triples spread modifiers beyond the simple spread damage flag.
- Adjacent/all field targeting rules, ally targeting, random adjacent target,
  redirectable targets, and target retargeting when the original target faints.
- Terrain/field/side-layer targets such as hazards, screens, rooms, and weather.

Damage formula integration:

- Move-specific power calculation such as weight-based, speed-based, HP-based,
  friendship-based, stat-stage-based, item-based, or previous-turn-based power.
- Move-specific type changes, category changes, critical-hit overrides, defense
  stat selection, fixed damage, percent damage, one-hit KO checks, and level-
  based damage.
- Immunity bypasses and effectiveness rewrites.

Secondary behavior:

- Independent secondary effect rolls rather than one shared group chance only.
- Volatile conditions such as confusion, attraction, taunt, encore, torment,
  disable, leech seed, curse-like effects, bind/trap, perish song, and flinch.
- Side and field effects such as reflect, light screen, safeguard, mist,
  spikes, toxic spikes, stealth rock, trick room, gravity, and terrain.
- Item, ability, and held-object interaction hooks.

State and metadata:

- Move flags: contact, sound, punch, bite, slicing, bullet, powder, dance,
  protectable, mirrorable, snatchable, magic-coatable, thawing, punching, etc.
- Contest metadata, Z-Move/Max Move/Tera-like transformations, and generation-
  specific compatibility.
- Per-move animation/audio presentation metadata separate from battle rules.

Learning and catalog governance:

- Learn methods such as level-up, TM, tutor, egg, evolution, reminder, event, or
  form-specific availability.
- Versioned balance changes across generations.
- Species/form learnset constraints beyond current provider-authored starter
  assignment.

## Implication

The current Vibemon move module is intentionally much smaller than Pokemon's
move interface. That is fine for first playable battles, but we should avoid
adding fields that imply unimplemented engine behavior. The next deepening step
should be one of:

1. Keep moves strictly declarative and grow the effect/condition interpreter only
   when a real move needs the behavior.
2. Reintroduce a script seam only when there are at least two concrete first-
   party moves that cannot be represented declaratively.
3. Add move flags only when another module consumes them, such as contact for an
   ability, sound for a silence effect, or protectable for a protect move.

The deletion test should stay strict: if a move field is persisted but no battle
or presentation module consumes it, it is cruft.
