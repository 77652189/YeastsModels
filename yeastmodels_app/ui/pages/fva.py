"""FVA page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import artifact_download_buttons, dataframe, format_value


def render_fva(st, service, job_service) -> None:
    import pandas as pd

    st.subheader("FVA 基线分析")
    st.markdown(
        """
        FBA 只给出一个最优解；FVA 会在保持一定 biomass optimum 的前提下，
        计算每个反应允许的最小和最大通量。这里继续使用子进程隔离和逐反应 fallback，
        避免 GLPK 底层错误拖垮主页面。
        """
    )
    fva_conditions = service.get_medium_conditions()
    fva_condition = st.selectbox(
        "选择培养条件",
        fva_conditions,
        format_func=lambda condition: f"{condition.name_zh} / {condition.name_en}",
        key="fva_condition",
    )
    fva_scope_options = service.get_fva_scope_options()
    scope_by_id = {option["scope"]: option for option in fva_scope_options}
    fva_scope = st.selectbox(
        "选择 FVA 范围",
        [option["scope"] for option in fva_scope_options],
        format_func=lambda scope: f"{scope_by_id[scope]['name_zh']} ({scope})",
    )
    fraction_of_optimum = st.slider(
        "保持 biomass optimum 的比例",
        min_value=0.50,
        max_value=1.00,
        value=0.95,
        step=0.05,
        help="0.95 表示至少保留 95% 的最优生长能力，再看反应通量范围。",
    )

    if st.button("运行 FVA 并保存任务", type="primary"):
        with st.spinner("正在运行 FVA..."):
            record = job_service.run_fva_job(
                {
                    "condition_id": fva_condition.condition_id,
                    "scope": fva_scope,
                    "fraction_of_optimum": fraction_of_optimum,
                }
            )
        st.session_state["selected_job_id"] = record.job_id
        st.session_state["fva_job_record"] = record
        if record.status == "failed":
            st.error(record.error or "FVA 运行失败。")
        elif record.status == "partial":
            st.warning(f"FVA 部分完成：{record.job_id}")
        else:
            st.success(f"FVA 任务完成：{record.job_id}")

    record = st.session_state.get("fva_job_record")
    if record is not None and record.result:
        _render_fva_result(st, record.result)
        artifact_download_buttons(st, record.artifacts, f"fva_{record.job_id}")
    else:
        st.info("选择参数后点击“运行 FVA 并保存任务”。结果会写入 Results，并可在 Details 下载。")


def _render_fva_result(st, fva_result: dict[str, object]) -> None:
    import pandas as pd

    fva_cols = st.columns(6)
    fva_cols[0].metric("求解状态", fva_result["solution_status"])
    fva_cols[1].metric("biomass objective", format_value(fva_result["objective_value"]))
    fva_cols[2].metric("反应数", fva_result["reaction_count"])
    fva_cols[3].metric("固定/窄范围", f"{fva_result['fixed_count']} / {fva_result['narrow_count']}")
    fva_cols[4].metric("可变通量", fva_result["variable_count"])
    fva_cols[5].metric("失败反应", fva_result.get("failed_count", 0))
    st.caption(f"FVA 执行方法：{fva_result.get('method', 'unknown')}")

    fva_rows = fva_result.get("rows", [])
    fva_df = pd.DataFrame(fva_rows)
    st.subheader("FVA 结果表")
    dataframe(st, fva_df)

    if not fva_df.empty:
        columns = [
            "reaction_id",
            "name_zh",
            "name",
            "minimum",
            "maximum",
            "flux_range",
            "category",
            "interpretation",
        ]
        st.subheader("最受约束的反应")
        st.table(fva_df.sort_values(["flux_range", "reaction_id"]).head(10)[columns])
        st.subheader("通量范围最大的反应")
        st.table(
            fva_df.sort_values(["flux_range", "reaction_id"], ascending=[False, True])
            .head(10)[columns]
        )

    failed_rows = fva_result.get("failed_rows", [])
    if failed_rows:
        st.warning("部分反应在逐反应 fallback 中仍然失败，下面列出失败项。")
        dataframe(st, failed_rows)

    st.info(
        "FVA 的重点不是单个通量值，而是范围。范围很窄说明在当前目标附近自由度小；"
        "范围很宽说明模型可能存在替代路径。后续加入 hLF demand 后，可以比较这些范围是否收紧。"
    )
