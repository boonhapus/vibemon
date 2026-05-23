# Move catalog uses global immutable move identity with strict uniqueness

Move publication uses globally unique move identity (`move.id`) and globally unique canonical move names across the full catalog, not provider-local scope. Draft content may be revised during review, but once a move is approved and published its `move.id` is immutable even if display naming changes. Validation rejects identifier or canonical-name collisions as hard failures; generation/review must resolve conflicts explicitly instead of auto-suffixing or silently rewriting identifiers. This keeps move references stable across battle logic, content tooling, and future migrations while preventing ambiguous lookup behavior.

