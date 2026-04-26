# Ideas

## Period: Vibemon Sound Generation

### Idea: AI-Generated Audio for Vibemon Cries & Sound Effects

**Problem Statement**
Generate unique sounds (cries, attack noises, victory calls) for each Vibemon using AI. Need cost-effective solution as ElevenLabs is expensive per-unit.

---

## Research Findings (2026)

### Best AI SFX Generators

| Service | Best For | Cost | Quality | License |
|---------|----------|------|---------|---------|
| **Noiz AI** | Foley, impacts, creature sounds | $$ | ★★★★★ | Commercial |
| **GenSFX** | Free SFX, quick prototyping | Free | ★★★ | Free commercial |
| **Adobe Firefly SFX** | Integrated with creative suite | $$ | ★★★★ | Commercial |
| **Kling SFX** | Video + audio workflow | $$ | ★★★★ | Commercial |
| **ElevenLabs SFX** | AI-native sound effects | $$$ | ★★★★ | Commercial |

### Best TTS/Voice Services (for battle cries that sound vocal)

| Service | Best For | Cost | Quality | License |
|---------|----------|------|---------|---------|
| **Inworld AI** | Real-time, #1 TTS quality | $$ | ★★★★★ | Commercial |
| **Cartesia** | Ultra-low latency | $$ | ★★★★ | Commercial |
| **ElevenLabs** | Emotion control, 70+ languages | $$$ | ★★★★★ | Commercial |
| **Kokoro** | Self-hostable, Apache 2.0 | Free | ★★★★ | Open (Apache 2.0) |
| **Fish Audio** | Open source, cheap | $ | ★★★ | Varies | Open |
| **Bark** | Free, music/SFX too | Free | ★★★ | Non-commercial | Open |
| **OpenAI TTS** | Simple integration | $$ | ★★★★★ | Commercial |

### Sound Effect Types Needed

| Category | Examples | Length | Style |
|----------|----------|--------|-------|
| **Battle Cries** | "Vulpix cry", "Growl" | 0.5-2s | Vocal/monster-like |
| **Attack Sounds** | "Fire blast", "Thunder hit" | 1-3s | Impact/elemental |
| **Catch Attempts** | "Ball shake", "Click" | 1-4s | Mechanical/UI |
| **Victory Fanfare** | "Catch success", "Level up" | 2-5s | Celebratory |
| **Ambient** | "Type ambience", "Area theme" | 5-30s | Atmospheric |

---

## Proposed Implementation

### Two-Tier Audio Strategy

**Tier 1: Base Cries (High Volume)**
Use free/cheap services for unique per-Vibemon cries:

```
Service: Kokoro (self-hosted) or Fish Audio
Cost: ~$0 (self-hosted) or ~$0.001/character
Quality: Good enough for 100+ Vibemon
Generation: Text prompt → "Cute fox creature cry, high pitch"
```

**Tier 2: Signature Sounds (Low Volume)**
Use premium services for key moments:

```
Services: ElevenLabs SFX or Noiz AI
Cost: ~$0.05-0.20/sound
Quality: Production-ready
Sounds: Catch success, level up, evolution, victory
```

### Sound Prompt Templates

**Vibemon Cry:**
```
Prompt: "A small fire fox creature letting out a high-pitched, 
         playful cry. Cute but fierce. Short burst, 1 second."
Style: Creature vocal, nature sound
```

**Attack Sound:**
```
Prompt: "Fire whoosh expanding outward, magical impact with 
         sparks. Sharp attack sound, 1.5 seconds."
Style: Magical fire, impact
```

**Catch Success:**
```
Prompt: "Mechanical click, ball wobbles three times with 
         increasing intensity, then final satisfying lock."
Style: Mechanical, game UI
```

### Sound Bank Structure

```
/audio/
  /cries/
    vulpix_cry.mp3      # Per Vibemon unique cry
    vulpix_cry_happy.mp3 # Variant (post-win)
  /attacks/
    fire_blast.mp3      # Shared elemental
    thunder_hit.mp3
  /ui/
    catch_success.mp3   # Shared UI sounds
    level_up.mp3
    victory_fanfare.mp3
  /ambient/
    fire_type_theme.mp3  # Per type
```

### Data Model

```python
@dataclass
class VibemonAudio:
    vibemon_id: str
    cry: AudioAsset
    cry_happy: Optional[AudioAsset]  # Post-victory variant
    attack_sounds: list[AudioAsset]
    victory_call: Optional[AudioAsset]
    generated_with: str  # Service used
    generated_at: datetime
    cost_per_unit: float
```

### Generation Pipeline

1. **Batch Generate** cries for all Vibemon (using Kokoro/Fish Audio)
2. **Manual Polish** key sounds with ElevenLabs/Noiz (catch, level-up)
3. **Quality Check** batch automatically, flag outliers
4. **Normalize** audio levels across all files
5. **Cache** generated files, store metadata in DB
6. **Fallback** to procedural audio if AI unavailable

### Batch Cost Estimate

| Approach | 100 Vibemon | 500 Vibemon |
|----------|------------|------------|
| **All ElevenLabs** | ~$500-1000 | ~$2500-5000 |
| **Hybrid (free cries + premium FX)** | ~$50-100 | ~$250-500 |
| **Self-hosted Kokoro** | ~$0 + infra | ~$0 + infra |

---

## Action Items

- [ ] Test GenSFX (free tier) for quick prototyping
- [ ] Deploy Kokoro locally, test voice quality
- [ ] Generate 5 sample cries, evaluate quality
- [ ] Test Noiz AI for attack sound effects
- [ ] Set up audio normalization pipeline
- [ ] Benchmark: quality vs cost per service
- [ ] Negotiate ElevenLabs volume pricing (if proceeding)

---

**Priority**: Low
**Complexity**: Medium
**Estimated Costs**:
- Free tier (GenSFX): $0
- Kokoro self-hosted: ~$20/month (GPU)
- Hybrid approach: $50-100 one-time
- Full ElevenLabs: $500+ (not recommended)
**Related Ideas**: vibemon-animation-system.md, vibemon-showcase-mode.md