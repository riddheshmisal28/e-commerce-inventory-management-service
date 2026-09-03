from typing import Dict, Set, List
import networkx as nx
from dataclasses import dataclass

@dataclass
class DependencyGraphFacts:
    """Dependency graph for blast-radius analysis"""
    graph: nx.DiGraph  # NetworkX directed graph
    nodes: Dict[str, Dict]  # node_id → metadata
    edges: List[tuple]  # list of (source, target)

class DependencyGraphBuilder:
    """
    Build dependency graph from:
    - Call graphs (function/method calls)
    - Import facts (module dependencies)
    - Field references (entity → model references)
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[tuple] = []

    def add_entity(self, entity_name: str, entity_type: str, file_path: str = ""):
        """Add entity node (class/function/module)"""
        node_id = f"{entity_type}:{entity_name}"
        self.graph.add_node(node_id, type=entity_type, name=entity_name, file=file_path)
        self.nodes[node_id] = {"type": entity_type, "name": entity_name, "file": file_path}

    def add_call_edge(self, caller: str, callee: str, line_number: int = 0):
        """Add call dependency: caller → callee"""
        edge = (caller, callee)
        if edge not in self.edges:
            self.graph.add_edge(caller, callee, relation="calls", line=line_number)
            self.edges.append(edge)

    def add_import_edge(self, source: str, target: str):
        """Add import dependency: source → target"""
        edge = (source, target)
        if edge not in self.edges:
            self.graph.add_edge(source, target, relation="imports")
            self.edges.append(edge)

    def add_field_reference(self, source: str, target: str):
        """Add a dependency from a class to a type used by one of its fields."""
        edge = (source, target)
        if edge not in self.edges:
            self.graph.add_edge(source, target, relation="field_reference")
            self.edges.append(edge)

    def get_blast_radius(self, node: str, depth: int = 3) -> Set[str]:
        """
        Get all nodes affected by changes to 'node'.
        Follows both forward (calls) and backward (called-by) paths.
        """
        affected = {node}

        # Forward: What does this node call?
        try:
            for successor in nx.descendants(self.graph, node):
                affected.add(successor)
        except nx.NetworkXError:
            pass

        # Backward: What calls this node?
        try:
            for predecessor in nx.ancestors(self.graph, node):
                affected.add(predecessor)
        except nx.NetworkXError:
            pass

        return affected

    def find_path(self, source: str, target: str) -> List[str]:
        """Return a directed dependency path, or an empty list if none exists."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def build(self) -> DependencyGraphFacts:
        """Return dependency graph facts"""
        return DependencyGraphFacts(
            graph=self.graph,
            nodes=self.nodes,
            edges=self.edges,
        )