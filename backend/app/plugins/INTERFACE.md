# Simplified VibeProvider Interface

## Overview
Eliminates intermediate `engine.py`, `Vocabulary`, `Ruleset`, and `Event` abstractions. Providers directly translate raw API data to game-ready `Affinity` components using optional shared helpers.

## Core Interface
### Base Class (`backend/app/plugins/provider.py`)
```python
from abc import ABC, abstractmethod
from app import schema
from typing import ClassVar

class VibeProvider(ABC):
    """Base interface for provider plugins."""
    
    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""
    
    @abstractmethod
    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Translate raw API data to Affinity components."""
    
    async def teardown(self) -> None:
        """Optional: Release provider-owned resources (e.g., API clients)."""
```

## Shared Optional Helpers
Importable from `app.plugins.helpers`:

### 1. Normalization
```python
def normalize(value: float, low: float, high: float) -> float:
    """Map raw value to 0-1 range, clamped to [0.0, 1.0]."""
```

### 2. Stat Mapping
```python
from app.balance.formulas import base_stat_asymmetric_scaling  # Existing shared utility
# Maps 0-1 ratio to Identity base stat using fixed min/med/max ranges
# Signature: (ratio: float, stat: str) -> int
```

### 3. Element Selection
```python
from app import types
from collections.abc import Mapping, Callable

ElementScoreCallback = Callable[[Mapping[str, float]], float]
"""Takes dict of normalized signal values, returns element score (0-1+)."""

def build_element_scores(
    data: Mapping[str, float],
    callbacks: Mapping[types.VibemonTypeT, ElementScoreCallback]
) -> dict[types.VibemonTypeT, float]:
    """Run all callbacks to build element score dict."""

def select_elements(
    scores: Mapping[types.VibemonTypeT, float],
    primary_min: float = 0.2,
    secondary_ratio: float = 0.75
) -> tuple[types.VibemonTypeT, ...]:
    """Apply threshold logic to pick final elements (replaces engine.py _pick_elements)."""
```

### 4. Move Pool Sampling
```python
from app import schema

def sample_move_pool(
    weighted_moves: Mapping[schema.Move, float],
    pool_size: int = 10
) -> list[schema.Move]:
    """Sample weighted moves to final pool (replaces engine.py _sample_move_pool)."""
```

## Contribution Effort
### Old Workflow (Eliminated)
1. Create 2-3 files: `provider.py`, `rules.py`, `moves.py`
2. Define complex `Ruleset` dataclass with 8+ required fields (`element_rules`, `event_affinities`, `stat_map`, `signal_move_rules`, `event_move_rules`, `severity_scale`, `visual_notes`, `default_note`)
3. Define `Vocabulary` and `Event` structs
4. Implement `make_vocabulary()` to normalize data into Vocabulary
5. Configure severity scales, event mappings, move rules
6. **Estimated effort: 2-4 hours for simple providers, 1+ day for complex ones**

### New Workflow
1. Create 1 file: `provider.py`
2. Subclass `VibeProvider`, set `name`
3. Implement single `synthesize()` method:
   - Fetch raw API data using `ctx.geo_coords`/`ctx.timestamp`
   - Normalize values with `normalize()`
   - Build element scores (manual or via callbacks + `build_element_scores()`)
   - Select elements with `select_elements()`
   - Map stats with `base_stat_asymmetric_scaling()`
   - Build weighted move dict, sample with `sample_move_pool()`
   - Calculate intensity (provider-specific logic)
   - Generate visual notes (provider-specific)
   - Return `Affinity`
4. Optional: Override `teardown()` for resource cleanup
5. **Estimated effort: 30-60 minutes for simple providers, 2-3 hours for complex ones**

## Example Skeleton Provider
```python
# backend/app/plugins/example/provider.py
from app.plugins.provider import VibeProvider
from app.plugins import helpers
from app import schema, types

class ExampleProvider(VibeProvider):
    name = "example"
    
    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        # 1. Fetch raw data (pseudo-code)
        raw_data = await self._fetch_api(ctx.geo_coords)
        
        # 2. Normalize signals
        signals = {
            "temp": helpers.normalize(raw_data.temperature, low=-30, high=50),
            "rain": helpers.normalize(raw_data.rainfall, low=0, high=50),
        }
        
        # 3. Build element scores (manual example)
        element_scores = {
            types.VibemonTypeT.FIRE: signals["temp"] if signals["temp"] > 0.4 else 0,
            types.VibemonTypeT.WATER: signals["rain"],
        }
        elements = helpers.select_elements(element_scores)
        
        # 4. Map stats
        stats = {
            "base_hp": helpers.base_stat_asymmetric_scaling(signals["temp"], "base_hp"),
            "base_attack": helpers.base_stat_asymmetric_scaling(signals["rain"], "base_attack"),
            "base_defense": 70,  # Fixed or calculated
            "base_sp_attack": 70,
            "base_sp_defense": 70,
            "base_speed": 70,
        }
        
        # 5. Build moves (manual example)
        weighted_moves = {
            schema.Move(name="Example Move", ...): signals["temp"] * 0.8,
            schema.Move(name="Another Move", ...): signals["rain"] * 0.5,
        }
        moves = helpers.sample_move_pool(weighted_moves)
        
        # 6. Calculate intensity (provider-specific)
        intensity = 0.5  # Replace with real logic (e.g., z-score calc)
        
        # 7. Return Affinity
        return schema.Affinity(
            identity=schema.Identity(name="__", elements=elements, **stats),
            visual_notes="Example visual note",
            intensity=intensity,
            provider_id=self.name,
            moves=moves,
        )
```

## Intensity Guidance
Intensity (0.0–1.0) weights the provider's contribution when merging affinities. Higher = more influence on the final merged Vibemon. It should reflect how "extreme" or "impactful" the current provider context is relative to its own baseline.

### Recommended patterns:
1. **Quantitative providers (weather, air quality)**:
   - Z-score of key signals vs 4–8 weeks of history → sigmoid of max absolute z-score (recommended)
   - Alternative: Percentile rank of current value vs history
   - *Climate example*: Calculate z-scores for temperature, wind gusts, humidity, solar radiation; take most extreme absolute z-score; map to 0–1 via sigmoid

2. **Categorical/event providers (local events, holidays)**:
   - Map event severity to 0–1 directly (no event=0.3, minor=0.6, major=0.9)

3. **Time/cyclical providers (time of day, season)**:
   - Deviation from neutral: e.g., summer solstice (extreme)=1.0, equinox=0.5

## Migration Notes
- Remove `engine.py` entirely (functionality replaced by helpers)
- Delete all `Ruleset`, `Vocabulary`, `Event` references
- Update existing providers (e.g., `climate/provider.py`) to use new interface
