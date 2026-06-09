"""Network page."""

from __future__ import annotations

from yeastmodels_app.ui.pages.common import artifact_download_buttons, dataframe, graphviz_chart


def render_network(st, service, job_service) -> None:
    st.subheader("代谢网络图")
    st.markdown(
        """
        这里先画可解释的子网络，而不是一次性展开全模型。
        全量 GEM 有两千多个反应，直接画会失去可读性；子网络更适合定位 hLF 建模链路。
        """
    )
    network_views = service.get_network_view_options()
    view_by_id = {view["view_id"]: view for view in network_views}
    selected_view_id = st.selectbox(
        "选择网络视图",
        [view["view_id"] for view in network_views],
        format_func=lambda view_id: (
            f"{view_by_id[view_id]['name_zh']} / {view_by_id[view_id]['name_en']}"
        ),
    )

    graph_condition_id = "default"
    graph_metabolite_id = "met_L_c"
    if selected_view_id == "exchange_to_biomass":
        medium_conditions = service.get_medium_conditions()
        graph_condition = st.selectbox(
            "选择培养条件",
            medium_conditions,
            format_func=lambda condition: f"{condition.name_zh} / {condition.name_en}",
            key="network_condition",
        )
        graph_condition_id = graph_condition.condition_id
    elif selected_view_id == "metabolite_neighborhood":
        amino_acid_options = service.get_amino_acid_options()
        metabolite_option = st.selectbox(
            "选择中心代谢物",
            amino_acid_options,
            format_func=lambda item: f"{item['label']} ({item['metabolite_id']})",
        )
        graph_metabolite_id = metabolite_option["metabolite_id"]

    graph = service.build_network_graph(
        selected_view_id,
        condition_id=graph_condition_id,
        metabolite_id=graph_metabolite_id,
    )
    st.caption(view_by_id[selected_view_id]["description"])
    graph_cols = st.columns(3)
    graph_cols[0].metric("节点数", len(graph.nodes))
    graph_cols[1].metric("边数", len(graph.edges))
    graph_cols[2].metric("视图", view_by_id[selected_view_id]["name_zh"])
    st.markdown(f"**{graph.title}**")
    st.caption(graph.description)
    graphviz_chart(st, graph.to_dot())

    if st.button("保存网络图任务", type="primary"):
        record = job_service.run_network_job(
            {
                "view_id": selected_view_id,
                "condition_id": graph_condition_id,
                "metabolite_id": graph_metabolite_id,
            }
        )
        st.session_state["selected_job_id"] = record.job_id
        st.session_state["network_job_record"] = record
        if record.status == "succeeded":
            st.success(f"网络任务完成：{record.job_id}")
            artifact_download_buttons(st, record.artifacts, f"network_{record.job_id}")
        else:
            st.error(record.error or "网络图任务失败。")

    with st.expander("查看节点与边数据"):
        dataframe(st, [node.to_dict() for node in graph.nodes])
        dataframe(st, [edge.to_dict() for edge in graph.edges])

    st.info(
        "hLF 草案图目前只表达“氨基酸 -> hLF”结构关系。"
        "等确定成熟 hLF 序列后，可以把每种氨基酸的消耗系数写入真实 hLF 合成反应。"
    )
