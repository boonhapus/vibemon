# Background scene style anchor

Reusable render rules for full-scene backgrounds (battle field, hatch field, etc.). Reference via `style_anchor: base-style-background.md`. Injected at render time — idea prompts carry the scene subject, composition, and mood only.

Backgrounds are the middle ground between the chunky isolated-sprite anchor and a full painterly illustration: same cozy-handheld world, but scenes get to breathe with richer color and denser texture. Do NOT carry the sprite anchor's "muted, desaturated, 2–3 flat tone steps, whisper grain" rules here — those flatten and wash out a scene.

---
COZY HANDHELD SCENE STYLE — a warm, painterly pixel-art landscape that reads as the same world as the chunky character sprites composited on top of it. Hand-pixeled, detailed, and lived-in, not flat or sparse.

COLOR — warm and richly saturated within a cohesive cozy palette: glowing skies, deep layered greens, earthy browns. Full tonal range with luminous highlights and soft deep shadows — never washed out, never dusty-grey. Many blended tone steps per zone for smooth painterly gradients in skies and atmosphere.

TEXTURE — varied, hand-pixeled detail across natural surfaces, but with a clear depth hierarchy so it never competes with the characters: concentrate the busiest, highest-contrast detail in the far distance and along the very bottom foreground edge, and keep the midground stage band — the central area where characters stand — visibly calmer, with softer, lower-contrast grass, gentle even shading, and muted value variation. Subtle atmospheric haze settles the midground back. Fine texture, not large empty flat fills, and not uniform high-contrast clutter edge to edge. Clean pixel-art edges with subtle dither for shading transitions only — no airbrushed blur, no photorealism, no heavy crosshatch banding across skies.

COMPOSITION — wide horizontal landscape designed as a stage: characters are composited on top at render time. Keep the foreground and center open, calm, and uncluttered with a believable ground plane for them to stand on — the character zone should read as a quiet rest area so the composited sprites pop clearly against it. No characters, no UI, no text, no vignette, no dark framing edges.
