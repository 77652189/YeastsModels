"""Job details page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import artifact_download_buttons, dataframe, graphviz_chart


def render_details(st, job_service) -> None:
    st.subheader("Details 任务详情")
    jobs = job_service.list_jobs(limit=200)
    if not jobs:
        st.info("还没有任务记录。")
        return

    job_ids = [job.job_id for job in jobs]
    selected_job_id = st.session_state.get("selected_job_id")
    index = job_ids.index(selected_job_id) if selected_job_id in job_ids else 0
    selected_job_id = st.selectbox("任务 ID", job_ids, index=index, key="details_job_id")
    st.session_state["selected_job_id"] = selected_job_id
    job = job_service.get_job(selected_job_id)
    if job is None:
        st.error("任务记录不存在或 JSON 已损坏。")
        return

    cols = st.columns(4)
    cols[0].metric("类型", job.analysis_type)
    cols[1].metric("状态", job.status)
    cols[2].metric("模型", job.model_id)
    cols[3].metric("Artifacts", len(job.artifacts))
    st.caption(job.created_at)

    if job.error:
        st.error(job.error)
    if job.logs_tail:
        with st.expander("诊断日志"):
            st.code(job.logs_tail[-4000:], language="text")

    st.subheader("参数")
    st.json(job.parameters)
    st.subheader("摘要")
    st.json(job.summary)

    if job.result:
        _render_result_preview(st, job.analysis_type, job.result)

    st.subheader("下载")
    artifact_download_buttons(st, job.artifacts, f"details_{job.job_id}")

    with st.expander("完整 JobRecord JSON"):
        st.json(job.to_dict())


def _render_result_preview(st, analysis_type: str, result: dict[str, object]) -> None:
    if analysis_type == "fva":
        rows = result.get("rows", [])
        failed_rows = result.get("failed_rows", [])
        st.subheader("FVA rows")
        dataframe(st, rows)
        if failed_rows:
            st.subheader("Failed rows")
            dataframe(st, failed_rows)
    elif analysis_type == "network":
        dot = str(result.get("dot", ""))
        if dot:
            st.subheader("Network graph")
            graphviz_chart(st, dot)
        st.subheader("Nodes")
        dataframe(st, result.get("nodes", []))
        st.subheader("Edges")
        dataframe(st, result.get("edges", []))
    else:
        st.subheader("Result")
        st.json(result)
