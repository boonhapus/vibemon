# Geolocation Traversal & Simulation

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Area** | Exploration & World Logic |
| **Related** | [vibe-gold-economy.md](vibe-gold-economy.md), [achievement-system.md](achievement-system.md) |

## Summary

**Vibemon** are born from real-world context. Trainers explore new vibe-biomes by moving in the physical world, with **Simulated Travel** and traversal perks as earned shortcuts when remote types or aesthetics are out of local reach.

## Problem

**Vibemon** types, stats, and aesthetics are steered by real-world data (weather, coordinates, topography). Trainers need a way to encounter distant biomes without always traveling physically, while keeping location-based generation honest and intentional.

## Concept

A two-tier exploration model:

1. **Real-world traversal** — primary path; **Birth Context** seeds from actual coordinates and local POI biomes.
2. **Simulated travel** — time-limited in-game coordinate tuning (voucher-gated) that swaps **Birth Context** to a chosen remote location.
3. **Traversal licenses** — Fly-style shortcuts to previously visited coordinates and map extensions that reveal vibe density before a visit.

## Design

### Real-world traversal

The primary way to encounter new species is to move in the real world.

- **Location-based seeding**: **Birth Context** uses the trainer's actual latitude/longitude to pull local climate data.
- **Biomes**: points of interest map to real-world features:
  - **Parks/forests**: high Grass/Bug density.
  - **Coastlines**: high Water density.
  - **Urban centers**: high Electric/Steel density.

### Simulated travel

Trainers purchase or earn **Simulation Vouchers** for creative license and remote hunting.

- **Location spoofing (in-game only)**: the trainer "tunes" to a distant coordinate (e.g., Tokyo, the Sahara, the Amazon).
- **Duration**: simulation lasts for a fixed window (hours TBD).
- **Encounter shift**: during simulation, the generation engine uses simulated coordinates instead of real ones.
- **Use case**: hunt types or aesthetics unavailable in local climate (e.g., Ice-types from a desert home base).

### HM Fly & travel licenses

Special items or moves that simplify traversal.

- **Fly**: jump to a coordinate the trainer has previously visited (saves a simulation voucher for that location).
- **Map extensions**: purchases that reveal **Vibe Density** of a real-world area before the trainer visits.

## Open Questions

- Simulation voucher duration and cooldown defaults?
- Fly unlock: first physical visit required, or also after simulated visit?
- Geography bucket taxonomy alignment with achievement gates?
