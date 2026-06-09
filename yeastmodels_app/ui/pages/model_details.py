"""Model details page."""

from __future__ import annotations


def render_model_details(st, summary, result) -> None:
    st.subheader("这些计数为什么重要")
    count_cols = st.columns(3)
    count_cols[0].markdown(f"**{summary.reaction_count} 个反应**\n\nFBA 可使用的代谢转化、转运和交换步骤。")
    count_cols[1].markdown(f"**{summary.metabolite_count} 个代谢物**\n\n由化学计量矩阵约束和平衡的化学物种。")
    count_cols[2].markdown(f"**{summary.gene_count} 个基因**\n\n后续 knockout、FVA、FSEOF 和候选基因分析的基础。")

    st.subheader("已加载模型")
    st.table(
        {
            "字段": ["文件", "ID", "名称", "目标函数", "求解状态"],
            "值": [
                summary.model_file,
                summary.model_id,
                summary.model_name,
                summary.objective,
                result.solution_status,
            ],
        }
    )
