from dataclasses import dataclass
from typing import Dict, Set, List, Any

import networkx as nx


@dataclass
class DependencyGraphFacts:
    """Dependency graph facts used for impact and blast-radius analysis."""

    graph: nx.DiGraph
    nodes: Dict[str, Dict[str, Any]]
    edges: List[tuple]


class DependencyGraphBuilder:
    """
    Build and query a dependency graph for blast-radius analysis.

    Supported dependency types:
    - calls
    - imports
    - field_reference

    Graph direction:

        caller       -> callee
        source       -> imported module
        class        -> referenced field/type

    For blast-radius analysis, the graph is traversed backwards
    from the changed node because callers/consumers are the
    potential impacted components.
    """

    # ------------------------------------------------------------------
    # Dependency relationship weights
    # ------------------------------------------------------------------

    RELATION_WEIGHTS = {
        "calls": 1.0,
        "field_reference": 0.8,
        "imports": 0.3,
    }

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self):
        self.graph = nx.DiGraph()

        # node_id -> metadata
        self.nodes: Dict[str, Dict[str, Any]] = {}

        # Unique (source, target) pairs
        self.edges: List[tuple] = []

    # ------------------------------------------------------------------
    # Node helpers
    # ------------------------------------------------------------------

    def _build_node_id(self, entity_name: str, entity_type: str) -> str:
        """Build a stable graph node identifier."""
        return f"{entity_type}:{entity_name}"

    def add_entity(
        self,
        entity_name: str,
        entity_type: str,
        file_path: str = "",
    ) -> str:
        """
        Add an entity node to the graph.

        Args:
            entity_name: Name of class/function/module/entity.
            entity_type: Type of node, e.g. class, function, module.
            file_path: Source file containing the entity.

        Returns:
            The generated node ID.
        """

        node_id = self._build_node_id(
            entity_name=entity_name,
            entity_type=entity_type,
        )

        metadata = {
            "type": entity_type,
            "name": entity_name,
            "file": file_path,
        }

        self.graph.add_node(
            node_id,
            **metadata,
        )

        self.nodes[node_id] = metadata

        return node_id

    # ------------------------------------------------------------------
    # Edge helpers
    # ------------------------------------------------------------------

    def _add_dependency_edge(
        self,
        source: str,
        target: str,
        relation: str,
        **metadata,
    ) -> None:
        """
        Add a dependency edge with relationship metadata.

        Graph direction:

            source -> target

        Example:

            OrderService -> SkuService
            relation = calls
        """

        if source not in self.graph:
            return

        if target not in self.graph:
            return

        edge_key = (source, target)

        if edge_key not in self.edges:
            self.edges.append(edge_key)

        self.graph.add_edge(
            source,
            target,
            relation=relation,
            weight=self.RELATION_WEIGHTS.get(
                relation,
                0.5,
            ),
            **metadata,
        )

    def add_call_edge(
        self,
        caller: str,
        callee: str,
        line_number: int = 0,
    ) -> None:
        """
        Add a function/method call dependency.

        Example:

            OrderService.process()
                -> SkuService.validate()
        """

        self._add_dependency_edge(
            source=caller,
            target=callee,
            relation="calls",
            line=line_number,
        )

    def add_import_edge(
        self,
        source: str,
        target: str,
    ) -> None:
        """
        Add a module import dependency.

        Example:

            order_service.py -> sku_service.py
        """

        self._add_dependency_edge(
            source=source,
            target=target,
            relation="imports",
        )

    def add_field_reference(
        self,
        source: str,
        target: str,
    ) -> None:
        """
        Add a field/type reference dependency.

        Example:

            Order -> Sku
        """

        self._add_dependency_edge(
            source=source,
            target=target,
            relation="field_reference",
        )

    # ------------------------------------------------------------------
    # Graph validation
    # ------------------------------------------------------------------

    def has_node(self, node: str) -> bool:
        """Check whether a node exists in the graph."""
        return node in self.graph

    # ------------------------------------------------------------------
    # Blast radius
    # ------------------------------------------------------------------

    def get_blast_radius(
        self,
        node: str,
        depth: int = 3,
    ) -> Set[str]:
        """
        Get nodes affected by a change to `node`.

        Traverses both:
        - Forward dependencies: node -> dependencies
        - Reverse dependencies: dependents -> node

        Args:
            node: Graph node ID, e.g. "function:SkuService"
            depth: Maximum traversal depth.

        Returns:
            Set of affected graph node IDs.
        """

        if node not in self.graph:
            return set()

        if depth < 0:
            return set()

        affected: Set[str] = {node}

        # ---------------------------------------------------------
        # Forward traversal
        # ---------------------------------------------------------

        forward_lengths = nx.single_source_shortest_path_length(
            self.graph,
            node,
            cutoff=depth,
        )

        affected.update(forward_lengths.keys())

        # ---------------------------------------------------------
        # Backward traversal
        # ---------------------------------------------------------

        reverse_graph = self.graph.reverse(copy=False)

        backward_lengths = nx.single_source_shortest_path_length(
            reverse_graph,
            node,
            cutoff=depth,
        )

        affected.update(backward_lengths.keys())

        return affected
        
    # ------------------------------------------------------------------
    # Detailed blast radius
    # ------------------------------------------------------------------

    def get_blast_radius_details(
        self,
        node: str,
        depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Return detailed blast-radius information.

        Each impacted node contains:

        - node
        - name
        - type
        - file
        - distance
        - path
        - relations
        - relationship_strength
        - impact_score

        This is the preferred method for feeding graph evidence
        into the Impact/Blast Radius Analyzer.
        """

        if node not in self.graph:
            return []

        if depth < 0:
            return []

        reverse_graph = self.graph.reverse(copy=False)

        try:
            paths = nx.single_source_shortest_path(
                reverse_graph,
                node,
                cutoff=depth,
            )
        except nx.NetworkXError:
            return []

        results: List[Dict[str, Any]] = []

        for affected_node, reverse_path in paths.items():

            # Don't report the changed node as its own impact.
            if affected_node == node:
                continue

            # Reverse the path back to the actual dependency direction.
            #
            # reverse_path:
            #
            # SkuValidator -> SkuService -> OrderService
            #
            # This already represents:
            #
            # changed node -> impacted consumer
            #
            path = reverse_path

            relations: List[str] = []
            relationship_strengths: List[float] = []

            for current, consumer in zip(
                path,
                path[1:],
            ):
                edge_data = self.graph.get_edge_data(
                    consumer,
                    current,
                )

                if edge_data:
                    relation = edge_data.get(
                        "relation",
                        "unknown",
                    )

                    weight = edge_data.get(
                        "weight",
                        self.RELATION_WEIGHTS.get(
                            relation,
                            0.5,
                        ),
                    )
                else:
                    relation = "unknown"
                    weight = 0.0

                relations.append(relation)
                relationship_strengths.append(float(weight))

            distance = len(path) - 1

            # Calculate path strength.
            #
            # Example:
            #
            # calls -> calls
            #
            # 1.0 * 1.0 = 1.0
            #
            # imports -> calls
            #
            # 0.3 * 1.0 = 0.3
            path_strength = 1.0

            for strength in relationship_strengths:
                path_strength *= strength

            # Apply distance decay so direct dependencies
            # have more influence than distant dependencies.
            distance_decay = 1.0 / max(distance, 1)

            impact_score = path_strength * distance_decay

            metadata = self.nodes.get(
                affected_node,
                {},
            )

            results.append(
                {
                    "node": affected_node,
                    "name": metadata.get(
                        "name",
                        affected_node,
                    ),
                    "type": metadata.get(
                        "type",
                        "unknown",
                    ),
                    "file": metadata.get(
                        "file",
                        "",
                    ),
                    "distance": distance,
                    "path": path,
                    "relations": relations,
                    "relationship_strengths": relationship_strengths,
                    "path_strength": round(
                        path_strength,
                        3,
                    ),
                    "impact_score": round(
                        impact_score,
                        3,
                    ),
                }
            )

        # Strongest/direct impacts first.
        results.sort(
            key=lambda item: (
                -item["impact_score"],
                item["distance"],
            )
        )

        return results

    # ------------------------------------------------------------------
    # Relationship-specific blast radius
    # ------------------------------------------------------------------

    def get_consumers(
        self,
        node: str,
        depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Return nodes that consume/depend on the given node.

        This is useful when determining which components need
        review after a code or data-model change.
        """

        details = self.get_blast_radius_details(
            node=node,
            depth=depth,
        )

        return [
            item
            for item in details
            if item["relations"]
            and any(
                relation in {
                    "calls",
                    "field_reference",
                    "imports",
                }
                for relation in item["relations"]
            )
        ]

    # ------------------------------------------------------------------
    # Direct dependencies
    # ------------------------------------------------------------------

    def get_direct_dependencies(
        self,
        node: str,
    ) -> List[Dict[str, Any]]:
        """
        Return direct outgoing dependencies of a node.

        Example:

            OrderService -> SkuService

        Calling:

            get_direct_dependencies("class:OrderService")

        returns SkuService.
        """

        if node not in self.graph:
            return []

        results = []

        for target in self.graph.successors(node):

            edge_data = self.graph.get_edge_data(
                node,
                target,
            ) or {}

            metadata = self.nodes.get(
                target,
                {},
            )

            relation = edge_data.get(
                "relation",
                "unknown",
            )

            results.append(
                {
                    "node": target,
                    "name": metadata.get(
                        "name",
                        target,
                    ),
                    "type": metadata.get(
                        "type",
                        "unknown",
                    ),
                    "file": metadata.get(
                        "file",
                        "",
                    ),
                    "relation": relation,
                    "weight": edge_data.get(
                        "weight",
                        self.RELATION_WEIGHTS.get(
                            relation,
                            0.5,
                        ),
                    ),
                }
            )

        return results

    # ------------------------------------------------------------------
    # Direct consumers
    # ------------------------------------------------------------------

    def get_direct_consumers(
        self,
        node: str,
    ) -> List[Dict[str, Any]]:
        """
        Return direct callers/consumers of a node.

        Example:

            OrderService -> SkuService

        For SkuService, OrderService is a direct consumer.
        """

        if node not in self.graph:
            return []

        results = []

        for source in self.graph.predecessors(node):

            edge_data = self.graph.get_edge_data(
                source,
                node,
            ) or {}

            metadata = self.nodes.get(
                source,
                {},
            )

            relation = edge_data.get(
                "relation",
                "unknown",
            )

            results.append(
                {
                    "node": source,
                    "name": metadata.get(
                        "name",
                        source,
                    ),
                    "type": metadata.get(
                        "type",
                        "unknown",
                    ),
                    "file": metadata.get(
                        "file",
                        "",
                    ),
                    "relation": relation,
                    "weight": edge_data.get(
                        "weight",
                        self.RELATION_WEIGHTS.get(
                            relation,
                            0.5,
                        ),
                    ),
                }
            )

        return results

    # ------------------------------------------------------------------
    # Path discovery
    # ------------------------------------------------------------------

    def find_path(
        self,
        source: str,
        target: str,
    ) -> List[str]:
        """
        Return the shortest directed dependency path.

        Returns an empty list when no path exists.
        """

        try:
            return nx.shortest_path(
                self.graph,
                source,
                target,
            )

        except (
            nx.NetworkXNoPath,
            nx.NodeNotFound,
        ):
            return []

    def find_all_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 3,
    ) -> List[List[str]]:
        """
        Return dependency paths between two nodes.

        Useful when there can be multiple dependency routes.
        """

        if source not in self.graph:
            return []

        if target not in self.graph:
            return []

        try:
            return list(
                nx.all_simple_paths(
                    self.graph,
                    source,
                    target,
                    cutoff=cutoff,
                )
            )

        except nx.NetworkXError:
            return []

    # ------------------------------------------------------------------
    # Graph statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """
        Return basic graph statistics for pipeline observability.
        """

        relation_counts: Dict[str, int] = {}

        for source, target, data in self.graph.edges(
            data=True,
        ):
            relation = data.get(
                "relation",
                "unknown",
            )

            relation_counts[relation] = (
                relation_counts.get(
                    relation,
                    0,
                )
                + 1
            )

        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "relation_counts": relation_counts,
            "is_directed": self.graph.is_directed(),
        }

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> DependencyGraphFacts:
        """
        Return immutable-style graph facts for pipeline consumption.
        """

        return DependencyGraphFacts(
            graph=self.graph,
            nodes=self.nodes,
            edges=self.edges,
        )