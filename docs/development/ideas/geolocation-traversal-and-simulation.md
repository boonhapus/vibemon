# Ideas: Geolocation Traversal & Simulation

## Period: Exploration & World Logic

### Problem Statement
Vibemon are tied to the real world. Their types, stats, and aesthetics are steered by real-world data (weather, coordinates, topography). Players need a way to explore new "Vibe-biomes" without necessarily physical travel, while maintaining the integrity of location-based generation.

---

## 1. Real-World Traversal
The primary way to encounter new species is to move in the real world.
- **Location-Based Seeding**: The `BirthContext` uses the trainer's actual latitude/longitude to pull local climate data.
- **Biomes**: Points of interest (POIs) are mapped to real-world features:
  - **Parks/Forests**: High Grass/Bug density.
  - **Coastlines**: High Water density.
  - **Urban Centers**: High Electric/Steel density.

---

## 2. Simulated Travel (The "Perk")
To give players creative license and access to remote Vibemon, they can purchase or earn **Simulation Vouchers**.

### How it Works:
- **Location Spoofing (In-Game Only)**: The trainer "tunes" their device to a distant coordinate (e.g., Tokyo, the Sahara, the Amazon).
- **Duration**: The simulation lasts for X hours.
- **Encounter Shift**: During this time, the generation engine (BirthContext) uses the *simulated* coordinates instead of the real ones.
- **Creative License**: This allows trainers to hunt for specific types or aesthetics that aren't available in their local climate (e.g., a trainer in a desert simulation for Ice-types).

---

## 3. HM Fly & Travel Licenses
Special items or moves that simplify traversal.
- **Fly**: Instead of walking, a trainer can "Fly" to a coordinate they have previously visited (saving the simulation voucher cost for that specific location).
- **Map Extensions**: Purchases that reveal the "Vibe Density" of a real-world area before the trainer visits.

---

**Priority**: Medium
**Complexity**: Medium
**Related Ideas**: trainer-progression-and-economy.md

