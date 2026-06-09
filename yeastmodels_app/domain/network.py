"""Network graph domain objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class NetworkNode:
    node_id: str
    label: str
    node_type: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NetworkEdge:
    source: str
    target: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NetworkGraph:
    graph_id: str
    title: str
    description: str
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "title": self.title,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_dot(self) -> str:
        lines = [
            "digraph metabolic_network {",
            "  graph [rankdir=LR, bgcolor=\"transparent\", pad=\"0.25\", nodesep=\"0.45\", ranksep=\"0.75\"];",
            "  node [shape=box, style=\"rounded,filled\", fontname=\"Microsoft YaHei\", fontsize=11, color=\"#5b6472\", fillcolor=\"#ffffff\"];",
            "  edge [fontname=\"Microsoft YaHei\", fontsize=9, color=\"#6b7280\", arrowsize=0.7];",
        ]
        for node in self.nodes:
            fill_color, shape = _node_style(node.node_type)
            lines.append(
                "  "
                f"{_dot_id(node.node_id)} "
                f"[label=\"{_dot_escape(node.label)}\", "
                f"tooltip=\"{_dot_escape(node.description)}\", "
                f"fillcolor=\"{fill_color}\", shape=\"{shape}\"];"
            )
        for edge in self.edges:
            label = f" [label=\"{_dot_escape(edge.label)}\"]" if edge.label else ""
            lines.append(f"  {_dot_id(edge.source)} -> {_dot_id(edge.target)}{label};")
        lines.append("}")
        return "\n".join(lines)


def _dot_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    if not safe or safe[0].isdigit():
        safe = f"n_{safe}"
    return safe


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _node_style(node_type: str) -> tuple[str, str]:
    styles = {
        "exchange": ("#e0f2fe", "box"),
        "reaction": ("#eef2ff", "box"),
        "metabolite": ("#dcfce7", "ellipse"),
        "amino_acid": ("#fef3c7", "ellipse"),
        "protein": ("#fee2e2", "box"),
        "objective": ("#f3e8ff", "box"),
        "process": ("#f8fafc", "box"),
    }
    return styles.get(node_type, ("#ffffff", "box"))
