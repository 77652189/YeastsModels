"""Overview page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import artifact_download_buttons


def render_overview(st, service, job_service, result, medium_interpretation) -> None:
    st.subheader("这次运行说明了什么")
    st.markdown(
        f"""
        模型已成功加载，FBA 求解状态为 **{result.solution_status}**。
        当前目标函数是 biomass exchange，因此 **{result.objective_value:.6g}**
        表示在模型当前默认约束下预测得到的最大生长通量。

        这一步是基线可行性检查：它说明 iMT1026 v3 可以被 Python/COBRApy
        正常读取，并且能够得到非零生长解。它还不是 hLF 产量预测，因为模型中尚未加入
        hLF 合成、分泌或折叠负担反应。
        """
    )
    st.table(
        {
            "信号": ["FBA 状态", "目标反应", "目标函数值", "直接结论", "主要限制"],
            "解释": [
                "optimal：线性规划存在可行最优解",
                "biomass exchange：当前优化目标是最大化生长",
                "当前默认约束下的基线生长能力",
                "模型链路已跑通，可以进入受控扰动实验",
                "尚未加入 hLF 负担、分泌、糖基化或培养基设计",
            ],
        }
    )
    st.caption(
        "结果解读由 service 层根据求解状态、目标函数和培养条件解释生成；页面只负责展示。"
    )

    if st.button("保存 FBA 任务", type="primary"):
        with st.spinner("正在运行并保存 FBA..."):
            record = job_service.run_fba_job({})
        st.session_state["selected_job_id"] = record.job_id
        st.success(f"已生成任务：{record.job_id}")
        artifact_download_buttons(st, record.artifacts, f"overview_{record.job_id}")

    with st.expander("术语中文对照"):
        st.table(
            {
                "English term": [
                    "FBA",
                    "objective value",
                    "exchange reaction",
                    "medium",
                    "uptake bound",
                    "biomass exchange",
                ],
                "中文含义": [
                    "通量平衡分析",
                    "目标函数值",
                    "交换反应",
                    "培养基/环境摄取约束",
                    "摄取上限",
                    "生物量目标反应",
                ],
                "在本 Demo 中怎么看": [
                    "用当前模型约束预测最大生长通量",
                    "当前培养条件下的预测生长能力",
                    "连接细胞模型与外部环境的入口/出口",
                    "决定模型能摄取哪些物质",
                    "数值越大，允许摄取越多",
                    "当前优化目标，还不是 hLF 产量",
                ],
            }
        )

    if medium_interpretation.observations:
        st.subheader("自动观察")
        st.table([{"观察": item} for item in medium_interpretation.observations])
