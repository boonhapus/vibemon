# JSON-Backed Move Content

## Summary

Move definitions should eventually move from Python modules exporting `schema.Move(...)` objects to data files validated at runtime. This is not urgent for the current battle refactor, but it is a useful future pattern for frontend inspection, localization, content tooling, and safer provider plugins.

The target shape is:

```text
provider move data file
  -> content loader
  -> Pydantic validation
  -> tuple[schema.Move, ...]
  -> BattleMove copies during battle setup
```

The battle engine should continue consuming typed `Move` / `BattleMove` objects. It should not parse raw JSON directly.

## Motivation

Python move objects are convenient while iterating, but they make content harder to inspect and localize:

- A frontend cannot read move data without a backend endpoint or Python import.
- Display strings are currently identity-like fields (`name`, `flavor_text`), which is awkward for localization.
- Generated content requires editing Python source instead of writing data.
- Provider plugins are supposed to be content plugins only; data files reinforce that boundary.
- Validation, audits, and balance reports are easier when content is structured data.

## Proposed File Shape

Example move data:

```json
{
  "id": "climate.raincarver_horn",
  "name_key": "move.climate.raincarver_horn.name",
  "flavor_key": "move.climate.raincarver_horn.flavor",
  "type": "bug",
  "category": "physical",
  "power": 100,
  "accuracy": 0.9,
  "pp": 10,
  "priority": 0,
  "level_requirement": 56,
  "target": "single",
  "effects": []
}
```

Localization data can live separately:

```json
{
  "move.climate.raincarver_horn.name": "Raincarver Horn",
  "move.climate.raincarver_horn.flavor": "A wet, chitinous charge that carves through heavy rain."
}
```

JSON is the most frontend-friendly option. YAML may be nicer for hand-authored content, but JSON keeps parsing and transport simple. If authoring ergonomics become painful, we can support YAML as source and compile to JSON.

## Schema Direction

`Move` should gain a stable id. Names should not be identity.

Near-term compatible shape:

```python
class Move(_Static):
    id: str | None = None
    name: str
    flavor_text: str
    ...
```

Long-term localized shape:

```python
class Move(_Static):
    id: str
    name_key: str
    flavor_key: str
    ...
```

The intermediate version lets existing code keep using `name` while loaders and generators start producing stable ids.

## Loader Design

Add a content loading layer, not battle-engine JSON parsing.

Potential layout:

```text
backend/app/content/
  moves.py                # loader and validation helpers
backend/app/plugins/
  universal_moves.json
  climate/
    moves.json
    locale/
      en.json
```

Responsibilities:

- Load provider move data from JSON.
- Validate with Pydantic into `schema.Move`.
- Resolve localization keys into display strings when needed by backend debug tools.
- Preserve typed `EffectGroup`, typed effects, `MoveBehavior`, and `MoveTargetT`.
- Reject unknown fields and invalid enum values.
- Keep executable behavior out of provider content. `script_id` may reference first-party scripts only.

## Migration Plan

1. Add `Move.id` while keeping `name` and `flavor_text`.
2. Add a JSON loader that returns `tuple[schema.Move, ...]`.
3. Convert a small source first, likely `backend/app/plugins/universal_moves.py`.
4. Update move audit tooling to accept either loaded JSON moves or Python `MOVES`.
5. Update the move generator to emit JSON data instead of Python source.
6. Convert climate moves after the generator and audit path are stable.
7. Add localization keys/files once a frontend needs translated strings.
8. Eventually make `id`, `name_key`, and `flavor_key` required and treat display text as localized output, not content identity.

## Open Questions

- Should the source format be JSON only, or YAML for authored files with compiled JSON output?
- Should localization be loaded by backend, frontend, or both?
- Should provider packages expose a manifest listing content files?
- How should duplicate ids be handled across providers?
- Do we want generated move ids to be stable slugs derived from approved concept names, or opaque ids?

## Out Of Scope For Now

- Converting existing climate moves.
- Removing `name` / `flavor_text`.
- Building frontend localization infrastructure.
- Letting providers register executable battle mechanics.

