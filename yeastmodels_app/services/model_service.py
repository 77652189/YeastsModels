"""Backward-compatible facade for iMT1026 v3 analyses."""

from __future__ import annotations

from pathlib import Path

from yeastmodels_app.config import DEFAULT_MODEL_PATH
from yeastmodels_app.domain import (
    FbaResult,
    FvaResult,
    MediumComparisonInterpretation,
    MediumCondition,
    MediumFbaResult,
    MediumSummary,
    ModelSummary,
    NetworkGraph,
)
from yeastmodels_app.services.fba_service import FbaService
from yeastmodels_app.services.fva_service import FvaService
from yeastmodels_app.services.hlf_preparation_service import HlfPreparationService
from yeastmodels_app.services.medium_service import MediumService
from yeastmodels_app.services.model_repository import ModelRepository
from yeastmodels_app.services.network_service import NetworkService


class YeastModelService:
    """Facade kept stable for CLI, FastAPI, Streamlit, and FVA worker."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.repository = ModelRepository(model_path)
        self.model_path = self.repository.model_path
        self.medium_service = MediumService(self.repository)
        self.fba_service = FbaService(self.repository, self.medium_service)
        self.fva_service = FvaService(self.repository, self.medium_service)
        self.network_service = NetworkService(self.repository, self.medium_service)
        self.hlf_preparation_service = HlfPreparationService()

    @property
    def model(self):
        return self.repository.model

    def get_summary(self) -> ModelSummary:
        return self.fba_service.get_summary()

    def run_fba(self) -> FbaResult:
        return self.fba_service.run_fba()

    def get_medium_summary(self) -> MediumSummary:
        return self.medium_service.get_summary()

    def get_medium_conditions(self) -> list[MediumCondition]:
        return self.medium_service.get_conditions()

    def run_fba_for_medium(self, condition_id: str) -> MediumFbaResult:
        return self.fba_service.run_for_medium(condition_id)

    def compare_medium_conditions(self) -> list[MediumFbaResult]:
        return self.fba_service.compare_medium_conditions()

    def interpret_medium_comparisons(
        self, comparisons: list[MediumFbaResult] | None = None
    ) -> MediumComparisonInterpretation:
        return self.medium_service.interpret_comparisons(
            comparisons or self.compare_medium_conditions()
        )

    def get_fva_scope_options(self) -> list[dict[str, str]]:
        return self.fva_service.get_scope_options()

    def run_fva(
        self,
        condition_id: str = "default",
        scope: str = "open_exchange",
        fraction_of_optimum: float = 0.95,
    ) -> FvaResult:
        return self.fva_service.run_fva(
            condition_id=condition_id,
            scope=scope,
            fraction_of_optimum=fraction_of_optimum,
        )

    def run_single_reaction_fva(
        self,
        condition_id: str,
        reaction_id: str,
        fraction_of_optimum: float,
    ) -> dict[str, object]:
        return self.fva_service.run_single_reaction_fva(
            condition_id=condition_id,
            reaction_id=reaction_id,
            fraction_of_optimum=fraction_of_optimum,
        )

    def run_fva_isolated(
        self,
        condition_id: str = "default",
        scope: str = "open_exchange",
        fraction_of_optimum: float = 0.95,
        timeout_seconds: int = 180,
    ) -> dict[str, object]:
        return self.fva_service.run_fva_isolated(
            condition_id=condition_id,
            scope=scope,
            fraction_of_optimum=fraction_of_optimum,
            timeout_seconds=timeout_seconds,
        )

    def get_network_view_options(self) -> list[dict[str, str]]:
        return self.network_service.get_view_options()

    def get_amino_acid_options(self) -> list[dict[str, str]]:
        return self.network_service.get_amino_acid_options()

    def build_network_graph(
        self,
        view_id: str,
        condition_id: str = "default",
        metabolite_id: str = "met_L_c",
    ) -> NetworkGraph:
        return self.network_service.build_graph(
            view_id=view_id,
            condition_id=condition_id,
            metabolite_id=metabolite_id,
        )

    def get_hlf_preparation_summary(self) -> dict[str, object]:
        return self.hlf_preparation_service.get_preparation_summary()
