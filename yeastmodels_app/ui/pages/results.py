"""Results list page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import dataframe


def render_results(st, job_service) -> None:
    st.subheader("Results 任务列表")
    st.caption("所有 FBA/FVA/network 运行都会写入本地 JSON 任务记录。")
    jobs = job_service.list_jobs(limit=200)
    if not jobs:
        st.info("还没有任务记录。可以先在 Overview 保存 FBA，或在 FVA/Network 页面运行分析。")
        return

    rows = [
        {
            "job_id": job.job_id,
            "created_at": job.created_at,
            "analysis_type": job.analysis_type,
            "status": job.status,
            "model_id": job.model_id,
            "summary": _short_summary(job.summary),
        }
        for job in jobs
    ]
    dataframe(st, rows)
    selected_job_id = st.selectbox(
        "选择要查看的任务",
        [job.job_id for job in jobs],
        index=_default_job_index(jobs, st.session_state.get("selected_job_id")),
    )
    st.session_state["selected_job_id"] = selected_job_id
    st.success("已选择任务，可切换到 Details 查看详情和下载。")


def _default_job_index(jobs, selected_job_id: str | None) -> int:
    if selected_job_id is None:
        return 0
    for index, job in enumerate(jobs):
        if job.job_id == selected_job_id:
            return index
    return 0


def _short_summary(summary: dict[str, object]) -> str:
    parts = []
    for key in ("solution_status", "objective_value", "reaction_count", "node_count", "edge_count", "method"):
        if key in summary:
            parts.append(f"{key}={summary[key]}")
    return "; ".join(parts) if parts else str(summary)[:120]
