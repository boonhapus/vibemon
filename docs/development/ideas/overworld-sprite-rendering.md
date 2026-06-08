# Overworld Sprite Rendering

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Area** | Assets / Rendering |
| **Related** | [sprite-anatomy-system.md](sprite-anatomy-system.md), [generative-aesthetics-and-showcase.md](generative-aesthetics-and-showcase.md) |

## Summary

Zero-overhead asset delivery: ingest a raw animation strip (manual or AI-generated), sanitize the canvas, slice frames with the Aseprite CLI, and emit engine-ready packed output (`.png` + `.json`) for runtime animation loops.

## Problem

Raw sprite strips from generators often carry compression framing, solid backgrounds, or grid drift. Hand-slicing coordinates for every asset does not scale, and variable aspect sizes cause frame index misalignment at runtime.

## Concept

A linear pipeline: **preprocess** (grid-normalize + background alpha) → **Aseprite batch slice** → **manifest JSON** consumed directly by the frontend engine (Svelte/Pixi/etc.) without manual UV math.

## Design

### Data ingestion & image conditioning

Raw generations or flat sprite strips need sanitization before Aseprite.

**Constraint A: perfect grid output**

The image generator must bind to native grid dimensions. Variable aspect sizes cause frame drift. Standard target layouts are linear horizontal rows:

| Total Width | Total Height | Frame Count | Calculated Cell Matrix |
| :--- | :--- | :--- | :--- |
| 192 px | 32 px | 6 frames | 32 × 32 px per frame |
| 384 px | 64 px | 6 frames | 64 × 64 px per frame |
| 480 px | 80 px | 6 frames | 80 × 80 px per frame |

**Constraint B: background transparency normalization**

A Python preprocess step (Pillow) samples pixel `(0,0)`. If it finds a solid matte (e.g., teal background box), apply global masking to swap the background for clear alpha (RGBA) before Aseprite runs.

### Background execution pipeline

Integrated sequence coordinates file conversion via `--batch` (no Aseprite UI). Outputs upscaled production texture and absolute UV-coordinate manifest.

```python
import subprocess
import os

ASEPRITE_PATH = r"C:\Program Files\Aseprite\Aseprite.exe"

def execute_pipeline(input_strip_path, output_directory, frame_w, frame_h):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    filename = os.path.splitext(os.path.basename(input_strip_path))[0]
    final_sheet = os.path.join(output_directory, f"{filename}_packed.png")
    final_json = os.path.join(output_directory, f"{filename}_map.json")

    cmd = [
        ASEPRITE_PATH,
        "-b",
        input_strip_path,
        "--sheet-width", str(frame_w),
        "--sheet-height", str(frame_h),
        "--split-layers",
        "--sheet-packing",
        "--sheet", final_sheet,
        "--data", final_json,
        "--format", "json-array",
        "--list-tags"
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] Export complete.\nSheet: {final_sheet}\nManifest: {final_json}")
    except subprocess.CalledProcessError as err:
        print(f"[FAILURE] Extraction fault generated within pipeline: {err}")

# execute_pipeline("src/pirate_run.png", "dist/assets/", 80, 80)
```

### Engine manifest layout

Aseprite emits JSON alongside the packed sheet. Runtime loads named frame pointers — no manual slicing.

```json
{
  "frames": [
    {
      "filename": "frame_0.png",
      "frame": { "x": 0, "y": 0, "w": 80, "h": 80 },
      "rotated": false,
      "trimmed": false,
      "sourceSize": { "w": 80, "h": 80 },
      "duration": 100
    },
    {
      "filename": "frame_1.png",
      "frame": { "x": 80, "y": 0, "w": 80, "h": 80 },
      "rotated": false,
      "trimmed": false,
      "sourceSize": { "w": 80, "h": 80 },
      "duration": 100
    }
  ],
  "meta": {
    "app": "http://www.aseprite.org/",
    "version": "1.3",
    "format": "IARRAY"
  }
}
```

## Implementation

Linear operational phases:

1. **Generate/acquire** — output or drop the character animation strip horizontally into an input folder.
2. **Analyze boundaries** — derive cell resolution from total width ÷ frame count.
3. **Preprocess cleansing** — optional background eraser when assets are not on alpha.
4. **Pipeline run** — slice strip into packed sheet + companion `_map.json`.
5. **Render execution** — frontend loads JSON manifest for runtime animation loops.

## Open Questions

- Cross-platform Aseprite path discovery (Windows vs. macOS vs. CI)?
- Upscale step: preprocess before or after Aseprite packing?
- Integration point with existing `materialize_vibemon` / `_sprite_assets` workflow?
