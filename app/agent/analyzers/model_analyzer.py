from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ModelImpact,
)


class ModelAnalyzer(AgentStep):

    name = "Model Analyzer"

    required_context = {
        "models",
    }

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        requirement = ctx.requirement_text

        impacts: list[ModelImpact] = []

        keywords = (
            ctx.context_plan.keywords
            if ctx.context_plan
            else []
        )

        if not self._is_relevant(
            requirement,
            keywords,
        ):
            ctx.model_impacts = impacts
            return

        for model in ctx.engineering_context.models:

            model_name = model.get("name")

            if not model_name:
                continue

            schema = model.get(
                "schema",
                {},
            )

            properties = schema.get(
                "properties",
                {},
            )

            model_fields = {
                field.lower()
                for field in properties.keys()
            }

            if "quantity" in model_fields:

                change = (
                    "Consider exposing "
                    "low-stock threshold and "
                    "stock status in the model."
                )

            else:

                change = (
                    "Model may require fields "
                    "to represent low-stock "
                    "threshold or stock status."
                )

            impacts.append(
                ModelImpact(
                    model=model_name,
                    change=change,
                )
            )

        ctx.model_impacts = impacts

    def _is_relevant(
        self,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        if keywords:
            return any(
                keyword.lower() in requirement
                for keyword in keywords
            )

        return any(
            keyword in requirement
            for keyword in [
                "stock",
                "inventory",
                "quantity",
                "sku",
                "threshold",
            ]
        )