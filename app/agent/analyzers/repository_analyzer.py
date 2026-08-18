from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


class RepositoryAnalyzer(AgentStep):

    name = "Repository Analyzer"

    required_context = {
        "repositories",
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
                keywords=keywords,
            ):
                continue

            impacts.append(
                ComponentImpact(
                    component=repository,
                    impact_type="Repository",
                    change=change,
                    reason=item.get("reason"),
                )
            )

        ctx.repository_impacts = impacts

    def _is_relevant(
        self,
        repository: str,
        change: str,
        keywords: list[str],
    ) -> bool:

        context = (
            f"{repository} {change}"
        ).lower()

        return any(
            keyword.lower() in context
            for keyword in keywords
        )