# Type System Architecture

## Current State
- **ELEMENT_CHART**: Offensive type effectiveness matrix (inherited from Pokémon)
- **Vibemon elements**: Dynamic, can have 1-3 types per vibemon (unlike Pokémon's fixed dual-type)
- **Move types**: 18 types, each move has exactly one type

## Problem Statement
Type relationships currently only influence **battle mechanics**. However, types should drive decisions across multiple systems:
1. Move assignment (which moves get assigned to which vibemon)
2. Team building (what type coverage does a trainer need)
3. Evolution paths (do types influence evolution outcomes)
4. Progression (which moves should be available at what level)
5. Affinity generation (when creating a new vibemon, should types guide move pools)

## Vision: Unified Type Relationship System

### Phase 1: Move Assignment (CURRENT)
**Goal**: Assign moves to vibemon with type-aware weighting

**Minimal implementation** (`get_move_assignment_bonus`):
- Same type match → 2.0x bonus
- Normal type → 1.0x (utility coverage, no bonus)
- Mismatched → 0.5x (antagonistic)

**Next step**: Evolve to include coverage bonuses:
- Coverage (move covers vibemon's defensive weakness) → 1.5x

### Phase 2: Coverage Matrix
Derive from ELEMENT_CHART:
- **Offensive coverage**: What types does this type beat? (already in ELEMENT_CHART)
- **Defensive coverage**: What types beat this type? (reverse of ELEMENT_CHART)
- **Synergy pairs**: Which type combinations create good defensive coverage together?
  - Example: Fire + Water = Fire covers Grass weakness, Water covers Fire's weakness

**Implementation approach**:
```python
TYPE_AFFINITIES = {
    FIRE: {
        "covers": [GRASS, BUG, ICE, STEEL],  # super-effective against
        "weak_to": [WATER, GROUND, ROCK],     # takes super-damage from
        "resists": [FIRE, GRASS, ICE, BUG, STEEL, FAIRY],  # reduces damage
        "synergies": [WATER, ROCK, ...],      # good defensive partner types
    },
    # ... for all 18 types
}
```

**Use cases**:
- Move assignment: prefer moves that cover weaknesses (1.5x bonus)
- UI tooltips: show what types this vibemon is weak to / strong against
- Team building: suggest type coverage gaps

### Phase 3: Progression & Evolution
**Goal**: Let type system influence level-up moves and evolution

**Questions to answer**:
- Do certain types only learn certain move types at certain levels?
- Do type combinations influence evolution branches?
- Should trainers with balanced type coverage progress faster?

### Phase 4: Affinity Generation
**Goal**: When generating new vibemon affinities, respect type synergies

**Current behavior**: Moves assigned semi-randomly, leading to 45% antagonistic moves

**Desired behavior**: Use TYPE_AFFINITIES to prefer:
1. Same-type moves
2. Coverage moves (fills gaps)
3. Discourage antagonistic moves

## Implementation Order
1. ✅ **Phase 1a** (DONE): Add `get_move_assignment_bonus` to element_chart.py
2. **Phase 1b** (TODO): Wire `get_move_assignment_bonus` into move assignment logic
3. **Phase 2a** (TODO): Build TYPE_AFFINITIES from ELEMENT_CHART
4. **Phase 2b** (TODO): Update move assignment to use coverage bonuses
5. **Phase 2c** (TODO): Add UI/tooltips showing type matchups
6. **Phase 3** (TODO): Design evolution/progression type interactions
7. **Phase 4** (TODO): Integrate type affinities into affinity generation

## Data Sources
- `ELEMENT_CHART` in `backend/app/balance/element_chart.py`: Offensive matchups
- `VibemonTypeT` enum in `backend/app/types.py`: Type definitions
- Move assignment logic: TBD (check genai/_image.py or models.py for generation pipeline)

## Open Questions
- Should synergy bonuses be symmetric? (Fire/Water both good together, or one-way?)
- How many moves should a vibemon have? Does type coverage influence this?
- Should type affinities influence stat generation?
- Do we want "type specialists" (high same-type moves) vs "type versatilists"?
