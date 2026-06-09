"""Metabolic network extraction service."""

from __future__ import annotations

from yeastmodels_app.domain import NetworkEdge, NetworkGraph, NetworkNode
from yeastmodels_app.services.constants import AMINO_ACID_METABOLITE_IDS
from yeastmodels_app.services.medium_service import MediumService
from yeastmodels_app.services.model_repository import ModelRepository


class NetworkService:
    """Build readable subgraphs from the full GEM."""

    def __init__(self, repository: ModelRepository, medium_service: MediumService) -> None:
        self.repository = repository
        self.medium_service = medium_service

    @property
    def model(self):
        return self.repository.model

    def get_view_options(self) -> list[dict[str, str]]:
        return [
            {
                "view_id": "exchange_to_biomass",
                "name_zh": "培养基到生物量",
                "name_en": "Exchange to biomass",
                "description": "显示开放摄取项如何进入模型，并连接到当前 biomass 目标。",
            },
            {
                "view_id": "amino_acids_to_hlf_draft",
                "name_zh": "氨基酸到 hLF 草案",
                "name_en": "Amino acids to hLF draft",
                "description": "显示 20 种氨基酸作为 hLF 合成草案的输入。",
            },
            {
                "view_id": "metabolite_neighborhood",
                "name_zh": "代谢物局部邻域",
                "name_en": "Metabolite neighborhood",
                "description": "围绕一个代谢物展示相邻反应和邻近代谢物。",
            },
        ]

    def get_amino_acid_options(self) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for metabolite_id, label in AMINO_ACID_METABOLITE_IDS.items():
            try:
                metabolite = self.model.metabolites.get_by_id(metabolite_id)
            except KeyError:
                continue
            options.append(
                {
                    "metabolite_id": metabolite_id,
                    "label": label,
                    "name": metabolite.name,
                }
            )
        return options

    def build_graph(
        self,
        view_id: str,
        condition_id: str = "default",
        metabolite_id: str = "met_L_c",
    ) -> NetworkGraph:
        if view_id == "exchange_to_biomass":
            return self._build_exchange_to_biomass_graph(condition_id)
        if view_id == "amino_acids_to_hlf_draft":
            return self._build_amino_acids_to_hlf_graph()
        if view_id == "metabolite_neighborhood":
            return self._build_metabolite_neighborhood_graph(metabolite_id)
        available = ", ".join(option["view_id"] for option in self.get_view_options())
        raise ValueError(f"Unknown network view '{view_id}'. Available: {available}")

    def _build_exchange_to_biomass_graph(self, condition_id: str) -> NetworkGraph:
        condition = self.medium_service.get_condition(condition_id)
        nodes: list[NetworkNode] = [
            NetworkNode(
                "environment",
                "培养基/环境",
                "process",
                "模型外部环境，可通过 exchange reaction 向模型供给物质。",
            ),
            NetworkNode(
                "internal_network",
                "iMT1026 v3\n内部代谢网络",
                "process",
                "这里折叠了完整 GEM 中的大量内部反应，避免全图不可读。",
            ),
            NetworkNode(
                "biomass_objective",
                "biomass objective\n生物量目标",
                "objective",
                "当前 FBA 优化目标。",
            ),
        ]
        edges: list[NetworkEdge] = [
            NetworkEdge("internal_network", "biomass_objective", "优化目标"),
        ]

        for reaction_id, bound in sorted(condition.medium.items()):
            if bound <= 0:
                continue
            try:
                reaction = self.model.reactions.get_by_id(reaction_id)
            except KeyError:
                continue
            reaction_node_id = f"rxn_{reaction.id}"
            metabolite = next(iter(reaction.metabolites), None)
            metabolite_node_id = f"met_{metabolite.id}" if metabolite else f"met_{reaction.id}"
            metabolite_label = (
                f"{metabolite.name}\n{metabolite.id}" if metabolite else "未知代谢物"
            )
            nodes.extend(
                [
                    NetworkNode(
                        reaction_node_id,
                        f"{reaction.id}\n{reaction.name}",
                        "exchange",
                        f"开放摄取上限：{bound}",
                    ),
                    NetworkNode(
                        metabolite_node_id,
                        metabolite_label,
                        "metabolite",
                        "exchange reaction 连接的外部/边界代谢物。",
                    ),
                ]
            )
            edges.extend(
                [
                    NetworkEdge("environment", reaction_node_id, f"uptake <= {bound:g}"),
                    NetworkEdge(reaction_node_id, metabolite_node_id, "摄取"),
                    NetworkEdge(metabolite_node_id, "internal_network", "进入模型"),
                ]
            )

        return self._dedupe_graph(
            NetworkGraph(
                graph_id="exchange_to_biomass",
                title=f"{condition.name_zh}：培养基到 biomass 的概念网络",
                description=(
                    "这张图展示当前培养条件开放的摄取项。内部代谢网络被折叠成一个节点，"
                    "避免把 2000 多个反应全部展开。"
                ),
                nodes=nodes,
                edges=edges,
            )
        )

    def _build_amino_acids_to_hlf_graph(self) -> NetworkGraph:
        nodes: list[NetworkNode] = [
            NetworkNode(
                "hlf_synthesis_draft",
                "hLF synthesis draft\n人乳铁蛋白合成草案",
                "protein",
                "占位反应：后续用成熟 hLF 序列统计氨基酸系数。",
            ),
            NetworkNode(
                "hlf_demand",
                "hLF demand / secretion\n产物需求或分泌",
                "objective",
                "后续 FBA/FSEOF 可强制该通量来模拟生产压力。",
            ),
        ]
        edges = [NetworkEdge("hlf_synthesis_draft", "hlf_demand", "产物通量")]

        for metabolite_id, label in AMINO_ACID_METABOLITE_IDS.items():
            try:
                metabolite = self.model.metabolites.get_by_id(metabolite_id)
            except KeyError:
                continue
            amino_node_id = f"aa_{metabolite_id}"
            nodes.append(
                NetworkNode(
                    amino_node_id,
                    f"{label}\n{metabolite.id}",
                    "amino_acid",
                    metabolite.name,
                )
            )
            edges.append(NetworkEdge(amino_node_id, "hlf_synthesis_draft", "消耗"))

            producer = self._find_representative_producing_reaction(metabolite_id)
            if producer is not None:
                reaction_node_id = f"rxn_{producer.id}"
                nodes.append(
                    NetworkNode(
                        reaction_node_id,
                        f"{producer.id}\n{producer.name}",
                        "reaction",
                        "模型中可产生该氨基酸的代表反应之一。",
                    )
                )
                edges.append(NetworkEdge(reaction_node_id, amino_node_id, "生成"))

        return self._dedupe_graph(
            NetworkGraph(
                graph_id="amino_acids_to_hlf_draft",
                title="氨基酸到 hLF 的合成草案",
                description=(
                    "这张图先展示 20 种氨基酸到 hLF 草案反应的关系。"
                    "它不是最终 hLF 化学计量反应；最终版本需要成熟 hLF 序列。"
                ),
                nodes=nodes,
                edges=edges,
            )
        )

    def _build_metabolite_neighborhood_graph(self, metabolite_id: str) -> NetworkGraph:
        try:
            metabolite = self.model.metabolites.get_by_id(metabolite_id)
        except KeyError as exc:
            raise ValueError(f"Unknown metabolite '{metabolite_id}'") from exc

        center_node_id = f"met_{metabolite.id}"
        nodes = [
            NetworkNode(
                center_node_id,
                f"{metabolite.name}\n{metabolite.id}",
                "amino_acid" if metabolite_id in AMINO_ACID_METABOLITE_IDS else "metabolite",
                "当前选中的中心代谢物。",
            )
        ]
        edges: list[NetworkEdge] = []
        connected_reactions = sorted(
            metabolite.reactions,
            key=lambda reaction: (len(reaction.metabolites), reaction.id),
        )[:12]

        for reaction in connected_reactions:
            reaction_node_id = f"rxn_{reaction.id}"
            nodes.append(
                NetworkNode(
                    reaction_node_id,
                    f"{reaction.id}\n{reaction.name}",
                    "reaction",
                    reaction.reaction,
                )
            )
            coefficient = reaction.metabolites[metabolite]
            if coefficient < 0:
                edges.append(NetworkEdge(center_node_id, reaction_node_id, "底物"))
            else:
                edges.append(NetworkEdge(reaction_node_id, center_node_id, "产物"))

            neighbors = [
                item
                for item in reaction.metabolites
                if item.id != metabolite_id and item.compartment == metabolite.compartment
            ][:4]
            for neighbor in neighbors:
                neighbor_node_id = f"met_{neighbor.id}"
                nodes.append(
                    NetworkNode(
                        neighbor_node_id,
                        f"{neighbor.name}\n{neighbor.id}",
                        "metabolite",
                        "与中心代谢物出现在同一反应中的邻近代谢物。",
                    )
                )
                neighbor_coefficient = reaction.metabolites[neighbor]
                if neighbor_coefficient < 0:
                    edges.append(NetworkEdge(neighbor_node_id, reaction_node_id, "底物"))
                else:
                    edges.append(NetworkEdge(reaction_node_id, neighbor_node_id, "产物"))

        return self._dedupe_graph(
            NetworkGraph(
                graph_id=f"metabolite_neighborhood:{metabolite_id}",
                title=f"{metabolite.name} 的局部反应邻域",
                description=(
                    "这张图从 GEM 中抽取中心代谢物相邻的部分反应和邻近代谢物。"
                    "为保持可读性，只展示前 12 个相邻反应。"
                ),
                nodes=nodes,
                edges=edges,
            )
        )

    def _find_representative_producing_reaction(self, metabolite_id: str):
        metabolite = self.model.metabolites.get_by_id(metabolite_id)
        candidates = [
            reaction
            for reaction in metabolite.reactions
            if reaction.metabolites[metabolite] > 0
            and not reaction.id.lower().startswith(("ex_", "dm_"))
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda reaction: (len(reaction.metabolites), reaction.id))[0]

    def _dedupe_graph(self, graph: NetworkGraph) -> NetworkGraph:
        nodes_by_id: dict[str, NetworkNode] = {}
        for node in graph.nodes:
            nodes_by_id.setdefault(node.node_id, node)

        seen_edges: set[tuple[str, str, str]] = set()
        edges: list[NetworkEdge] = []
        for edge in graph.edges:
            key = (edge.source, edge.target, edge.label)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(edge)

        return NetworkGraph(
            graph_id=graph.graph_id,
            title=graph.title,
            description=graph.description,
            nodes=list(nodes_by_id.values()),
            edges=edges,
        )
