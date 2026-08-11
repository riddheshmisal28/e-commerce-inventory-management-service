from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    BusinessLogicImpact,
)


class BusinessLogicAnalyzer(AgentStep):

    name = "Business Logic Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[BusinessLogicImpact] = []

        requirement = ctx.requirement_text

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
                requirement=requirement,
                keywords=keywords,
            ):
                continue

            impacts.append(
                BusinessLogicImpact(
                    component=component,
                    change=change,
                )
            )

        ctx.business_logic_impacts = impacts

    def _is_relevant(
        self,
        component: str,
        change: str,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        context = (
            f"{component} {change}"
        ).lower()

        if any(
            keyword.lower() in context
            for keyword in keywords
        ):
            return True

        requirement_keywords = [
            "stock",
            "inventory",
            "quantity",
            "threshold",
            "alert",
            "notification",
        ]

        return any(
            keyword in requirement
            and keyword in context
            for keyword in requirement_keywords
        )