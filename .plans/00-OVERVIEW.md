# Vibemon — Build Plan Overview

Web UI tokens, battle layout, typography, motion, and raster sprite notes: [vibemon-visual-design-system.md](vibemon-visual-design-system.md).

## Phases & Tasks

| ID | Task | Dependencies |
|---|---|---|
| **Phase 1 — Core Pipeline** | | |
| P1-T1 | Backend Scaffold & Health Endpoint | — |
| P1-T2 | Core Data Models & Provider ABC | P1-T1 |
| P1-T3 | Weather Provider (Open-Meteo) | P1-T2 |
| P1-T4 | Stat Engine (Seeds, Stats, Merging, Elements) | P1-T2 |
| P1-T5 | Visual DNA Generation & Name Generator | P1-T2, P1-T4 |
| P1-T6 | Orchestrator & Generate Endpoint | P1-T1, P1-T2, P1-T3, P1-T4, P1-T5 |
| P1-T7 | Frontend Scaffold & Location Flow | P1-T6 |
| **Phase 2 — Spotify Integration** | | |
| P2-T1 | Spotify PKCE OAuth Flow (Frontend) | P1-T7 |
| P2-T2 | Spotify Provider (Backend) | P1-T6, P2-T1 |
| P2-T3 | Complete Move Pools & Multi-Provider Merge | P2-T2, P1-T6 |
| **Phase 3 — Visual Rendering** | | |
| P3-T1 | Seeded RNG & Blob Hull Generation | P1-T7 |
| P3-T2 | Limbs, Eyes, Mouth & Texture Rendering | P3-T1 |
| P3-T3 | VibemonRenderer Component & Animations | P3-T1, P3-T2 |
| **Phase 4 — Battle System** | | |
| P4-T1 | Battle State Machine & Turn Logic | P3-T3, P2-T3, P1-T7 |
| P4-T2 | Battle UI (Gen 3 layout, HP, neutral moves, log) | P4-T1 |
| P4-T3 | Battle Animations & End Screens | P4-T1, P4-T2 |
| **Phase 5 — GitHub Integration & Polish** | | |
| P5-T1 | GitHub OAuth Proxy & Provider | P1-T6 |
| P5-T2 | GitHub OAuth Frontend & Guest Mode | P5-T1, P1-T7 |
| P5-T3 | UI Polish, Error States & Responsive Design | P4-T3, P5-T2 |

## Dependency Graph

```
P1-T1
 └─► P1-T2
      ├─► P1-T3 ──────────────┐
      ├─► P1-T4 ───┐          │
      │    └─► P1-T5          │
      │         │              │
      └─────────┴──────────────┴─► P1-T6
                                    ├─► P1-T7
                                    │    ├─► P2-T1 → P2-T2 → P2-T3
                                    │    ├─► P3-T1 → P3-T2 → P3-T3
                                    │    └─► P5-T2                 
                                    └─► P5-T1 → P5-T2             
                                                                   
P2-T3 + P3-T3 ─► P4-T1 → P4-T2 → P4-T3 ─┐
                                           ├─► P5-T3
P5-T2 ─────────────────────────────────────┘
```

## Parallelisation Opportunities

Once P1-T6 and P1-T7 are complete, three workstreams can run in parallel:

1. **Spotify** (P2-T1 → P2-T2 → P2-T3)
2. **Visual Rendering** (P3-T1 → P3-T2 → P3-T3)
3. **GitHub Backend** (P5-T1) — can start early since it only needs the orchestrator

Phase 4 (Battle System) requires both Spotify move pools (P2-T3) and the renderer (P3-T3) to be complete.

## Working Order (Sequential Path)

If working solo, the critical path is:

```
P1-T1 → P1-T2 → P1-T3 → P1-T4 → P1-T5 → P1-T6 → P1-T7
→ P3-T1 → P3-T2 → P3-T3
→ P2-T1 → P2-T2 → P2-T3
→ P4-T1 → P4-T2 → P4-T3
→ P5-T1 → P5-T2 → P5-T3
```

Note: P1-T3 and P1-T4 can be done in parallel since they both only depend on P1-T2.
