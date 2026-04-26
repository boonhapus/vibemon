# Ideas

## Period: HM System & Travel

### Idea: Hidden Move (HM) System for Location Travel

**Problem Statement**
Players need a way to travel between different geographic areas to encounter new Vibemon. The HM system lets Vibemon learn travel abilities (like Fly, Surf) that unlock new areas.

---

## Core Concept

Hidden Moves (HMs) are special abilities that:
- **Can only be taught** to Vibemon that can learn them (based on type/line)
- **Persist on the Vibemon** once learned (unlike TMs which are consumable)
- **Unlock world traversal** (areas, water, caves, etc.)
- **Must be used** to access certain regions

---

## HM Move Roster

| HM | Name | Effect | Unlocks | Learnable By |
|----|------|--------|---------|--------------|
| HM01 | **Fly** | Transport to previously visited areas | Air travel, new routes | Flying types, certain evolved forms |
| HM02 | **Surf** | Travel across water | Oceans, lakes, rivers | Water types |
| HM03 | **Rock Climb** | Scale steep surfaces | Mountain paths, cliff faces | Rock/Steel types |
| HM04 | **Strength** | Push heavy objects | Move boulders, open paths | Strong types (high ATK) |
| HM05 | **Flash** | Illuminate dark areas | Caves, dark zones | Light-emitting types |
| HM06 | **Dive** | Swim underwater | Underwater zones, coral reefs | Water types (Stage 2+) |
| HM07 | **Teleport** | Instant return to base | Quick recall | Psychic types |
| HM08 | **Nature Walk** | Calm wild Vibemon | Peaceful routes, rare spawns | Nature/Grass types |

---

## Implementation Details

### Teaching HMs

```
┌─────────────────────────────────────────────────────────────────┐
│  TEACH HIDDEN MOVE                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                                                │
│  │             │  Which move would you like to teach?            │
│  │  VULPIX     │                                                 │
│  │  🔥 Lv.24   │  ┌─────────────────────────────────────────┐   │
│  │             │  │  ✈️ FLY         [Not Learned]            │   │
│  │             │  │  Required: Flying-type or evolved form   │   │
│  └─────────────┘  │  Unlocks: Air travel to Route 5, etc.     │   │
│                   └─────────────────────────────────────────┘   │
│                   ┌─────────────────────────────────────────┐   │
│                   │  🌊 SURF        [Grayed Out]             │   │
│                   │  Vulpix cannot learn this move.          │   │
│                   └─────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Location Unlock Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  CURRENT: Oak Town                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│     [Route 2] ←──── ✈️ FLY AVAILABLE                           │
│        │          (Unlocked by: Flare Wolf learning Fly)        │
│        │                                                          │
│     [Route 3]                                                     │
│        │                                                          │
│     [🌊 Ocean] ←── SURF REQUIRED                                │
│                  (Flare Wolf cannot learn Surf)                 │
│                                                                  │
│  ────────────────────────────────────────────────────────────    │
│  💡 Tip: Vulpix (Fire) cannot learn Surf. Try evolving to        │
│     Flare Wolf for more move options!                           │
└─────────────────────────────────────────────────────────────────┘
```

### Travel System

#### Area Selection UI
```
┌─────────────────────────────────────────────────────────────────┐
│  ✈️ FLY - Select Destination                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ★ Oak Town          (Current Location)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Route 2             🌿 Common Vibemon    [UNLOCKED]     │    │
│  │  Route 3             🌿🌿 Uncommon       [UNLOCKED]      │    │
│  │  Route 4             🌿🌿🌿 Rare          [UNLOCKED]      │    │
│  │  Route 5             🌿🌿🌿 Rare          [FLY REQUIRED]  │    │
│  │  🌊 Coral Bay        🌊 Aquatic Vibemon   [FLY + SURF]    │    │
│  │  ⛰️ Mt. Ironpeak     ⛰️ Rock/Steel       [FLY + CLIMB]  │    │
│  │  🌑 Dark Hollow     👻 Rare Ghost       [FLY + FLASH]   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [Selected Vibemon with Fly: Flare Wolf]                        │
└─────────────────────────────────────────────────────────────────┘
```

### Area Types & Vibemon Distribution

| Area Type | Available HMs | Vibemon Types Found |
|-----------|---------------|-------------------|
| **Plains/Fields** | None | Grass, Normal, Bug |
| **Forests** | None | Grass, Poison, Bug, Ghost |
| **Mountains** | Rock Climb | Rock, Steel, Flying, Fire |
| **Oceans/Lakes** | Surf, Dive | Water, Ice, Electric |
| **Caves** | Flash, Rock Climb | Rock, Ground, Dark, Ghost |
| **Towns** | None | (Trading, healing, shops) |
| **Sky Islands** | Fly | Flying, Dragon, Psychic |
| **Volcanic Zones** | None | Fire, Rock |
| **Ancient Ruins** | All HMs | All types, Legendaries |

---

## Data Model

```python
@dataclass
class HiddenMove:
    id: str  # "HM01"
    name: str  # "Fly"
    description: str
    effect_type: MoveEffectType  # TELEPORT, TERRAIN_MODIFY, etc.
    unlocks_area_types: list[AreaType]
    required_vibemon_types: list[VibemonType]

@dataclass
class Vibemon:
    # ... existing fields
    known_hms: list[str]  # ["HM01", "HM04"]

@dataclass
class AreaUnlock:
    area_id: str
    required_hms: list[str]
    unlocked_by: list[str]  # vibemon_ids that know required HMs
    is_accessible: bool
```

### Progression Gate

```
Area Access = All(Required HMs Learned)

Example: Coral Bay requires:
  - Surf (learned by any water-type Vibemon)
  - Fly (to reach the area)
  
  Result: Flare Wolf cannot help → need a water-type with Fly
```

---

## UI/UX Features

### HM Notification
```
┌────────────────────────────��────────────────────────────────────┐
│  🎉 NEW MOVE LEARNED!                                           │
│                                                                  │
│  ✈️ FLY - Now you can travel to new areas!                       │
│                                                                  │
│  New areas unlocked:                                             │
│    • Sky Islands (rare Flying Vibemon)                           │
│    • Route 5 ( evolved Fire types)                              │
│                                                                  │
│  [View Travel Menu]  [Continue]                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Area Preview
Before traveling, show what's available:
- Vibemon encounter table for the area
- Required HMs
- Special features (shops, trainers, story events)

---

## Integration Points

| System | Integration |
|--------|-------------|
| **Encounter System** | Different areas = different Vibemon pools |
| **Showcase Mode** | "Seen in [Area]" filter |
| **Battle Record** | Track which areas have been explored |
| **Evolution System** | Some HMs require evolved forms |

---

**Priority**: High
**Complexity**: Medium
**Related Ideas**: vibemon-showcase-mode.md, battle-record-system.md