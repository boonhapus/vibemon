# Vibemon Battle — Cozy Pixel Aesthetic Through a 1960s–70s Lens (Design Document)

## 1. Vision Statement
Vibemon's battle interface is a **cozy, nostalgic handheld monster-battler rendered in pixel art**, art-directed through a prominent **1960s–70s mid-century lens**. The pixel art is the *medium*; the mid-century sensibility is the *worldview*; warmth and comfort are the *feeling*. It ships as a single **responsive web app** — the same build in a desktop browser or on a phone — so the interface is designed **16:9-first** and adapts gracefully down to a hand (see §5).

The look deliberately blends two directions. From the authentic handheld tradition we take **structure and restraint** — readable, low-resolution sprites; familiar battle-screen conventions; flat, legible shading. From a warmer, more atmospheric reinterpretation we take the **soul** — a desaturated mid-century palette, layered backgrounds with real depth, a gentle film grain, and soft, rounded UI. The result should feel like a beloved cartridge you'd swear existed, designed in a world where the 1970s never ended: tactile, warm, unhurried, and a little hand-made.

We are explicitly *not* chasing hardware-accurate harshness (no aggressive scanlines, no loud primary-color UI) and *not* chasing modern illustration (no soft-focus, no depth-of-field blur, no high-detail painterly sprites). Cozy means **simple, warm, and readable**; nostalgic means **familiar conventions plus a whisper of analog texture**.

Quick reference: `VOICE.md` for player-facing copy and tone.

## 2. Color Palette
The palette is mid-century at heart — drawn from period interior design and Kodachrome film — but tuned toward **desaturated warmth** rather than the era's louder moments. Every color below lives inside a single locked set (§2.0); nothing is sampled outside it.

### 2.0 The Locked Palette Principle
Pixel art reads as cohesive only when colors are disciplined. **Commit to a fixed palette of ~16–24 colors total** (the Core Palette plus the type and status hues below, harmonized into one set). Every sprite, tile, and UI element samples from this locked set — no off-palette colors, no per-asset improvisation. This single rule is the strongest consistency tool in the project; it is also exactly what a sprite-generation pipeline (a trained on-style model, or a pixel-art generator) should be given as its basis so every generated asset arrives on-model.

### 2.1 Core Palette

Quick reference: `COLORS.md`. Trainer gear color mapping: `GEAR.md`.

| Color Name | Hex Code | Usage |
| :--- | :--- | :--- |
| **Parchment Cream** | #F0E7CE | Text boxes, light fills, background contrast |
| **Tobacco Brown** | #3D2B1F | Text, outlines, shadows — a *warm dark*, never pure black |
| **Burnt Orange** | #C0542A | Fire accents, primary warm highlight |
| **Sage Olive** | #6E7540 | Environments, foliage, stat-bar fills |
| **Soft Mustard** | #C9A23F | Selection cursor, HP highlight — small accents only, never large fills |
| **Grape Plum** | #7C4D8A | Decorative accent; secondary UI borders; ability-badge backgrounds |

The earlier mustard and avocado have been **muted** toward soft mustard and sage olive — the cozy register lives in the desaturated middle, not in full-strength 70s primaries. Tobacco Brown replaces black everywhere (outlines, shadows, the iris overlay); the warmth of the dark tone is doing real cozy work. Parchment Cream is the dominant light value — text boxes and the background sit on it.

The **Grape Plum** accent draws from the era's enthusiasm for bold, slightly-muted purples — 1960s mod fashion, early psychedelic posters, the warm linen prints of the 1970s. It pairs with Soft Mustard as a classic mid-century complementary tension (yellow–purple) and softens against Parchment Cream. Use it as the **plum border accent on the dialogue box** and as a tertiary decorative flourish — never at full saturation across large areas.

---

### 2.2 Vibemon Type Colors
All type colors are drawn from period-accurate mid-century references — Pantone textile standards, Kodachrome film stock, the muted-but-warm household trends of the 1960s–70s. Full-saturation digital primaries are intentionally avoided. These hues are part of the locked palette and should be quantized to it.

| Type | Color Name | Hex Code | Reference |
| :--- | :--- | :--- | :--- |
| **Normal** | Warm Parchment | #C4A882 | Aged paper, manila folders, linen upholstery |
| **Fire** | Terracotta | #C0542A | 70s earthenware pottery, Southwestern ceramics |
| **Water** | Teal Mist | #3D8C8C | Mid-century aqua bathroom tile, Formica countertops |
| **Electric** | Harvest Gold | #D4A017 | Appliance gold, 70s kitchen hardware |
| **Grass** | Olive Drab | #6B7A2A | Army surplus, mid-century botanical illustration |
| **Ice** | Powder Blue | #A0BAC8 | 60s leisure wear, institutional wall paint |
| **Fighting** | Brick Red | #8B3A2A | Exposed brick, Saltillo tile |
| **Poison** | Grape Plum *(shared)* | #7C4D8A | Poison dart frogs, psychedelic ink prints |
| **Ground** | Sienna Sand | #A0784A | Southwest adobe, pre-Columbian pottery glaze |
| **Flying** | Slate Sky | #6E8FA8 | Faded denim, horizon haze photography |
| **Psychic** | Dusty Orchid | #B0607A | Mod Op Art, pop-art poster ink |
| **Bug** | Moss Khaki | #7A8C2A | Field guide illustration, olive cotton canvas |
| **Rock** | Warm Slate | #8C7A5A | Slate tile, mid-century stone veneer |
| **Ghost** | Dusk Indigo | #524870 | Late-evening Kodachrome sky, Ektachrome shadow tones |
| **Dragon** | Deep Verdigris | #2A5C58 | Oxidized copper, brass-and-patina hardware |
| **Dark** | Espresso | #4A3428 | Dark-roast coffee, walnut veneer furniture |
| **Steel** | Pewter | #8A8C8E | Vintage Airstream aluminum, faded 60s appliance chrome |
| **Fairy** | Rose Quartz | #C4909A | Pastel cosmetics packaging, 50s–60s nursery pink |

Type badges render as small **pixel pills** — rounded-rectangle labels with the type color as background and Tobacco Brown or Parchment Cream as text, chosen by luminosity. Add character with a **subtle dither texture** rather than a smooth grain (dithering is the pixel-art way to suggest the linen/print feel while staying on-palette).

---

### 2.3 Status Colors
Status indicators follow the same period-accurate desaturation — not traffic-light primaries, but their warm, analog equivalents.

| Status | Color Name | Hex Code | Usage |
| :--- | :--- | :--- | :--- |
| **Green (Healthy)** | Sage | #6B9B5A | Full or near-full HP, "OK" state, active/ready indicators |
| **Orange (Caution)** | Amber | #CC7A22 | Mid-range HP, status conditions (burn, poison tick), warnings |
| **Red (Critical)** | Brick | #A03020 | Low HP, fainted, critical states |

These three map onto the segmented health-bar blocks in §3.2. As HP drops, the filled blocks transition Sage → Amber → Brick at **50%** (Sage→Amber) and **20%** (Amber→Brick), consistent with mainline conventions. Unfilled segments render as Tobacco Brown at ~30% opacity.

## 3. Typography & UI Elements
### 3.1 Typography
* **Title / Logo:** Bold, geometric sans-serifs like *Futura* or *ITC Avant Garde* — unmistakably mid-century, and the place where the 60s–70s framing speaks loudest. Used for the logo, title screen, and large display moments only.
* **Battle / UI Text:** A **bitmap (pixel) font**, not a vector typeface — chunky, warm, and highly readable at small sizes, in the handheld tradition. A custom ~8px bitmap face is ideal; the goal is the friendly, slightly-rounded character of a beloved cartridge, set in Tobacco Brown on Parchment Cream.
* **Texture:** A **soft 1px ink-bleed** and a faint grain — enough to read as warm and analog. *No* chromatic aberration and *no* harsh CRT scanlines; those tip from cozy toward hardware-authentic, which is the wrong direction for this game.

### 3.2 Health Bars & Menus
* **Health Bars:** Segmented blocks with pixel-rounded corners — *not* smooth gradients. The container reads like a plastic-molded dashboard gauge from a 1970s sedan, but drawn in clean pixels (corners shaped pixel-by-pixel, not via blurred CSS radii).
* **Dialogue & Menu Boxes:** Rounded boxes with a **soft drop shadow** and the **Grape Plum border accent** on the main dialogue box. Friendly, tactile, and warm — the cozy-illustration UI treatment, executed in pixels.
* **Buttons:** Tactile "pressed" states that suggest physical depth. Backgrounds carry a **light dithered grain** (paper/linen feel) kept subtle enough never to fight legibility.

## 4. Scene Composition
A classic battle layout: the trainer's Vibemon foreground-left, the opponent on a raised circular stage upper-right, dialogue and command menus along the bottom.

* **Foreground Vibemon:** Rendered at full palette warmth with crisp, readable pixel edges. Depth comes from **palette and contrast, not blur** — there is no soft-focus or depth-of-field here. The fire-type's orange leans toward the Terracotta tone to sit inside the palette.
* **Background Vibemon:** On a circular "stage" of dirt. The opponent reads as slightly more distant through **cooler, more muted color choices** (atmospheric perspective done with the palette), never through blur.
* **Environment:** Layered **pixel parallax** tree-lines in Sage Olive and Olive Drab, with simple foreground grass tufts. Depth is built from stacked flat pixel layers, not vector shapes.
* **Atmosphere:** A gentle warm **vignette** and a **light film grain**, both applied as a **screen-space post-process over the final rendered frame** — never baked into individual sprites (baking them in breaks animation and consistency, and locks you out of tuning later). Dial the grain well back from "aged film"; it should whisper, not shout. No scanlines.

## 5. Asset Pipeline, Display & Responsive Layout
This section codifies the decisions that keep a blended style from drifting into mush, and the display architecture that lets one web build run cleanly on both a desktop browser and a phone. Lock these *before* producing any production sprite.

### 5.1 Production Rules
* **Internal resolution:** **320×180** — a clean 16:9 pixel canvas, fixed and never changed. All scene rendering targets it, then scales to the viewport with **nearest-neighbor (integer) scaling**. 320×180 integer-multiples land exactly on common sizes (×2 = 640×360, ×4 = 1280×720, ×6 = 1920×1080), keeping pixels crisp at desktop resolutions.
* **Sprite resolution:** **48–64px character sprites** — the cozy mid-detail sweet spot. Larger than true GBA (so we keep a little of the warmer, fuller form), smaller than illustration (so sprites stay legible and *animatable* across many monsters).
* **Locked palette:** The ~16–24 colors of §2 are the only colors that exist. Quantize every asset to them.
* **Style bible:** Maintain one reference sheet — a single hero sprite, the palette swatches, and a sample UI box — and use it as the reference image for everything downstream. Any sprite-generation tool (a trained on-style model, a pixel-art generator) should be seeded from this sheet plus the locked palette so output arrives on-model.
* **Render discipline:** `image-rendering: pixelated` everywhere; all post-process (grain, vignette) sits above the upscaled frame, not on the sprites.
* **Prompt provenance:** Hand-generated static art under `vibemon/frontend/static/game/` is documented in `vibemon/frontend/asset-prompts/game/` as `.mdc` instance records (model, date, asset path, frozen prompt). See **`ASSET-PROMPTS.md`**. Do not store prompt markdown inside `static/`.

### 5.2 Display Canvas & Scaling
A two-layer architecture keeps the pixel art perfect while letting the interface adapt:

* **Scene layer** — the fixed **320×180** pixel canvas: backgrounds, sprites, effects, HP plates. It never reflows; it only scales. Render with `imageSmoothingEnabled = false` and `image-rendering: pixelated`.
* **UI layer** — the dialogue box and command menu, drawn as pixel-styled HTML/CSS at display resolution (bitmap font, 9-slice pixel borders). This is the layer that resizes and repositions per device.

**Scaling rule:** compute the largest **integer** scale that fits the viewport in both dimensions — `scale = floor(min(viewportW / 320, viewportH / 180))` — center the canvas, and recompute on every resize and orientation change. Integer scaling keeps every pixel the same size; fractional scaling makes some pixels wider than others and shimmers under motion.

**The bezel (letterboxing as a feature):** integer scaling rarely fills an arbitrary window exactly, so frame the leftover space with a **diegetic bezel** instead of dead black bars — Tobacco Brown with an optional subtle wood-grain or linen texture, reading as the cabinet of a 1960s–70s wooden TV set. This turns an unavoidable letterbox into an on-aesthetic frame, and is one of the best places the mid-century lens shows itself. (If a specific target leaves an awkward amount of empty space, a single half-step of fractional scale is tolerable — but integer-plus-bezel is the default.)

### 5.3 Responsive Layout
The interface is designed **16:9-first**, then adapts by device:

* **Desktop:** the bezel-framed 16:9 canvas centered in the window, scaling live as the window resizes. Mouse plus keyboard/gamepad input.
* **Mobile landscape (intended play orientation):** the canvas fills most of the screen with a thin bezel. Respect device cutouts and the home indicator via `env(safe-area-inset-*)` so nothing important sits under a notch.
* **Mobile portrait:** a tall phone only fits a small 16:9 strip, so **reflow rather than shrink**. The 320×180 **scene layer pins to the top** at the widest integer scale the screen width allows, and the **UI layer detaches into a thumb-friendly touch panel** filling the space below — larger command buttons, larger dialogue text, identical pixel styling. The battle scene stays pixel-perfect; only the chrome moves. A gentle, dismissible "rotate for the full view" nudge can point toward landscape, but portrait must stay fully playable.

### 5.4 Input & Touch Targets
* **Desktop:** keyboard/gamepad D-pad with confirm/cancel, mirrored by mouse clicks on the command menu. Hover states are mouse-only.
* **Touch:** command buttons live on the UI layer — never as tiny tap-regions inside the upscaled canvas — and are at least **44–48 CSS px** on their smallest side. Every interactive element needs a clear **pressed/active** state, since touch has no hover to telegraph focus.

## 6. Visual Effects & Animation System

The animation language is **limited-frame sprite animation** — the shared ancestry of 1960s television limited animation (a deliberate, prominent reference) and the handheld sprite tradition. Both hold a single drawing across several frames and snap between poses rather than interpolating. Every motion should feel hand-placed and a touch choppy: alive, warm, and unmistakably non-digital.

---

### 6.1 Foundational Animation Principles

#### The "Step" Timing Function — Limited Animation
Both 1960s TV animation (shot on "twos" and "threes" on tight budgets, ~8–12 drawings per second) and handheld sprite work advance in discrete jumps, not smooth interpolation. `steps(N)` replicates this exactly. Using `ease` or `linear` on an action would feel immediately wrong — too fluid, too modern. **Use `steps(8)` to `steps(16)` for all action states. Reserve `ease-in-out` only for slow ambient loops like breathing.**

#### Non-Uniform Scaling — Squash & Stretch
A character landing squashes wide and flat; one reaching stretches tall and thin. The key is that **volume is conserved**: as width grows, height shrinks proportionally. `scale(1.02, 0.98)` expresses this — 2% wider, 2% shorter — keeping mass while signalling life. A rigid `scale(1.02, 1.02)` just enlarges the sprite; it doesn't feel alive.

#### The Hit-Flash — A Warm Analog Snap
When a Vibemon is struck, it strobes in hard, binary jumps — opaque to semi-transparent and back — rather than fading smoothly. Pair the opacity pulse with a **gentle brightness lift** and a faint warm tint, evoking an analog frame hiccup without the harsh, blown-out overexposure of a true kinescope splice. **Always apply `steps()` to the flash — a smooth sine fade reads as a modern "ghost" effect; a hard snap reads as analog.**

> **Pixel-art note for all transforms:** sub-pixel transforms (`translateY(-5px)`, `scale(1.02)`) shimmer on crisp pixel sprites. Because the game renders on a low-res canvas scaled up (§5), one source pixel equals several screen pixels, so these small transforms land on whole source pixels and stay clean. If animating sprites directly at display scale instead, prefer integer-pixel transforms or true stepped sprite frames.

---

### 6.2 Foundational CSS Variables

Define timing constants at the root so all animations share one coherent system:

```css
:root {
  /* Animation timing presets */
  --anim-cel-fps: 12;          /* Target "drawings per second" for action states */
  --anim-idle-duration: 3s;
  --anim-attack-duration: 0.6s;
  --anim-hurt-duration: 0.35s;
  --anim-projectile-duration: 0.5s;
  --anim-transition-duration: 0.7s;
}
```

---

### 6.3 Idle State: The Breathing Loop

The idle uses a slow, smooth loop — `ease-in-out` suits breathing because it's continuous and biological, not mechanical. The squash-and-stretch is intentionally subtle: subliminal life, not a visible bounce.

```css
.vibemon-model {
  width: 64px;                       /* Source sprite size; scaled up with nearest-neighbor */
  height: 64px;
  image-rendering: pixelated;
  transform-origin: bottom center;   /* Scale from the feet, not the center */
  animation: idle-breathe var(--anim-idle-duration) infinite ease-in-out;
}

@keyframes idle-breathe {
  0%, 100% { transform: translateY(0)    scale(1, 1);       }
  50%       { transform: translateY(-2px) scale(1.02, 0.98); } /* Volume-conserving squash */
}
```

---

### 6.4 Physical Attack: The Contact Lunge

Four beats — **anticipation**, **action**, **impact hold**, **recovery** — mapping to the classical principle of the same name. `steps(12)` gives the lunge its limited-animation choppiness. Recovery is the longest phase; snapping back instantly would feel weightless.

```css
.is-attacking {
  animation: physical-lunge var(--anim-attack-duration) steps(12) forwards;
}

@keyframes physical-lunge {
  0%   { transform: translateX(0)     rotate(0deg)  scaleX(1);   } /* Rest */
  15%  { transform: translateX(-20px) rotate(-5deg) scaleX(0.9); } /* Anticipation: wind-up, compress */
  30%  { transform: translateX(100px) rotate(3deg)  scaleX(1.2); } /* Action: stretch into the hit */
  50%  { transform: translateX(90px)  rotate(1deg)  scaleX(1.05);} /* Impact hold: brief freeze */
  100% { transform: translateX(0)     rotate(0deg)  scaleX(1);   } /* Recovery: snap back */
}
```

**Corrections from a naive implementation:** anticipation must use *negative* X and *compressed* scaleX to sell the wind-up — rotation alone reads as leaning, not coiling. The impact hold at 50% sits at a *slightly reduced* X offset versus the action peak (90px vs. 100px), simulating the natural rebound of contact.

---

### 6.5 Damage Received: The Hit-Flash

`steps(4)` on the flash is mandatory — a smooth fade reads as a modern ghost effect; the hard binary snap reads as analog. Keep the brightness lift **gentle and warm** rather than blown-out. The animation repeats three times, matching mainline convention.

```css
.is-hurt {
  animation: hurt-flash var(--anim-hurt-duration) steps(4) 3;
}

@keyframes hurt-flash {
  0%, 100% { opacity: 1;   filter: brightness(1);              }
  50%       { opacity: 0.4; filter: brightness(1.6) sepia(0.15); } /* Soft warm lift, not overexposure */
}
```

---

### 6.6 Special / Ranged Attack: The Projectile

Ranged moves (Ember, Water Gun) spawn a projectile that separates from the attacker and crosses the field — absolutely positioned, spawned via JavaScript at attack time. It uses `steps(8)` — snappier than character movement, as projectiles tend to be in limited animation.

```css
.projectile {
  position: absolute;
  opacity: 0;
  image-rendering: pixelated;
  transform-origin: center center;
}

.projectile.is-fired {
  animation: projectile-travel var(--anim-projectile-duration) steps(8) forwards;
}

@keyframes projectile-travel {
  0%   { opacity: 0;   transform: translateX(0)    scale(0.5);       }
  10%  { opacity: 1;   transform: translateX(20px)  scale(1.1, 0.8); } /* Pop in, stretched */
  85%  { opacity: 1;   transform: translateX(220px) scale(1, 1);     } /* Travel */
  100% { opacity: 0;   transform: translateX(240px) scale(1.4, 0.6); } /* Impact: squash on contact */
}
```

The initial pop (`scale(1.1, 0.8)`) stretches the projectile wide and flat in its travel direction; the final frame squashes on the opposite axis to read as impact before it disappears.

---

### 6.7 Scene Transitions: Iris & Wipe

Two transitions, used exclusively for entering and exiting the battle screen.

**Iris Close/Open** — the circular vignette that contracts to a point (entering) or expands from one (returning to overworld). A staple of 1960s television direction borrowed from silent film, and equally at home as a handheld screen wipe. Implemented via `clip-path: circle()`:

```css
.scene-overlay {
  position: fixed;
  inset: 0;
  background: #3D2B1F; /* Tobacco Brown — warmer than pure black */
  pointer-events: none;
}

/* Entering battle: world closes to a point */
.iris-close {
  animation: iris-close var(--anim-transition-duration) steps(16) forwards;
}

/* Returning to overworld: battle expands out from center */
.iris-open {
  animation: iris-open var(--anim-transition-duration) steps(16) forwards;
}

@keyframes iris-close {
  0%   { clip-path: circle(100% at 50% 50%); }
  100% { clip-path: circle(0%   at 50% 50%); }
}

@keyframes iris-open {
  0%   { clip-path: circle(0%   at 50% 50%); }
  100% { clip-path: circle(100% at 50% 50%); }
}
```

**Horizontal Wipe** — a secondary option for lower-stakes transitions (switching battle sub-screens). The Tobacco Brown overlay sweeps left to right, hiding the change beneath it:

```css
.wipe-in {
  animation: wipe-in var(--anim-transition-duration) steps(16) forwards;
}

@keyframes wipe-in {
  0%   { clip-path: inset(0 100% 0 0); } /* Fully hidden */
  100% { clip-path: inset(0 0%   0 0); } /* Fully revealed */
}
```

**Implementation note:** `steps(16)` gives both transitions a characteristic "notched" edge as they advance — they don't glide, they step. This is deliberate. A smooth `ease` iris reads as a modern video effect; a stepped iris reads as a handheld screen wipe.

---

## 7. Audio Architecture

### 7.1 Sonic Vision
The audio keeps its distinctive spine — **1990s monster-game structure filtered through a 1960s–70s analog sound world** — but its *temperament* is now **cozy**: warm, gentle, simple, and unhurried rather than tense or scrappy. The 1990s influence still shapes the *form* (immediate cue starts, short memorable hooks, compact loops, a clear role hierarchy, tight UI rhythm). The 1960s–70s influence still owns the *timbre* (analog, tape-warm, played through a wooden-cabinet TV or transistor radio). What changes is the *energy*: less psych-rock drive and dense jazz-funk, more soft melodic warmth, space, and comfort.

Avoid modern orchestral scoring, EDM polish, pristine square-wave chiptune, novelty instrumentation — and now also avoid aggression and density. Even at its liveliest, the score should feel like a warm afternoon, not a chase.

This vision spans the **entire game**. Title themes, menu sounds, overworld ambience, and every battle variant must read as cuts from the same gentle 1960s–70s library record. Shared traits:

* **Common instrumentation pool** — Hammond B3 + Leslie (soft, rotary-warm), mellow electric piano, upright or round-toned bass, brushed/damped drums, clean-to-lightly-warmed guitar, Mellotron, sparse analog synth blips. A cue may emphasize a subset, but none introduces timbres outside the family.
* **Common processing chain** — every asset, music and SFX, passes through the lo-fi chain in §7.2. The title theme should sound like it came off the same tape reel as a wild encounter.
* **Common harmonic language** — warm modal colorings, gentle major-seventh and added-tone warmth, soft parallel motion typical of cozy period library cues. Related across the whole soundtrack, like tracks from one composer's notebook.
* **Common rhythmic DNA** — even lively cues keep a relaxed, brushed, conga-and-soft-tom vocabulary so moving between menu and battle never feels like crossing genres.

A player hearing the title theme should already anticipate the warmth of their first wild encounter — and the jump to a boss should feel like the same cozy record getting a little livelier, not a switch to a different soundtrack.

### 7.2 The "Lo-Fi" Processing Chain
To achieve the Vibemon sound, all audio — music or SFX — passes through a simulated signal chain. This chain is itself a cozy asset; keep it.
* **Tape Saturation:** Subtle harmonic warmth to "glue" the frequencies and round off any harsh edges.
* **Wow & Flutter:** Slight periodic pitch instability (0.1%–0.3%), the gentle drift of a spinning reel.
* **Frequency Capping:** A soft high-cut around **12kHz** and a low-cut near **100Hz**. The warm, slightly tinny mids are where the nostalgia and comfort live.
* **Resolution Texture:** 12-bit (or 8-bit) texture only where it adds warmth and period character — never to sound damaged.
* **Mono Compatibility:** Music may stay stereo, but bass, drums, hooks, and loop seams must survive small-speaker and mono playback.

### 7.3 SFX Palette: Soft, Physical & Electrical
| Event | Sound Description | Analog Reference |
| :--- | :--- | :--- |
| **Menu Navigation** | A soft, rounded plastic "thunk" with a little body. | 1970s typewriter keys; a rotary phone dial returning home. |
| **Selection / Confirm** | A warm, resonant sine "blip" with a gentle, longish decay. | Early console UI tones; a soft laboratory oscillator. |
| **Taking Damage** | A short, muffled thump with a brief warm-noise edge — felt, not harsh. | A soft knock on a wooden cabinet; a damped speaker cone. |
| **Fainting** | A gentle downward pitch-slide that eases to a stop. | A record player winding down, needle lifting. |
| **HP Bar Draining** | A soft, rhythmic, rounded "tick." | A film projector's muted shutter. |

### 7.4 Musical Direction: "The Cozy Lounge"
The soundtrack leans into **Library Music**, mellow **Soft-Psych**, gentle **Jazz-Funk**, and unhurried **bossa nova** warmth. Battles should feel warm, lively, playful, and comforting — present and engaging, but never tense, dense, or aggressive.

* **Instrumentation:** Hammond B3 with a slow Leslie as a signature warm color, supported by mellow electric piano, round-toned bass, brushed/damped drums, lightly warmed rhythm guitar, soft Mellotron pads, and sparse analog synth blips.
* **Composition:** Relaxed 4/4 with a gentle forward lilt, short memorable hooks, and compact A/B/A loop forms. The B section adds warmth and color, not drama.
* **Looping:** A short intro plus a separate loop. Loops may carry a subtle tape-seam artifact when musically apt, but the runtime loop must feel intentional and never distracting.
* **Tone Guardrails:** Keep playful from tipping into comedic. Avoid circus colors, cartoon novelty, cinematic risers, EDM drops, metal aggression, dense jazz-funk frenzy, and pristine chiptune. **Warmth over tension, space over density.** Copy guardrails: `VOICE.md`.

### 7.5 Soundtrack Hierarchy
Each cue has a role on the emotional ladder, but the whole ladder sits in the **cozy register** — intensity rises through *liveliness, warmth, and arrangement density*, not through tension or aggression. Every cue shares the instrumentation pool, processing chain, and harmonic language of §7.1.

| Cue | Role | Relative Liveliness |
| :--- | :--- | :--- |
| **Title Theme** | Calm, warm, a signature melodic motif that gently foreshadows the battle themes | Lowest |
| **Menu / UI Beds** | Sparse, soft pad or organ drone under menus; quiet enough to layer with SFX | Very low |
| **Overworld / Ambience** | Light and unobtrusive, shared instrumentation at low density | Low |
| **Wild Battle** | Immediate, simple, warm, gently lively; the first battle layer | Medium |
| **Trainer Battle** | A touch more developed and present; fuller kit, longer A/B/A | Higher |
| **Rare Vibemon Battle** | Warmly special — a soft modal shift, a little extra percussion and lift | High |
| **Special Event / Boss Vibemon** | The liveliest and fullest — warm and climactic, never harsh or urgent | Highest |

The Title Theme plants a short melodic or harmonic motif that the battle cues later quote, paraphrase, or invert — this is what makes the whole game feel like one warm record rather than a playlist.

### 7.6 Technical Implementation (Web Audio API)
To match the `steps()` logic of the animation, audio may pass through a **Bit-Crusher node** at 12-bit or 8-bit depth when a source feels too clean — used for warmth, not grit. For battle music with separate intro and loop assets, prefer tightly scheduled playback so the intro hands off to the loop with no perceptible gap.

## 8. Trainer Gear & Capture Media

Trainers do not throw spheres. They carry a **Vibe Deck** on the belt and store **Vibemon** on **Vibe Carts** in a **Cart Folio** — field-portable gear that replaces the handheld index, bag, and capture-item conventions of mainline monster battlers without copying their silhouettes.

* **Vibe Deck** — clamshell wood-grain player; closed in icons; three-quarter reference pose **facing right**. Crew index, encounter log, and **Press** capture interface.
* **Vibe Cart** — rounded-rect cartridge with circular label window; the same physical object blank (**Blank Cart**) or occupied.
* **Cart Folio** — six-slot canvas wallet; diegetic **Crew** holder.

Wild capture presentation: slot **Blank Cart** → **Press** → stepped reel pulse → labeled cart returns to folio. Use plastic thunk + warm blip SFX (§7.3). **Hatch** / **Generation** birth rituals stay separate from field capture.

Full visual tokens, tier names, player copy, and concept-art prompt anchors: **`GEAR.md`**. Domain definitions: **`CONTEXT.md`**. Copy tone: **`VOICE.md`**.

## 9. Wild Battle Screen

The wild battle UI is a **320×180-first scene** (`BattleScene`) mounted at `/battle/{id}`. It mirrors the cozy handheld flow: intro iris → command menu → move select → event replay → loop or end. Copy follows `VOICE.md` **Battle Beats**; progression label is **XP** (two letters, pairs with HP).

### 9.1 State Machine

| Phase | Player sees | Input |
| :--- | :--- | :--- |
| `intro` | Iris open + *A wild {name} steps out.* | Enter / Space |
| `command` | 2×2 **MOVES / DECK / CREW / RUN** (DECK + CREW greyed) | Arrow keys + Enter |
| `moveSelect` | 2×2 move tiles + side panel (PP, power, accuracy, type) | Arrow keys + Enter; Esc back |
| `resolving` | Event-replay queue (dialog → animation → HP drain) | Enter / Space between steps |
| `won` | Silent → XP bar; optional *{name} grew to Lv {n}!* | Enter returns to crew |
| `defeat` | *You and your crew head home to rest.* | Enter returns to crew |
| `fled` | *You slip away.* | Enter returns to crew |

**Event-replay model:** each `BattleTurnRead` becomes an ordered queue — `message` lines from the API, `animation` beats derived from `(category, type)`, `hurt` flash, and `hp` tweens to the post-turn values. The HUD never jumps instantly to the final state while `resolving`.

### 9.2 Deck Read (hold C)

Hint: *Hold C — Read*. Keyboard-only this slice.

| Layer | Always visible (baseline) | Shown while C held (Deck Read) |
| :--- | :--- | :--- |
| Combatant HUD | Name, Lv, HP bar + exact HP, XP bar (hero) | Stat-stage arrows (non-zero), status/volatile turn counters, *XP to Lv {n}* |
| Move menu | PP, power, accuracy, type per tile | Effectiveness glyph + tint on every tile; highlighted tile spells *Super effective* / *Not very effective* / *No effect* |

Reveal uses stepped opacity (`--anim-ui-reveal-steps`) — quick, on-aesthetic, not a smooth fade.

### 9.3 Animation Profile

Frontend derives animation from `(category, type)` per `docs/development/adr/0004`. No `animation_key` on domain moves.

| `(category, type)` | Animation | CSS / timing |
| :--- | :--- | :--- |
| `physical` + any | Contact lunge toward opponent | `physical-lunge`, `--anim-attack-duration`, `steps(--anim-action-steps)` |
| `special` + any | Type-tinted projectile across field | `projectile-travel`, `--anim-projectile-duration`, `steps(8)` |
| `status` + any | Attacker glow (no projectile) | Short glow beat on attacker sprite |

**Override registry:** `moveAnimations.ts` keyed by move id — stubbed empty; bespoke signature moves land here later without backend changes.

Cross-ref: §6.3 idle breathe, §6.4 physical lunge, §6.5 hurt flash, §6.6 projectile — all `image-rendering: pixelated`, transforms stepped per §6.
