from typing import Any

from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext
from app.agent.code_analysis.dependency_graph import DependencyGraphBuilder
from app.core.logger import get_logger


logger = get_logger(__name__)


class DependencyGraphBuilderStep(AgentStep):
    """
    Build a NetworkX dependency graph from engineering entities
    and extracted code facts.

    Graph enables:
    - Accurate blast-radius calculation
    - Dependency path finding
    - Impact propagation analysis
    - Evidence-based blast-radius reasoning

    Results stored in:
    - ctx.dependency_graph: DependencyGraphFacts
    - ctx.graph_builder: DependencyGraphBuilder
    """

    name = "Dependency Graph Builder"

    required_context = {"entities"}

    def execute(self, ctx: AnalysisContext) -> None:
        """
        Build dependency graph from engineering context.

        Requires:
        - ctx.engineering_context.entities
        - ctx.code_facts (optional)

        Produces:
        - ctx.dependency_graph
        - ctx.graph_builder
        """

        builder = DependencyGraphBuilder()

        # -------------------------------------------------------------
        # 1. Validate engineering context
        # -------------------------------------------------------------

        if (
            not hasattr(ctx, "engineering_context")
            or not ctx.engineering_context
            or not ctx.engineering_context.entities
        ):
            logger.warning(
                "No engineering entities found; "
                "building empty dependency graph"
            )

            ctx.dependency_graph = builder.build()
            ctx.graph_builder = builder
            return

        # -------------------------------------------------------------
        # 2. Register entities
        # -------------------------------------------------------------

        for entity in ctx.engineering_context.entities:
            if not isinstance(entity, dict):
                continue

            entity_name = entity.get("name", "").strip()
            entity_type = entity.get("type", "entity").strip()
            file_path = entity.get("file_path", "") or ""

            if not entity_name:
                continue

            node_id = builder.add_entity(
                entity_name=entity_name,
                entity_type=entity_type,
                file_path=file_path,
            )

            logger.debug(
                "Added dependency graph node: %s",
                node_id,
            )

        # -------------------------------------------------------------
        # 3. Extract relationships from code facts
        # -------------------------------------------------------------

        if hasattr(ctx, "code_facts") and ctx.code_facts:
            self._extract_relationships_from_facts(
                builder=builder,
                code_facts=ctx.code_facts,
            )

        # -------------------------------------------------------------
        # 4. Build and store graph
        # -------------------------------------------------------------

        ctx.dependency_graph = builder.build()
        ctx.graph_builder = builder

        statistics = builder.get_statistics()

        logger.info(
            "Dependency graph built: nodes=%s, edges=%s, relations=%s",
            statistics["node_count"],
            statistics["edge_count"],
            statistics["relation_counts"],
        )

    # =================================================================
    # RELATIONSHIP EXTRACTION
    # =================================================================

    def _extract_relationships_from_facts(
        self,
        builder: DependencyGraphBuilder,
        code_facts: dict,
    ) -> None:
        """
        Extract dependency relationships from AST/code facts.

        Supported relationships:
        - calls
        - imports
        - field_reference

        Important:
        Relationships are only added when both endpoints can be
        resolved to nodes already present in the graph.
        """

        if not isinstance(code_facts, dict):
            logger.warning(
                "Invalid code_facts type: %s",
                type(code_facts).__name__,
            )
            return

        for entity_name, facts in code_facts.items():

            if facts is None:
                continue

            # ---------------------------------------------------------
            # Resolve source entity
            # ---------------------------------------------------------

            source_node = self._resolve_node(
                builder=builder,
                name=entity_name,
            )

            if not source_node:
                logger.debug(
                    "Skipping code facts for unknown entity: %s",
                    entity_name,
                )
                continue

            # ---------------------------------------------------------
            # Imports
            # ---------------------------------------------------------

            self._extract_import_relationships(
                builder=builder,
                source_node=source_node,
                facts=facts,
            )

            # ---------------------------------------------------------
            # Field references
            # ---------------------------------------------------------

            self._extract_field_relationships(
                builder=builder,
                facts=facts,
            )

            # ---------------------------------------------------------
            # Method/function calls
            # ---------------------------------------------------------

            self._extract_call_relationships(
                builder=builder,
                source_node=source_node,
                facts=facts,
            )

    # =================================================================
    # IMPORT RELATIONSHIPS
    # =================================================================

    def _extract_import_relationships(
        self,
        builder: DependencyGraphBuilder,
        source_node: str,
        facts: Any,
    ) -> None:
        """
        Extract module import relationships.

        Example:

            order_service.py
                -> sku_service.py
        """

        imports = getattr(facts, "imports", None)

        if not imports:
            return

        if not isinstance(imports, dict):
            return

        for import_dict in imports.values():

            import_items = (
                import_dict
                if isinstance(import_dict, list)
                else [import_dict]
            )

            for import_fact in import_items:

                if import_fact is None:
                    continue

                module = getattr(
                    import_fact,
                    "module",
                    None,
                )

                if not module:
                    continue

                target_node = self._resolve_node(
                    builder=builder,
                    name=module,
                )

                if not target_node:
                    logger.debug(
                        "Skipping import edge because target "
                        "node was not found: %s -> %s",
                        source_node,
                        module,
                    )
                    continue

                builder.add_import_edge(
                    source=source_node,
                    target=target_node,
                )

                logger.debug(
                    "Dependency edge: %s -> %s [imports]",
                    source_node,
                    target_node,
                )

    # =================================================================
    # FIELD REFERENCES
    # =================================================================

    def _extract_field_relationships(
        self,
        builder: DependencyGraphBuilder,
        facts: Any,
    ) -> None:
        """
        Extract class -> referenced type relationships.

        Example:

            Order -> Sku
        """

        classes = getattr(facts, "classes", None)

        if not classes or not isinstance(classes, dict):
            return

        for class_name, class_fact in classes.items():

            if class_fact is None:
                continue

            fields = getattr(
                class_fact,
                "fields",
                None,
            )

            if not fields or not isinstance(fields, dict):
                continue

            source_node = self._resolve_node(
                builder=builder,
                name=class_name,
                preferred_types=("class",),
            )

            if not source_node:
                continue

            for field_name, field_fact in fields.items():

                if field_fact is None:
                    continue

                type_annotation = getattr(
                    field_fact,
                    "type_annotation",
                    None,
                )

                if not type_annotation:
                    continue

                # Ignore complex/unresolved annotations for now.
                if "::" in type_annotation:
                    continue

                target_node = self._resolve_node(
                    builder=builder,
                    name=type_annotation,
                    preferred_types=("class", "model", "entity"),
                )

                if not target_node:
                    logger.debug(
                        "Skipping field reference because target "
                        "node was not found: %s -> %s",
                        source_node,
                        type_annotation,
                    )
                    continue

                builder.add_field_reference(
                    source=source_node,
                    target=target_node,
                )

                logger.debug(
                    "Dependency edge: %s -> %s "
                    "[field_reference:%s]",
                    source_node,
                    target_node,
                    field_name,
                )

    # =================================================================
    # CALL RELATIONSHIPS
    # =================================================================

    def _extract_call_relationships(
        self,
        builder: DependencyGraphBuilder,
        source_node: str,
        facts: Any,
    ) -> None:
        """
        Extract function/method call relationships.

        This method supports common fact representations without
        assuming a single AST schema.

        Expected possible structures include:

            facts.calls

        where calls may be:

            {
                "method": [...],
                ...
            }

        or:

            [
                CallFact(...)
            ]
        """

        calls = getattr(facts, "calls", None)

        if not calls:
            return

        # Normalize calls to a list.
        if isinstance(calls, dict):
            call_items = []

            for value in calls.values():
                if isinstance(value, list):
                    call_items.extend(value)
                else:
                    call_items.append(value)

        elif isinstance(calls, list):
            call_items = calls

        else:
            call_items = [calls]

        for call_fact in call_items:

            if call_fact is None:
                continue

            callee = self._extract_callee_name(call_fact)

            if not callee:
                continue

            target_node = self._resolve_node(
                builder=builder,
                name=callee,
            )

            if not target_node:
                logger.debug(
                    "Skipping call edge because target "
                    "node was not found: %s -> %s",
                    source_node,
                    callee,
                )
                continue

            line_number = getattr(
                call_fact,
                "line_number",
                getattr(
                    call_fact,
                    "line",
                    0,
                ),
            )

            builder.add_call_edge(
                caller=source_node,
                callee=target_node,
                line_number=line_number or 0,
            )

            logger.debug(
                "Dependency edge: %s -> %s [calls]",
                source_node,
                target_node,
            )

    # =================================================================
    # NODE RESOLUTION
    # =================================================================

    def _resolve_node(
        self,
        builder: DependencyGraphBuilder,
        name: str,
        preferred_types: tuple[str, ...] = (),
    ) -> str | None:
        """
        Resolve a raw entity/type/module name to a graph node ID.

        Supports:
            SkuService
            class:SkuService
            module:sku_service
            model:Sku

        Returns:
            Existing node ID or None.
        """

        if not name:
            return None

        name = str(name).strip()

        # -------------------------------------------------------------
        # Already a node ID
        # -------------------------------------------------------------

        if builder.has_node(name):
            return name

        # -------------------------------------------------------------
        # Try preferred types first
        # -------------------------------------------------------------

        for entity_type in preferred_types:
            candidate = f"{entity_type}:{name}"

            if builder.has_node(candidate):
                return candidate

        # -------------------------------------------------------------
        # Search all registered nodes by name
        # -------------------------------------------------------------

        for node_id, metadata in builder.nodes.items():
            if metadata.get("name") == name:
                return node_id

        # -------------------------------------------------------------
        # Handle qualified Python names
        # -------------------------------------------------------------

        short_name = name.split(".")[-1]

        for entity_type in preferred_types:
            candidate = f"{entity_type}:{short_name}"

            if builder.has_node(candidate):
                return candidate

        for node_id, metadata in builder.nodes.items():
            if metadata.get("name") == short_name:
                return node_id

        return None

    # =================================================================
    # CALLEE EXTRACTION
    # =================================================================

    def _extract_callee_name(
        self,
        call_fact: Any,
    ) -> str | None:
        """
        Extract callee name from a call fact.

        Supports common field names:
        - callee
        - function
        - function_name
        - method
        - method_name
        - name
        """

        if isinstance(call_fact, str):
            return call_fact.strip()

        for attribute in (
            "callee",
            "function",
            "function_name",
            "method",
            "method_name",
            "name",
        ):
            value = getattr(
                call_fact,
                attribute,
                None,
            )

            if value:
                return str(value).strip()

        return None