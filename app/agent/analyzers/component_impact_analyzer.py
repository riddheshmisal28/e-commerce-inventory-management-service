from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


class ComponentImpactAnalyzer(AgentStep):

    name = "Component Impact Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[ComponentImpact] = []

        for item in ctx.engineering_context.components:

            component = item.get("component")

            if not component:
                continue

            impact_type = item.get("impact_type")

            if not impact_type:
                continue

            change = item.get("change")

            if not change:
                continue

            impacts.append(
                ComponentImpact(
                    component=component,
                    impact_type=impact_type,
                    change=change,
                    reason=item.get("reason"),
                )
            )

        ctx.component_impacts = impacts