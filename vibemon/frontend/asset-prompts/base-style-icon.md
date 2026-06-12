# Icon style anchor

Reusable render rules for HUD icons. Reference via `style_anchor: base-style-icon.md`. Injected at render time — idea prompts carry subject and layout only.

Aligned with `docs/development/DESIGN.md` §1 (cozy handheld pixel battler), §2 (locked palette), §5 (320×180 production rules).

Chroma-key matte is solved and injected at generation time; pin with `matte: "#RRGGBB"` in frontmatter to freeze.

---
WORLD & SCALE — icons live on Vibemon's **320×180** cozy handheld UI. Each HUD icon is **tiny**: roughly **16–24 source pixels** tall — the same visual weight as a command-menu glyph or health-bar segment, not a large app-store icon. Draw with a **visible chunky pixel grid**; every edge should read as stepped pixels, never smooth anti-aliased illustration.

ART STYLE — cozy nostalgic **16-bit pixel art** in the Game Boy / GBA handheld tradition: simple, warm, readable. Thick **Tobacco Brown (#3D2B1F)** outlines — a warm dark, **never pure black**. **2–3 flat tone steps** per color zone with soft stepped edges — not airbrushed gradients, not glossy plastic specular highlights. **Whisper-level dither** on large flat fills only (paper/linen feel per DESIGN.md §3.2) — never heavy crosshatch across the whole icon.

LOCKED PALETTE ONLY — sample exclusively from the Vibemon core set (`COLORS.md`):
- **Parchment Cream** #F0E7CE — dominant light fill
- **Tobacco Brown** #3D2B1F — outlines, shadows
- **Soft Mustard** #C9A23F — tiny accents only (never large fills)
- **Grape Plum** #7C4D8A — tiny accents, border flourishes
- **Sage Olive** #6E7540 — secondary fills when needed
- **Burnt Orange / Terracotta** #C0542A — warm emphasis (warnings, alerts)
- **Status Sage** #6B9B5A — success / OK states
- **Status Amber** #CC7A22 — caution
- **Status Brick** #A03020 — critical

PERSPECTIVE & LAYOUT — flat 2D front-facing view, straight-on orthographic projection, perfectly centered in a square 1:1 frame. No three-quarter tilt, no perspective distortion.

COMPOSITION — clear silhouette, uniform padding on all sides. No drop shadow baked into the sprite, no glow, no floor line, no human hands, no text, no logos. Cozy means **simple, warm, and readable** — not hardware-harsh, not modern Material/iOS thin-line UI.
