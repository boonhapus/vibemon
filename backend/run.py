"""Dev entry: `uv run python run.py` from the backend directory."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
