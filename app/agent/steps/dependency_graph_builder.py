from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext
from app.agent.code_analysis.dependency_graph import DependencyGraphBuilder
from app.core.logger import get_logger

logger = get_logger(__name__)


class DependencyGraphBuilderStep(AgentStep):
    """
    Build NetworkX dependency graph from entities and code facts.
    
    Graph enables:
    - Accurate blast-radius calculation
    - Dependency path finding
    - Impact propagation analysis
    
    Results stored in:
    - ctx.dependency_graph: DependencyGraphFacts
    - ctx.graph_builder: DependencyGraphBuilder (for queries)
    """

    name = "Dependency Graph Builder"

    required_context = {"entities"}

    def execute(self, ctx: AnalysisContext) -> None:
        """
        Build dependency graph from engineering context.
        
        Requires:
        - ctx.engineering_context.entities: List of entities
        - ctx.code_facts (optional): AST facts for relationship extraction
        
        Produces:
        - ctx.dependency_graph: Serializable graph facts
        - ctx.graph_builder: Builder for queries like get_blast_radius()
        """
        builder = DependencyGraphBuilder()

        if not hasattr(ctx, "engineering_context") or not ctx.engineering_context.entities:
            logger.warning("No entities found in context")
            ctx.dependency_graph = builder.build()
            ctx.graph_builder = builder
            return

        # 1. Register all entities
        for entity in ctx.engineering_context.entities:
            entity_name = entity.get("name", "")
            entity_type = entity.get("type", "entity")
            file_path = entity.get("file_path")

            if not entity_name:
                continue

            builder.add_entity(entity_name, entity_type, file_path)
            logger.debug(f"Added entity: {entity_type}:{entity_name}")

        # 2. Extract relationships from code facts (if available)
        if hasattr(ctx, "code_facts") and ctx.code_facts:
            self._extract_relationships_from_facts(builder, ctx.code_facts)

        # 3. Build and store graph
        ctx.dependency_graph = builder.build()
        ctx.graph_builder = builder

        logger.info(
            f"Dependency graph built: "
            f"{len(builder.graph.nodes)} nodes, "
            f"{len(builder.graph.edges)} edges"
        )

    def _extract_relationships_from_facts(
        self, builder: DependencyGraphBuilder, code_facts: dict
    ) -> None:
        """
        Extract relationship edges from AST facts.
        
        Looks for:
        - Import statements (add_import_edge)
        - Field type references (add_field_reference)
        """
        for entity_name, facts in code_facts.items():
            # Extract imports
            for import_dict in facts.imports.values():
                for import_fact in (
                    import_dict if isinstance(import_dict, list) else [import_dict]
                ):
                    if hasattr(import_fact, "module"):
                        # Add import relationship
                        builder.add_import_edge(entity_name, import_fact.module)
                        logger.debug(f"Edge: {entity_name} -> {import_fact.module} (import)")

            # Extract field type references (class-to-class relationships)
            for class_name, class_fact in facts.classes.items():
                for field_name, field_fact in class_fact.fields.items():
                    # If field type is another class, add reference edge
                    if field_fact.type_annotation and "::" not in field_fact.type_annotation:
                        # Simple type reference (not a method, just a field type)
                        builder.add_field_reference(class_name, field_fact.type_annotation)
                        logger.debug(
                            f"Edge: {class_name} -> {field_fact.type_annotation} "
                            f"(field type: {field_name})"
                        )
