"""Medium presets, summaries, and interpretation."""

from __future__ import annotations

from yeastmodels_app.domain import (
    ExchangeReaction,
    MediumComparisonInterpretation,
    MediumCondition,
    MediumConditionInsight,
    MediumSummary,
)
from yeastmodels_app.domain.fba import MediumFbaResult
from yeastmodels_app.services.constants import (
    CARBON_EXCHANGE_IDS,
    EXCHANGE_CHINESE_NAMES,
    OBJECTIVE_RANK_TOLERANCE,
)
from yeastmodels_app.services.model_repository import ModelRepository


class MediumService:
    def __init__(self, repository: ModelRepository) -> None:
        self.repository = repository

    @property
    def model(self):
        return self.repository.model

    def get_summary(self) -> MediumSummary:
        medium = self.model.medium
        exchanges = [
            ExchangeReaction(
                reaction_id=reaction.id,
                name=reaction.name,
                name_zh=EXCHANGE_CHINESE_NAMES.get(reaction.id, ""),
                lower_bound=float(reaction.lower_bound),
                upper_bound=float(reaction.upper_bound),
                medium_bound=medium.get(reaction.id),
                can_uptake=reaction.lower_bound < 0,
                can_secrete=reaction.upper_bound > 0,
            )
            for reaction in self.model.exchanges
        ]
        exchanges.sort(key=lambda reaction: reaction.reaction_id)
        open_uptakes = [
            reaction for reaction in exchanges if reaction.medium_bound is not None
        ]
        return MediumSummary(
            exchange_count=len(exchanges),
            open_uptake_count=len(open_uptakes),
            secretion_allowed_count=sum(1 for reaction in exchanges if reaction.can_secrete),
            open_uptakes=open_uptakes,
            all_exchanges=exchanges,
        )

    def get_conditions(self) -> list[MediumCondition]:
        base_medium = self.model.medium.copy()
        non_carbon_medium = {
            reaction_id: bound
            for reaction_id, bound in base_medium.items()
            if reaction_id not in CARBON_EXCHANGE_IDS
        }
        return [
            MediumCondition(
                condition_id="default",
                name="默认培养基 (Default medium)",
                name_zh="默认培养基",
                name_en="Default medium",
                description="模型文件中的默认边界条件；当前主要碳源为 glycerol。",
                medium=base_medium,
            ),
            MediumCondition(
                condition_id="glycerol",
                name="甘油 (Glycerol)",
                name_zh="甘油",
                name_en="Glycerol",
                description="仅开放 glycerol 作为碳源，摄取上限为 1。",
                medium={**non_carbon_medium, "Ex_glyc": 1.0},
            ),
            MediumCondition(
                condition_id="glucose",
                name="葡萄糖 (Glucose)",
                name_zh="葡萄糖",
                name_en="Glucose",
                description="仅开放 D-glucose 作为碳源，摄取上限为 1。",
                medium={**non_carbon_medium, "Ex_glc_D": 1.0},
            ),
            MediumCondition(
                condition_id="methanol",
                name="甲醇 (Methanol)",
                name_zh="甲醇",
                name_en="Methanol",
                description="仅开放 methanol 作为碳源，摄取上限为 1。",
                medium={**non_carbon_medium, "Ex_meoh": 1.0},
            ),
            MediumCondition(
                condition_id="glycerol_methanol",
                name="甘油 + 甲醇 (Glycerol + Methanol)",
                name_zh="甘油 + 甲醇",
                name_en="Glycerol + Methanol",
                description="glycerol 与 methanol 共喂养，各自摄取上限为 0.5。",
                medium={**non_carbon_medium, "Ex_glyc": 0.5, "Ex_meoh": 0.5},
            ),
            MediumCondition(
                condition_id="oxygen_limited_glycerol",
                name="氧限制甘油 (Oxygen-limited Glycerol)",
                name_zh="氧限制甘油",
                name_en="Oxygen-limited Glycerol",
                description="glycerol 摄取上限为 1，氧气摄取上限降为 0.5。",
                medium={**non_carbon_medium, "Ex_glyc": 1.0, "Ex_o2": 0.5},
            ),
        ]

    def get_condition(self, condition_id: str) -> MediumCondition:
        conditions = {condition.condition_id: condition for condition in self.get_conditions()}
        if condition_id not in conditions:
            available = ", ".join(sorted(conditions))
            raise ValueError(f"Unknown medium condition '{condition_id}'. Available: {available}")
        return conditions[condition_id]

    def interpret_comparisons(
        self, comparisons: list[MediumFbaResult]
    ) -> MediumComparisonInterpretation:
        valid_results = [
            comparison
            for comparison in comparisons
            if comparison.objective_value is not None
        ]
        ranked_results = sorted(
            valid_results,
            key=lambda comparison: comparison.objective_value or 0,
            reverse=True,
        )
        ranks = self._rank_results(ranked_results)
        best = ranked_results[0] if ranked_results else None
        lowest = ranked_results[-1] if ranked_results else None
        insights = [
            self._build_condition_insight(
                comparison=comparison,
                rank=ranks.get(comparison.condition.condition_id),
                total=len(ranked_results),
            )
            for comparison in comparisons
        ]
        hlf_focus_condition_ids = [
            insight.condition_id
            for insight in insights
            if "甲醇" in insight.role or "氧限制" in insight.role
        ]

        observations: list[str] = []
        if best is not None:
            observations.append(
                f"{best.condition.name_zh}在本次设置中给出最高 biomass objective。"
            )
        if lowest is not None and best is not lowest:
            observations.append(
                f"{lowest.condition.name_zh}给出最低 biomass objective，需要关注限制因素。"
            )
        if hlf_focus_condition_ids:
            observations.append(
                "含甲醇或氧限制的条件更接近后续 hLF 诱导/瓶颈分析场景。"
            )

        return MediumComparisonInterpretation(
            best_condition_id=best.condition.condition_id if best else None,
            lowest_condition_id=lowest.condition.condition_id if lowest else None,
            hlf_focus_condition_ids=hlf_focus_condition_ids,
            observations=observations,
            insights=insights,
        )

    def _rank_results(self, ranked_results: list[MediumFbaResult]) -> dict[str, int]:
        ranks: dict[str, int] = {}
        previous_value: float | None = None
        previous_rank = 0
        for index, comparison in enumerate(ranked_results, start=1):
            value = comparison.objective_value
            if (
                previous_value is not None
                and value is not None
                and abs(value - previous_value) <= OBJECTIVE_RANK_TOLERANCE
            ):
                rank = previous_rank
            else:
                rank = index
            ranks[comparison.condition.condition_id] = rank
            previous_rank = rank
            previous_value = value
        return ranks

    def _build_condition_insight(
        self,
        comparison: MediumFbaResult,
        rank: int | None,
        total: int,
    ) -> MediumConditionInsight:
        medium = comparison.condition.medium
        has_glycerol = medium.get("Ex_glyc", 0) > 0
        has_glucose = medium.get("Ex_glc_D", 0) > 0
        has_methanol = medium.get("Ex_meoh", 0) > 0
        oxygen_bound = medium.get("Ex_o2")
        is_oxygen_limited = oxygen_bound is not None and oxygen_bound <= 0.5

        role_parts: list[str] = []
        if has_methanol and has_glycerol:
            role_parts.append("甲醇共喂养候选")
        elif has_methanol:
            role_parts.append("甲醇诱导候选")
        elif has_glucose:
            role_parts.append("高生长碳源对照")
        elif has_glycerol:
            role_parts.append("甘油生长基线")
        else:
            role_parts.append("模型默认基线")
        if is_oxygen_limited:
            role_parts.append("氧限制压力测试")
        role = " / ".join(role_parts)

        rank_text = f"排名第 {rank}/{total}" if rank is not None and total else "无排名"
        if comparison.solution_status != "optimal":
            takeaway = f"求解状态为 {comparison.solution_status}，不应直接比较 objective。"
            next_action = "先检查该培养条件的 exchange bounds 是否导致模型不可行。"
        elif comparison.objective_value is None:
            takeaway = "未得到 objective value，暂时无法判断该条件的生长表现。"
            next_action = "先确认求解器返回值，再纳入 hLF 场景比较。"
        elif has_methanol:
            takeaway = (
                f"{rank_text}；含甲醇，生长值可作为 AOX1 诱导场景的基线，"
                "但不能直接等同于 hLF 产量。"
            )
            next_action = "优先在该条件下加入 hLF demand，观察生长-生产权衡。"
        elif is_oxygen_limited:
            takeaway = f"{rank_text}；氧摄取被限制，可用于观察供氧不足对生长的影响。"
            next_action = "增加不同氧摄取上限扫描，判断氧是否会成为 hLF 场景瓶颈。"
        elif has_glucose:
            takeaway = f"{rank_text}；如果生长较高，它更适合作为生长能力对照。"
            next_action = "保留为对照，不直接把最高 biomass 解读为最高 hLF 生产。"
        elif has_glycerol:
            takeaway = f"{rank_text}；甘油条件适合作为诱导前或非诱导生产前基线。"
            next_action = "与甲醇或共喂养条件并列比较，区分生长阶段和诱导阶段。"
        else:
            takeaway = f"{rank_text}；这是模型文件默认开放摄取条件的表现。"
            next_action = "用作基线检查，后续用显式培养基替代默认 medium。"

        return MediumConditionInsight(
            condition_id=comparison.condition.condition_id,
            rank=rank,
            role=role,
            takeaway=takeaway,
            next_action=next_action,
        )
