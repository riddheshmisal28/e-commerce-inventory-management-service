from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


class BusinessLogicAnalyzer(AgentStep):

    name = "Business Logic Analyzer"

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

        for item in ctx.engineering_context.business_logic:

            component = item.get("component")

            if not component:
                continue

            change = item.get("change")

            if not change:
                continue

            if not self._is_relevant(
                component=component,
                change=change,
                keywords=keywords,
            ):
                continue

            impacts.append(
                ComponentImpact(
                    component=component,
                    impact_type="Business Logic",
                    change=change,
                    reason=item.get("reason"),
                )
            )

        ctx.business_logic_impacts = impacts

    def _is_relevant(
        self,
        component: str,
        change: str,
        keywords: list[str],
    ) -> bool:

        context = (
            f"{component} {change}"
        ).lower()

        return any(
            keyword.lower() in context
            for keyword in keywords
        )