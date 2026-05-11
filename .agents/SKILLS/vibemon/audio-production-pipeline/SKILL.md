---
name: audio-production-pipeline
description: Process, loop-test, and export Vibemon music/audio cues with a repeatable ffmpeg-based pipeline. Use when creating or finalizing battle music, title music, loopable game music, intro+loop pairs, runtime OGG exports, loudness checks, metadata, or when guiding a human through listening approval for generated audio assets.
---

# Audio Production Pipeline

Use this skill to turn generated or composed audio into staged game-ready assets. The bundled CLI lives at `scripts/audio_pipeline.py` and is a standalone `uv` script with inline dependencies.

For new cue workspaces, use a user-provided folder. In Vibemon, prefer `assets/audio/music/<cue>/` for committed production assets or `.generated/audio/<cue>/` for scratch work.

## Core Workflow

1. Identify the cue role: battle music, title/menu music, SFX, or another asset.
2. Use `battle-music` for wild/trainer battle cues and `title-music` for title/menu cues. Reject `sfx` as not implemented instead of reusing music settings blindly.
3. Initialize the cue folder if needed:

```powershell
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py init-cue <cue-dir> --profile <battle-music|title-music>
```

4. Ask the human to generate/select the source audio. Prefer WAV PCM 44.1/48 kHz; FLAC is acceptable; use MP3/M4A only when that is the provider's best export.
5. Stage/process the loop source:

```powershell
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py process <cue-dir> --profile <battle-music|title-music> --source <path-to-source.wav>
```

6. Process cue folders sequentially. Do not run multiple `process` renders in parallel; concurrent ffmpeg `loudnorm` renders have produced invalid full-scale DC WAVs.
7. Choose one of the finalization paths below.
8. Run `verify`, then make the user listen before marking the asset accepted.

## Finalization Paths

Use `stage-loop` for title/menu music or any loop-only cue:

```powershell
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py stage-loop <cue-dir> --profile title-music
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py verify <cue-dir> --profile title-music
```

Use `stage-pair` when the provider generated separate intro and loop files:

```powershell
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py stage-pair <cue-dir> --intro-source <intro.wav> --loop-source <cue-dir>/02-mastered-full.wav
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py verify <cue-dir> --profile battle-music
```

Use `suggest-loop` and `cut` when the provider generated one full cue:

```powershell
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py suggest-loop <cue-dir> --candidates 4
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py cut <cue-dir> --intro-end <seconds> --loop-start <seconds> --loop-end <seconds>
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py verify <cue-dir> --profile battle-music
```

The loop suggester creates disposable files in `_previews/`. Have the user listen to them and choose; never treat suggested loop points as final without human approval.

## Staged Files

The script uses these stage names:

```text
prompt.txt
metadata.md
01-provider-source.<original-ext>
02-mastered-full.wav
03-intro.wav
04-loop.wav
05-intro-runtime.ogg
06-loop-runtime.ogg
_previews/
```

Keep `01-provider-source.*` unchanged as provenance. Battle cues usually produce both `05-intro-runtime.ogg` and `06-loop-runtime.ogg`; title/menu cues are loop-only and normally produce `06-loop-runtime.ogg`.

## Battle-Music Targets

The current battle profile is tuned for Vibemon battle music:

- integrated loudness around `-12 LUFS`, with normal range `-11.5` to `-12.5`
- true peak `<= -1.0 dBTP`
- loop duration warning outside `30-60s`, but long loops can be accepted if intentional
- LRA warning outside the rough `2-5` target, but listening takes priority
- OGG runtime export with a small gain pad to prevent compressed true-peak overshoot

Warnings are not automatic failures. True peak above `-1.0 dBTP`, missing files, unreadable files, or failed media commands are failures.

## Title-Music Targets

The title profile is tuned to sit far below battle intensity:

- integrated loudness around `-22 LUFS`, with normal range `-23.5` to `-20.5`
- true peak `<= -3.0 dBTP`
- loop duration warning outside `45-180s`
- loop-only export; do not require an intro stage
- preserve calm title/menu mood even if measurements are technically acceptable

Warnings are not automatic failures. True peak above `-3.0 dBTP`, missing files, unreadable files, or failed media commands are failures.

## Human Approval Gate

Do not mark an audio asset accepted until the user confirms:

- battle intro plays once and hands off cleanly to the loop, when the cue has an intro
- loop repeats several times without an audible break
- track fits the cue role and intensity hierarchy
- headphones/laptop/phone checks are acceptable when relevant

Record acceptance in `metadata.md`. Keep metadata concise: provider/source, date, prompt, attribution/license note, processing, loop notes, measurements, acceptance notes.

## Provider Provenance

Record how the provider source was made. Common paths:

- Text-only generation from `prompt.txt`.
- Uploaded-reference remix, where the human uploaded reference music and remixed it against a shortened brand prompt.
- Manual/composed source.

For uploaded-reference remix, ask whether the uploaded reference is owned, licensed, public-domain, or otherwise cleared for this use. If not confirmed, mark the output as prototype/internal and do not call it production-safe. The pipeline can still process and test the asset, but the metadata must not hide the source chain.

In `metadata.md`, keep the note short:

```text
Provider/source: Suno remix from uploaded reference audio; source staged as `01-provider-source.wav`
Attribution/license note: Reference-audio rights: <confirmed/unknown>; provider plan/rights: <note>
```

## Prompt Guidance

For wild battle music, `init-cue --profile battle-music` writes a fast wild-encounter prompt template. If the user reports slow or relaxed outputs, strengthen the prompt around perceived tempo, no half-time feel, busy drums/bass/hook, short phrases, and a rapid encounter-alarm mood.

For title/menu music, `init-cue --profile title-music` writes a calmer loop prompt. Keep it lower intensity than all battle music: warm analog library/psych texture, clear early hook, 60-120 second loop body, no fadeout, no heroic fanfare, no battle urgency.

Do not upload unlicensed reference audio to providers for production assets. When a user has already used uploaded references, preserve that provenance and separate audio quality acceptance from legal/rights acceptance.

## Maintenance

After editing the bundled script, run:

```powershell
uv run --with ruff ruff check .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py
uv run .agents/skills/vibemon/audio-production-pipeline/scripts/audio_pipeline.py --help
```

After editing skill metadata, validate:

```powershell
uv run C:\Users\boonhapus\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents/skills/vibemon/audio-production-pipeline
```
