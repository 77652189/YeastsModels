"""Shared Streamlit page helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def format_value(value: float | None) -> str:
    if value is None:
        return "不可用"
    return f"{value:.6g}"


def dataframe(st, data: Any, hide_index: bool = True) -> None:
    try:
        st.dataframe(data, width="stretch", hide_index=hide_index)
    except TypeError:
        st.dataframe(data)


def graphviz_chart(st, dot: str) -> None:
    try:
        st.graphviz_chart(dot, width="stretch")
    except TypeError:
        st.graphviz_chart(dot)


def artifact_download_buttons(st, artifacts: list[Any], key_prefix: str) -> None:
    for artifact in artifacts:
        path = Path(artifact.path)
        if not path.exists():
            st.caption(f"未找到文件：{path}")
            continue
        st.download_button(
            artifact.label,
            data=path.read_bytes(),
            file_name=path.name,
            mime=_mime_for_format(artifact.format),
            key=f"{key_prefix}_{artifact.format}_{path.name}",
        )


def _mime_for_format(file_format: str) -> str:
    return {
        "json": "application/json",
        "csv": "text/csv",
        "dot": "text/vnd.graphviz",
    }.get(file_format, "application/octet-stream")
