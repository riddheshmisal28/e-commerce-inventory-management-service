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
            severity="Medium",
        )

        self._add_layer_impact(
            impacts=ctx.endpoint_impacts,
            blast_radius=blast_radius,
            component="API / Endpoint Layer",
            default_reason=(
                "Existing or new API endpoints may require "
                "request, response, or behavioral changes."
            ),
            severity="Medium",
        )

        self._add_layer_impact(
            impacts=ctx.model_impacts,
            blast_radius=blast_radius,
            component="Request / Response Model Layer",
            default_reason=(
                "Pydantic request or response models may require "
                "schema or validation changes."
            ),
            severity="Medium",
        )

        self._add_layer_impact(
            impacts=ctx.business_logic_impacts,
            blast_radius=blast_radius,
            component="Business Logic / Service Layer",
            default_reason=(
                "Business rules, application services, workflows, "
                "or validations may require changes."
            ),
            severity="High",
        )

        self._add_layer_impact(
            impacts=ctx.repository_impacts,
            blast_radius=blast_radius,
            component="Repository / Data Access Layer",
            default_reason=(
                "Database queries, repository methods, CRUD operations, "
                "or data-access logic may change."
            ),
            severity="Medium",
        )

        self._add_layer_impact(
            impacts=ctx.integration_impacts,
            blast_radius=blast_radius,
            component="External Integration Layer",
            default_reason=(
                "External services or third-party integrations "
                "may be required or modified."
            ),
            severity="High",
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
        severity: str,
    ) -> None:

        if not impacts:
            return

        reasons = self._extract_reasons(
            impacts,
        )

        reason = default_reason

        if reasons:
            reason = " ".join(reasons)

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

            blast_radius.append(
                BlastRadius(
                    component=impact.component,
                    reason=(
                        impact.reason
                        or impact.change
                    ),
                    severity=self._determine_component_severity(
                        impact.impact_type,
                    ),
                )
            )

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

            if reason and reason not in reasons:
                reasons.append(reason)

        return reasons

    def _determine_component_severity(
        self,
        impact_type: str | None,
    ) -> str:

        if not impact_type:
            return "Medium"

        impact_type = impact_type.lower()

        if any(
            keyword in impact_type
            for keyword in (
                "integration",
                "external",
                "critical",
            )
        ):
            return "High"

        if any(
            keyword in impact_type
            for keyword in (
                "business",
                "logic",
                "workflow",
            )
        ):
            return "High"

        return "Medium"

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

            existing.severity = self._max_severity(
                existing.severity,
                impact.severity,
            )

            if (
                impact.reason
                and impact.reason not in existing.reason
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