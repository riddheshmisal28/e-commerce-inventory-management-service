from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    BlastRadius,
)


class BlastRadiusAnalyzer(AgentStep):

    name = "Blast Radius Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        blast_radius: list[BlastRadius] = []

        self._add_layer_impact(
            ctx.entity_impacts,
            blast_radius,
            "Database / Entity Layer",
            "Database entities or their schema may require changes to support the requirement.",
            "Medium",
        )

        self._add_layer_impact(
            ctx.endpoint_impacts,
            blast_radius,
            "API / Endpoint Layer",
            "Existing or new API endpoints may require request, response, or behavioral changes.",
            "Medium",
        )

        self._add_layer_impact(
            ctx.model_impacts,
            blast_radius,
            "Request / Response Model Layer",
            "Pydantic request or response models may require schema or validation changes.",
            "Medium",
        )

        self._add_layer_impact(
            ctx.business_logic_impacts,
            blast_radius,
            "Business Logic / Service Layer",
            "Business rules, application services, workflows, or validations may require changes.",
            "High",
        )

        self._add_layer_impact(
            ctx.repository_impacts,
            blast_radius,
            "Repository / Data Access Layer",
            "Database queries, repository methods, CRUD operations, or data-access logic may change.",
            "Medium",
        )

        self._add_layer_impact(
            ctx.integration_impacts,
            blast_radius,
            "External Integration Layer",
            "External services or third-party integrations may be required or modified.",
            "High",
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
        reason: str,
        severity: str,
    ) -> None:

        if not impacts:
            return

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

            blast_radius.append(
                BlastRadius(
                    component=impact.component,
                    reason=impact.reason or impact.change,
                    severity="Medium",
                )
            )

    def _deduplicate(
        self,
        impacts: list[BlastRadius],
    ) -> list[BlastRadius]:

        unique: dict[str, BlastRadius] = {}

        for impact in impacts:

            key = impact.component.lower()

            if key not in unique:
                unique[key] = impact

        return list(unique.values())