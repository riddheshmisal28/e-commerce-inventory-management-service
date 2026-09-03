from typing import Any

from app.agent.core.agent_step import AgentStep
from app.agent.execution.execution_policy import ExecutionPolicy
from app.agent.models import (
    AnalysisContext,
    BlastRadius,
)
from app.core.logger import get_logger


logger = get_logger(__name__)


class BlastRadiusAnalyzer(AgentStep):
    """
    Analyze blast radius using validated impacts and the dependency graph.

    Strategy:

        Impact
          ↓
        Resolve impacted entity/component
          ↓
        Traverse dependency graph
          ↓
        Identify affected nodes
          ↓
        Group nodes into architectural layers
          ↓
        Generate evidence-based blast radius

    The dependency graph is treated as the primary source of truth
    for dependency propagation.
    """

    name = "Blast Radius Analyzer"

    required_context: set[str] = set()

    # Maximum graph traversal distance.
    DEFAULT_DEPTH = 3

    # Minimum confidence/relevance for an impact to participate
    # in blast-radius analysis.
    MIN_RELEVANCE = 0.50
    MIN_CONFIDENCE = 0.50

    def __init__(self):
        self.execution_policy = ExecutionPolicy()

    # =================================================================
    # EXECUTION
    # =================================================================

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        blast_radius: list[BlastRadius] = []

        graph_builder = getattr(
            ctx,
            "graph_builder",
            None,
        )

        # -------------------------------------------------------------
        # No graph available
        # -------------------------------------------------------------

        if graph_builder is None:
            logger.warning(
                "No dependency graph available. "
                "Falling back to impact-based blast radius."
            )

            self._fallback_layer_analysis(
                ctx,
                blast_radius,
            )

            ctx.blast_radius = self._deduplicate(
                blast_radius,
            )

            return

        # -------------------------------------------------------------
        # Collect all validated impacts
        # -------------------------------------------------------------

        impacts = self._collect_impacts(ctx)

        if not impacts:
            logger.info(
                "No validated impacts available for blast-radius analysis."
            )

            ctx.blast_radius = []

            return

        # -------------------------------------------------------------
        # Resolve impact -> graph nodes
        # -------------------------------------------------------------

        resolved_impacts = []

        for impact in impacts:

            if not self._is_relevant(impact):
                continue

            nodes = self._resolve_impact_nodes(
                graph_builder,
                impact,
            )

            if not nodes:
                logger.debug(
                    "Could not resolve impact to graph node: %s",
                    getattr(impact, "entity", None),
                )
                continue

            resolved_impacts.append(
                (
                    impact,
                    nodes,
                )
            )

        # -------------------------------------------------------------
        # Traverse dependency graph
        # -------------------------------------------------------------

        for impact, nodes in resolved_impacts:

            for node in nodes:

                affected_nodes = graph_builder.get_blast_radius(
                    node,
                    depth=self.DEFAULT_DEPTH,
                )

                self._add_graph_impacts(
                    graph_builder=graph_builder,
                    source_node=node,
                    affected_nodes=affected_nodes,
                    source_impact=impact,
                    blast_radius=blast_radius,
                )

        # -------------------------------------------------------------
        # If graph resolution produced nothing, fallback
        # -------------------------------------------------------------

        if not blast_radius:
            logger.info(
                "Dependency graph produced no blast-radius results. "
                "Using impact-based fallback."
            )

            self._fallback_layer_analysis(
                ctx,
                blast_radius,
            )

        # -------------------------------------------------------------
        # Deduplicate
        # -------------------------------------------------------------

        ctx.blast_radius = self._deduplicate(
            blast_radius,
        )

        logger.info(
            "Blast radius analysis complete: %s components",
            len(ctx.blast_radius),
        )

    # =================================================================
    # IMPACT COLLECTION
    # =================================================================

    def _collect_impacts(
        self,
        ctx: AnalysisContext,
    ) -> list[Any]:
        """
        Collect validated impacts from all impact categories.
        """

        impacts: list[Any] = []

        for attribute in (
            "entity_impacts",
            "endpoint_impacts",
            "model_impacts",
            "business_logic_impacts",
            "repository_impacts",
            "integration_impacts",
            "component_impacts",
        ):

            values = getattr(
                ctx,
                attribute,
                None,
            )

            if not values:
                continue

            impacts.extend(values)

        return impacts

    # =================================================================
    # IMPACT -> GRAPH NODE RESOLUTION
    # =================================================================

    def _resolve_impact_nodes(
        self,
        graph_builder,
        impact,
    ) -> list[str]:
        """
        Resolve an impact to graph nodes.

        Supports common impact attributes:
        - entity
        - component
        - target
        - name

        Returns graph node IDs.
        """

        candidates = []

        for attribute in (
            "entity",
            "component",
            "target",
            "name",
        ):

            value = getattr(
                impact,
                attribute,
                None,
            )

            if value:
                candidates.append(
                    str(value).strip()
                )

        resolved = []

        for candidate in candidates:

            node = self._resolve_node(
                graph_builder,
                candidate,
            )

            if node and node not in resolved:
                resolved.append(node)

        return resolved

    def _resolve_node(
        self,
        graph_builder,
        name: str,
    ) -> str | None:
        """
        Resolve raw entity/component name to graph node ID.
        """

        if not name:
            return None

        name = name.strip()

        # Already a node ID.
        if graph_builder.has_node(name):
            return name

        # Exact name match.
        for node_id, metadata in graph_builder.nodes.items():

            if metadata.get("name") == name:
                return node_id

        # Handle qualified names.
        short_name = name.split(".")[-1]

        for node_id, metadata in graph_builder.nodes.items():

            if metadata.get("name") == short_name:
                return node_id

        # Case-insensitive match.
        name_lower = name.lower()

        for node_id, metadata in graph_builder.nodes.items():

            metadata_name = str(
                metadata.get("name", "")
            ).lower()

            if metadata_name == name_lower:
                return node_id

        return None

    # =================================================================
    # GRAPH ANALYSIS
    # =================================================================

    def _add_graph_impacts(
        self,
        graph_builder,
        source_node: str,
        affected_nodes: set[str],
        source_impact,
        blast_radius: list[BlastRadius],
    ) -> None:
        """
        Convert dependency graph nodes into architectural
        blast-radius components.
        """

        for node in affected_nodes:

            metadata = graph_builder.nodes.get(
                node,
                {},
            )

            node_type = metadata.get(
                "type",
                "unknown",
            )

            node_name = metadata.get(
                "name",
                node,
            )

            file_path = metadata.get(
                "file",
                "",
            )

            distance = self._calculate_distance(
                graph_builder,
                source_node,
                node,
            )

            component = self._classify_component(
                node_type=node_type,
                file_path=file_path,
            )

            reason = self._build_graph_reason(
                source_impact=source_impact,
                source_node=source_node,
                affected_node=node_name,
                distance=distance,
                file_path=file_path,
            )

            severity = self._determine_graph_severity(
                source_impact=source_impact,
                distance=distance,
                node_type=node_type,
            )

            blast_radius.append(
                BlastRadius(
                    component=component,
                    reason=reason,
                    severity=severity,
                )
            )

    # =================================================================
    # DISTANCE
    # =================================================================

    def _calculate_distance(
        self,
        graph_builder,
        source: str,
        target: str,
    ) -> int:
        """
        Calculate shortest directed dependency distance.

        Checks both directions because blast radius considers
        both dependencies and dependents.
        """

        if source == target:
            return 0

        try:
            forward = graph_builder.find_path(
                source,
                target,
            )

            if forward:
                return len(forward) - 1

        except Exception:
            pass

        try:
            reverse = graph_builder.find_path(
                target,
                source,
            )

            if reverse:
                return len(reverse) - 1

        except Exception:
            pass

        return self.DEFAULT_DEPTH

    # =================================================================
    # COMPONENT CLASSIFICATION
    # =================================================================

    def _classify_component(
        self,
        node_type: str,
        file_path: str,
    ) -> str:
        """
        Classify a graph node into an architectural layer.

        Classification is deterministic and based on code facts.
        """

        node_type = (
            node_type or ""
        ).lower()

        file_path = (
            file_path or ""
        ).lower()

        # -------------------------------------------------------------
        # Entity / database
        # -------------------------------------------------------------

        if (
            node_type in {
                "entity",
                "database",
                "table",
            }
            or any(
                value in file_path
                for value in (
                    "/entity/",
                    "/entities/",
                    "/model/",
                    "/models/",
                    "schema",
                )
            )
        ):
            return "Database / Entity Layer"

        # -------------------------------------------------------------
        # API / endpoint
        # -------------------------------------------------------------

        if (
            node_type in {
                "endpoint",
                "route",
                "controller",
            }
            or any(
                value in file_path
                for value in (
                    "/api/",
                    "/endpoint/",
                    "/endpoints/",
                    "/controller/",
                    "/controllers/",
                    "route",
                )
            )
        ):
            return "API / Endpoint Layer"

        # -------------------------------------------------------------
        # Repository
        # -------------------------------------------------------------

        if (
            node_type in {
                "repository",
                "dao",
            }
            or any(
                value in file_path
                for value in (
                    "/repository/",
                    "/repositories/",
                    "/dao/",
                )
            )
        ):
            return "Repository / Data Access Layer"

        # -------------------------------------------------------------
        # Integration
        # -------------------------------------------------------------

        if (
            node_type in {
                "integration",
                "external_service",
            }
            or any(
                value in file_path
                for value in (
                    "/integration/",
                    "/integrations/",
                    "/external/",
                    "/clients/",
                )
            )
        ):
            return "External Integration Layer"

        # -------------------------------------------------------------
        # Business logic
        # -------------------------------------------------------------

        if (
            node_type in {
                "service",
                "business_logic",
                "function",
                "class",
            }
            or any(
                value in file_path
                for value in (
                    "/service/",
                    "/services/",
                    "/business/",
                    "/logic/",
                )
            )
        ):
            return "Business Logic / Service Layer"

        # -------------------------------------------------------------
        # Generic component
        # -------------------------------------------------------------

        return "Application Component"

    # =================================================================
    # REASON GENERATION
    # =================================================================

    def _build_graph_reason(
        self,
        source_impact,
        source_node: str,
        affected_node: str,
        distance: int,
        file_path: str,
    ) -> str:
        """
        Build an evidence-based reason for the blast-radius entry.
        """

        original_reason = getattr(
            source_impact,
            "reason",
            None,
        )

        if distance == 0:

            if original_reason:
                return original_reason

            return (
                f"{affected_node} is directly identified by "
                "the validated impact."
            )

        reason = (
            f"{affected_node} is within {distance} dependency "
            f"hop{'s' if distance != 1 else ''} of "
            f"{source_node} and may be affected by the change."
        )

        if original_reason:
            reason = (
                f"{reason} "
                f"Source impact: {original_reason}"
            )

        if file_path:
            reason = (
                f"{reason} "
                f"Code location: {file_path}."
            )

        return reason

    # =================================================================
    # SEVERITY
    # =================================================================

    def _determine_graph_severity(
        self,
        source_impact,
        distance: int,
        node_type: str,
    ) -> str:
        """
        Determine severity using:
        - source impact confidence
        - source impact relevance
        - graph distance
        - component type
        """

        relevance = getattr(
            source_impact,
            "relevance_score",
            1.0,
        )

        confidence = getattr(
            source_impact,
            "confidence",
            1.0,
        )

        node_type = (
            node_type or ""
        ).lower()

        # Directly impacted component.
        if distance == 0:

            if (
                relevance >= 0.90
                and confidence >= 0.90
            ):
                return "High"

            if (
                relevance >= 0.75
                and confidence >= 0.75
            ):
                return "Medium"

            return "Low"

        # High-risk downstream integrations.
        if node_type in {
            "integration",
            "external_service",
        }:
            if (
                relevance >= 0.75
                and confidence >= 0.75
            ):
                return "High"

        # One-hop dependency.
        if distance == 1:

            if (
                relevance >= 0.75
                and confidence >= 0.75
            ):
                return "Medium"

            return "Low"

        # Deeper transitive dependency.
        return "Low"

    # =================================================================
    # RELEVANCE
    # =================================================================

    def _is_relevant(
        self,
        impact,
    ) -> bool:

        relevance_score = getattr(
            impact,
            "relevance_score",
            1.0,
        )

        confidence = getattr(
            impact,
            "confidence",
            1.0,
        )

        return (
            relevance_score >= self.MIN_RELEVANCE
            and confidence >= self.MIN_CONFIDENCE
        )

    # =================================================================
    # FALLBACK
    # =================================================================

    def _fallback_layer_analysis(
        self,
        ctx: AnalysisContext,
        blast_radius: list[BlastRadius],
    ) -> None:
        """
        Fallback for cases where graph information is unavailable.

        This preserves the previous behavior but should only be used
        when graph-based analysis cannot be performed.
        """

        layer_configs = (
            (
                ctx.entity_impacts,
                "Database / Entity Layer",
                "Database entities or their schema may require changes.",
            ),
            (
                ctx.endpoint_impacts,
                "API / Endpoint Layer",
                "API endpoints may require changes.",
            ),
            (
                ctx.model_impacts,
                "Request / Response Model Layer",
                "Request or response models may require changes.",
            ),
            (
                ctx.business_logic_impacts,
                "Business Logic / Service Layer",
                "Business rules or services may require changes.",
            ),
            (
                ctx.repository_impacts,
                "Repository / Data Access Layer",
                "Data-access logic may require changes.",
            ),
            (
                ctx.integration_impacts,
                "External Integration Layer",
                "External integrations may require changes.",
            ),
        )

        for impacts, component, reason in layer_configs:

            self._add_layer_impact(
                impacts=impacts,
                blast_radius=blast_radius,
                component=component,
                default_reason=reason,
            )

        self._add_component_impact(
            ctx,
            blast_radius,
        )

    # =================================================================
    # LEGACY LAYER SUPPORT
    # =================================================================

    def _add_layer_impact(
        self,
        impacts: list,
        blast_radius: list[BlastRadius],
        component: str,
        default_reason: str,
    ) -> None:

        if not impacts:
            return

        relevant_impacts = [
            impact
            for impact in impacts
            if self._is_relevant(impact)
        ]

        if not relevant_impacts:
            return

        reasons = self._extract_reasons(
            relevant_impacts,
        )

        reason = (
            " ".join(reasons)
            if reasons
            else default_reason
        )

        severity = self._determine_layer_severity(
            relevant_impacts,
        )

        blast_radius.append(
            BlastRadius(
                component=component,
                reason=reason,
                severity=severity,
            )
        )

    def _add_component_impact(
        self,
        ctx: AnalysisContext,
        blast_radius: list[BlastRadius],
    ) -> None:

        for impact in getattr(
            ctx,
            "component_impacts",
            [],
        ):

            component = getattr(
                impact,
                "component",
                None,
            )

            if not component:
                continue

            if not self._is_relevant(impact):
                continue

            blast_radius.append(
                BlastRadius(
                    component=component,
                    reason=(
                        getattr(
                            impact,
                            "reason",
                            None,
                        )
                        or getattr(
                            impact,
                            "change",
                            "",
                        )
                    ),
                    severity=(
                        self._determine_component_severity(
                            impact,
                        )
                    ),
                )
            )

    # =================================================================
    # SEVERITY HELPERS
    # =================================================================

    def _determine_layer_severity(
        self,
        impacts: list,
    ) -> str:

        highest_relevance = max(
            (
                getattr(
                    impact,
                    "relevance_score",
                    1.0,
                )
                for impact in impacts
            ),
            default=0.0,
        )

        highest_confidence = max(
            (
                getattr(
                    impact,
                    "confidence",
                    1.0,
                )
                for impact in impacts
            ),
            default=0.0,
        )

        if (
            highest_relevance >= 0.90
            and highest_confidence >= 0.90
        ):
            return "High"

        if (
            highest_relevance >= 0.75
            and highest_confidence >= 0.75
        ):
            return "Medium"

        return "Low"

    def _determine_component_severity(
        self,
        impact,
    ) -> str:

        change_type = getattr(
            impact,
            "change_type",
            "",
        )

        relevance_score = getattr(
            impact,
            "relevance_score",
            1.0,
        )

        confidence = getattr(
            impact,
            "confidence",
            1.0,
        )

        if (
            relevance_score >= 0.90
            and confidence >= 0.90
        ):
            return "High"

        change_type = change_type.lower()

        if any(
            keyword in change_type
            for keyword in (
                "integration",
                "external",
                "critical",
            )
        ):
            return "High"

        if any(
            keyword in change_type
            for keyword in (
                "business",
                "logic",
                "workflow",
                "state_transition",
            )
        ):
            return "High"

        if (
            relevance_score >= 0.75
            and confidence >= 0.75
        ):
            return "Medium"

        return "Low"

    # =================================================================
    # REASONS
    # =================================================================

    def _extract_reasons(
        self,
        impacts: list,
    ) -> list[str]:

        reasons: list[str] = []

        for impact in impacts:

            reason = getattr(
                impact,
                "reason",
                None,
            )

            if (
                reason
                and reason not in reasons
            ):
                reasons.append(reason)

        return reasons

    # =================================================================
    # DEDUPLICATION
    # =================================================================

    def _deduplicate(
        self,
        impacts: list[BlastRadius],
    ) -> list[BlastRadius]:

        unique: dict[str, BlastRadius] = {}

        for impact in impacts:

            key = impact.component.lower()

            existing = unique.get(key)

            if existing is None:
                unique[key] = impact
                continue

            existing.severity = (
                self._max_severity(
                    existing.severity,
                    impact.severity,
                )
            )

            if (
                impact.reason
                and impact.reason
                not in existing.reason
            ):
                existing.reason = (
                    f"{existing.reason} "
                    f"{impact.reason}"
                )

        return list(
            unique.values()
        )

    def _max_severity(
        self,
        first: str,
        second: str,
    ) -> str:

        ranking = {
            "Low": 1,
            "Medium": 2,
            "High": 3,
            "Critical": 4,
        }

        first_rank = ranking.get(
            first,
            1,
        )

        second_rank = ranking.get(
            second,
            1,
        )

        return (
            first
            if first_rank >= second_rank
            else second
        )