from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


class ComponentImpactAnalyzer(AgentStep):

    name = "Component Impact Analyzer"
    
    required_context = {
        "components",
    }

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[ComponentImpact] = []

        for item in ctx.engineering_context.components:

            component = item.get("component")

            if not component:
                continue

            change_type = item.get("change_type")

            if not change_type:
                continue

            change = item.get("change")

            if not change:
                continue

            impacts.append(
                ComponentImpact(
                    component=component,
                    change_type=change_type,
                    change=change,
                    reason=item.get("reason"),
                )
            )

        ctx.component_impacts = impacts