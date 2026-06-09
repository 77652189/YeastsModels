"""Medium page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import dataframe, format_value


def render_medium(st, service, medium, medium_comparisons, medium_interpretation) -> None:
    import pandas as pd

    st.subheader("默认培养基与边界条件")
    st.markdown(
        """
        FBA 的 objective value 强烈依赖 exchange reaction 的上下界。
        这些边界定义了模型可以从环境中摄取什么、最多摄取多少，以及可以向环境中分泌什么。

        当前 iMT1026 v3 的默认 medium 是模型文件中已经开放的摄取约束；
        后续比较 hLF 产量时，需要显式设置培养条件。
        """
    )

    medium_cols = st.columns(3)
    medium_cols[0].metric("交换反应总数", medium.exchange_count)
    medium_cols[1].metric("开放摄取项", medium.open_uptake_count)
    medium_cols[2].metric("允许分泌项", medium.secretion_allowed_count)

    st.subheader("培养条件 FBA 对比")
    default_value = next(
        (
            comparison.objective_value
            for comparison in medium_comparisons
            if comparison.condition.condition_id == "default"
        ),
        None,
    )
    insights_by_condition = {
        insight.condition_id: insight for insight in medium_interpretation.insights
    }
    comparison_rows = []
    for comparison in medium_comparisons:
        value = comparison.objective_value
        delta = value - default_value if value is not None and default_value not in (None, 0) else None
        insight = insights_by_condition.get(comparison.condition.condition_id)
        comparison_rows.append(
            {
                "培养条件（中文）": comparison.condition.name_zh,
                "Condition (English)": comparison.condition.name_en,
                "条件 ID": comparison.condition.condition_id,
                "状态": comparison.solution_status,
                "growth objective": value,
                "相对默认变化": delta,
                "角色": insight.role if insight else "",
                "结果解读": insight.takeaway if insight else "",
                "建议动作": insight.next_action if insight else "",
            }
        )
    comparison_df = pd.DataFrame(comparison_rows)
    st.table(comparison_df)
    st.bar_chart(comparison_df, x="培养条件（中文）", y="growth objective")
    st.caption(
        "说明：glucose、glycerol、methanol 的摄取上限按通量数值设置，尚未按碳原子数或实验补料速率归一化。"
    )

    valid_comparisons = [
        comparison for comparison in medium_comparisons if comparison.objective_value is not None
    ]
    if valid_comparisons:
        best = next(
            (
                comparison
                for comparison in valid_comparisons
                if comparison.condition.condition_id == medium_interpretation.best_condition_id
            ),
            max(valid_comparisons, key=lambda item: item.objective_value or 0),
        )
        lowest = next(
            (
                comparison
                for comparison in valid_comparisons
                if comparison.condition.condition_id == medium_interpretation.lowest_condition_id
            ),
            min(valid_comparisons, key=lambda item: item.objective_value or 0),
        )
        st.subheader("这张图应该怎么读")
        insight_cols = st.columns(3)
        insight_cols[0].metric("预测生长最高", best.condition.name_zh, format_value(best.objective_value))
        insight_cols[1].metric("预测生长最低", lowest.condition.name_zh, format_value(lowest.objective_value))
        insight_cols[2].metric(
            "hLF 重点场景",
            f"{len(medium_interpretation.hlf_focus_condition_ids)} 个条件",
            "由培养基组成推导",
        )
        st.table([{"自动观察": observation} for observation in medium_interpretation.observations])

    st.subheader("查看单个培养条件的 exchange 设置")
    selected_condition = st.selectbox(
        "选择培养条件",
        [comparison.condition for comparison in medium_comparisons],
        format_func=lambda condition: f"{condition.name_zh} / {condition.name_en}",
    )
    st.caption(selected_condition.description)
    exchange_by_id = {reaction.reaction_id: reaction for reaction in medium.all_exchanges}
    dataframe(
        st,
        [
            {
                "反应 ID": reaction_id,
                "中文名称": exchange_by_id.get(reaction_id).name_zh if reaction_id in exchange_by_id else "",
                "English name": exchange_by_id.get(reaction_id).name if reaction_id in exchange_by_id else "",
                "摄取上限": bound,
            }
            for reaction_id, bound in sorted(selected_condition.medium.items())
        ],
    )

    st.subheader("当前开放摄取项")
    dataframe(
        st,
        [
            {
                "反应 ID": reaction.reaction_id,
                "中文名称": reaction.name_zh,
                "English name": reaction.name,
                "摄取上限": reaction.medium_bound,
                "lower bound": reaction.lower_bound,
                "upper bound": reaction.upper_bound,
            }
            for reaction in medium.open_uptakes
        ],
    )

    with st.expander("查看所有 exchange reactions"):
        dataframe(
            st,
            [
                {
                    "反应 ID": reaction.reaction_id,
                    "中文名称": reaction.name_zh,
                    "English name": reaction.name,
                    "lower bound": reaction.lower_bound,
                    "upper bound": reaction.upper_bound,
                    "可摄取": reaction.can_uptake,
                    "可分泌": reaction.can_secrete,
                }
                for reaction in medium.all_exchanges
            ],
        )
