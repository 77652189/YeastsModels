"""FVA analysis service with subprocess isolation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from cobra.flux_analysis import flux_variability_analysis
from cobra.util.solver import fix_objective_as_constraint

from yeastmodels_app.domain import (
    FvaReactionFailure,
    FvaReactionResult,
    FvaResult,
)
from yeastmodels_app.services.constants import (
    AMINO_ACID_METABOLITE_IDS,
    EXCHANGE_CHINESE_NAMES,
    FVA_FIXED_TOLERANCE,
    FVA_NARROW_TOLERANCE,
    FVA_SCOPE_OPTIONS,
)
from yeastmodels_app.services.medium_service import MediumService
from yeastmodels_app.services.model_repository import ModelRepository


class FvaService:
    """Run FVA directly or through a worker process for UI safety."""

    def __init__(self, repository: ModelRepository, medium_service: MediumService) -> None:
        self.repository = repository
        self.medium_service = medium_service

    @property
    def model(self):
        return self.repository.model

    def get_scope_options(self) -> list[dict[str, str]]:
        return [
            {"scope": scope, "name_zh": name}
            for scope, name in FVA_SCOPE_OPTIONS.items()
        ]

    def run_fva(
        self,
        condition_id: str = "default",
        scope: str = "open_exchange",
        fraction_of_optimum: float = 0.95,
    ) -> FvaResult:
        self._validate_scope(scope)
        self._validate_fraction(fraction_of_optimum)

        condition = self.medium_service.get_condition(condition_id)
        reaction_ids = self._get_fva_reaction_ids(scope, condition.medium)
        rows: list[FvaReactionResult] = []

        with self.repository.model_context() as model:
            model.medium = condition.medium
            solution = model.optimize()
            if solution.status == "optimal" and reaction_ids:
                reactions = [model.reactions.get_by_id(reaction_id) for reaction_id in reaction_ids]
                fva_frame = flux_variability_analysis(
                    model,
                    reaction_list=reactions,
                    fraction_of_optimum=fraction_of_optimum,
                    processes=1,
                )
                rows = [
                    self._build_fva_reaction_result(
                        reaction_id=reaction_id,
                        minimum=float(fva_frame.loc[reaction_id, "minimum"]),
                        maximum=float(fva_frame.loc[reaction_id, "maximum"]),
                    )
                    for reaction_id in reaction_ids
                ]

        rows.sort(key=lambda row: (row.flux_range, row.reaction_id))
        fixed_count = sum(1 for row in rows if row.category == "固定通量")
        narrow_count = sum(1 for row in rows if row.category == "窄范围")
        variable_count = sum(1 for row in rows if row.category == "可变通量")

        return FvaResult(
            condition=condition,
            scope=scope,
            fraction_of_optimum=fraction_of_optimum,
            method="cobra_fva",
            solution_status=solution.status,
            objective_value=solution.objective_value,
            reaction_count=len(rows),
            fixed_count=fixed_count,
            narrow_count=narrow_count,
            variable_count=variable_count,
            failed_count=0,
            rows=rows,
            failed_rows=[],
        )

    def run_single_reaction_fva(
        self,
        condition_id: str,
        reaction_id: str,
        fraction_of_optimum: float,
    ) -> dict[str, Any]:
        self._validate_fraction(fraction_of_optimum)
        condition = self.medium_service.get_condition(condition_id)
        if not self._has_reaction(reaction_id):
            raise ValueError(f"Unknown reaction '{reaction_id}'.")

        with self.repository.model_context() as model:
            model.medium = condition.medium
            solution = model.optimize()
            if solution.status != "optimal":
                raise ValueError(f"Base optimization failed with status '{solution.status}'.")

            fix_objective_as_constraint(model, fraction=fraction_of_optimum)
            reaction = model.reactions.get_by_id(reaction_id)
            model.objective = reaction

            model.objective_direction = "min"
            minimum_solution = model.optimize()
            if minimum_solution.status != "optimal":
                raise ValueError(
                    f"Minimum optimization failed for {reaction_id}: {minimum_solution.status}"
                )
            minimum = float(minimum_solution.objective_value)

            model.objective_direction = "max"
            maximum_solution = model.optimize()
            if maximum_solution.status != "optimal":
                raise ValueError(
                    f"Maximum optimization failed for {reaction_id}: {maximum_solution.status}"
                )
            maximum = float(maximum_solution.objective_value)

        row = self._build_fva_reaction_result(
            reaction_id=reaction_id,
            minimum=minimum,
            maximum=maximum,
        )
        return {
            "solution_status": solution.status,
            "objective_value": solution.objective_value,
            "row": row.to_dict(),
        }

    def run_fva_isolated(
        self,
        condition_id: str = "default",
        scope: str = "open_exchange",
        fraction_of_optimum: float = 0.95,
        timeout_seconds: int = 180,
    ) -> dict[str, Any]:
        batch_payload = self._run_fva_worker(
            [
                "--mode",
                "batch",
                "--condition-id",
                condition_id,
                "--scope",
                scope,
                "--fraction-of-optimum",
                str(fraction_of_optimum),
            ],
            timeout_seconds=timeout_seconds,
        )
        if batch_payload.get("ok"):
            return batch_payload

        return self._run_fva_reaction_by_reaction_isolated(
            condition_id=condition_id,
            scope=scope,
            fraction_of_optimum=fraction_of_optimum,
            batch_error=batch_payload,
            timeout_seconds=max(30, timeout_seconds),
        )

    def _run_fva_worker(
        self,
        args: list[str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        project_root = Path(__file__).resolve().parents[2]
        command = [
            sys.executable,
            "-m",
            "yeastmodels_app.services.fva_worker",
            *args,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "error": f"FVA 超时：超过 {timeout_seconds} 秒仍未完成。",
                "stdout": _tail_text(exc.stdout),
                "stderr": _tail_text(exc.stderr),
            }

        marker = "FVA_JSON:"
        payload_line = next(
            (line for line in completed.stdout.splitlines() if line.startswith(marker)),
            None,
        )
        if completed.returncode == 0 and payload_line:
            return {
                "ok": True,
                "result": json.loads(payload_line[len(marker) :]),
            }

        return {
            "ok": False,
            "error": (
                "FVA 子进程异常退出。可能是 GLPK 求解器的底层内存错误，"
                "主应用已保留运行。"
            ),
            "returncode": completed.returncode,
            "stdout": _tail_text(completed.stdout, limit=4000),
            "stderr": _tail_text(completed.stderr, limit=4000),
        }

    def _run_fva_reaction_by_reaction_isolated(
        self,
        condition_id: str,
        scope: str,
        fraction_of_optimum: float,
        batch_error: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        try:
            self._validate_scope(scope)
            self._validate_fraction(fraction_of_optimum)
            condition = self.medium_service.get_condition(condition_id)
        except ValueError as exc:
            return {"ok": False, "error": str(exc), "batch_error": batch_error}

        reaction_ids = self._get_fva_reaction_ids(scope, condition.medium)
        rows: list[FvaReactionResult] = []
        failed_rows: list[FvaReactionFailure] = []
        solution_status = "unknown"
        objective_value: float | None = None

        for reaction_id in reaction_ids:
            payload = self._run_fva_worker(
                [
                    "--mode",
                    "single",
                    "--condition-id",
                    condition_id,
                    "--reaction-id",
                    reaction_id,
                    "--fraction-of-optimum",
                    str(fraction_of_optimum),
                ],
                timeout_seconds=timeout_seconds,
            )
            if payload.get("ok"):
                result = payload["result"]
                solution_status = str(result.get("solution_status", solution_status))
                objective_value = result.get("objective_value", objective_value)
                row_data = result["row"]
                rows.append(
                    FvaReactionResult(
                        reaction_id=row_data["reaction_id"],
                        name=row_data["name"],
                        name_zh=row_data["name_zh"],
                        minimum=float(row_data["minimum"]),
                        maximum=float(row_data["maximum"]),
                        flux_range=float(row_data["flux_range"]),
                        category=row_data["category"],
                        interpretation=row_data["interpretation"],
                    )
                )
            else:
                failed_rows.append(
                    FvaReactionFailure(
                        reaction_id=reaction_id,
                        error=str(payload.get("error", "single reaction FVA failed")),
                    )
                )

        rows.sort(key=lambda row: (row.flux_range, row.reaction_id))
        fixed_count = sum(1 for row in rows if row.category == "固定通量")
        narrow_count = sum(1 for row in rows if row.category == "窄范围")
        variable_count = sum(1 for row in rows if row.category == "可变通量")
        result = FvaResult(
            condition=condition,
            scope=scope,
            fraction_of_optimum=fraction_of_optimum,
            method="safe_single_reaction",
            solution_status=solution_status,
            objective_value=objective_value,
            reaction_count=len(rows),
            fixed_count=fixed_count,
            narrow_count=narrow_count,
            variable_count=variable_count,
            failed_count=len(failed_rows),
            rows=rows,
            failed_rows=failed_rows,
        )

        if not rows and failed_rows:
            return {
                "ok": False,
                "error": "批量 FVA 失败，逐反应 fallback 也未得到可用结果。",
                "batch_error": batch_error,
                "result": result.to_dict(),
            }

        return {
            "ok": True,
            "result": result.to_dict(),
            "fallback_used": True,
            "batch_error": batch_error,
        }

    def _get_fva_reaction_ids(
        self,
        scope: str,
        medium: dict[str, float],
    ) -> list[str]:
        if scope == "open_exchange":
            return sorted(
                reaction_id
                for reaction_id, bound in medium.items()
                if bound > 0 and self._has_reaction(reaction_id)
            )
        if scope == "all_exchange":
            return sorted(reaction.id for reaction in self.model.exchanges)
        if scope == "amino_acid_supply":
            reaction_ids = set()
            for metabolite_id in AMINO_ACID_METABOLITE_IDS:
                producer = self._find_representative_producing_reaction(metabolite_id)
                if producer is not None:
                    reaction_ids.add(producer.id)
            return sorted(reaction_ids)
        return []

    def _build_fva_reaction_result(
        self,
        reaction_id: str,
        minimum: float,
        maximum: float,
    ) -> FvaReactionResult:
        reaction = self.model.reactions.get_by_id(reaction_id)
        flux_range = maximum - minimum
        category = self._classify_range(flux_range)
        return FvaReactionResult(
            reaction_id=reaction_id,
            name=reaction.name,
            name_zh=EXCHANGE_CHINESE_NAMES.get(reaction_id, ""),
            minimum=minimum,
            maximum=maximum,
            flux_range=flux_range,
            category=category,
            interpretation=self._interpret_row(reaction_id, category, minimum, maximum),
        )

    def _classify_range(self, flux_range: float) -> str:
        if abs(flux_range) <= FVA_FIXED_TOLERANCE:
            return "固定通量"
        if abs(flux_range) <= FVA_NARROW_TOLERANCE:
            return "窄范围"
        return "可变通量"

    def _interpret_row(
        self,
        reaction_id: str,
        category: str,
        minimum: float,
        maximum: float,
    ) -> str:
        if category == "固定通量":
            return "在当前最优约束附近几乎没有自由度，可能是被培养基或目标函数锁定的步骤。"
        if category == "窄范围":
            return "通量可调空间很小，后续加入 hLF 后值得观察是否进一步收紧。"
        if minimum < 0 < maximum:
            return "通量可跨过 0，说明该反应方向或使用状态有较大替代空间。"
        if reaction_id.lower().startswith("ex_"):
            return "交换反应有较大范围，说明环境摄取/分泌边界对结果可能敏感。"
        return "通量范围较宽，说明在保持生长目标时模型存在替代路径或调节空间。"

    def _find_representative_producing_reaction(self, metabolite_id: str):
        metabolite = self.model.metabolites.get_by_id(metabolite_id)
        candidates = [
            reaction
            for reaction in metabolite.reactions
            if reaction.metabolites[metabolite] > 0
            and not reaction.id.lower().startswith(("ex_", "dm_"))
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda reaction: (len(reaction.metabolites), reaction.id))[0]

    def _has_reaction(self, reaction_id: str) -> bool:
        try:
            self.model.reactions.get_by_id(reaction_id)
        except KeyError:
            return False
        return True

    def _validate_scope(self, scope: str) -> None:
        if scope not in FVA_SCOPE_OPTIONS:
            available = ", ".join(sorted(FVA_SCOPE_OPTIONS))
            raise ValueError(f"Unknown FVA scope '{scope}'. Available: {available}")

    def _validate_fraction(self, fraction_of_optimum: float) -> None:
        if not 0 < fraction_of_optimum <= 1:
            raise ValueError("fraction_of_optimum must be in (0, 1].")


def _tail_text(value: object, limit: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    return text[-limit:]
