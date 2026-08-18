from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


class IntegrationAnalyzer(AgentStep):

    name = "Integration Analyzer"

    required_context = {
        "integrations",
    }

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[ComponentImpact] = []

        keywords = (
            ctx.context_plan.keywords
            if ctx.context_plan
            else []
        )

        for item in ctx.engineering_context.integrations:

            integration = item.get("integration")

            if not integration:
                continue

            change = item.get("change")

            if not change:
                continue

            if not self._is_relevant(
                integration=integration,
                change=change,
                keywords=keywords,
            ):
                continue

            impacts.append(
                ComponentImpact(
                    component=integration,
                    impact_type="Integration",
                    change=change,
                    reason=item.get("reason"),
                )
            )

        ctx.integration_impacts = impacts

    def _is_relevant(
        self,
        integration: str,
        change: str,
        keywords: list[str],
    ) -> bool:

        context = (
            f"{integration} {change}"
        ).lower()

        return any(
            keyword.lower() in context
            for keyword in keywords
        )