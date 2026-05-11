# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "cyclopts>=4.11.0",
#   "numpy>=2.0.0",
#   "structlog>=25.5.0",
# ]
# ///
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import cyclopts
import numpy as np
import structlog

_LOGGER = structlog.get_logger(__name__)

app = cyclopts.App(help="Vibemon staged audio production helper.")

BATTLE_PROFILE = "battle-music"
TITLE_PROFILE = "title-music"
RESERVED_PROFILES = frozenset({"sfx"})
SUPPORTED_PROFILES = (BATTLE_PROFILE, TITLE_PROFILE)

SOURCE_STAGE_STEM = "01-provider-source"
SOURCE_EXTENSIONS = (".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg")
MASTER_STAGE = "02-mastered-full.wav"
INTRO_STAGE = "03-intro.wav"
LOOP_STAGE = "04-loop.wav"
INTRO_RUNTIME_STAGE = "05-intro-runtime.ogg"
LOOP_RUNTIME_STAGE = "06-loop-runtime.ogg"
PROMPT_FILE = "prompt.txt"
METADATA_FILE = "metadata.md"
PREVIEW_DIR = "_previews"

SAMPLE_RATE = 44_100
RUNTIME_OGG_QUALITY = "5"

BATTLE_TARGET_I = -12.0
BATTLE_TARGET_LRA = 5.0
BATTLE_TARGET_TP = -1.0
BATTLE_LUFS_MIN = -12.5
BATTLE_LUFS_MAX = -11.5
BATTLE_LOOP_MIN_SECONDS = 30.0
BATTLE_LOOP_MAX_SECONDS = 60.0
BATTLE_INTRO_MIN_SECONDS = 1.0
BATTLE_INTRO_MAX_SECONDS = 4.0

TITLE_TARGET_I = -22.0
TITLE_TARGET_LRA = 4.0
TITLE_TARGET_TP = -3.0
TITLE_LUFS_MIN = -23.5
TITLE_LUFS_MAX = -20.5
TITLE_LOOP_MIN_SECONDS = 45.0
TITLE_LOOP_MAX_SECONDS = 180.0

BATTLE_PROMPT_TEMPLATE = """Original instrumental wild encounter battle theme for a retro monster-battle game.

Target a classic fast wild-battle cue: sudden alarm, rising panic intro, frantic double-time motion, short looping motifs, no empty space. Do not copy existing melody, bassline, harmony, or arrangement.

Style: 1960s-70s analog TV action, garage psych-rock, spy-library chase, vintage organ battle music. Frantic, nervous, scrappy, loopable. Lean forward.

4/4. Pulse 92-96 BPM with 184-192 BPM double-time energy. Straight 16ths, constant 8th-note drive, pickups into downbeats. No swing, shuffle, halftime.

Structure: 2-bar rising intro, then 64-bar loop: A hook, A variation, B contrast, return to A, repeat/intensify. Hook in first 4 bars. Tight 1-bar turnaround, no fadeout.

Hammond B3, fuzzy bass ostinato, dry 70s drums with busy hats, clipped wah guitar, Mellotron stabs, analog synth blips.

Instrumental only. No vocals, EDM, orchestral, chiptune, lounge, smooth funk, trailer percussion.
"""

TITLE_PROMPT_TEMPLATE = """Original instrumental title/menu theme for a retro monster-battle game.

Target a calm, inviting, slightly mysterious first-screen cue. It should establish Vibemon's analog monster-world mood, not battle urgency.

Style: 1960s-70s library music, warm psych-rock, gentle jazz-funk, mellow garage organ, soft analog synth, and wooden-cabinet television playback. Vibey, handmade, curious, and quietly magical.

70-95 BPM or a relaxed moderate pulse. Keep motion steady enough for a menu loop, but avoid fast battle energy, heroic fanfare, cinematic drama, EDM polish, or clean chiptune leads.

Structure: loopable 60-120 second body with a clear 4-8 bar hook early, small variations, and a clean return to the start. No fadeout, no long tail, no large one-time climax.

Instrumentation: Hammond or mellow combo organ, warm electric bass, dry brushed or damped drum kit, light wah or tremolo guitar, Mellotron/analog string pads, sparse analog synth blips.

Production feel: warm midrange, tape softness, subtle pitch instability, mono-compatible stereo, dry and intimate rather than huge.

Instrumental only. No vocals, lyrics, chanting, scat singing, vocal chops, orchestral scoring, trailer percussion, EDM drops, or modern hyper-polished mastering.
"""

BATTLE_METADATA_TEMPLATE = """# Wild Battle

Provider/source:
Date:
Prompt: prompt.txt
Attribution/license note:
Processing:
Loop notes:
Measurements:
Acceptance notes:
"""

TITLE_METADATA_TEMPLATE = """# Title Music

Provider/source:
Date:
Prompt: prompt.txt
Attribution/license note:
Processing:
Loop notes:
Measurements:
Acceptance notes:
"""


@dataclass(frozen=True)
class ProfileSettings:
    prompt_template: str
    metadata_template: str
    filter_chain: str
    target_i: float
    target_lra: float
    target_tp: float
    lufs_min: float
    lufs_max: float
    loop_min_seconds: float
    loop_max_seconds: float
    lra_warning_min: float
    lra_warning_max: float
    requires_intro: bool
    intro_min_seconds: float | None = None
    intro_max_seconds: float | None = None


BATTLE_FILTER_CHAIN = ",".join(
    [
        "highpass=f=100",
        "lowpass=f=12000",
        "acompressor=threshold=0.125:ratio=1.6:attack=20:release=250:knee=3:mix=0.85",
        "vibrato=f=0.35:d=0.003",
        "acrusher=bits=12:mix=0.10:samples=1:aa=0.65",
    ]
)
TITLE_FILTER_CHAIN = ",".join(
    [
        "highpass=f=80",
        "lowpass=f=12000",
        "acompressor=threshold=0.18:ratio=1.3:attack=35:release=350:knee=4:mix=0.65",
        "vibrato=f=0.25:d=0.002",
        "acrusher=bits=12:mix=0.06:samples=1:aa=0.65",
    ]
)
PROFILE_SETTINGS = {
    BATTLE_PROFILE: ProfileSettings(
        prompt_template=BATTLE_PROMPT_TEMPLATE,
        metadata_template=BATTLE_METADATA_TEMPLATE,
        filter_chain=BATTLE_FILTER_CHAIN,
        target_i=BATTLE_TARGET_I,
        target_lra=BATTLE_TARGET_LRA,
        target_tp=BATTLE_TARGET_TP,
        lufs_min=BATTLE_LUFS_MIN,
        lufs_max=BATTLE_LUFS_MAX,
        loop_min_seconds=BATTLE_LOOP_MIN_SECONDS,
        loop_max_seconds=BATTLE_LOOP_MAX_SECONDS,
        lra_warning_min=1.5,
        lra_warning_max=6.5,
        requires_intro=True,
        intro_min_seconds=BATTLE_INTRO_MIN_SECONDS,
        intro_max_seconds=BATTLE_INTRO_MAX_SECONDS,
    ),
    TITLE_PROFILE: ProfileSettings(
        prompt_template=TITLE_PROMPT_TEMPLATE,
        metadata_template=TITLE_METADATA_TEMPLATE,
        filter_chain=TITLE_FILTER_CHAIN,
        target_i=TITLE_TARGET_I,
        target_lra=TITLE_TARGET_LRA,
        target_tp=TITLE_TARGET_TP,
        lufs_min=TITLE_LUFS_MIN,
        lufs_max=TITLE_LUFS_MAX,
        loop_min_seconds=TITLE_LOOP_MIN_SECONDS,
        loop_max_seconds=TITLE_LOOP_MAX_SECONDS,
        lra_warning_min=0.5,
        lra_warning_max=8.0,
        requires_intro=False,
    ),
}


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


def fail(message: str) -> None:
    raise SystemExit(message)


def require_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        fail(f"Missing required audio tool(s): {', '.join(missing)}")


def require_profile(profile: str) -> None:
    if profile in PROFILE_SETTINGS:
        return
    if profile in RESERVED_PROFILES:
        fail(f"Profile '{profile}' is reserved but not implemented yet.")
    fail(f"Unknown profile '{profile}'. Supported: {', '.join(SUPPORTED_PROFILES)}")


def profile_settings(profile: str) -> ProfileSettings:
    require_profile(profile)
    return PROFILE_SETTINGS[profile]


def check_can_write(path: pathlib.Path, *, force: bool) -> None:
    if path.exists() and not force:
        fail(f"Refusing to overwrite existing file without --force: {path}")


def source_stage_path(cue_dir: pathlib.Path, source: pathlib.Path) -> pathlib.Path:
    suffix = source.suffix.lower()
    if suffix not in SOURCE_EXTENSIONS:
        fail(
            f"Unsupported source extension '{source.suffix}'. Supported: {', '.join(SOURCE_EXTENSIONS)}"
        )
    return cue_dir / f"{SOURCE_STAGE_STEM}{suffix}"


def find_source_stage(cue_dir: pathlib.Path) -> pathlib.Path:
    matches = [cue_dir / f"{SOURCE_STAGE_STEM}{suffix}" for suffix in SOURCE_EXTENSIONS]
    existing = [path for path in matches if path.exists()]
    if len(existing) == 1:
        return existing[0]
    if not existing:
        fail(
            f"Missing provider source: expected {SOURCE_STAGE_STEM} with one of {', '.join(SOURCE_EXTENSIONS)}"
        )
    fail(
        f"Multiple provider source files found: {', '.join(str(path) for path in existing)}"
    )


def run_text(
    args: list[str], *, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args, input=input_text, capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        command = " ".join(args)
        detail = (e.stderr or e.stdout or "").strip()
        fail(f"Command failed: {command}\n{detail}")


def run_binary(
    args: list[str], *, input_data: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(args, input=input_data, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        command = " ".join(args)
        detail = (e.stderr or e.stdout or b"").decode(errors="replace").strip()
        fail(f"Command failed: {command}\n{detail}")


def extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        fail(f"Could not parse ffmpeg JSON output:\n{text}")
    return json.loads(text[start : end + 1])


def append_metadata_log(
    cue_dir: pathlib.Path, event: str, values: dict[str, Any]
) -> None:
    metadata = cue_dir / METADATA_FILE
    if not metadata.exists():
        return

    timestamp = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat()
    parts = [f"{key}={value}" for key, value in values.items()]
    existing = metadata.read_text(encoding="utf-8")
    line = "" if "\n## Pipeline Log\n" in existing else "\n## Pipeline Log\n\n"
    line += f"- {timestamp} {event}"
    if parts:
        line += " " + " ".join(parts)
    line += "\n"
    with metadata.open("a", encoding="utf-8") as f:
        f.write(line)


def loudnorm_measure(
    path: pathlib.Path,
    *,
    filters: str | None = None,
    profile: str = BATTLE_PROFILE,
) -> dict[str, Any]:
    settings = profile_settings(profile)
    chain = []
    if filters:
        chain.append(filters)
    chain.append(
        f"loudnorm=I={settings.target_i}:LRA={settings.target_lra}:TP={settings.target_tp}:print_format=json"
    )
    result = run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            ",".join(chain),
            "-f",
            "null",
            os.devnull,
        ]
    )
    return extract_json_object(result.stderr + result.stdout)


def ffprobe_report(path: pathlib.Path) -> dict[str, Any]:
    result = run_text(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def audio_duration(path: pathlib.Path) -> float:
    report = ffprobe_report(path)
    duration = report.get("format", {}).get("duration")
    if duration is None:
        fail(f"Could not read duration: {path}")
    return float(duration)


def measure_audio(path: pathlib.Path, *, profile: str = BATTLE_PROFILE) -> dict[str, Any]:
    if not path.exists():
        fail(f"Missing input file: {path}")

    probe = ffprobe_report(path)
    streams = [
        stream
        for stream in probe.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]
    if not streams:
        fail(f"No audio stream found: {path}")

    loudness = loudnorm_measure(path, profile=profile)
    stream = streams[0]
    report = {
        "path": str(path),
        "duration": float(probe.get("format", {}).get("duration", 0.0)),
        "bit_rate": probe.get("format", {}).get("bit_rate"),
        "codec": stream.get("codec_name"),
        "channels": stream.get("channels"),
        "sample_rate": stream.get("sample_rate"),
        "integrated_lufs": loudness.get("input_i"),
        "true_peak_dbtp": loudness.get("input_tp"),
        "lra": loudness.get("input_lra"),
    }
    _LOGGER.info("audio_measurement", **report)
    return report


def render_master(
    source: pathlib.Path,
    output: pathlib.Path,
    *,
    profile: str,
    force: bool,
) -> None:
    check_can_write(output, force=force)

    settings = profile_settings(profile)
    filters = settings.filter_chain
    loudnorm = f"loudnorm=I={settings.target_i}:LRA={settings.target_lra}:TP={settings.target_tp}:print_format=summary"
    final_filters = f"{filters},{loudnorm},aformat=sample_fmts=flt"

    _LOGGER.info(
        "render_master",
        source=str(source),
        output=str(output),
        profile=profile,
        filters=final_filters,
    )
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-af",
            final_filters,
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def cut_wav(
    source: pathlib.Path, output: pathlib.Path, *, start: float, end: float, force: bool
) -> None:
    if end <= start:
        fail(f"Invalid cut range: start={start}, end={end}")
    check_can_write(output, force=force)
    _LOGGER.info(
        "cut_wav", source=str(source), output=str(output), start=start, end=end
    )
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def decode_pcm(
    path: pathlib.Path,
    *,
    sample_rate: int,
    channels: int,
    start: float | None = None,
    end: float | None = None,
) -> np.ndarray:
    args = ["ffmpeg", "-v", "error", "-i", str(path)]
    if start is not None:
        args.extend(["-ss", f"{start:.3f}"])
    if end is not None:
        args.extend(["-to", f"{end:.3f}"])
    args.extend(
        [
            "-map",
            "a:0",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-f",
            "f32le",
            "-",
        ]
    )
    result = run_binary(args)
    data = np.frombuffer(result.stdout, dtype=np.float32)
    if channels > 1:
        return data.reshape((-1, channels))
    return data


def encode_wav_from_pcm(path: pathlib.Path, data: np.ndarray, *, force: bool) -> None:
    check_can_write(path, force=force)
    run_binary(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-f",
            "f32le",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-i",
            "pipe:0",
            "-c:a",
            "pcm_s16le",
            str(path),
        ],
        input_data=np.asarray(data, dtype=np.float32).tobytes(),
    )


def cut_loop_with_crossfade(
    source: pathlib.Path,
    output: pathlib.Path,
    *,
    start: float,
    end: float,
    crossfade_ms: float,
    force: bool,
) -> None:
    if crossfade_ms <= 0:
        cut_wav(source, output, start=start, end=end, force=force)
        return

    segment = decode_pcm(
        source, sample_rate=SAMPLE_RATE, channels=2, start=start, end=end
    )
    fade_samples = int(SAMPLE_RATE * (crossfade_ms / 1000.0))
    if fade_samples <= 0:
        cut_wav(source, output, start=start, end=end, force=force)
        return
    if fade_samples * 4 >= len(segment):
        fail("Crossfade is too long for the selected loop segment.")

    fade = np.linspace(
        0.0, 1.0, fade_samples, endpoint=False, dtype=np.float32
    ).reshape((-1, 1))
    rendered = segment[fade_samples:].copy()
    rendered[-fade_samples:] = (segment[-fade_samples:] * (1.0 - fade)) + (
        segment[:fade_samples] * fade
    )
    _LOGGER.info(
        "cut_loop_with_crossfade",
        source=str(source),
        output=str(output),
        start=start,
        end=end,
        crossfade_ms=crossfade_ms,
        effective_start=start + (crossfade_ms / 1000.0),
    )
    encode_wav_from_pcm(output, rendered, force=force)


def export_ogg(source: pathlib.Path, output: pathlib.Path, *, force: bool) -> None:
    check_can_write(output, force=force)
    _LOGGER.info(
        "export_ogg",
        source=str(source),
        output=str(output),
        quality=RUNTIME_OGG_QUALITY,
    )
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-map",
            "a:0",
            "-af",
            "volume=-0.7dB",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "libvorbis",
            "-q:a",
            RUNTIME_OGG_QUALITY,
            str(output),
        ]
    )


def render_intro(source: pathlib.Path, output: pathlib.Path, *, force: bool) -> None:
    check_can_write(output, force=force)
    _LOGGER.info("render_intro", source=str(source), output=str(output))
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-af",
            "highpass=f=100,lowpass=f=12000,acrusher=bits=12:mix=0.06:samples=1:aa=0.65,aformat=sample_fmts=s16",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def loop_source_for(cue_dir: pathlib.Path, source: pathlib.Path | None) -> pathlib.Path:
    if source is not None:
        return source
    mastered = cue_dir / MASTER_STAGE
    if mastered.exists():
        return mastered
    fallback = find_source_stage(cue_dir)
    _LOGGER.warning("master_missing_using_provider_source", source=str(fallback))
    return fallback


def spectral_distance(a: np.ndarray, b: np.ndarray) -> float:
    size = min(len(a), len(b))
    if size == 0:
        return float("inf")
    a = a[:size]
    b = b[:size]
    a_mag = np.abs(np.fft.rfft(a * np.hanning(size)))
    b_mag = np.abs(np.fft.rfft(b * np.hanning(size)))
    a_mag = a_mag / (np.linalg.norm(a_mag) + 1e-9)
    b_mag = b_mag / (np.linalg.norm(b_mag) + 1e-9)
    return float(np.linalg.norm(a_mag - b_mag))


def score_loop_candidates(
    samples: np.ndarray,
    *,
    sample_rate: int,
    intro_start: float,
    min_loop: float,
    max_loop: float,
    count: int,
) -> list[dict[str, float]]:
    duration = len(samples) / sample_rate
    if duration < min_loop + 4.0:
        fail(f"Source is too short for loop suggestion: {duration:.2f}s")

    start_min = max(0.0, intro_start + 1.0)
    start_max = min(duration - min_loop, intro_start + 4.0)
    if start_max <= start_min:
        fail("Could not find a valid intro/loop start scan range.")

    step = 0.25
    energy_window = int(0.2 * sample_rate)
    fingerprint_window = int(1.0 * sample_rate)
    candidates: list[dict[str, float]] = []

    start_times = np.arange(start_min, start_max + step, step)
    for start_time in start_times:
        end_min = start_time + min_loop
        end_max = min(start_time + max_loop, duration - 1.2)
        if end_max <= end_min:
            continue

        for end_time in np.arange(end_min, end_max + step, step):
            start_i = int(start_time * sample_rate)
            end_i = int(end_time * sample_rate)
            if end_i + energy_window >= len(
                samples
            ) or start_i + fingerprint_window >= len(samples):
                continue
            if end_i - fingerprint_window <= 0:
                continue

            start_cut = samples[
                max(0, start_i - energy_window) : start_i + energy_window
            ]
            end_cut = samples[max(0, end_i - energy_window) : end_i + energy_window]
            start_fp = samples[start_i : start_i + fingerprint_window]
            end_fp = samples[end_i - fingerprint_window : end_i]
            cut_energy = float(
                np.sqrt(np.mean(start_cut**2)) + np.sqrt(np.mean(end_cut**2))
            )
            boundary_jump = float(abs(samples[end_i - 1] - samples[start_i]))
            similarity = spectral_distance(end_fp, start_fp)
            score = (similarity * 2.0) + cut_energy + boundary_jump
            candidates.append(
                {
                    "score": score,
                    "intro_end": float(start_time),
                    "loop_start": float(start_time),
                    "loop_end": float(end_time),
                    "loop_duration": float(end_time - start_time),
                }
            )

    chosen: list[dict[str, float]] = []
    for candidate in sorted(candidates, key=lambda c: c["score"]):
        if all(
            abs(candidate["loop_end"] - existing["loop_end"]) >= 2.0
            for existing in chosen
        ):
            chosen.append(candidate)
        if len(chosen) >= count:
            break
    return chosen


def write_preview(
    source: pathlib.Path, output: pathlib.Path, *, loop_start: float, loop_end: float
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pre_start = max(loop_start, loop_end - 4.0)
    post_end = min(loop_end, loop_start + 12.0)
    filter_complex = (
        f"[0:a]atrim=start={pre_start:.3f}:end={loop_end:.3f},asetpts=PTS-STARTPTS[a0];"
        f"[0:a]atrim=start={loop_start:.3f}:end={post_end:.3f},asetpts=PTS-STARTPTS[a1];"
        f"[0:a]atrim=start={loop_start:.3f}:end={post_end:.3f},asetpts=PTS-STARTPTS[a2];"
        "[a0][a1][a2]concat=n=3:v=0:a=1[out]"
    )
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "libvorbis",
            "-q:a",
            RUNTIME_OGG_QUALITY,
            str(output),
        ]
    )


@app.command(name="init-cue")
def init_cue(
    cue_dir: pathlib.Path, *, profile: str = BATTLE_PROFILE, force: bool = False
) -> None:
    """Create a staged cue folder with prompt and metadata templates."""
    configure_logging()
    settings = profile_settings(profile)
    cue_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = cue_dir / PROMPT_FILE
    metadata_path = cue_dir / METADATA_FILE
    check_can_write(prompt_path, force=force)
    check_can_write(metadata_path, force=force)

    prompt_path.write_text(settings.prompt_template, encoding="utf-8")
    metadata_path.write_text(settings.metadata_template, encoding="utf-8")
    _LOGGER.info("cue_initialized", cue_dir=str(cue_dir), profile=profile)


@app.command
def measure(path: pathlib.Path, *, profile: str = BATTLE_PROFILE) -> None:
    """Measure format and loudness for one audio file."""
    configure_logging()
    require_tools()
    require_profile(profile)
    report = measure_audio(path, profile=profile)
    print(json.dumps(report, indent=2))


@app.command
def process(
    cue_dir: pathlib.Path,
    *,
    profile: str = BATTLE_PROFILE,
    source: pathlib.Path | None = None,
    force: bool = False,
) -> None:
    """Render the processed full WAV stage from a provider source."""
    configure_logging()
    require_tools()
    require_profile(profile)

    cue_dir.mkdir(parents=True, exist_ok=True)
    source_path = source if source is not None else find_source_stage(cue_dir)
    if not source_path.exists():
        fail(f"Missing source file: {source_path}")

    canonical_source = source_stage_path(cue_dir, source_path)
    if source is not None and source_path.resolve() != canonical_source.resolve():
        check_can_write(canonical_source, force=force)
        shutil.copy2(source_path, canonical_source)
        _LOGGER.info(
            "source_staged", source=str(source_path), staged=str(canonical_source)
        )
        source_path = canonical_source

    output = cue_dir / MASTER_STAGE
    render_master(source_path, output, profile=profile, force=force)
    append_metadata_log(
        cue_dir,
        "process",
        {
            "profile": profile,
            "source": source_path.name,
            "output": output.name,
            "ffmpeg": ffmpeg_version(),
        },
    )


@app.command(name="suggest-loop")
def suggest_loop(
    cue_dir: pathlib.Path,
    *,
    source: pathlib.Path | None = None,
    intro_start: float = 0.0,
    min_loop: float = BATTLE_LOOP_MIN_SECONDS,
    max_loop: float = BATTLE_LOOP_MAX_SECONDS,
    candidates: int = 3,
    previews: bool = True,
) -> None:
    """Suggest loop cut points and optionally render disposable previews."""
    configure_logging()
    require_tools()
    source_path = loop_source_for(cue_dir, source)
    samples = decode_pcm(source_path, sample_rate=11_025, channels=1)
    suggestions: list[dict[str, Any]] = score_loop_candidates(
        samples,
        sample_rate=11_025,
        intro_start=intro_start,
        min_loop=min_loop,
        max_loop=max_loop,
        count=candidates,
    )
    if not suggestions:
        fail("No loop candidates found.")

    preview_dir = cue_dir / PREVIEW_DIR
    for index, candidate in enumerate(suggestions, start=1):
        candidate["index"] = index
        _LOGGER.info("loop_candidate", **candidate)
        if previews:
            write_preview(
                source_path,
                preview_dir / f"preview-loop-candidate-{index}.ogg",
                loop_start=candidate["loop_start"],
                loop_end=candidate["loop_end"],
            )

    print(json.dumps(suggestions, indent=2))
    print("\nUse one candidate with:")
    first = suggestions[0]
    script_path = pathlib.Path(__file__)
    print(
        f"uv run {script_path} cut "
        f"{cue_dir} --intro-end {first['intro_end']:.3f} "
        f"--loop-start {first['loop_start']:.3f} --loop-end {first['loop_end']:.3f}"
    )


@app.command
def cut(
    cue_dir: pathlib.Path,
    *,
    intro_end: float,
    loop_start: float,
    loop_end: float,
    intro_start: float = 0.0,
    crossfade_ms: float = 0.0,
    force: bool = False,
) -> None:
    """Cut canonical intro/loop WAVs and export runtime OGGs."""
    configure_logging()
    require_tools()
    source = cue_dir / MASTER_STAGE
    if not source.exists():
        fail(f"Missing mastered source: {source}")
    if intro_end <= intro_start:
        fail("intro_end must be greater than intro_start.")
    if loop_end <= loop_start:
        fail("loop_end must be greater than loop_start.")

    intro_wav = cue_dir / INTRO_STAGE
    loop_wav = cue_dir / LOOP_STAGE
    intro_ogg = cue_dir / INTRO_RUNTIME_STAGE
    loop_ogg = cue_dir / LOOP_RUNTIME_STAGE

    for output in (intro_wav, loop_wav, intro_ogg, loop_ogg):
        check_can_write(output, force=force)

    cut_wav(source, intro_wav, start=intro_start, end=intro_end, force=force)
    cut_loop_with_crossfade(
        source,
        loop_wav,
        start=loop_start,
        end=loop_end,
        crossfade_ms=crossfade_ms,
        force=force,
    )
    export_ogg(intro_wav, intro_ogg, force=force)
    export_ogg(loop_wav, loop_ogg, force=force)
    append_metadata_log(
        cue_dir,
        "cut",
        {
            "intro_start": f"{intro_start:.3f}",
            "intro_end": f"{intro_end:.3f}",
            "loop_start": f"{loop_start:.3f}",
            "loop_end": f"{loop_end:.3f}",
            "crossfade_ms": f"{crossfade_ms:.1f}",
        },
    )


@app.command(name="stage-loop")
def stage_loop(
    cue_dir: pathlib.Path,
    *,
    loop_source: pathlib.Path | None = None,
    profile: str = BATTLE_PROFILE,
    force: bool = False,
) -> None:
    """Stage one loop-only source as canonical loop WAV and runtime OGG."""
    configure_logging()
    require_tools()
    require_profile(profile)
    source = loop_source_for(cue_dir, loop_source)
    if not source.exists():
        fail(f"Missing loop source: {source}")

    loop_wav = cue_dir / LOOP_STAGE
    loop_ogg = cue_dir / LOOP_RUNTIME_STAGE

    for output in (loop_wav, loop_ogg):
        check_can_write(output, force=force)

    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(loop_wav),
        ]
    )
    export_ogg(loop_wav, loop_ogg, force=force)
    append_metadata_log(
        cue_dir,
        "stage-loop",
        {
            "profile": profile,
            "loop_source": source.name,
            "loop": loop_wav.name,
            "runtime_loop": loop_ogg.name,
        },
    )


@app.command(name="stage-pair")
def stage_pair(
    cue_dir: pathlib.Path,
    *,
    intro_source: pathlib.Path,
    loop_source: pathlib.Path,
    force: bool = False,
) -> None:
    """Stage separate provider intro and loop files as canonical outputs."""
    configure_logging()
    require_tools()
    if not intro_source.exists():
        fail(f"Missing intro source: {intro_source}")
    if not loop_source.exists():
        fail(f"Missing loop source: {loop_source}")

    intro_wav = cue_dir / INTRO_STAGE
    loop_wav = cue_dir / LOOP_STAGE
    intro_ogg = cue_dir / INTRO_RUNTIME_STAGE
    loop_ogg = cue_dir / LOOP_RUNTIME_STAGE

    for output in (intro_wav, loop_wav, intro_ogg, loop_ogg):
        check_can_write(output, force=force)

    render_intro(intro_source, intro_wav, force=force)
    run_text(
        [
            "ffmpeg",
            "-hide_banner",
            "-y" if force else "-n",
            "-i",
            str(loop_source),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(loop_wav),
        ]
    )
    export_ogg(intro_wav, intro_ogg, force=force)
    export_ogg(loop_wav, loop_ogg, force=force)
    append_metadata_log(
        cue_dir,
        "stage-pair",
        {
            "intro_source": intro_source.name,
            "loop_source": loop_source.name,
            "intro": intro_wav.name,
            "loop": loop_wav.name,
        },
    )


@app.command
def verify(cue_dir: pathlib.Path, *, profile: str = BATTLE_PROFILE) -> None:
    """Check expected stages, duration warnings, and runtime loop loudness."""
    configure_logging()
    require_tools()
    settings = profile_settings(profile)
    source_file = find_source_stage(cue_dir)
    expected = [
        PROMPT_FILE,
        METADATA_FILE,
        MASTER_STAGE,
        LOOP_STAGE,
        LOOP_RUNTIME_STAGE,
    ]
    if settings.requires_intro:
        expected.extend([INTRO_STAGE, INTRO_RUNTIME_STAGE])
    errors: list[str] = []
    warnings: list[str] = []

    for name in expected:
        path = cue_dir / name
        if not path.exists():
            errors.append(f"missing {name}")
    if not source_file.exists():
        errors.append(f"missing provider source {SOURCE_STAGE_STEM}.*")

    if errors:
        for error in errors:
            _LOGGER.error("verify_error", error=error)
        fail("Verification failed.")

    intro_duration: float | None = None
    if settings.requires_intro:
        intro_duration = audio_duration(cue_dir / INTRO_RUNTIME_STAGE)
        if (
            settings.intro_min_seconds is not None
            and settings.intro_max_seconds is not None
            and not (
                settings.intro_min_seconds
                <= intro_duration
                <= settings.intro_max_seconds
            )
        ):
            warnings.append(
                f"intro duration {intro_duration:.2f}s outside {settings.intro_min_seconds}-{settings.intro_max_seconds}s"
            )

    loop_duration = audio_duration(cue_dir / LOOP_RUNTIME_STAGE)
    if not (settings.loop_min_seconds <= loop_duration <= settings.loop_max_seconds):
        warnings.append(
            f"loop duration {loop_duration:.2f}s outside {settings.loop_min_seconds}-{settings.loop_max_seconds}s"
        )

    loop_measurement = measure_audio(cue_dir / LOOP_RUNTIME_STAGE, profile=profile)
    lufs = float(loop_measurement["integrated_lufs"])
    true_peak = float(loop_measurement["true_peak_dbtp"])
    lra = float(loop_measurement["lra"])
    if not (settings.lufs_min <= lufs <= settings.lufs_max):
        warnings.append(
            f"runtime loop loudness {lufs:.2f} LUFS outside {settings.lufs_min}-{settings.lufs_max}"
        )
    if true_peak > settings.target_tp:
        errors.append(
            f"runtime loop true peak {true_peak:.2f} dBTP above {settings.target_tp}"
        )
    if lra < settings.lra_warning_min or lra > settings.lra_warning_max:
        warnings.append(
            f"runtime loop LRA {lra:.2f} outside rough {settings.lra_warning_min}-{settings.lra_warning_max} target"
        )

    for warning in warnings:
        _LOGGER.warning("verify_warning", warning=warning)
    for error in errors:
        _LOGGER.error("verify_error", error=error)
    metadata_values: dict[str, Any] = {
        "profile": profile,
        "loop_duration": f"{loop_duration:.2f}s",
        "loop_lufs": f"{lufs:.2f}",
        "loop_tp": f"{true_peak:.2f}",
        "loop_lra": f"{lra:.2f}",
        "warnings": len(warnings),
        "errors": len(errors),
    }
    if intro_duration is not None:
        metadata_values["intro_duration"] = f"{intro_duration:.2f}s"
    append_metadata_log(cue_dir, "verify", metadata_values)

    if errors:
        fail("Verification failed.")
    _LOGGER.info("verify_complete", profile=profile, warnings=len(warnings))


@app.command(name="clean-previews")
def clean_previews(cue_dir: pathlib.Path) -> None:
    """Delete only the cue folder's disposable _previews directory."""
    configure_logging()
    preview_dir = cue_dir / PREVIEW_DIR
    if preview_dir.name != PREVIEW_DIR:
        fail(f"Refusing to delete unexpected path: {preview_dir}")
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
        _LOGGER.info("previews_deleted", path=str(preview_dir))
    else:
        _LOGGER.info("previews_absent", path=str(preview_dir))


def ffmpeg_version() -> str:
    require_tools()
    result = run_text(["ffmpeg", "-version"])
    first_line = result.stdout.splitlines()[0] if result.stdout else "ffmpeg unknown"
    match = re.search(r"ffmpeg version ([^\s]+)", first_line)
    return match.group(1) if match else first_line


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
