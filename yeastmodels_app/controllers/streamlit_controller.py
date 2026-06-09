"""Streamlit controller for iMT1026 v3 analyses."""

from yeastmodels_app.services import JobService, YeastModelService
from yeastmodels_app.ui.pages.details import render_details
from yeastmodels_app.ui.pages.fva import render_fva
from yeastmodels_app.ui.pages.hlf_preparation import render_hlf_preparation
from yeastmodels_app.ui.pages.medium import render_medium
from yeastmodels_app.ui.pages.model_details import render_model_details
from yeastmodels_app.ui.pages.network import render_network
from yeastmodels_app.ui.pages.overview import render_overview
from yeastmodels_app.ui.pages.results import render_results


def render() -> None:
    import streamlit as st

    @st.cache_resource
    def get_services() -> tuple[YeastModelService, JobService]:
        analysis_service = YeastModelService()
        return analysis_service, JobService(analysis_service=analysis_service)

    service, job_service = get_services()
    result = service.run_fba()
    summary = result.summary
    medium = service.get_medium_summary()
    medium_comparisons = service.compare_medium_conditions()
    medium_interpretation = service.interpret_medium_comparisons(medium_comparisons)

    st.set_page_config(page_title="iMT1026 v3 Pichia GEM", layout="wide")
    st.title("iMT1026 v3 Pichia GEM")
    st.caption(
        "本机单用户研究工作台：FBA/FVA/network 共用同一套计算逻辑，"
        "每次任务可追踪、可查看详情、可下载结果。"
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("反应数", summary.reaction_count)
    metric_cols[1].metric("代谢物数", summary.metabolite_count)
    metric_cols[2].metric("基因数", summary.gene_count)
    metric_cols[3].metric("目标函数值", f"{result.objective_value:.6g}")

    st.divider()

    tabs = st.tabs(
        [
            "Overview",
            "Medium",
            "FVA",
            "Network",
            "Results",
            "Details",
            "Model",
            "hLF Preparation",
        ]
    )

    with tabs[0]:
        render_overview(st, service, job_service, result, medium_interpretation)
    with tabs[1]:
        render_medium(st, service, medium, medium_comparisons, medium_interpretation)
    with tabs[2]:
        render_fva(st, service, job_service)
    with tabs[3]:
        render_network(st, service, job_service)
    with tabs[4]:
        render_results(st, job_service)
    with tabs[5]:
        render_details(st, job_service)
    with tabs[6]:
        render_model_details(st, summary, result)
    with tabs[7]:
        render_hlf_preparation(st, service)
