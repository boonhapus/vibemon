"""Headless JSON generate (no Litestar, no raster sprites)."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import attrs

from app.serialization import structure_generate_request
from app.services.generate_service import generate


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        raw = open(argv[0], encoding="utf-8").read()
    else:
        raw = sys.stdin.read()
    data: dict[str, Any] = json.loads(raw)
    req = structure_generate_request(data)
    req = attrs.evolve(req, render_assets="none")
    out = asyncio.run(generate(req))
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
