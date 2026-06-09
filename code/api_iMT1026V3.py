#!/usr/bin/env python
"""FastAPI entry point for the P. pastoris iMT1026 v3 FBA demo."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from yeastmodels_app.controllers.api_controller import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

