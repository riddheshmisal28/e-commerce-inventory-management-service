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

        repositories = ctx.engineering_context.repositories

        for item in repositories:

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
                    change_type="Repository",
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

        normalized_keywords = {
            keyword.strip().lower()
            for keyword in keywords
            if keyword and keyword.strip()
        }

        return any(
            keyword in context
            for keyword in normalized_keywords
        )