# Vibemon Audio Production Plan

Date captured: 2026-05-09

This document records the plan for turning the existing `.ideas` music references into a production-ready Vibemon soundtrack direction, with special focus on creating or finalizing a version of `gen1-battle_vs_wild_pokemon.mp3` that matches `.ideas/DESIGN.md` and remains consistent with the other MP3s in `.ideas`.

## Goal

Create a production asset that can be locked and used as the canonical wild battle theme for Vibemon.

The goal is not to keep regenerating the track until it is "interesting." The goal is to choose or generate a suitable composition once, then make it fit the project through a repeatable audio treatment and export process.

## Existing Context

Relevant files:

| File | Role |
| --- | --- |
| `.ideas/DESIGN.md` | Visual and audio style source of truth |
| `.ideas/gen1-battle_vs_wild_pokemon.mp3` | Current wild battle reference/source |
| `.ideas/gen1-battle_vs_trainer.mp3` | Higher-intensity battle reference |
| `.ideas/gen1-battle_vs_gym_leader.mp3` | Boss-like battle reference |
| `.ideas/gen1-last_battle_vs_rival.mp3` | Most dramatic battle reference |
| `.ideas/gen1-title_screen.mp3` | Calm title/menu reference |

The existing MP3s are all stereo, 44.1 kHz files. They are consistent at the container level, but not at the loudness level.

Measured with `ffmpeg loudnorm`:

| File | Duration | Bitrate | Integrated Loudness | True Peak | LRA |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gen1-battle_vs_gym_leader.mp3` | 120.03s | 175 kbps | -10.50 LUFS | -0.22 dBTP | 4.80 |
| `gen1-battle_vs_trainer.mp3` | 196.78s | 157 kbps | -10.96 LUFS | -0.45 dBTP | 2.10 |
| `gen1-battle_vs_wild_pokemon.mp3` | 90.38s | 139 kbps | -11.86 LUFS | -0.84 dBTP | 2.90 |
| `gen1-last_battle_vs_rival.mp3` | 150.10s | 130 kbps | -12.82 LUFS | -1.31 dBTP | 1.60 |
| `gen1-title_screen.mp3` | 113.08s | 197 kbps | -21.89 LUFS | -6.29 dBTP | 1.00 |

Interpretation:

- The battle tracks currently cluster around roughly `-10.5` to `-12.8 LUFS`.
- The title screen is much quieter and should be treated as a different category, not forced to battle loudness.
- If the existing battle refs remain the sound family, the wild battle should target about `-12 LUFS`, not the more conservative web-background target of `-16 LUFS`.

## Design Audio Target

From `.ideas/DESIGN.md`, the soundtrack should avoid clean modern handheld/chiptune polish and instead sound like:

- 1970s wooden-cabinet television audio
- Portable transistor radio playback
- Magnetic tape or analog synth source material
- Slight distortion, warmth, and pitch instability
- Saturday-morning TV rather than modern orchestral game scoring

Required audio traits:

- Tape saturation
- Subtle wow and flutter, around `0.1%` to `0.3%`
- High-cut around `12 kHz`
- Low-cut around `100 Hz`
- Mid-forward, warm, slightly tinny playback
- Optional `12-bit` texture; use `8-bit` only if the result is still too clean
- Physical loop-point imperfection, such as a tiny crackle or pop

Musical direction:

- Library music
- Psych-rock
- Fast bossa nova
- Jazz-funk
- Hammond B3 organ with Leslie speaker
- Fuzzy distorted bass guitar
- Dry, damped 1970s drums
- Mellotron string stabs
- Muted wah-wah guitar
- Warm analog synth blips

## Soundtrack Hierarchy

The wild battle theme should fit into the full set, not replace the role of the more intense cues.

Recommended intensity ladder:

| Track | Role | Relative Intensity |
| --- | --- | --- |
| `gen1-title_screen.mp3` | Title/menu | Calm, much quieter, atmospheric |
| `gen1-battle_vs_wild_pokemon.mp3` | Wild battle | Immediate, simple, tense, playful |
| `gen1-battle_vs_trainer.mp3` | Trainer battle | More developed, more assertive |
| `gen1-battle_vs_gym_leader.mp3` | Gym leader battle | Boss-like, denser, more urgent |
| `gen1-last_battle_vs_rival.mp3` | Rival finale | Most dramatic and climactic |

The wild battle cue should not become the most harmonically dense, dramatic, or polished cue. It should feel like the first battle layer in the world: fast, compact, memorable, but lower-stakes than trainer/gym/rival.

## Rights And Source Safety

If any `.ideas/gen1-*.mp3` file is the actual Pokemon music, a cover, or a close derivative, do not upload it to a provider or ship it unless the project has rights to it.

For production-safe AI prompting:

- Do not mention Pokemon, Nintendo, Game Boy, specific song titles, named artists, named composers, or exact source cues.
- Do not ask the model to preserve or recreate the melody from an existing commercial track.
- Use the existing files internally as taste and structure references only.
- Use descriptive language: "retro monster-battle game," "early handheld RPG energy," "1960s-70s library music," "psych-rock jazz-funk battle loop."

If the current MP3 is only a temporary reference, the production asset should be an original composition generated or composed from the written brief, then processed to match the audio family.

## Provider Recommendation

The user is okay with using a provider's web interface. Since the goal is to lock a production asset, the provider should be chosen for exportability, commercial usability, and repeatability, not just novelty.

### Recommended For New Original Music: Eleven Music

Use Eleven Music through the ElevenLabs web interface if a new original composition is needed.

Reasons:

- Eleven Music is positioned around commercially usable generated music.
- It is available in the web UI.
- Its terms are more production-oriented than typical consumer music generators.
- It supports explicit structure, mood, genre, instrumentation, and instrumental/vocal direction in natural-language prompts.

Important caveats as of 2026-05-09:

- Re-check the current Music Terms before locking the asset.
- ElevenLabs Music Terms prohibit certain prompt inputs, including artist names, song titles, album titles, labels, publishers, and attempts to mimic identifiable artists.
- Self-serve media rights allow broad commercial use but may exclude film, TV, radio, and large studio games depending on plan. For an indie game, confirm the current plan tier is sufficient.
- Free-plan output should not be treated as a commercial production asset.

Useful official pages to re-check:

- https://elevenlabs.io/music-terms
- https://elevenlabs.io/eleven-music-v1-terms
- https://help.elevenlabs.io/hc/en-us/articles/37780368848785-What-is-Eleven-Music

### Good For Exploration Only: Suno

Suno can be useful for quick ideation and prompt exploration, especially because its web UI supports audio uploads and paid plans support WAV download.

Use it only if:

- The account is Pro or Premier before generation.
- The generated track is not based on unlicensed uploaded music.
- The result will still be processed/mastered through the shared Vibemon chain.

Caveats:

- Free-plan output is not appropriate for commercial production use.
- Paid-plan commercial rights do not make output automatically copyright-protectable.
- It is more stochastic and less ideal as the final "locked" production step.

Useful official pages to re-check:

- https://help.suno.com/en/articles/9601665
- https://help.suno.com/en/articles/2409921
- https://help.suno.com/en/articles/6141569

### Not Recommended Right Now: Udio

Udio has strong style/remix tools, but it is not recommended for this production-lock workflow right now.

Reason as of 2026-05-09:

- Udio's official UMG transition page says downloading audio, video, and stems has been disabled.

Useful official pages to re-check:

- https://help.udio.com/en/articles/12683565-changes-associated-with-the-universal-music-group-umg-partnership
- https://help.udio.com/en/articles/10754328-create-or-remix-music-with-your-own-audio

### Final Mastering/Consistency Tool

Do not rely on repeated AI regeneration to make the final track consistent. Use a deterministic mastering chain.

Options:

- DAW with saved effects preset, preferred if available
- LANDR or another web mastering tool, if the workflow must stay web-based
- Local `ffmpeg` only for measurement, filtering, normalization, and export checks; it is not a complete musical mastering environment by itself

## Recommended Workflow

### Phase 1: Decide Whether The Existing Wild Battle Composition Is Usable

Decision:

- If the existing `gen1-battle_vs_wild_pokemon.mp3` is legally usable and musically close enough, do not regenerate the composition. Process/master it into the final Vibemon sound.
- If it is not legally usable or is too close to protected source material, generate a new original wild battle cue from text only.

Lock criteria for the composition:

- It loops or can be edited into a loop without obvious musical discontinuity.
- It is less intense than trainer/gym/rival.
- It has a short, memorable hook without quoting protected melodies.
- It supports repeated battle playback without becoming tiring.
- It can survive the lo-fi treatment without turning muddy.

### Phase 2: Generate Candidate Only If Needed

If using Eleven Music:

1. Open ElevenLabs web UI.
2. Use Eleven Music.
3. Choose instrumental-only generation.
4. Target length around `90s`.
5. Generate multiple candidates from the same prompt.
6. Pick one candidate based on composition, not mix quality.
7. Download the highest-quality available file allowed by the plan.
8. Do not keep regenerating after choosing a winner.

Preferred generation prompt:

```text
Create an original instrumental wild battle theme for a retro monster-battle game soundtrack.

This track must sit alongside a family of Gen-1-inspired battle cues: title screen is calm and much quieter, wild battle is the simplest and most immediate battle cue, trainer battle is more developed, gym leader is more intense, and rival battle is the most dramatic.

Style: 1960s-70s library music, fast jazz-funk, psych-rock, and bossa nova. Energetic, tense, playful, compact, loopable. Do not make it cinematic or orchestral.

Instrumentation: Hammond B3 organ with Leslie speaker, fuzzy bass guitar, dry damped 1970s drums, muted wah-wah rhythm guitar, Mellotron string stabs, warm analog synth blips.

Production feel: wooden-cabinet television, portable transistor radio, tape saturation, subtle wow/flutter, warm midrange, high-cut near 12 kHz, low-cut near 100 Hz, light crackle, mono-compatible stereo.

Keep it less intense than trainer, gym leader, or rival battle music. No vocals. No direct quotation of existing game melodies. No clean chiptune lead. No modern EDM polish.
```

If the tool supports negative prompting, use:

```text
No vocals, no lyrics, no orchestral trailer music, no EDM drop, no modern hyper-clean mastering, no clean square-wave chiptune lead, no direct quotation of existing video game melodies, no named artist imitation, no song-title references.
```

If the tool supports structure instructions, add:

```text
Structure: 4-bar intro, 16-bar A section, 16-bar B section, return to A, short loopable ending. Keep the loop compact and suitable for repeated gameplay.
```

### Phase 3: Build The Shared Vibemon Music Chain

Apply a shared chain to the selected wild battle track and, eventually, to every final music asset.

Baseline chain:

1. High-pass filter around `100 Hz`
2. Low-pass filter around `12 kHz`
3. Gentle tape saturation
4. Subtle wow/flutter, around `0.1%` to `0.3%`
5. Mild compression, 1970s-style glue, not modern loudness maximization
6. Slight stereo narrowing or mono-compatibility check
7. Optional bit-depth texture:
   - Start with `12-bit`
   - Use `8-bit` only if the result still feels too clean
8. Low-level tape/vinyl crackle
9. Tiny crackle/pop at the loop point only if it reads as intentional and not like an export glitch

Do not overdo the lo-fi layer. The goal is a 1970s TV/radio illusion, not damaged audio.

### Phase 4: Loudness Targets

Use different targets by category.

Battle BGM target:

- Integrated loudness: about `-12 LUFS`
- Acceptable range: roughly `-11.5` to `-12.5 LUFS`
- True peak: `<= -1.0 dBTP`
- Loudness range: around `2` to `5 LRA`

Title/menu target:

- Keep significantly quieter than battle.
- Current title reference is about `-21.89 LUFS`.
- Do not normalize title screen to battle loudness unless the whole game audio-mix plan changes.

If the game later adopts a global BGM target such as `-16 LUFS`, then re-master the whole music set together. Do not normalize only the wild battle in isolation.

### Phase 5: Loop Editing

For the locked production version:

- Create a clean loop region.
- Prefer a musically complete loop over simply looping the full generated file.
- If possible, render a short intro plus a loop segment separately:
  - `wild_battle_intro`
  - `wild_battle_loop`
- If the engine only supports one looping file, make the full file loop acceptably.
- Test the loop in the game or a looping audio player for at least 5 consecutive repeats.
- Confirm that the deliberate crackle/pop at the loop point feels like a tape artifact, not an accidental click.

### Phase 6: Export Format

Keep masters separate from runtime exports.

Recommended source/master format:

- WAV
- 44.1 kHz
- 24-bit or 16-bit PCM
- Stereo, mono-compatible

Recommended runtime format:

- OGG Vorbis for game/web runtime if supported
- MP3 only if that is what the current asset pipeline expects
- Keep sample rate at 44.1 kHz for consistency with existing references

Suggested naming:

```text
assets/audio/music/wild_battle_master.wav
assets/audio/music/wild_battle_loop.ogg
assets/audio/music/wild_battle_intro.ogg
```

If staying within `.ideas` until final integration:

```text
.ideas/vibemon-wild-battle-production-candidate.wav
.ideas/vibemon-wild-battle-production-loop.ogg
```

## Quality Checklist

Before locking the asset:

- The cue is original or legally usable.
- The provider plan/license permits this project use.
- The file has been exported/downloaded and archived locally.
- The composition is no longer being regenerated.
- The track is less intense than trainer/gym/rival.
- The track matches `.ideas/DESIGN.md`: 1970s, analog, TV/radio, tape, jazz-funk/psych/library feel.
- The battle version lands around `-12 LUFS`, or the whole battle set has been re-mastered to a new shared target.
- True peak is below `-1 dBTP`.
- Loop point has been tested repeatedly.
- The asset sounds acceptable on laptop speakers, headphones, and small phone speakers.
- The track does not contain obvious modern EDM, orchestral trailer, pristine chiptune, or copyrighted melody quotation.
- Final source and runtime exports are both preserved.

## Measurement Commands

Inspect format:

```powershell
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,channels,sample_rate -of default=noprint_wrappers=1 .ideas/gen1-battle_vs_wild_pokemon.mp3
```

Measure loudness:

```powershell
ffmpeg -hide_banner -nostats -i .ideas/gen1-battle_vs_wild_pokemon.mp3 -af loudnorm=I=-12:LRA=11:TP=-1:print_format=json -f null NUL
```

Measure all `.ideas` MP3s:

```powershell
Get-ChildItem .ideas -Filter *.mp3 | Sort-Object Name | ForEach-Object {
  $name=$_.Name
  $out = ffmpeg -hide_banner -nostats -i $_.FullName -af loudnorm=I=-16:LRA=11:TP=-1:print_format=json -f null NUL 2>&1 | Out-String
  $inputI = [regex]::Match($out, '"input_i"\s*:\s*"([^"]+)"').Groups[1].Value
  $inputTP = [regex]::Match($out, '"input_tp"\s*:\s*"([^"]+)"').Groups[1].Value
  $inputLRA = [regex]::Match($out, '"input_lra"\s*:\s*"([^"]+)"').Groups[1].Value
  [pscustomobject]@{Name=$name; LUFS=$inputI; TruePeak=$inputTP; LRA=$inputLRA}
} | Format-Table -AutoSize
```

## Final Recommendation

For this specific task:

1. Use the existing `.ideas` MP3 set to define the soundtrack family.
2. Treat the title screen as intentionally quieter than battle music.
3. Treat the battle tracks as a roughly `-12 LUFS` family.
4. If a new original wild battle composition is required, use Eleven Music web UI with the prompt above.
5. Do not use Udio for the locked asset unless downloads are restored and terms are re-checked.
6. Use Suno only for exploration unless the account and generated asset clearly meet production-use requirements.
7. Lock the composition first, then apply one saved Vibemon mastering chain.
8. Export and archive a WAV master plus runtime OGG/MP3.
9. Loop-test before integrating.

The key principle: consistency should come from one shared production/mastering chain across the soundtrack, not from repeatedly asking a music model to "sound more consistent."
