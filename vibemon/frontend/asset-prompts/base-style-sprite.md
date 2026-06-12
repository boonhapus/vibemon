# Gear sprite style anchor

Reusable render rules for gear sprites. Reference via `style_anchor: base-style-sprite.md`. Injected at render time — idea prompts carry subject and orientation only.

After generation, run `generate_static_assets.py derive-poses` to write `{gear}-left.png` and `{gear}-right.png` from the canonical sprite — no second GenAI call.

---
COZY HANDHELD SPRITE STYLE — design as a 48–64px-tall inventory / style-bible sprite: chunky, simple, warm, readable. Thick tobacco-brown pixelated outlines (#3D2B1F), pixel-rounded forms, simple silhouettes. Shading: 2–3 flat tone steps per color zone with soft stepped edges — not airbrushed gradients, not heavy crosshatch. Whisper-level paper grain and subtle dither on large object fills only — never on the background matte. Locked mid-century muted palette. No neon, no glossy plastic, no photorealism, no text, no logos, no human hands.

ORIENTATION — three-quarter hero view, object centered with uniform margin:
- **Camera** canonical generation targets **left**; center detection defaults to left.
- **Belt gear** (Vibe Deck, Vibe Cart) canonical generation targets **right**; center detection defaults to right.

CANVAS — flat matte chroma-key background as ONE uniform wash filling every non-object pixel (exact hex supplied in the prompt). Background perfectly flat — no texture, grain, vignette, or dither on the matte. No scenery, floor line, drop shadow, contact shadow, or props outside the object.
