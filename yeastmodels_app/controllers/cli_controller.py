"""CLI controller for the iMT1026 v3 FBA demo."""

import sys

from yeastmodels_app.services import YeastModelService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    service = YeastModelService()
    result = service.run_fba()
    medium = service.get_medium_summary()
    summary = result.summary

    print(f"model file: {summary.model_file}")
    print(f"model id: {summary.model_id}")
    print(f"model name: {summary.model_name}")
    print(f"reaction count: {summary.reaction_count}")
    print(f"metabolite count: {summary.metabolite_count}")
    print(f"gene count: {summary.gene_count}")
    print(f"objective: {summary.objective}")
    print(f"solution status: {result.solution_status}")
    print(f"objective value: {result.objective_value}")
    print(f"exchange count: {medium.exchange_count}")
    print(f"open uptake count: {medium.open_uptake_count}")
    print("open uptake reactions / 开放摄取反应:")
    for reaction in medium.open_uptakes:
        name_zh = f"{reaction.name_zh} / " if reaction.name_zh else ""
        print(
            f"  - {reaction.reaction_id}: {name_zh}{reaction.name} "
            f"({reaction.medium_bound})"
        )
    print("medium condition comparison / 培养条件对比:")
    for comparison in service.compare_medium_conditions():
        print(
            f"  - {comparison.condition.name_zh} / {comparison.condition.name_en}: "
            f"{comparison.solution_status}, {comparison.objective_value}"
        )
    fva_payload = service.run_fva_isolated(scope="open_exchange", fraction_of_optimum=0.95)
    print("FVA baseline / 通量变异分析基线:")
    if not fva_payload.get("ok"):
        print(f"  failed: {fva_payload.get('error')}")
        return
    fva_data = fva_payload["result"]
    print(
        f"  condition: {fva_data['condition']['name_zh']} / {fva_data['condition']['name_en']}; "
        f"scope: {fva_data['scope']}; fraction: {fva_data['fraction_of_optimum']}"
    )
    print(
        f"  reactions: {fva_data['reaction_count']}; fixed: {fva_data['fixed_count']}; "
        f"narrow: {fva_data['narrow_count']}; variable: {fva_data['variable_count']}"
    )
    for row in fva_data["rows"][:5]:
        print(
            f"  - {row['reaction_id']}: min={row['minimum']:.6g}, "
            f"max={row['maximum']:.6g}, range={row['flux_range']:.6g}, {row['category']}"
        )
