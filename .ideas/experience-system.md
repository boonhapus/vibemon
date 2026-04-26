# Ideas

## Period: Experience System for Released Vibemon

### Idea: Post-Release Experience & Evolution System

**Problem Statement**
Vibemon that are "released" (promoted, freed from party, or sent on their own missions) should continue to gain experience through battles and evolve after reaching certain thresholds.

---

## Proposed Mechanics

### Experience Gain

| Scenario | XP Rate |
|---------|---------|
| Fighting alongside main party | 100% (full rate) |
| Solo missions | 150% (risk/reward bonus) |
| Tutorial/early game battles | 200% (catch-up bonus) |
| Boss battles | 200% (milestone bonus) |

- Released Vibemon can participate in battles **independently** or **alongside the main party**
- XP earned in battle is **credited to each participating released Vibemon**
- XP is **scaled based on difficulty** of enemies defeated

### Evolution System

Each evolution stage unlocks specific rewards:

| Stage | Threshold | Rewards |
|-------|-----------|---------|
| **Novice** | 0 XP | Base stats, basic abilities |
| **Adept** | 1,000 XP | +10% stats, 1 new ability |
| **Expert** | 3,000 XP | +20% stats, 2 new abilities, title change |
| **Master** | 7,500 XP | +30% stats, 3 new abilities, visual change |
| **Legend** | 15,000 XP | +50% stats, ultimate ability, unique title |

Evolution triggers:
- **Auto-evolve** when threshold reached (with confirmation prompt)
- **Manual evolve** option in character menu (if threshold met)
- Evolution **animation plays** during progression
- Notification sent to **all party members**

### Alumni Roster (UI)

A dedicated screen showing all released Vibemon:

```
┌─────────────────────────────────────────────────────────────┐
│  ALUMNI ROSTER                                              │
├─────────────────────────────────────────────────────────────┤
│  [Filter: All | Active | Inactive]  [Sort: Level | Name]    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐                                                 │
│  │  Sprite │  Flare Wolf "Blade" - Adept ★★                  │
│  │   IMG   │  Level 12 | XP: 2,450 / 3,000                    │
│  │         │  ████████████░░░░░                             │
│  │         │  Last seen: Route 7 (3 days ago)                │
│  └─────────┘                                                 │
│                                                              │
│  ┌─────────┐                                                 │
│  │  Sprite │  Jolteon "Spark" - Expert ★★★                    │
│  │   IMG   │  Level 18 | XP: 5,200 / 7,500                   │
│  │         │  ███████░░░░░░░░░░░                             │
│  │         │  Last seen: Victory Tower (1 week ago)          │
│  └─────────┘                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Model Extension

```python
class ReleasedVibemon:
    id: str
    name: str
    title: str
    evolution_stage: EvolutionStage  # NOVICE, ADEPT, EXPERT, MASTER, LEGEND
    current_xp: int
    xp_to_next_stage: int
    abilities: list[Ability]
    unlocked_titles: list[str]
    last_seen_location: str
    last_seen_date: datetime
    battle_stats: BattleStats
```

### Integration Points

- **Battle System**: Track XP gains for released Vibemon
- **Showcase Mode**: Display evolution stage and titles
- **Notification System**: Alert when evolution available
- **Achievement System**: Track evolution milestones

---

**Priority**: Medium
**Complexity**: Medium
**Related Ideas**: battle-record-system.md, vibemon-showcase-mode.md