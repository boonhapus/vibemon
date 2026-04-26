# Ideas

## Period: Vibemon Showcase Mode

### Idea: Encyclopedia & Showcase of Seen Vibemon

**Problem Statement**
Players want to share their Vibemon journey and view all Vibemon they've encountered in a polished showcase mode that integrates animations, sounds, and battle history.

---

## Core Features

### Encyclopedia View (Primary Mode)

```
┌─────────────────────────────────────────────────────────────────┐
│  📖 VIBEMON ENCYCLOPEDIA                          [⚙️ Settings] │
├─────────────────────────────────────────────────────────────────┤
│  Search: [________________]   Filter: [All Types ▼] [★ Rarity] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐│
│  │              │ │              │ │              │ │          ││
│  │  [ANIMATED]  │ │  [ANIMATED]  │ │  [ANIMATED]  │ │ [ANIMAT] ││
│  │   Vulpix     │ │   Flare Wolf  │ │   Charmander │ │ Eevee   ││
│  │              │ │              │ │              │ │          ││
│  │   🔥 Fire    │ │   🔥 Fire    │ │   🔥 Fire    │ │ 🌿 Norm ││
│  │  ★★★ Rarity │ │  ★★★★ Rarity│ │  ★★ Rarity  │ │ ★ Rarity ││
│  │  [🐕 Caught] │ │  [🐕 Caught] │ │  [❌ Missed] │ │[🐕 Caugh]││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘│
│                                                                  │
│  Page 1 of 25  ◀ ▶                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Card Detail View (On Click)

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Encyclopedia                    [🔊 Play Cry] [▶ Anim]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────┐  VULPIX                              │
│  │                       │  🔥 Fire Type                        │
│  │   [ANIMATED SPRITE]   │  ★★★ Rare                           │
│  │    (idle animation)   │                                      │
│  │                       │  ──────────────────────────          │
│  │                       │  ENCOUNTER #1                       │
│  │                       │  Trainer: Professor Oak             │
│  │                       │  Location: Route 7                   │
│  │                       │  Result: 🏆 Caught                  │
│  │                       │  Date: Apr 22, 2026                  │
│  │                       │  Caught by: Vulpix                   │
│  └───────────────────────┘                                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  BASE STATS              │  EVOLUTION LINE                  │ │
│  │  HP: 38                  │                                  │ │
│  │  Attack: 41              │  Vulpix ──▶ Flare Wolf ──▶       │ │
│  │  Defense: 40             │  Blazefang                      │ │
│  │  Speed: 65               │                                  │ │
│  │                          │  [Seen 3/3 in line]               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  BATTLE STATISTICS                                          │ │
│  │  Times Faced: 12 | Times Caught: 3 | Escape Rate: 25%      │ │
│  │  Last Seen: 2 days ago (Professor Oak, Route 12)           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## View Modes

### 1. Grid View (Default)
- 4-column responsive grid
- Animated sprite on hover
- Quick stats on card back
- Drag to reorder favorites

### 2. List View
- Compact rows with key info
- Sortable columns
- Bulk actions (select multiple)

### 3. Carousel View
- One Vibemon at a time
- Swipe/arrow navigation
- Large animation + sound

### 4. Comparison Mode
- Side-by-side two Vibemon
- Stats overlay comparison
- Type effectiveness indicator

---

## Filters & Sorting

### Filters
| Filter | Options |
|--------|---------|
| Type | Fire, Water, Grass, Electric, Normal, etc. |
| Rarity | ★ to ★★★★★ |
| Status | Caught, Missed, Never Seen |
| Evolution Stage | Baby, Basic, Stage 1, Stage 2, Final |
| Location | (Area names) |

### Sorting
- Alphabetical (A-Z, Z-A)
- Seen Date (Newest, Oldest)
- Rarity (Highest, Lowest)
- Stats (Total, HP, Attack, Speed)
- Dex Number

---

## Display Elements Per Vibemon

| Element | Source | Notes |
|---------|--------|-------|
| Animated Sprite | vibemon-animation-system.md | Idle animation, click for action |
| Sound/Cry | vibemon-sound-generation.md | Click or hover |
| Caught Status | battle-record-system.md | 🏆 Caught / ❌ Missed / ❓ Never Seen |
| Last Seen Info | battle-record-system.md | Trainer, location, date |
| Stats | Vibemon data model | Base + current level stats |
| Evolution Line | Vibemon data model | Progress through line |
| Encounters | battle-record-system.md | Count, win rate |

---

## Share Feature

### Export Options
1. **Screenshot**: Capture current view as PNG
2. **Share Link**: Public page with showcase URL
3. **Compare Link**: Share comparison of two Vibemon
4. **Badge**: Generate "Seen X% of Vibemon" badge

### Share Page Design
```
┌─────────────────────────────────────────┐
│  Marcus's Vibemon Showcase              │
│  "Fire type collector"                 │
├─────────────────────────────────────────┤
│                                         │
│  Stats:                                 │
│  📖 247/500 Vibemon Seen                │
│  🏆 89 Caught                           │
│  🔥 Most Common: Fire Type (34)        │
│                                         │
│  Top Encounters:                       │
│  1. Professor Oak (23 battles)          │
│  2. Wild Caught (156 times)            │
│                                         │
│  ─────────────────────────────────────  │
│  [View Full Showcase]                   │
└─────────────────────────────────────────┘
```

---

## Data Integration

### Sources Pulled From

| Data | Source | Display Location |
|------|--------|----------------|
| Encounter history | battle-record-system.md | Card detail, stats |
| Catch status | battle-record-system.md | Grid card badge |
| Last seen (trainer) | battle-record-system.md | Card detail |
| Animation | vibemon-animation-system.md | All views |
| Sound | vibemon-sound-generation.md | Play on interaction |

### New Data Fields

```python
@dataclass
class EncounterRecord:
    vibemon_id: str
    catching_vibemon_id: str
    trainer_id: Optional[str]  # If wild, None
    location: str
    timestamp: datetime
    result: EncounterResult  # CAUGHT, ESCAPED, RELEASED, DEFEATED
    current_xp: int
```

---

## UI/UX Requirements

### Animation Handling
- **Lazy Load**: Load sprite on scroll into view
- **Loop**: Idle animation loops seamlessly
- **Memory**: Dispose animations when off-screen
- **Fallback**: Static sprite if animation unavailable

### Sound Handling
- **Auto-play**: Optional (off by default)
- **Mute Control**: Global and per-type mute
- **Overlap**: Allow only one sound at a time
- **Preload**: Cache next card's sound

---

**Priority**: Medium
**Complexity**: Medium
**Related Ideas**:
- vibemon-animation-system.md
- vibemon-sound-generation.md
- battle-record-system.md
- experience-system.md