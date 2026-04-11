# P1-T2 — Core Data Models & Provider ABC

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T1
**Depends on this:** P1-T3, P1-T4, P1-T5, P1-T6

---

## Objective

Define the foundational data structures and the provider interface that every data source must implement. These models are the contract between providers, engine, and API layer.

## Tasks

1. **Create `backend/app/providers/base.py`**
   - Implement `SourceData` as an `@define` attrs class with all fields from the design doc:
     - `hp_factor`, `attack_factor`, `defense_factor`, `sp_attack_factor`, `sp_defense_factor`, `speed_factor` — all `Optional[float]`
     - `element_votes: list[tuple[str, float]]`
     - `hue_primary`, `hue_secondary`, `luminosity` — `Optional[float]`
     - `flavour_text: Optional[str]`
     - `raw: dict`
   - Implement `GenerationContext` as an `@define` attrs class:
     - `user_id: str`, `timestamp: datetime`, `latitude: Optional[float]`, `longitude: Optional[float]`, `auth_tokens: dict[str, str]`
   - Implement `VibemonProvider` ABC with:
     - `source_id` abstract property → `str`
     - `fetch(context: GenerationContext) -> SourceData` abstract async method

2. **Create `backend/app/engine/models.py`**
   - `VibemonStats` — six int stats + `element: str` + `element_secondary: Optional[str]`
   - `Move` — `name`, `type`, `category`, `power`, `accuracy`, `is_signature`, `effect`
   - `VisualDNA` — all 17 fields per design doc
   - `VibemonPayload` — `uid`, `name`, `source`, `stats`, `moves`, `visual_dna`, `flavour_text`, `stat_origins`, `fallback`

3. **Create `backend/app/providers/__init__.py`**
   - Define `PROVIDER_REGISTRY: list[type[VibemonProvider]]` (empty for now)

4. **Add cattrs structuring/unstructuring configuration**
   - Create `backend/app/serialization.py`
   - Configure a `cattrs.Converter` that handles attrs classes → JSON-safe dicts and back
   - Ensure tuples (used in `VisualDNA` colour fields) round-trip correctly

5. **Write unit tests for model construction and serialization**
   - Test that `SourceData` fields default to `None` / empty
   - Test that `VibemonPayload` round-trips through cattrs

## Acceptance Criteria

- All model classes instantiate with valid data and reject bad types
- `cattrs.unstructure(payload)` produces a JSON-serializable dict
- `cattrs.structure(dict_data, VibemonPayload)` reconstructs the object

## Files Created

```
backend/app/
  providers/
    __init__.py
    base.py
  engine/
    __init__.py
    models.py
  serialization.py
tests/
  test_models.py
```
