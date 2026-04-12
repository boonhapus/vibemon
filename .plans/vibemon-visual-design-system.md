# Vibemon Visual Design System

**Version:** 0.3  
**Aesthetic:** Retro pixel × modern flat × synthwave neon  
**Layout reference:** Pokémon Gen 3 battle UI  
**Platforms:** Web (desktop + mobile)

---

## 1. Color System

All colors are defined as CSS custom properties on `:root`. Groups: **background layers**, **neon and side accents**, **HP state colors**, **text**.

### 1.1 Background Layers

| Token | Hex | Usage |
|---|---|---|
| `--vb-void` | `#06040F` | Deepest background, HP track fills |
| `--vb-abyss` | `#0D0B1E` | Battle scene background, app frame base |
| `--vb-deep` | `#130F2A` | Battle bottom panel |
| `--vb-surface` | `#1C1838` | Move buttons (default), component cards |
| `--vb-raised` | `#262049` | Elevated surfaces, hover states |
| `--vb-border` | `#3A3360` | Default borders, dividers |

### 1.2 Neon and Side Accents

| Token | Hex | Usage |
|---|---|---|
| `--violet` | `#9D4EDD` | Structural accents, highlights |
| `--violet-hi` | `#B76FFF` | Violet hover/active |
| `--magenta` | `#E040FB` | Player info card border, player platform accent |
| `--pink` | `#FF6EC7` | Branding gradients |
| `--teal` | `#00E5FF` | Synthwave ground grid, enemy info card border, enemy platform accent |
| `--teal-hi` | `#64FFDA` | Teal hover/active |
| `--coral` | `#FF6B9D` | Warm branding accent |
| `--gold` | `#FFD600` | Level numbers, mid-importance labels |

**Battle chrome:** Enemy side uses **teal** accents (card border, platform). Player side uses **magenta** accents. The move grid stays **neutral** (`--vb-surface` / `--vb-border`); hover uses raised surface treatment only — no per-move or per-element color system.

### 1.3 HP State Colors

Applied from current HP percentage.

| Token | Hex | Threshold |
|---|---|---|
| `--hp-hi` | `#39FF14` | HP > 50% |
| `--hp-mid` | `#FFD600` | HP 26–50% |
| `--hp-lo` | `#FF3860` | HP ≤ 25% |

HP fill uses `transition: background 0.3s` (and width per §4.1).

### 1.4 Text Colors

| Token | Hex | Usage |
|---|---|---|
| `--vb-text` | `#EDE5FF` | Primary text |
| `--vb-subtle` | `#9B8EC4` | Secondary text, labels |
| `--vb-muted` | `#5A508A` | Tertiary text, disabled |

---

## 2. Typography

Three fonts, fixed roles.

### 2.1 Font Stack

| Variable | Family | Source | Role |
|---|---|---|---|
| `--f-px` | `'Press Start 2P', monospace` | Google Fonts | Monster names, move names, HP label, level label text, UI alerts |
| `--f-ui` | `'Oxanium', sans-serif` | Google Fonts | HP numbers, battle copy, menus, descriptions |
| `--f-dt` | `'Share Tech Mono', monospace` | Google Fonts | Stat numbers, timestamps, PP, category line on moves |

### 2.2 Type Scale

| Role | Font | Size | Weight | Color |
|---|---|---|---|---|
| Monster name | `--f-px` | 8px | 400 | `--vb-text` |
| Move name | `--f-px` | 7px | 400 | `--vb-text` |
| HP label ("HP") | `--f-px` | 5–6px | 400 | `--vb-muted` |
| Level number | `--f-dt` | 11px | 400 | `--vb-subtle` (number in `--gold`) |
| HP numbers (e.g. 128/160) | `--f-ui` | 11–22px | 700 | `--vb-text` |
| Battle message | `--f-px` | 7–8px | 400 | `--vb-text` |
| Move secondary (category · power, PP) | `--f-dt` | 10px | 400 | `--vb-muted` |
| Stat readout | `--f-dt` | 12–14px | 400 | `--teal` or `--vb-subtle` |
| Section label | `--f-dt` | 9–11px | 400 | `--vb-muted` |

**Rule:** Never use `--f-ui` or `--f-dt` for monster or move **names**. Never use `--f-px` for HP numerals or dense numeric readouts.

---

## 3. Battle UI Layout

Gen 3–style split: **battle scene** (top) and **battle panel** (bottom).

### 3.1 Layout Structure

```
┌─────────────────────────────────────────────────┐
│  [Enemy Info Card]          [Enemy Sprite]       │  ← Battle scene (~55–60% height)
│                   [platforms / ground]           │
│  [Player Sprite]        [Player Info Card]       │
├─────────────────────────────────────────────────┤
│  [Message bar: "What will X do?"]                │  ← Battle panel
│  ┌──────────────┬──────────────┐                 │
│  │  Move 1      │  Move 2      │                 │
│  ├──────────────┼──────────────┤                 │
│  │  Move 3      │  Move 4      │                 │
│  └──────────────┴──────────────┘                 │
└─────────────────────────────────────────────────┘
```

### 3.2 Battle Scene

- **Background:** Synthwave dusk gradient — `#06030D` → `#1A0933` → `#4A1261` → `#8B1A5C` → `#C42B60` → `#E8553A` → `#F5874A` (horizon)
- **Ground grid:** Perspective grid `rgba(0,229,255,0.35)` to horizon (vertical fan + horizontal arcs)
- **Stars:** Dots in upper ~55% of sky, 0.3–1.5px radius, white 20–90% opacity
- **Enemy platform:** Top-right. Ellipse `rgba(0,229,255,0.2)` fill, `rgba(0,229,255,0.5)` top edge, ~160×22px
- **Player platform:** Bottom-left. Ellipse `rgba(224,64,251,0.2)` fill, `rgba(224,64,251,0.5)` top edge, ~200×26px
- **Enemy sprite:** Top-right, above platform, front-facing
- **Player sprite:** Bottom-left, above platform, back-facing

### 3.3 Info Cards

Shared base:

```css
background: rgba(6, 4, 15, 0.82);
border-radius: 10px;
padding: 10px 14px;
min-width: 190px;
```

| Card | Position | Border |
|---|---|---|
| Enemy | `top: 14px; left: 14px` | `rgba(0, 229, 255, 0.45)` |
| Player | `bottom: 14px; right: 14px` | `rgba(224, 64, 251, 0.45)` |

**Enemy card:** Name + level; HP label + HP bar only (no numeric HP).  
**Player card:** Name + level; HP label + HP numbers + HP bar; EXP bar under HP bar.

### 3.4 Battle Panel

- **Background:** `--vb-deep`
- **Top border:** `2px solid var(--vb-border)`
- **Message bar:** `padding: 10px 16px`, `border-bottom: 1px solid var(--vb-border)`, `min-height: 40px`, pixel font + blink cursor (§4.6)
- **Move grid:** `grid-template-columns: 1fr 1fr`, `gap: 2px`, `padding: 3px`

---

## 4. Components

### 4.1 HP Bar

Three layers: track → fill (by HP%) → top highlight.

```
[track: --vb-void, 1px rgba(255,255,255,0.06) border]
  └── [fill: HP% colors, transition width + background]
        └── [highlight: top 40% of fill, rgba(255,255,255,0.2)]
```

- Card bars: `height: 7px`, `border-radius: 2px`
- Standalone bars: `height: 10–12px`, `border-radius: 3px`
- Width: `0.6s cubic-bezier(0.4, 0, 0.2, 1)`; fill color: `background 0.3s`

**HP % → color:** >50% `--hp-hi`, >25% `--hp-mid`, else `--hp-lo`.

### 4.2 EXP Bar

Below player HP only.

```css
height: 3px;
background: linear-gradient(90deg, #5C6BC0, var(--teal));
border-radius: 2px;
margin-top: 5px;
```

Width = progress toward next level. No state color changes.

### 4.3 Move Buttons

Four buttons, **neutral** chrome (no elemental or provider-based palettes).

**Base:**

```css
background: var(--vb-surface);
border: 1px solid var(--vb-border);
border-radius: 7px;
padding: 10px 12px;
display: flex;
flex-direction: column;
gap: 4px;
transition: background 0.12s, border-color 0.12s, box-shadow 0.12s;
```

**Hover / focus:** `--vb-raised` background, border remains `var(--vb-border)` or one step brighter; optional very subtle shadow `0 2px 8px rgba(0,0,0,0.35)` — **no** colored glow per move.

**Contents:**

1. Move name — `--f-px`, 7px, `--vb-text`
2. Secondary line — `--f-dt`, 10px, `--vb-muted`: category, power if applicable, **PP** when battle state exposes it. **Do not** show elemental type on the button; type belongs in engine and log, not move chrome.

### 4.4 Info Card Name Row

- Name: `--f-px`, 8px, `--vb-text`
- Level: `--f-dt`, 11px — `Lv.` in `--vb-subtle`, digits in `--gold`

### 4.5 Status Badges

Inline with name when a status applies.

```css
font-family: var(--f-px);
font-size: 6px;
padding: 3px 7px;
border-radius: 3px;
```

| Status | Abbr | Background | Text | Border |
|---|---|---|---|---|
| Poisoned | PSN | `rgba(156,39,176,0.4)` | `#CE93D8` | `rgba(156,39,176,0.6)` |
| Burned | BRN | `rgba(255,87,34,0.4)` | `#FFAB91` | `rgba(255,87,34,0.6)` |
| Asleep | SLP | `rgba(96,125,139,0.4)` | `#B0BEC5` | `rgba(96,125,139,0.6)` |
| Paralyzed | PAR | `rgba(255,214,0,0.3)` | `#FFD600` | `rgba(255,214,0,0.5)` |
| Frozen | FRZ | `rgba(0,229,255,0.2)` | `#00E5FF` | `rgba(0,229,255,0.5)` |

### 4.6 Message Box

```css
font-family: var(--f-px);
font-size: 7–8px;
color: var(--vb-text);
line-height: 1.9;
padding: 10px 16px;
min-height: 40px;
```

**Cursor** — inline span, `7×7px`, `background: var(--vb-text)`, `margin-left: 6px`, `animation: blink 1s step-end infinite` (keyframes in §8.3).

---

## 5. Spacing & Layout Tokens

```css
--sp-1:  4px;
--sp-2:  8px;
--sp-3:  12px;
--sp-4:  16px;
--sp-5:  20px;
--sp-6:  24px;
--sp-8:  32px;
--sp-10: 40px;
--sp-12: 48px;
--sp-16: 64px;
--sp-20: 80px;
```

---

## 6. Border Radius Tokens

```css
--r-sm:   3px;
--r-md:   6px;
--r-lg:   10px;   /* info cards, component cards */
--r-xl:   16px;   /* outer battle wrapper */
--r-pill: 9999px; /* chips */
```

---

## 7. Motion & Animation System

### 7.1 Transition Speeds

```css
--t-snap:   80ms ease;
--t-fast:   140ms ease;
--t-normal: 220ms ease;
--t-slow:   380ms ease;
--t-bounce: 420ms cubic-bezier(0.34, 1.56, 0.64, 1);
--t-spring: 500ms cubic-bezier(0.16, 1, 0.3, 1);
```

### 7.2 Named Animations

| Name | Duration | Easing | Trigger | Description |
|---|---|---|---|---|
| `attack-shake` | 350ms | ease | Move use (attacker) | Horizontal shake ±8px → ±5px |
| `damage-flash` | 450ms | ease | Target hit | `brightness(8) saturate(0)` flash; neutral white/gray — **not** tied to move type |
| `float-idle` | 2.8s | ease-in-out | Loop | `translateY(0 → -8px → 0)` |
| `bounce-in` | 400ms | spring | Sprite enters | `scale(0.5) → 1.2 → 1` |
| `slide-up` | 250ms | ease | Panel open | `translateY(14px)` + opacity in |
| `glitch` | 300ms | steps(1) | Special status (e.g. confused) | `clip-path` + `translateX` jitter — not decorative |
| `pulse-glow` | 1.5s | ease-in-out | Active loop | Opacity pulse on glow layer |

### 7.3 Keyframe Definitions

```css
@keyframes attack-shake {
  0%, 100% { transform: translateX(0); }
  20%       { transform: translateX(-8px); }
  40%       { transform: translateX(8px); }
  60%       { transform: translateX(-5px); }
  80%       { transform: translateX(5px); }
}

@keyframes damage-flash {
  0%, 100% { filter: none; opacity: 1; }
  30%, 70% { filter: brightness(8) saturate(0); opacity: 0.7; }
  50%       { opacity: 0; }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-8px); }
}

@keyframes bounce-in {
  0%   { transform: scale(0.5); opacity: 0; }
  60%  { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes slide-up {
  from { transform: translateY(14px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}

@keyframes glitch {
  0%, 100% { clip-path: none; transform: none; }
  25%       { clip-path: polygon(0 20%, 100% 20%, 100% 40%, 0 40%); transform: translateX(5px); }
  50%       { clip-path: polygon(0 60%, 100% 60%, 100% 80%, 0 80%); transform: translateX(-4px); }
  75%       { clip-path: none; transform: none; }
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.5; }
  50%       { opacity: 1; }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}
```

### 7.4 Usage Rules

- Idle `float` on sprites; player **3.6s**, enemy **3s**, ~0.5s phase offset.
- `attack-shake` on attacker; `damage-flash` on target ~200ms after attack start.
- `bounce-in` on sprite enter; `slide-up` on panels.
- Looping animations `paused` when fainted.

---

## 8. Component Elevation

| Level | Background | Border | Used for |
|---|---|---|---|
| Base | `--vb-abyss` | — | Battle scene frame |
| Surface | `--vb-surface` | `1px solid var(--vb-border)` | Move buttons, cards |
| Raised | `--vb-raised` | `1px solid var(--vb-border)` | Hover, selection |
| Overlay | `rgba(6,4,15,0.82)` | **Enemy:** `1px solid rgba(0,229,255,0.45)` — **Player:** `1px solid rgba(224,64,251,0.45)` | Info cards over scene |

---

## 9. Responsive Breakpoints

| Breakpoint | Width | Adjustments |
|---|---|---|
| Mobile | ≤ 560px | Move grid stays 2-col; monster name 6px; card `min-width: 160px`; scene height ~240px |
| Tablet / Desktop | > 560px | Full layout |

Move grid **always** two columns.

---

## 10. CSS Variable Quick Reference

```css
:root {
  --vb-void:    #06040F;
  --vb-abyss:   #0D0B1E;
  --vb-deep:    #130F2A;
  --vb-surface: #1C1838;
  --vb-raised:  #262049;
  --vb-border:  #3A3360;

  --vb-text:   #EDE5FF;
  --vb-subtle: #9B8EC4;
  --vb-muted:  #5A508A;

  --violet:    #9D4EDD;
  --violet-hi: #B76FFF;
  --magenta:   #E040FB;
  --pink:      #FF6EC7;
  --teal:      #00E5FF;
  --teal-hi:   #64FFDA;
  --coral:     #FF6B9D;
  --gold:      #FFD600;

  --hp-hi:  #39FF14;
  --hp-mid: #FFD600;
  --hp-lo:  #FF3860;

  --f-px: 'Press Start 2P', monospace;
  --f-ui: 'Oxanium', sans-serif;
  --f-dt: 'Share Tech Mono', monospace;

  --sp-1: 4px;  --sp-2: 8px;   --sp-3: 12px;  --sp-4: 16px;
  --sp-5: 20px; --sp-6: 24px;  --sp-8: 32px;  --sp-10: 40px;
  --sp-12: 48px; --sp-16: 64px; --sp-20: 80px;

  --r-sm: 3px; --r-md: 6px; --r-lg: 10px; --r-xl: 16px; --r-pill: 9999px;

  --t-snap:   80ms ease;
  --t-fast:   140ms ease;
  --t-normal: 220ms ease;
  --t-slow:   380ms ease;
  --t-bounce: 420ms cubic-bezier(0.34, 1.56, 0.64, 1);
  --t-spring: 500ms cubic-bezier(0.16, 1, 0.3, 1);
}
```

---

## 11. Raster Sprites (Together / FLUX)

Battle sprites are **isolated** raster images: one creature, **transparent** background, no ground and no UI in-frame. Prompts use high-fidelity pixel language with **light** neon-friendly rim or accent lighting so creatures read clearly on the synthwave dusk scene without painting an environment in the image.
