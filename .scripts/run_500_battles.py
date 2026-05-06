"""Run 500 battles and save output to batch_500 directory."""
import subprocess
import sys
from pathlib import Path

out_dir = Path("battle_runs/batch_500")
out_dir.mkdir(parents=True, exist_ok=True)

for i in range(1, 501):
    result = subprocess.run(
        [
            "uv", "run", "battle_debug.py",
            "--render", "chat",
            "--output-dir", str(out_dir),
            "--battle-id", str(i),
        ],
        capture_output=True,
        text=True,
    )
    if i % 50 == 0:
        print(f"Completed {i}/500 battles", flush=True)
    if result.returncode != 0:
        print(f"Battle {i} failed: {result.stderr}", file=sys.stderr, flush=True)

print("All 500 battles complete!")
