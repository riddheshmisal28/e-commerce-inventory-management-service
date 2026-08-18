from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
)


BUSINESS_LOGIC_RULES = [
    {
        "keywords": [
            "stock",
            "inventory",
            "quantity",
            "threshold",
        ],
        "impact_type": "ADD_RULE",
        "change": (
            "Evaluate inventory quantity against "
            "the configured low-stock threshold "
            "and trigger the low-stock workflow "
            "when the threshold is breached."
        ),
        "reason": (
            "The requirement introduces a business rule "
            "based on inventory quantity and threshold."
        ),
    },
    {
        "keywords": [
            "notification",
            "alert",
        ],
        "impact_type": "ADD_RULE",
        "change": (
            "Prevent duplicate low-stock alerts "
            "until the inventory condition is reset."
        ),
        "reason": (
            "Low-stock notifications require "
            "duplicate-alert prevention."
        ),
    },
]


class BusinessLogicAnalyzer(AgentStep):

    name = "Business Logic Analyzer"

    required_context = {
        "business_logic",
    }

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts: list[ComponentImpact] = []

        requirement = (
            ctx.requirement_text
        )

        keywords = (
            ctx.context_plan.keywords
            if ctx.context_plan
            else []
        )

        for item in (
            ctx.engineering_context.business_logic
        ):

            component = item.get(
                "component",
            )

            if not component:
                continue

            change = item.get(
                "change",
            )

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
                    impact_type=item.get(
                        "impact_type",
                        "MODIFY_RULE",
                    ),
                    change=change,
                    reason=item.get(
                        "reason",
                    ),
                )
            )

        impacts.extend(
            self._infer_impacts(
                requirement=requirement,
                keywords=keywords,
                existing_impacts=impacts,
            )
        )

        ctx.business_logic_impacts = impacts

    def _infer_impacts(
        self,
        requirement: str,
        keywords: list[str],
        existing_impacts: list[ComponentImpact],
    ) -> list[ComponentImpact]:

        impacts: list[ComponentImpact] = []

        existing_changes = {
            impact.change.lower()
            for impact in existing_impacts
        }

        for rule in BUSINESS_LOGIC_RULES:

            if not self._matches_rule(
                requirement=requirement,
                keywords=keywords,
                rule_keywords=rule["keywords"],
            ):
                continue

            change = rule["change"]

            if change.lower() in existing_changes:
                continue

            impacts.append(
                ComponentImpact(
                    component="Inventory Business Logic",
                    impact_type=rule[
                        "impact_type"
                    ],
                    change=change,
                    reason=rule[
                        "reason"
                    ],
                )
            )

        return impacts

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

    def _matches_rule(
        self,
        requirement: str,
        keywords: list[str],
        rule_keywords: list[str],
    ) -> bool:

        requirement = requirement.lower()

        if keywords:
            if not any(
                keyword.lower() in requirement
                for keyword in keywords
            ):
                return False

        return any(
            keyword.lower() in requirement
            for keyword in rule_keywords
        )