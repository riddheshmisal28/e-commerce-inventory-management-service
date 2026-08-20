from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    BlastRadius,
)


class BlastRadiusAnalyzer(AgentStep):

    name = "Blast Radius Analyzer"

    required_context: set[str] = set()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        blast_radius: list[BlastRadius] = []

        self._add_layer_impact(
            impacts=ctx.entity_impacts,
            blast_radius=blast_radius,
            component="Database / Entity Layer",
            default_reason=(
                "Database entities or their schema may require "
                "changes to support the requirement."
            ),
        )

        self._add_layer_impact(
            impacts=ctx.endpoint_impacts,
            blast_radius=blast_radius,
            component="API / Endpoint Layer",
            default_reason=(
                "Existing or new API endpoints may require "
                "request, response, or behavioral changes."
            ),
        )

        self._add_layer_impact(
            impacts=ctx.model_impacts,
            blast_radius=blast_radius,
            component="Request / Response Model Layer",
            default_reason=(
                "Pydantic request or response models may require "
                "schema or validation changes."
            ),
        )

        self._add_layer_impact(
            impacts=ctx.business_logic_impacts,
            blast_radius=blast_radius,
            component="Business Logic / Service Layer",
            default_reason=(
                "Business rules, application services, workflows, "
                "or validations may require changes."
            ),
        )

        self._add_layer_impact(
            impacts=ctx.repository_impacts,
            blast_radius=blast_radius,
            component="Repository / Data Access Layer",
            default_reason=(
                "Database queries, repository methods, CRUD operations, "
                "or data-access logic may change."
            ),
        )

        self._add_layer_impact(
            impacts=ctx.integration_impacts,
            blast_radius=blast_radius,
            component="External Integration Layer",
            default_reason=(
                "External services or third-party integrations "
                "may be required or modified."
            ),
        )

        self._add_component_impact(
            ctx,
            blast_radius,
        )

        ctx.blast_radius = self._deduplicate(
            blast_radius,
        )

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
            if self._is_relevant(
                impact,
            )
        ]

        if not relevant_impacts:
            return

        reasons = self._extract_reasons(
            relevant_impacts,
        )

        reason = default_reason

        if reasons:
            reason = " ".join(reasons)

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

        for impact in ctx.component_impacts:

            if not impact.component:
                continue

            if not self._is_relevant(
                impact,
            ):
                continue

            blast_radius.append(
                BlastRadius(
                    component=impact.component,
                    reason=(
                        impact.reason
                        or impact.change
                    ),
                    severity=(
                        self._determine_component_severity(
                            impact,
                        )
                    ),
                )
            )

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
            relevance_score >= 0.50
            and confidence >= 0.50
        )

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
                reasons.append(
                    reason,
                )

        return reasons

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