from models import DataModelImpact


ENTITY_RULES = [
    {
        "keywords": ["stock", "inventory", "quantity"],
        "required_columns": ["quantity"],
        "impacts": [
            "Inventory quantity tracking exists. Low stock alert evaluation logic may be required.",
            "Consider adding low_stock_threshold configuration.",
            "Consider storing last_alert_timestamp to avoid duplicate notifications.",
        ],
    },
]


class EntityAnalyzer:

    def analyze(
        self,
        requirement: str,
        entities: list,
    ) -> list[DataModelImpact]:

        requirement = requirement.lower()

        impacts: list[DataModelImpact] = []

        for entity in entities:

            entity_name = entity["name"]

            columns = {
                column.lower()
                for column in entity["columns"]
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

        return impacts

    def _matches_requirement(
        self,
        requirement: str,
        keywords: list[str],
    ) -> bool:

        return any(
            keyword in requirement
            for keyword in keywords
        )

    def _matches_entity(
        self,
        columns: set[str],
        required_columns: list[str],
    ) -> bool:

        return all(
            column in columns
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


def analyze_entities(
    requirement: str,
    entities: list,
) -> list[DataModelImpact]:

    analyzer = EntityAnalyzer()

    return analyzer.analyze(
        requirement,
        entities,
    )