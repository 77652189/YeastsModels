"""hLF model preparation service.

This service intentionally does not create a real hLF reaction before the
sequence and modeling assumptions are available.
"""

from __future__ import annotations

from typing import Any


class HlfPreparationService:
    """Expose the hLF modeling contract for the UI/API."""

    def get_preparation_summary(self) -> dict[str, Any]:
        return {
            "status": "waiting_for_sequence",
            "can_create_reaction": False,
            "message": "暂未提供成熟 hLF 序列，因此 v1 不生成真实 hLF demand reaction。",
            "required_inputs": [
                {
                    "name": "成熟 hLF 蛋白序列",
                    "why": "用于统计 20 种氨基酸的化学计量系数。",
                },
                {
                    "name": "是否模拟分泌",
                    "why": "决定第一版使用 demand reaction，还是增加分泌/转运近似。",
                },
                {
                    "name": "糖基化与折叠假设",
                    "why": "决定是否加入额外前体、能量和 ER 负担项。",
                },
                {
                    "name": "生产目标定义",
                    "why": "决定后续 FBA/FVA/FSEOF 是固定 hLF 通量还是最大化 hLF。",
                },
            ],
            "recommended_v1_assumptions": [
                "优先使用成熟 hLF 蛋白序列，不把信号肽混入第一版反应。",
                "第一版先构造 demand reaction，验证模型能否承载 hLF 氨基酸需求。",
                "第一版先不加入糖基化和折叠负担，避免假设过多导致结果难解释。",
                "在 glycerol、methanol、glycerol + methanol、oxygen-limited 条件下并列比较。",
            ],
            "future_contract": {
                "input": {
                    "protein_sequence": "str",
                    "include_secretion": "bool",
                    "include_glycosylation": "bool",
                    "atp_cost_per_residue": "float | None",
                },
                "output": {
                    "reaction_id": "HLF_SYNTHESIS_DRAFT",
                    "stoichiometry": "dict[metabolite_id, coefficient]",
                    "warnings": "list[str]",
                },
            },
        }
