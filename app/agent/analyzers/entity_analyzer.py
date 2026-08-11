from app.agent.core.agent_step import AgentStep
from app.agent.models import (
    AnalysisContext,
    DataModelImpact,
)

ENTITY_RULES = [
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
        ],
        "required_columns": [
            "quantity",
        ],
        "impacts": [
            "Inventory quantity tracking exists. Low stock alert evaluation logic may be required.",
            "Consider adding low_stock_threshold configuration.",
            "Consider storing last_alert_timestamp to avoid duplicate notifications.",
        ],
    },  
]

class EntityAnalyzer(AgentStep):

    name = "Entity Analyzer"

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        requirement = self._build_requirement_text(
            ctx,
        )

        impacts: list[DataModelImpact] = []

        for entity in ctx.engineering_context.entities:

            entity_name = entity.get(
                "name",
                "",
            )

            columns = {
                column.lower()
                for column in entity.get(
                    "columns",
                    [],
                )
            }

            for rule in ENTITY_RULES:

                if not self._matches_requirement(
                    requirement,
                    rule["keywords"],
                ):
                    continue

                if not self._matches_entity(
                    columns,
                    rule["required_columns"],
                ):
                    continue

                impacts.extend(
                    self._build_impacts(
                        entity_name,
                        rule["impacts"],
                    )
                )

        ctx.entity_impacts = impacts

    def _build_requirement_text(
        self,
        ctx: AnalysisContext,
    ) -> str:

        requirement = ctx.requirement

        return f"""
        {requirement.title}

        {requirement.description}

        {' '.join(requirement.acceptance_criteria)}
        """.lower()

    def _matches_requirement(
        self,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        return any(
            keyword.lower() in requirement
            for keyword in keywords
        )

    def _matches_entity(
        self,
        columns: set[str],
        required_columns: list[str],
    ) -> bool:

        return all(
            column.lower() in columns
            for column in required_columns
        )

    def _build_impacts(
        self,
        entity_name: str,
        changes: list[str],
    ) -> list[DataModelImpact]:

        return [
            DataModelImpact(
                entity=entity_name,
                change=change,
            )
            for change in changes
        ]
