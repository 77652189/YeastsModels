"""FVA domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from yeastmodels_app.domain.medium import MediumCondition


@dataclass(frozen=True)
class FvaReactionResult:
    reaction_id: str
    name: str
    name_zh: str
    minimum: float
    maximum: float
    flux_range: float
    category: str
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FvaReactionFailure:
    reaction_id: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FvaResult:
    condition: MediumCondition
    scope: str
    fraction_of_optimum: float
    method: str
    solution_status: str
    objective_value: float | None
    reaction_count: int
    fixed_count: int
    narrow_count: int
    variable_count: int
    failed_count: int
    rows: list[FvaReactionResult]
    failed_rows: list[FvaReactionFailure]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition.to_dict(),
            "scope": self.scope,
            "fraction_of_optimum": self.fraction_of_optimum,
            "method": self.method,
            "solution_status": self.solution_status,
            "objective_value": self.objective_value,
            "reaction_count": self.reaction_count,
            "fixed_count": self.fixed_count,
            "narrow_count": self.narrow_count,
            "variable_count": self.variable_count,
            "failed_count": self.failed_count,
            "rows": [row.to_dict() for row in self.rows],
            "failed_rows": [row.to_dict() for row in self.failed_rows],
        }
