"""Core model-domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModelSummary:
    model_file: str
    model_id: str
    model_name: str
    reaction_count: int
    metabolite_count: int
    gene_count: int
    objective: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExchangeReaction:
    reaction_id: str
    name: str
    name_zh: str
    lower_bound: float
    upper_bound: float
    medium_bound: float | None
    can_uptake: bool
    can_secrete: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
