# Game Asset Prompts

Provenance records for **hand-authored or manually generated** static game art under `vibemon/frontend/static/game/`. These are frozen prompt instances — not Jinja templates and not runtime assets.

## Where prompts live

```
vibemon/frontend/
  static/game/          ← shipped PNGs (and other runtime media)
  asset-prompts/game/   ← .mdc prompt records; mirrors static/game/ paths
```

**Do not** store prompt records inside `static/`. Everything under `static/` is deployed verbatim; prompt markdown is dev metadata and should stay out of the production bundle.

**Mirror rule:** an asset at `static/game/icons/vibe-deck.png` is documented by `asset-prompts/game/icons/vibe-deck.mdc`. Same relative path, same basename, different root and extension.

### Not the same as backend GenAI templates

| Location | Purpose | Body |
| :--- | :--- | :--- |
| `vibemon/backend/app/genai/prompts/*.mdc` | Versioned **templates** rendered with Jinja for generated **Vibemon** assets | Jinja + `{% include %}` |
| `vibemon/frontend/asset-prompts/game/**/*.mdc` | **Instance** records for fixed UI/game art prompts | Plain text only |

Shared `.mdc` extension and YAML frontmatter delimiter convention; different `kind` and fields.

## File format

Each file is YAML frontmatter + the exact prompt text used (or to be used) for generation.

```yaml
---
name: vibe-deck-icon
kind: asset-instance
asset: game/icons/vibe-deck.png
model: gemini-3-pro-image
generated: 2025-06-07
status: approved
---
A portable clamshell Vibe Deck …
```

### Frontmatter fields

| Field | Required | Description |
| :--- | :--- | :--- |
| `name` | yes | Stable slug; usually matches the asset basename |
| `kind` | yes | Always `asset-instance` for this tree |
| `asset` | yes | Path relative to `static/` (e.g. `game/icons/vibe-deck.png`) |
| `model` | when known | Image model or tool that produced the PNG |
| `generated` | when known | ISO date (`YYYY-MM-DD`) the image was generated |
| `status` | recommended | `draft` (prompt only), `approved` (prompt + PNG committed), `superseded` (replaced — point to successor in commit message or a new file) |

Optional later: `supersedes`, `notes`, `style_anchor: base-style.md`.

The **body** is the full prompt text — no Jinja, no includes, and no references to other prompt files in the body. Inline the shared style block from `base-style.md` verbatim at the end so each record is self-contained for generation tools. Record `style_anchor: base-style.md` in frontmatter for provenance only.

## Workflow

1. Add or edit `asset-prompts/game/.../*.mdc` with `status: draft` if the PNG does not exist yet.
2. Generate the image; save PNG to the mirrored path under `static/game/`.
3. Fill in `model` and `generated`; set `status: approved`.
4. Commit **both** files in the same commit when possible.

Retroactive catalog: add `.mdc` files for existing PNGs when revisiting art; best-effort `model` / `generated` if unknown.

## Related docs

- Shared style anchor appended to every prompt: `vibemon/frontend/asset-prompts/base-style.md`
- Visual tokens and gear prompts: `GEAR.md`
- Locked palette: `COLORS.md`, `DESIGN.md` §2
- Style bible and production rules: `DESIGN.md` §5
