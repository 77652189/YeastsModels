#!/usr/bin/env python
"""CLI entry point for the P. pastoris iMT1026 v3 FBA demo."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from yeastmodels_app.controllers.cli_controller import main


if __name__ == "__main__":
    main()
