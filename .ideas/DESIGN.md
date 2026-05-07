# Retro Pokémon Battle: 1960s-70s Aesthetic Design Document

## 1. Vision Statement
The objective is to reimagine the iconic Pokémon battle interface through the stylistic lens of the mid-20th century. By blending the digital "modernity" of the Pokémon franchise with the analog, tactile warmth of the 1960s and 70s, we create a "retro-futuristic" experience that feels both nostalgic and fresh.

## 2. Color Palette
The design moves away from the vibrant, primary-colored high-contrast UI of modern gaming, opting instead for a palette inspired by mid-century interior design and Kodachrome photography.

### 2.1 Core Palette

| Color Name | Hex Code | Usage |
| :--- | :--- | :--- |
| **Mustard Yellow** | #E1AD01 | Highlights, Selection cursors, Health bars |
| **Avocado Green** | #568203 | Background environments, Stat bars |
| **Burnt Orange** | #CC5500 | Menus, Charmander's flame accents |
| **Tobacco Brown** | #3D2B1F | Text, Borders, Shadows |
| **Cream/Eggshell** | #F5F5DC | Text boxes, Background contrast |
| **Grape Plum** | #7C4D8A | Accent color; psychedelic flourishes, secondary borders, ability badge backgrounds |

The **Grape Plum** accent draws from the era's enthusiasm for bold, slightly-muted purples — found in 1960s mod fashion, early psychedelic concert posters, and the warm-toned linen prints of the 1970s. It pairs with Mustard Yellow as a classic mid-century complementary tension (yellow-purple) and softens against Cream backgrounds. Avoid using it at full saturation in large areas; instead deploy it as a tertiary decorative accent and in the Psychic and Ghost type treatments below.

---

### 2.2 Vibemon Type Colors
All type colors are drawn from period-accurate mid-century references: Pantone textile standards of the era, Kodachrome film stock, and the muted-but-warm household color trends of the 1960s–70s. Full-saturation digital primaries are intentionally avoided.

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
| **Ghost** | Dusk Indigo | #524870 | Late-evening sky in Kodachrome, shadow tones in Ektachrome slides |
| **Dragon** | Deep Verdigris | #2A5C58 | Oxidized copper, mid-century brass-and-patina hardware |
| **Dark** | Espresso | #4A3428 | Dark-roast coffee, walnut veneer furniture |
| **Steel** | Pewter | #8A8C8E | Vintage Airstream aluminum, 60s appliance chrome faded by use |
| **Fairy** | Rose Quartz | #C4909A | Pastel cosmetics packaging, 50s–60s nursery pink |

Type badges should be rendered as small pill or rounded-rectangle labels using the type color as a background and Tobacco Brown or Cream as text, depending on luminosity. Apply a subtle linen-grain texture overlay to each badge.

---

### 2.3 Status Colors
Status indicators follow the same period-accurate desaturation principle — these are not traffic-light primaries, but their warm, analog equivalents.

| Status | Color Name | Hex Code | Usage |
| :--- | :--- | :--- | :--- |
| **Green (Healthy)** | Sage | #6B9B5A | Full or near-full HP, "OK" state, active/ready indicators |
| **Orange (Caution)** | Amber | #CC7A22 | Mid-range HP, status conditions (burn, poison tick), warning states |
| **Red (Critical)** | Brick | #A03020 | Low HP, fainted, critical-error states |

These three map directly onto the segmented health-bar blocks described in §3.2. As HP decreases, the filled blocks transition through Sage → Amber → Brick. The transition thresholds should be 50% (Sage→Amber) and 20% (Amber→Brick), consistent with mainline Pokémon conventions. The unfilled block segments should render in a desaturated Tobacco Brown at ~30% opacity.

---

## 3. Typography & UI Elements
### 3.1 Typography
* **Headings:** Bold, geometric sans-serifs like *Futura* or *ITC Avant Garde*.
* **Battle Text:** High-readability slab serifs reminiscent of IBM Selectric typewriter fonts or early television broadcast graphics.
* **Texture:** All text should feature a slight "ink bleed" or "chromatic aberration" effect to simulate analog printing or CRT screens.

### 3.2 Health Bars & Menus
* **Health Bars:** Instead of sleek gradients, use segmented blocks with rounded corners. The containers should look like plastic-molded dashboard gauges from a 1970s sedan.
* **Buttons:** Tactile-looking buttons with "pressed" states that suggest physical depth. Use aged textures (simulated paper grain or linen finish) on the menu backgrounds.

## 4. Scene Composition
The battle utilizes a classic "Over-the-Shoulder" perspective, emphasizing the scale between the trainer's Pokémon and the opponent.

* **Foreground:** Charmander (Level 12). Rendered with soft-focus edges to create depth of field. The orange of its skin should lean toward a "terracotta" tone to fit the palette.
* **Background:** Rattata (Level 10). Positioned on a circular "stage" of dirt. The background environment should feature simplified, flat-vector trees in Avocado Green and Olive.
* **Atmosphere:** A subtle grain overlay (film grain) and a slight vignette at the corners of the frame to mimic a vintage camera lens.

## 6. Visual Effects & Animation System

The animation language must feel like Saturday-morning television, not a game engine. Every motion should carry the weight of a physical, hand-crafted medium. The three pillars that make this possible in CSS — stepped timing, non-uniform scaling, and analog flicker — each map directly to a period technique and are described below before their implementations.

---

### 6.1 Foundational Animation Principles

#### The "Step" Timing Function — Limited Animation
Hanna-Barbera productions of the 1960s operated on strict budgets, which forced animators to shoot on "twos" or "threes" — holding a single drawing for two or three film frames rather than one. The result was a characteristic choppiness running at roughly 8–12 drawings per second. `steps(N)` replicates this exactly: it snaps between keyframe positions in discrete jumps rather than interpolating smoothly. Using `ease` or `linear` on an attack animation would immediately feel wrong — too fluid, too digital. **Use `steps(8)` to `steps(16)` for all action states. Reserve `ease-in-out` only for slow, ambient loops like breathing.**

#### Non-Uniform Scaling — Rubber-Hose Squash & Stretch
The Fleischer Studios and early Disney shorts of the 1930s–40s established squash-and-stretch as a fundamental principle of organic animation. A character landing from a jump squashes wide and flat; a character reaching for something stretches tall and thin. The key insight is that **volume is conserved**: when width increases, height decreases proportionally, and vice versa. `scale(1.02, 0.98)` expresses this — 2% wider, 2% shorter — maintaining mass while communicating life. A rigid `scale(1.02, 1.02)` just makes the sprite bigger; it doesn't feel alive.

#### The Flicker — Kinescope & Celluloid Artifacts
Before videotape became standard in US television broadcasting (roughly 1956–1960 for color), live programs were preserved by pointing a film camera at a monitor — a process called kinescoping. The resulting recordings carry a characteristic brightness pulse and grain flutter on hard cuts. When a Pokémon takes a hit, the mainline games approximate this with a rapid opacity strobe. We pair that opacity pulse with a `brightness` spike to simulate the overexposed frame that occurs during a kinescope splice or a film-projector hiccup. **Always apply `steps()` to damage flicker — a smooth sine-wave fade reads as "modern." A hard, binary snap reads as "analog."**

---

### 6.2 Foundational CSS Variables

Define timing constants at the root so all animations share a coherent system:

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

The idle state uses a slow, smooth loop — `ease-in-out` is appropriate here because breathing is continuous and biological, not mechanical. The squash-and-stretch values are intentionally subtle; the goal is subliminal life, not a visible bounce.

```css
.pokemon-model {
  width: 150px;
  height: 150px;
  transform-origin: bottom center; /* Scale from the feet, not the center */
  animation: idle-breathe var(--anim-idle-duration) infinite ease-in-out;
}

@keyframes idle-breathe {
  0%, 100% { transform: translateY(0)    scale(1, 1);       }
  50%       { transform: translateY(-5px) scale(1.02, 0.98); } /* Volume-conserving squash */
}
```

---

### 6.4 Physical Attack: The Contact Lunge

This animation has four distinct beats — **anticipation**, **action**, **impact hold**, and **recovery** — which map directly to the classical animation principle of the same name. The `steps(12)` timing gives the lunge the limited-animation choppiness of a Saturday-morning cartoon fight sequence. Note that recovery is the longest phase; snapping back instantly would feel weightless.

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

**Key corrections from a naive implementation:** the anticipation phase must use *negative* X and *compressed* scaleX to sell the wind-up. An anticipation that only rotates, without the backward pull, feels like the Pokémon is leaning rather than coiling. The impact hold at 50% must be at a *slightly reduced* X offset compared to the action peak (90px vs. 100px) — this simulates the natural rebound of physical contact.

---

### 6.5 Damage Received: The Kinescope Flicker

`steps(4)` on the flicker is mandatory. A smooth opacity fade reads as a modern "ghost" effect; the hard binary snap between opaque and semi-transparent reads as a film splice. The `brightness` spike on the dark frame simulates the brief overexposure of a kinescope dropout. The animation repeats three times to match mainline Pokémon conventions.

```css
.is-hurt {
  animation: hurt-flash var(--anim-hurt-duration) steps(4) 3;
}

@keyframes hurt-flash {
  0%, 100% { opacity: 1;   filter: brightness(1) sepia(0);    }
  50%       { opacity: 0.3; filter: brightness(2.5) sepia(0.4); }
  /* Brightness spike + sepia tint simulates kinescope overexposure on a warm film stock */
}
```

---

### 6.6 Special / Ranged Attack: The Projectile

Ranged moves (e.g., Ember, Water Gun) require a projectile that separates from the attacker and travels across the field. The projectile element should be absolutely positioned and spawned via JavaScript at attack time. It uses `steps(8)` — fewer steps than the lunge, because projectiles in cel animation often feel snappier than character movement.

```css
.projectile {
  position: absolute;
  opacity: 0;
  transform-origin: center center;
}

.projectile.is-fired {
  animation: projectile-travel var(--anim-projectile-duration) steps(8) forwards;
}

@keyframes projectile-travel {
  0%   { opacity: 0;   transform: translateX(0)    scale(0.5);  }
  10%  { opacity: 1;   transform: translateX(20px)  scale(1.1, 0.8); } /* Pop into existence, stretched */
  85%  { opacity: 1;   transform: translateX(220px) scale(1, 1);     } /* Travel */
  100% { opacity: 0;   transform: translateX(240px) scale(1.4, 0.6); } /* Impact: final squash on contact */
}
```

The initial pop (`scale(1.1, 0.8)`) applies the stretch principle: a projectile launched horizontally should be wide and flat, not a perfect circle. The final frame squashes on the opposite axis to simulate impact deformation before the projectile disappears.

---

### 6.7 Scene Transitions: Iris & Wipe

Two transition types are period-accurate and should be used exclusively for entering and exiting the battle screen.

**Iris Close/Open** is the circular vignette that contracts to black (entering battle) or expands from black (returning to overworld). It was a staple of 1960s television direction, borrowed from silent film. Implemented via `clip-path: circle()`:

```css
.scene-overlay {
  position: fixed;
  inset: 0;
  background: #3D2B1F; /* Tobacco Brown — warmer than pure black, period-accurate */
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

**Horizontal Wipe** is a secondary option for lower-stakes transitions (e.g., switching between battle sub-screens). The Tobacco Brown overlay sweeps across the viewport from left to right, momentarily hiding the scene change beneath it:

```css
.wipe-in {
  animation: wipe-in var(--anim-transition-duration) steps(16) forwards;
}

@keyframes wipe-in {
  0%   { clip-path: inset(0 100% 0 0); } /* Fully hidden: right edge flush with left */
  100% { clip-path: inset(0 0%   0 0); } /* Fully revealed */
}
```

**Implementation note:** `steps(16)` on both transitions gives the wipe and iris a characteristic "notched" edge as they move — they do not glide smoothly, they advance in visible increments. This is deliberate and period-accurate; a smooth `ease` iris would read as a modern video effect. A stepped iris reads as a 16mm projector.

---

## 7. Audio Architecture

### 7.1 Sonic Vision
The audio must avoid the "clean" digital oscillators of modern handhelds. Instead, it should mimic the warm, slightly distorted output of a 1970s wooden-cabinet television or a portable transistor radio. Every sound should feel like it was recorded onto magnetic tape or generated by an analog synthesizer (e.g., Moog or Buchla).

### 7.2 The "Lo-Fi" Processing Chain
To achieve the "Vibemon" sound, all audio assets—whether music or SFX—must pass through a simulated signal chain:
* **Tape Saturation:** A subtle harmonic distortion to "glue" the frequencies together.
* **Wow & Flutter:** Slight, periodic pitch instability (0.1%–0.3%) to mimic a spinning record or tape reel.
* **Frequency Capping:** A steep high-cut filter at **12kHz** and a low-cut at **100Hz**. The "tinny" mids are where the nostalgia lives.

### 7.3 SFX Palette: Physical & Electrical
| Event | Sound Description | Analog Reference |
| :--- | :--- | :--- |
| **Menu Navigation** | A heavy, plastic "thunk" or a metallic "clack." | 1970s typewriter keys; rotary phone dial returning to home. |
| **Selection/Confirm** | A warm, resonant sine-wave "blip" with a long decay. | Early Atari 2600 UI sounds; laboratory oscillators. |
| **Taking Damage** | A brief burst of white noise followed by a low-frequency hum. | A CRT television being slapped; a mic-stand being bumped. |
| **Fainting** | A pitch-sliding downward "whirr" that slows down. | A record player being switched off while the needle is still down. |
| **HP Bar Draining** | A rhythmic, percussive "ticking." | A film projector's mechanical shutter. |

### 7.4 Musical Direction: "The Lounge Battle"
The soundtrack should pivot away from "epic orchestral" and toward **Library Music** and **Psych-Rock**.
* **Instrumentation:** Hammond B3 organs (with Leslie speakers), "fuzzy" distorted bass guitars, dry "dead" drums (mimicking 70s studio dampening), and Mellotron strings.
* **Composition:** Fast-paced Bossa Nova or Jazz-Funk for battles. Use "Phasing" effects and "Wah-wah" pedals on guitar tracks to match the **Grape Plum** psychedelic visual flourishes.
* **Looping:** Instead of a perfect digital loop, the music should have a 0.5-second "pop" or "crackle" at the loop point, simulating the physical seam of a tape loop.

### 7.5 Technical Implementation (Web Audio API)
To match the `steps()` logic of the animations, the audio should utilize a **Bit-Crusher node** set to 12-bit or 8-bit depth, ensuring the "resolution" of the sound matches the "choppiness" of the Saturday-morning animation style.
