# Move animation is a frontend concern, not a Move Catalog field

The battle screen needs each Move to play a visual animation. We considered adding an `animation_key` to the domain `Move` (Move Catalog) so it travels end-to-end, but chose instead to keep the domain Move presentation-free: the frontend derives a generic **Animation Profile** from the Move's existing `category` + `type` (PHYSICAL → contact lunge, SPECIAL → type-tinted projectile, STATUS → glow), and any bespoke signature-move animation lives in a frontend registry keyed by move id.

We picked this because animation is presentation, not behavior — modeling it as a Move `Effect` would be wrong, and persisting a VFX key in the Move Catalog couples the domain to one renderer. Frontends may eventually differ (a second client, a different battle renderer), and each owns its own animation responsibility. The backend battle read model already carries `category` and `type`, so the generic mapping ships with zero new domain surface, and the override registry stays cheap and reversible.

## Considered Options

- **Frontend-derived Animation Profile + frontend override registry** (chosen) — domain stays pure; per-client.
- **`animation_key` on domain `Move`** (rejected) — one field travels end-to-end, but puts frontend VFX into the Move Catalog schema, contradicting the domain-purity stance in `CONTEXT.md`, and is hard to walk back once persisted.
