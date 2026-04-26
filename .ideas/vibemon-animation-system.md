# Ideas

## Period: Vibemon Animation System

### Idea: AI-Generated Sprite Animations via Seedance

**Problem Statement**
We want to animate Vibemon sprites using AI video generation, starting with idle animations and expanding to battle states.

---

## Research Findings

### Seedance 2.0 (ByteDance)

**Key Capabilities:**
- **Image-to-Video**: Upload up to **9 images** per generation
- **Multi-image control**: Use `@` syntax to assign roles (front view, back view, etc.)
- **Duration**: 4-15 seconds per output
- **Audio**: Built-in stereo audio generation
- **Consistency**: One-take continuity across frames
- **Camera control**: Specify pan, zoom, rotation in prompts
- **Commercial rights**: Generated content is yours to use

**Input Formats Supported:**
- Images (up to 9): Perfect for sprite sheets or multi-angle views
- Videos (up to 3): For motion reference
- Audio (up to 3): For lip-sync or sound-linked animations
- Text prompts: For motion description

### Alternative: Gif-PT

**Specialized for sprite sheets:**
- Generates sprite sheet animations from descriptions
- Can slice existing sprite sheets into frames
- Direct game engine export

---

## Proposed Implementation

### Animation States Required

| State | Description | Seedance Input | Duration |
|-------|-------------|---------------|----------|
| `idle` | Gentle breathing/hovering | 1 sprite | 2-4 sec loop |
| `idle_happy` | Excited idle (after win) | 1 sprite | 2-3 sec |
| `attack` | Attack pose/charge | 1-2 sprites | 1 sec |
| `damage` | Hit reaction | 2 sprites | 0.5 sec |
| `faint` | Defeat animation | 3-4 sprites | 2 sec |
| `victory` | Celebration pose | 1 sprite | 3 sec loop |
| `catch_attempt` | Ball throw reaction | 3-4 sprites | 2 sec |

### Workflow

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Static Sprite  │────▶│  Seedance    │────▶│  Video Output    │
│  (front view)   │     │  Image-to-Vid│     │  (4-15 sec)      │
└─────────────────┘     └──────────────┘     └──────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Sprite Sheet   │◀────│  Extract    │◀────│  Frame Split    │
│  (.png)        │     │  Frames     │     │  (30fps)       │
└─────────────────┘     └──────────────┘     └──────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Animation JSON │◀────│  Map to    │◀────│  Frame Count    │
│  (Define states)│     │  States    │     │  & Timing       │
└─────────────────┘     └──────────────┘     └──────────────────┘
```

### Seedance Prompt Templates

**Idle Animation:**
```
Prompt: "Character gently hovering, subtle breathing motion, 
         slight up-down float, soft lighting, clean background"
@1: [sprite] role=subject
Duration: 4 seconds
Camera: static, slight zoom in
```

**Attack Animation:**
```
Prompt: "Character lunging forward with energy charge, 
         arms extended, motion blur, dynamic pose"
@1: [sprite] role=subject
Duration: 2 seconds
Camera: push forward
```

### Output Pipeline

1. **Generate** → Seedance creates video
2. **Download** → Store in asset cache
3. **Extract** → Split video to frames (ffmpeg or similar)
4. **Optimize** → Crop to sprite bounds, optimize palette
5. **Export** → Generate sprite sheet PNG + JSON metadata
6. **Integrate** → Add to Vibemon animation library

### Data Model Extension

```python
@dataclass
class VibemonAnimation:
    vibemon_id: str
    state: AnimationState
    sprite_sheet_path: str
    frame_count: int
    fps: int
    frame_dimensions: tuple[int, int]
    loop: bool
    duration_ms: int
    seedance_job_id: str
    generated_at: datetime
    source_sprite_hash: str  # For cache invalidation
```

### Animation Config JSON

```json
{
  "vibemon_id": "vulpix_001",
  "animations": {
    "idle": {
      "sprite_sheet": "vulpix_idle.png",
      "frames": {"cols": 4, "rows": 1},
      "fps": 8,
      "loop": true,
      "animation": {"start": 0, "end": 3}
    },
    "attack": {
      "sprite_sheet": "vulpix_attack.png",
      "frames": {"cols": 4, "rows": 1},
      "fps": 12,
      "loop": false,
      "animation": {"start": 0, "end": 3}
    }
  }
}
```

### Integration Points

- **Showcase Mode**: Play idle animation on hover
- **Battle System**: Trigger state-based animations
- **Sound System**: Sync audio cues with animation frames
- **Asset Pipeline**: Automated regeneration if sprite updates

---

## Action Items

- [ ] Sign up for Seedance 2.0 and test free tier
- [ ] Upload one static sprite, generate idle animation
- [ ] Evaluate output quality (smoothness, file size)
- [ ] Test multi-image input (front + side for depth)
- [ ] Implement frame extraction pipeline
- [ ] Prototype idle animation for one Vibemon
- [ ] Benchmark: cost per animation, generation time
- [ ] Evaluate Gif-PT as alternative/supplement

---

**Priority**: Medium
**Complexity**: High
**Tech**: Seedance 2.0, ffmpeg (frame extraction), Piskel/TexturePacker (sprite sheets)
**Estimated Cost**: ~$0.05-0.10 per animation (Seedance credits)
**Related Ideas**: vibemon-sound-generation.md, vibemon-showcase-mode.md