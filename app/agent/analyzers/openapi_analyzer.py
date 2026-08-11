from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ApiMutation,
)


class OpenAPIAnalyzer(AgentStep):

    name = "OpenAPI Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        openapi = ctx.engineering_context.openapi

        if not openapi:
            return

        existing = {
            (
                impact.endpoint,
                impact.change_type,
            )
            for impact in ctx.endpoint_impacts
        }

        for path, methods in openapi.get(
            "paths",
            {},
        ).items():

            for method, definition in methods.items():

                if method.lower() == "parameters":
                    continue

                if not self._matches_keywords(
                    ctx,
                    path,
                    definition,
                ):
                    continue

                change_type = self._determine_change_type(
                    definition,
                )

                key = (
                    path,
                    change_type,
                )

                if key in existing:
                    continue

                ctx.endpoint_impacts.append(
                    ApiMutation(
                        endpoint=path,
                        change_type=change_type,
                        details=(
                            f"OpenAPI contract for "
                            f"{method.upper()} {path} "
                            f"may require changes."
                        ),
                    )
                )

                existing.add(key)

    def _matches_keywords(
        self,
        ctx: AnalysisContext,
        path: str,
        definition: dict,
    ) -> bool:

        keywords = (
            ctx.context_plan.keywords
            if ctx.context_plan
            else []
        )

        searchable_text = " ".join(
            [
                path,
                definition.get("summary", ""),
                definition.get("description", ""),
                definition.get("operationId", ""),
            ]
        ).lower()

        return any(
            keyword.lower() in searchable_text
            for keyword in keywords
        )

    def _determine_change_type(
        self,
        definition: dict,
    ) -> str:

        if definition.get("requestBody"):
            return "Request Contract Update"

        if definition.get("responses"):
            return "Response Contract Update"

        if definition.get("parameters"):
            return "Parameter Contract Update"

        return "API Contract Update"