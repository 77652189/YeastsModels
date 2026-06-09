"""FBA analysis service."""

from __future__ import annotations

from yeastmodels_app.domain import FbaResult, MediumFbaResult, ModelSummary
from yeastmodels_app.services.medium_service import MediumService
from yeastmodels_app.services.model_repository import ModelRepository


class FbaService:
    """Run baseline and medium-specific FBA without owning model loading."""

    def __init__(self, repository: ModelRepository, medium_service: MediumService) -> None:
        self.repository = repository
        self.medium_service = medium_service

    @property
    def model(self):
        return self.repository.model

    def get_summary(self) -> ModelSummary:
        model = self.model
        return ModelSummary(
            model_file=str(self.repository.model_path),
            model_id=model.id,
            model_name=model.name,
            reaction_count=len(model.reactions),
            metabolite_count=len(model.metabolites),
            gene_count=len(model.genes),
            objective=str(model.objective.expression),
        )

    def run_fba(self) -> FbaResult:
        solution = self.model.optimize()
        return FbaResult(
            summary=self.get_summary(),
            solution_status=solution.status,
            objective_value=solution.objective_value,
        )

    def run_for_medium(self, condition_id: str) -> MediumFbaResult:
        condition = self.medium_service.get_condition(condition_id)
        with self.repository.model_context() as model:
            model.medium = condition.medium
            solution = model.optimize()

        return MediumFbaResult(
            condition=condition,
            solution_status=solution.status,
            objective_value=solution.objective_value,
        )

    def compare_medium_conditions(self) -> list[MediumFbaResult]:
        return [
            self.run_for_medium(condition.condition_id)
            for condition in self.medium_service.get_conditions()
        ]
