from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    IntegrationImpact,
)


class IntegrationAnalyzer(AgentStep):

    name = "Integration Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[IntegrationImpact] = []

        for item in ctx.engineering_context.integrations:

            integration = item.get("integration")

            if not integration:
                continue

            change = item.get("change")

            if not change:
                continue

            impacts.append(
                IntegrationImpact(
                    integration=integration,
                    change=change,
                )
            )

        ctx.integration_impacts = impacts