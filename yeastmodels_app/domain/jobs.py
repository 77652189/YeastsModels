"""Job-domain objects for local analysis history."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AnalysisType = Literal["fba", "fva", "network"]
JobStatus = Literal["running", "succeeded", "failed", "partial"]


@dataclass(frozen=True)
class JobArtifact:
    format: str
    path: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    created_at: str
    analysis_type: AnalysisType
    status: JobStatus
    model_id: str
    parameters: dict[str, Any]
    summary: dict[str, Any]
    result: dict[str, Any] | None = None
    artifacts: list[JobArtifact] = field(default_factory=list)
    error: str | None = None
    logs_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "analysis_type": self.analysis_type,
            "status": self.status,
            "model_id": self.model_id,
            "parameters": self.parameters,
            "summary": self.summary,
            "result": self.result,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "error": self.error,
            "logs_tail": self.logs_tail,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        return cls(
            job_id=payload["job_id"],
            created_at=payload["created_at"],
            analysis_type=payload["analysis_type"],
            status=payload["status"],
            model_id=payload.get("model_id", ""),
            parameters=payload.get("parameters", {}),
            summary=payload.get("summary", {}),
            result=payload.get("result"),
            artifacts=[
                JobArtifact(
                    format=artifact["format"],
                    path=artifact["path"],
                    label=artifact.get("label", artifact["format"]),
                )
                for artifact in payload.get("artifacts", [])
            ],
            error=payload.get("error"),
            logs_tail=payload.get("logs_tail", ""),
        )
