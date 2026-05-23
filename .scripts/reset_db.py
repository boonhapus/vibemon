"""Drop all local dev database files and clear generated monstore assets.

Usage: uv run --project backend python .scripts/reset_db.py
"""

from pathlib import Path
import shutil
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PATHS_TO_REMOVE: list[Path] = [
    _REPO_ROOT / ".scripts" / "vibemon.db",
    _REPO_ROOT / ".generated" / "database" / "vibemon.db",
    _REPO_ROOT / ".generated" / "monstore",
    _REPO_ROOT / ".scripts" / "__pycache__",
]


def main() -> int:
    for path in PATHS_TO_REMOVE:
        if not path.exists():
            print(f"SKIP  {path} (not found)")
            continue
        if path.is_dir():
            shutil.rmtree(path)
            print(f"RM -R {path}")
        else:
            path.unlink()
            print(f"RM    {path}")

    (PATHS_TO_REMOVE[1].parent).mkdir(parents=True, exist_ok=True)

    print("Done. Run `uv run --project backend python .scripts/vibemon_generator.py` to regenerate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
