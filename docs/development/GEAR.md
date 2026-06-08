# Trainer Gear & Capture Media

Visual tokens and iconography for the trainer's field equipment. Domain meaning and player-facing copy live in `CONTEXT.md`; locked hex values live in `COLORS.md` and `DESIGN.md` §2.

## Canonical Objects

| Object | Role | Silhouette |
| :--- | :--- | :--- |
| **Vibe Deck** | Always-carried trainer device — crew index, encounter log, field capture tool (Pokédex + bag in one) | Clamshell handheld; wood-grain body; closed by default in icons |
| **Vibe Cart** | Physical medium a **Vibemon** is stored on; same object before and after capture | Rounded rect + circular label window |
| **Cart Folio** | Portable **Crew** holder — six cart slots on belt or in deck lid | Canvas wallet; cart spines visible |
| **Blank Cart** | Consumable capture medium used in wild **Catch** | Unlabeled **Vibe Cart** |

Use **Cart** in UI once context is established. Reserve **cartridge** for flavor text or tooltips only.

## Player-Facing Copy

| Context | Preferred | Avoid |
| :--- | :--- | :--- |
| Wild capture action | **Press**, **Slot Cart** | throw, trap |
| Capture item menu | **CART** | ball |
| Success | **Cart saved!**, **Vibe recorded!** | caught, gotcha |
| Failure | **Cart blank**, **Signal lost** | broke free |
| Full roster | **Folio full** | box full, PC full |

## Capture Cart Tiers

Same **Vibe Cart** shape at every tier — differentiate with label stock and subtle texture, not colored spheres.

| Tier | Name | Notes |
| :--- | :--- | :--- |
| Basic | **Field Cart** | Default consumable |
| Mid | **Studio Cart** | Cleaner signal; warmer dub |
| High | **Master Cart** | Full-fidelity capture; optional flavor alias **Master Loop** |

## Vibe Deck — Visual Tokens

**Form:** Chunky clamshell, slightly wider than tall — 1970s wood-cabinet transistor radio × early pocket media player. **Closed** in inventory, battle, and icon contexts unless a screen explicitly shows the interior.

**Palette mapping** (names from `COLORS.md`):

| Part | Color |
| :--- | :--- |
| Wood body | Warm walnut / **Espresso**–**Tobacco Brown** grain |
| Face plate | **Parchment Cream** |
| Bezels, seams, outlines | **Tobacco Brown** |
| Hinge accent stripe | **Grape Plum** |
| Selection notch / slider | **Soft Mustard** |
| Indicator lamps | **Sage** (ready), **Burnt Orange** (active) |
| Belt clip | **Pewter** |

**Front face (closed):** rounded-rect cart slot mouth; circular label window (may show abstract silhouette in deck UI); small loop counter / reel window (circular glass); one chunky confirm button; minimal analog indicators — no digital readouts.

**Wear:** Belt clip on back or side; reads as hip-worn field gear on the overworld trainer sprite.

**Reference pose:** Three-quarter front view **facing right** — front panel toward the right edge of the frame, right cheek and belt clip partially visible, as if worn on the trainer's right hip.

## Vibe Cart — Visual Tokens

**Form:** Small rounded-rect cartridge; circular label window in the upper third showing the **Vibemon** (or blank abstract silhouette when unlabeled).

**Palette mapping:**

| Part | Color |
| :--- | :--- |
| Body | **Parchment Cream** |
| Outline | **Tobacco Brown** |
| Accent stripe / notch | **Grape Plum** |
| Contact pins (optional) | **Soft Mustard** |
| Label fill (occupied) | Type color or **Warm Parchment** |

**Icon sizes:** Design for legibility at 16×16 and 32×32 — rect + circle reads at a glance; avoid hemisphere or button-center silhouettes.

## Cart Folio — Visual Tokens

**Form:** Six-slot canvas/leather wallet — olive **Moss Khaki** or **Sage Olive** stitching; cart spines protruding; active slot marked with **Soft Mustard** notch.

**Relationship to Crew:** One occupied cart per **Battle Slot**; folio is diegetic **Crew** storage, not a remote box or PC.

## Capture Flow (Presentation)

1. Trainer presents **Vibe Deck** (already on belt).
2. Insert **Blank Cart** into slot mouth.
3. **Press** — stepped "recording" pulse on reel window; `steps()` timing per `DESIGN.md` §6.
4. Success: cart label populates; cart returns to **Cart Folio**. Failure: cart ejects blank.

**SFX alignment:** soft plastic thunk on insert; warm sine blip on confirm (`DESIGN.md` §7.3).

**Boundary:** **Hatch** / **Generation** is birth from **Provider** signals at a ritual screen — not field **Press** capture. Do not conflate the hatchling silhouette flow with **Blank Cart** capture.

## Concept Art Prompt Anchor

Saved gear prompts live under `vibemon/frontend/asset-prompts/game/` (mirrors `static/game/`). Format and workflow: **`ASSET-PROMPTS.md`**.

Append to gear reference prompts for pipeline consistency:

```text
In a high-quality, illustrative pixel art concept style. Render with thick, distinct dark brown pixelated outlines defining the silhouette. Apply a subtle but continuous coarse watercolor paper canvas texture over the entire image surface. The shading must use a grainy, speckled, wash effect (not flat pixels). The color palette is slightly muted and desaturated. Isolated on a clean, solid white background, presented in a static, detailed sprite pose.
```

**Vibe Deck (closed, facing right) — base prompt:**

```text
A portable clamshell Vibe Deck — a trainer's field device for carrying and recording Vibemon, combining the utility of a Pokédex and an adventure bag in one object. Chunky handheld proportions, slightly wider than tall, designed like a 1970s wood-cabinet transistor radio crossed with an early pocket media player. The clamshell is fully closed, compact and belt-ready. Exterior: warm wood-grain paneling in muted walnut tones (matte, hand-finished, not glossy), face plate in parchment cream, thick tobacco-brown bezels and seams, a small grape-plum accent stripe along the hinge, and a soft mustard selection notch or slider on the side. Front face shows a rounded-rect Vibe Cart slot mouth with a circular label window displaying a tiny abstract creature silhouette (not a specific character), a tiny loop counter / reel window (circular glass), and two minimal soft-glow indicator lamps in sage green and burnt orange — cozy analog UI, not digital. Sturdy brushed pewter belt clip on the back, clearly meant to hang from a trainer's hip on a long walk. Subtle dither on flat surfaces, pixel-rounded corners, one chunky confirm button with tactile pressed depth. No logos, no text, no human hands. Cozy, mid-century, well-worn but cared for — a beloved object carried on an adventure. Three-quarter front view facing right — the front panel and controls turned toward the right side of the frame, right cheek and belt clip partially visible, device oriented as if worn on a trainer's right hip, static hero pose suitable for a style bible reference sheet.
```

(Then append the concept art prompt anchor above.)
