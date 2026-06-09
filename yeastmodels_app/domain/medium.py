"""Medium and medium-comparison domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from yeastmodels_app.domain.model import ExchangeReaction


@dataclass(frozen=True)
class MediumSummary:
    exchange_count: int
    open_uptake_count: int
    secretion_allowed_count: int
    open_uptakes: list[ExchangeReaction]
    all_exchanges: list[ExchangeReaction]

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_count": self.exchange_count,
            "open_uptake_count": self.open_uptake_count,
            "secretion_allowed_count": self.secretion_allowed_count,
            "open_uptakes": [reaction.to_dict() for reaction in self.open_uptakes],
            "all_exchanges": [reaction.to_dict() for reaction in self.all_exchanges],
        }


@dataclass(frozen=True)
class MediumCondition:
    condition_id: str
    name: str
    name_zh: str
    name_en: str
    description: str
    medium: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediumConditionInsight:
    condition_id: str
    rank: int | None
    role: str
    takeaway: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediumComparisonInterpretation:
    best_condition_id: str | None
    lowest_condition_id: str | None
    hlf_focus_condition_ids: list[str]
    observations: list[str]
    insights: list[MediumConditionInsight]

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_condition_id": self.best_condition_id,
            "lowest_condition_id": self.lowest_condition_id,
            "hlf_focus_condition_ids": self.hlf_focus_condition_ids,
            "observations": self.observations,
            "insights": [insight.to_dict() for insight in self.insights],
        }
