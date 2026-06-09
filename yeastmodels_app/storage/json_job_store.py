"""JSON-backed local job storage."""

from __future__ import annotations

import json
from pathlib import Path

from yeastmodels_app.config import PICHIA_JOBS_DIR
from yeastmodels_app.domain import JobRecord


class JsonJobStore:
    """Persist JobRecord objects as one JSON file per job."""

    def __init__(self, base_dir: Path = PICHIA_JOBS_DIR) -> None:
        self.base_dir = Path(base_dir)

    def save(self, record: JobRecord) -> Path:
        path = self._path_for_record(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)
        return path

    def get(self, job_id: str) -> JobRecord | None:
        for path in self.base_dir.glob(f"*/{job_id}.json"):
            try:
                return JobRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                return None
        return None

    def list(self, limit: int | None = None) -> list[JobRecord]:
        records: list[JobRecord] = []
        for path in self.base_dir.glob("*/*.json"):
            try:
                records.append(
                    JobRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        records.sort(key=lambda record: record.created_at, reverse=True)
        if limit is not None:
            return records[:limit]
        return records

    def _path_for_record(self, record: JobRecord) -> Path:
        return self.base_dir / _date_key(record.created_at) / f"{record.job_id}.json"


def _date_key(created_at: str) -> str:
    if len(created_at) >= 10:
        return created_at[:10].replace("-", "")
    return "unknown_date"
