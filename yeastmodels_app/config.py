"""Application-level paths and defaults."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = REPO_ROOT / "models" / "iMT1026V3.xml"
PICHIA_RESULTS_DIR = REPO_ROOT / "results" / "pichia_app"
PICHIA_JOBS_DIR = PICHIA_RESULTS_DIR / "jobs"
PICHIA_EXPORTS_DIR = PICHIA_RESULTS_DIR / "exports"
