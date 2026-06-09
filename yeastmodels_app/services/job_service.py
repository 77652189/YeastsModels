"""Application service for traceable local analysis jobs."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from yeastmodels_app.config import PICHIA_EXPORTS_DIR
from yeastmodels_app.domain import JobArtifact, JobRecord, JobStatus
from yeastmodels_app.services.model_service import YeastModelService
from yeastmodels_app.storage import JsonJobStore


class JobService:
    """Run analyses and persist JSON records plus downloadable exports."""

    def __init__(
        self,
        analysis_service: YeastModelService | None = None,
        store: JsonJobStore | None = None,
        exports_dir: Path = PICHIA_EXPORTS_DIR,
    ) -> None:
        self.analysis_service = analysis_service or YeastModelService()
        self.store = store or JsonJobStore()
        self.exports_dir = Path(exports_dir)

    def run_fba_job(self, parameters: dict[str, Any] | None = None) -> JobRecord:
        parameters = parameters or {}
        record = self._new_record("fba", parameters)
        self.store.save(record)
        try:
            result = self.analysis_service.run_fba().to_dict()
            summary = _fba_summary(result)
            status: JobStatus = "succeeded"
            record = replace(
                record,
                status=status,
                summary=summary,
                result=result,
                artifacts=self._write_artifacts(record.job_id, "fba", result),
            )
        except Exception as exc:  # noqa: BLE001 - job records should capture failures.
            record = replace(record, status="failed", error=str(exc), logs_tail=str(exc)[-4000:])
        self.store.save(record)
        return record

    def run_fva_job(self, parameters: dict[str, Any] | None = None) -> JobRecord:
        parameters = parameters or {}
        condition_id = str(parameters.get("condition_id", "default"))
        scope = str(parameters.get("scope", "open_exchange"))
        fraction_of_optimum = float(parameters.get("fraction_of_optimum", 0.95))
        timeout_seconds = int(parameters.get("timeout_seconds", 180))

        record = self._new_record("fva", parameters)
        self.store.save(record)
        try:
            payload = self.analysis_service.run_fva_isolated(
                condition_id=condition_id,
                scope=scope,
                fraction_of_optimum=fraction_of_optimum,
                timeout_seconds=timeout_seconds,
            )
            result = payload.get("result")
            if result is None:
                raise RuntimeError(str(payload.get("error", "FVA did not return a result.")))

            failed_count = int(result.get("failed_count", 0))
            status: JobStatus
            if payload.get("ok") and failed_count == 0:
                status = "succeeded"
            elif result.get("rows"):
                status = "partial"
            else:
                status = "failed"

            record = replace(
                record,
                status=status,
                summary=_fva_summary(result, payload),
                result=result,
                artifacts=self._write_artifacts(record.job_id, "fva", result),
                error=None if payload.get("ok") else str(payload.get("error", "")),
                logs_tail=_payload_logs(payload),
            )
        except Exception as exc:  # noqa: BLE001
            record = replace(record, status="failed", error=str(exc), logs_tail=str(exc)[-4000:])
        self.store.save(record)
        return record

    def run_network_job(self, parameters: dict[str, Any] | None = None) -> JobRecord:
        parameters = parameters or {}
        view_id = str(parameters.get("view_id", "exchange_to_biomass"))
        condition_id = str(parameters.get("condition_id", "default"))
        metabolite_id = str(parameters.get("metabolite_id", "met_L_c"))

        record = self._new_record("network", parameters)
        self.store.save(record)
        try:
            graph = self.analysis_service.build_network_graph(
                view_id=view_id,
                condition_id=condition_id,
                metabolite_id=metabolite_id,
            )
            result = graph.to_dict()
            result["dot"] = graph.to_dot()
            record = replace(
                record,
                status="succeeded",
                summary={
                    "title": graph.title,
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                    "view_id": view_id,
                },
                result=result,
                artifacts=self._write_artifacts(record.job_id, "network", result),
            )
        except Exception as exc:  # noqa: BLE001
            record = replace(record, status="failed", error=str(exc), logs_tail=str(exc)[-4000:])
        self.store.save(record)
        return record

    def list_jobs(self, limit: int | None = None) -> list[JobRecord]:
        return self.store.list(limit=limit)

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.store.get(job_id)

    def get_download(self, job_id: str, file_format: str) -> tuple[Path, str, str]:
        record = self.get_job(job_id)
        if record is None:
            raise FileNotFoundError(f"Unknown job '{job_id}'.")

        for artifact in record.artifacts:
            if artifact.format == file_format:
                path = Path(artifact.path)
                if path.exists():
                    return path, _media_type(file_format), path.name

        raise FileNotFoundError(
            f"Job '{job_id}' does not have a downloadable {file_format} artifact."
        )

    def _new_record(self, analysis_type: str, parameters: dict[str, Any]) -> JobRecord:
        summary = self.analysis_service.get_summary()
        return JobRecord(
            job_id=f"{analysis_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            analysis_type=analysis_type,  # type: ignore[arg-type]
            status="running",
            model_id=summary.model_id,
            parameters=parameters,
            summary={"message": "任务已创建，正在运行。"},
            result=None,
            artifacts=[],
            error=None,
            logs_tail="",
        )

    def _write_artifacts(
        self,
        job_id: str,
        analysis_type: str,
        result: dict[str, Any],
    ) -> list[JobArtifact]:
        export_dir = self.exports_dir / job_id
        export_dir.mkdir(parents=True, exist_ok=True)
        artifacts: list[JobArtifact] = []

        json_path = export_dir / "result.json"
        json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        artifacts.append(JobArtifact(format="json", path=str(json_path), label="完整结果 JSON"))

        if analysis_type == "fba":
            csv_path = export_dir / "fba_summary.csv"
            _write_dict_rows_csv(csv_path, _flatten_fba_for_csv(result))
            artifacts.append(JobArtifact(format="csv", path=str(csv_path), label="FBA 摘要 CSV"))
        elif analysis_type == "fva":
            csv_path = export_dir / "fva_rows.csv"
            _write_dict_rows_csv(csv_path, result.get("rows", []))
            artifacts.append(JobArtifact(format="csv", path=str(csv_path), label="FVA 结果 CSV"))
        elif analysis_type == "network":
            dot_path = export_dir / "network.dot"
            dot_path.write_text(str(result.get("dot", "")), encoding="utf-8")
            artifacts.append(JobArtifact(format="dot", path=str(dot_path), label="网络 DOT"))

        return artifacts


def _fba_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary", {})
    return {
        "solution_status": result.get("solution_status"),
        "objective_value": result.get("objective_value"),
        "reaction_count": summary.get("reaction_count"),
        "metabolite_count": summary.get("metabolite_count"),
        "gene_count": summary.get("gene_count"),
    }


def _fva_summary(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "solution_status": result.get("solution_status"),
        "objective_value": result.get("objective_value"),
        "reaction_count": result.get("reaction_count"),
        "fixed_count": result.get("fixed_count"),
        "narrow_count": result.get("narrow_count"),
        "variable_count": result.get("variable_count"),
        "failed_count": result.get("failed_count", 0),
        "method": result.get("method"),
        "fallback_used": bool(payload.get("fallback_used")),
    }


def _payload_logs(payload: dict[str, Any]) -> str:
    parts = [
        str(payload.get("error", "")),
        str(payload.get("stdout", "")),
        str(payload.get("stderr", "")),
    ]
    batch_error = payload.get("batch_error")
    if isinstance(batch_error, dict):
        parts.extend(
            [
                str(batch_error.get("error", "")),
                str(batch_error.get("stdout", "")),
                str(batch_error.get("stderr", "")),
            ]
        )
    return "\n".join(part for part in parts if part)[-4000:]


def _flatten_fba_for_csv(result: dict[str, Any]) -> list[dict[str, Any]]:
    summary = result.get("summary", {})
    rows = [
        {"metric": "solution_status", "value": result.get("solution_status")},
        {"metric": "objective_value", "value": result.get("objective_value")},
    ]
    rows.extend({"metric": key, "value": value} for key, value in summary.items())
    return rows


def _write_dict_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _media_type(file_format: str) -> str:
    return {
        "json": "application/json",
        "csv": "text/csv",
        "dot": "text/vnd.graphviz",
    }.get(file_format, "application/octet-stream")
