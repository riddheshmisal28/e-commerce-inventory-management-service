from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    RepositoryImpact,
)


class RepositoryAnalyzer(AgentStep):

    name = "Repository Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[RepositoryImpact] = []

        requirement = ctx.requirement_text

        keywords = (
            ctx.context_plan.keywords
            if ctx.context_plan
            else []
        )

        for item in ctx.engineering_context.repositories:

            repository = item.get("repository")

            if not repository:
                continue

            change = item.get("change")

            if not change:
                continue

            if not self._is_relevant(
                repository=repository,
                change=change,
                requirement=requirement,
                keywords=keywords,
            ):
                continue

            impacts.append(
                RepositoryImpact(
                    repository=repository,
                    change=change,
                )
            )

        ctx.repository_impacts = impacts

    def _is_relevant(
        self,
        repository: str,
        change: str,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        context = (
            f"{repository} {change}"
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
            "sku",
            "product",
        ]

        return any(
            keyword in requirement
            and keyword in context
            for keyword in requirement_keywords
        )