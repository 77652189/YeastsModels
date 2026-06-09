"""hLF preparation page."""

from __future__ import annotations


def render_hlf_preparation(st, service) -> None:
    preparation = service.get_hlf_preparation_summary()
    st.subheader("hLF Preparation")
    st.info(preparation["message"])

    st.subheader("当前接口状态")
    st.table(
        {
            "字段": ["status", "can_create_reaction"],
            "值": [str(preparation["status"]), str(preparation["can_create_reaction"])],
        }
    )

    st.subheader("加入 hLF 前需要补齐")
    st.table(preparation["required_inputs"])

    st.subheader("建议 v1 建模假设")
    st.table([{"建议": item} for item in preparation["recommended_v1_assumptions"]])

    st.subheader("未来接口契约")
    st.json(preparation["future_contract"])

    st.warning(
        "当前版本不会修改模型 XML，也不会硬编码 hLF 反应。等成熟 hLF 序列确定后，再生成可审阅的反应草案。"
    )
