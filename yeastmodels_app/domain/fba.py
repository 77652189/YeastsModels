"""FBA domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yeastmodels_app.domain.medium import MediumCondition
from yeastmodels_app.domain.model import ModelSummary


@dataclass(frozen=True)
class FbaResult:
    summary: ModelSummary
    solution_status: str
    objective_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "solution_status": self.solution_status,
            "objective_value": self.objective_value,
        }


@dataclass(frozen=True)
class MediumFbaResult:
    condition: MediumCondition
    solution_status: str
    objective_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition.to_dict(),
            "solution_status": self.solution_status,
            "objective_value": self.objective_value,
        }
