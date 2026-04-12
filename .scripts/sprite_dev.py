#!/usr/bin/env python3
"""
Quick harness for battle sprite prompts and Gemini generation.

Run from repo root (uses backend venv and `app` package):

    cd backend
    uv run python ..\\.scripts\\sprite_dev.py prompt --role both
    uv run python ..\\.scripts\\sprite_dev.py generate --role player --force

Loads `GEMINI_API_KEY` / `GOOGLE_API_KEY` from the repo `.env` when present.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"


def _bootstrap() -> None:
    sys.path.insert(0, str(BACKEND_DIR))
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")


def _demo_payload(*, uid: str) -> "VibemonPayload":
    from app.domain.models import Move, VibemonPayload, VibemonStats, VisualDNA

    stats = VibemonStats(
        hp=100,
        attack=80,
        defense=90,
        sp_attack=70,
        sp_defense=75,
        speed=85,
        element="Grass",
    )
    dna = VisualDNA(
        n_points=10,
        spikiness=0.2,
        limb_count=2,
        limb_style="stubby",
        eye_count=2,
        eye_size=0.08,
        eye_shape="circle",
        mouth_style="line",
        texture_pattern="dots",
        color_primary=(55.0, 0.7, 0.5),
        color_secondary=(120.0, 0.6, 0.45),
        color_accent=(300.0, 0.5, 0.55),
        color_eye=(200.0, 0.8, 0.4),
        outline_weight=1.5,
        glow_intensity=0.2,
        size_scale=1.0,
        animation_speed=1.0,
    )
    moves = [
        Move("Vine Lash", "Grass", "physical", 40, 100, False),
        Move("Tackle", "Normal", "physical", 40, 100, False),
        Move("Growl", "Normal", "status", 0, 100, False),
        Move("Leech Seed", "Grass", "status", 0, 90, False),
    ]
    return VibemonPayload(
        uid=uid,
        name="SpriteDev",
        source="sprite_dev",
        stats=stats,
        moves=moves,
        visual_dna=dna,
        flavour_text="",
        stat_origins={k: "Baseline" for k in ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")},
        fallback=False,
    )


def _roles_arg(s: str) -> list[str]:
    if s == "both":
        return ["player", "enemy"]
    if s in ("player", "enemy"):
        return [s]
    raise argparse.ArgumentTypeError("expected player, enemy, or both")


def cmd_prompt(args: argparse.Namespace) -> int:
    from app.infra.sprites import BattleContext, _generate_prompt, vibemon_to_monster_state

    payload = _demo_payload(uid=args.uid)
    for role in args.role:
        ctx = BattleContext.PLAYER if role == "player" else BattleContext.ENEMY
        m = vibemon_to_monster_state(payload, ctx)
        text = _generate_prompt(m, payload, paired_battle=args.paired)
        print(f"=== {role.upper()} ({ctx.value}) ===\n{text}\n", flush=True)
    return 0


def _sprite_path(payload_uid: str, role: str) -> Path:
    from app.infra.sprites import SPRITES_DIR

    safe = payload_uid.replace("/", "_").replace("\\", "_").replace(":", "_")
    return SPRITES_DIR / f"{safe}_{role}.png"


async def cmd_generate_async(args: argparse.Namespace) -> int:
    from app.infra.sprites import BattleContext, ensure_sprite

    payload = _demo_payload(uid=args.uid)
    pair_uid = args.pair_uid or payload.uid

    for role in args.role:
        if args.force:
            p = _sprite_path(payload.uid, role)
            if p.exists():
                p.unlink()
                print(f"removed cache: {p}", flush=True)

        ctx = BattleContext.PLAYER if role == "player" else BattleContext.ENEMY
        url = await ensure_sprite(
            payload,
            ctx,
            model=args.model,
            paired_battle=args.paired,
            pair_identity_uid=pair_uid,
        )
        if url is None:
            print(f"{role}: generation skipped or failed (check API key and logs).", file=sys.stderr, flush=True)
            return 1
        disk = BACKEND_DIR / url.lstrip("/").replace("/", os.sep)
        print(f"{role}: {url}\n      -> {disk}", flush=True)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    return asyncio.run(cmd_generate_async(args))


def main() -> int:
    _bootstrap()

    parser = argparse.ArgumentParser(description="Sprite prompt / generation dev helper.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prompt = sub.add_parser("prompt", help="Print sprite prompts (no API calls).")
    p_prompt.add_argument(
        "--role",
        type=_roles_arg,
        default=["player", "enemy"],
        help="player | enemy | both (default: both)",
    )
    p_prompt.add_argument("--uid", default="sprite-dev", help="Payload uid (affects DESIGN LOCK / filenames).")
    p_prompt.add_argument("--paired", action="store_true", default=True, help="Include BATTLE SET paired text (default: on).")
    p_prompt.add_argument("--no-paired", action="store_false", dest="paired", help="Omit paired-battle paragraph.")
    p_prompt.set_defaults(func=cmd_prompt)

    p_gen = sub.add_parser("generate", help="Call ensure_sprite (uses Gemini + rembg).")
    p_gen.add_argument(
        "--role",
        type=_roles_arg,
        default=["player", "enemy"],
        help="player | enemy | both (default: both)",
    )
    p_gen.add_argument("--uid", default="sprite-dev", help="Payload uid and default pair_identity_uid.")
    p_gen.add_argument("--pair-uid", default=None, help="Override pair seed identity (default: same as --uid).")
    p_gen.add_argument("--model", default="gemini-2.5-flash-image", help="Gemini image model id.")
    p_gen.add_argument("--force", action="store_true", help="Delete cached PNG(s) before generating.")
    p_gen.add_argument("--paired", action="store_true", default=True, help="Include BATTLE SET paired text (default: on).")
    p_gen.add_argument("--no-paired", action="store_false", dest="paired", help="Omit paired-battle paragraph.")
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
