# Move Content JSON v1

Move content is authored as strict JSON and loaded into typed `schema.Move` objects before persistence or battle use.

## File Shape

Each provider owns one canonical file:

```json
{
  "version": 1,
  "provider": "climate",
  "moves": []
}
```

`provider` must match the provider slug used in each move id.

## Move Fields

Required fields:

- `id`: stable globally unique identifier in `<provider_slug>.<move_slug>` format.
- `name`: globally unique display label.
- `flavor_text`: player-facing move description.
- `type`: `normal`, `fire`, `water`, `electric`, `grass`, `ice`, `fighting`, `poison`, `ground`, `flying`, `psychic`, `bug`, `rock`, `ghost`, `dragon`, `dark`, `steel`, or `fairy`.
- `category`: `physical`, `special`, or `status`.

Optional fields use the backend `schema.Move` defaults:

- `power`: integer or `null`; defaults to `null`.
- `accuracy`: number from `0.0` to `1.0` or `null`; defaults to `1.0`.
- `pp`: integer; defaults to `10`.
- `priority`: integer from `-7` to `7`; defaults to `0`.
- `target`: move target enum; defaults to `single`.
- `level_requirement`: integer; defaults to `1`.
- `effects`: declarative effect groups; defaults to `[]`.
- `behavior`: conditional behavior and optional first-party `script_id`; defaults to no behavior.

Unknown fields are invalid.

## Identity Rules

`id` is immutable after approval and publication. Renaming a move preserves the same `id`.

Move names are globally unique on a canonical key: trimmed, case-folded, and punctuation-normalized. For example, `Spark-Tap` and `spark tap!` collide.

Loader/catalog validation must reject duplicate ids, duplicate canonical names, invalid enum values, malformed effects, and malformed conditions. Validation errors should identify the provider and move so content authors can fix the source JSON.
