from __future__ import annotations

from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext, ContextPlan, Requirement

PLANNING_RULES = [
{
    "keywords": [
        "stock",
        "inventory",
        "quantity",
        "sku",
    ],
    "need_entities": True,
    "need_endpoints": True,
    "need_business_logic": True,
    "need_repositories": True,
},
{
    "keywords": [
        "product",
    ],
    "need_entities": True,
    "need_endpoints": True,
    "need_business_logic": True,
    "need_repositories": True,
},
{
    "keywords": [
        "category",
    ],
    "need_entities": True,
    "need_repositories": True,
},
{
    "keywords": [
        "api",
        "request",
        "response",
        "endpoint",
    ],
    "need_endpoints": True,
    "need_models": True,
    "need_openapi": True,
},
{
    "keywords": [
        "validation",
        "validate",
        "rule",
        "business",
        "logic",
        "calculation",
        "calculate",
        "workflow",
        "condition",
    ],
    "need_business_logic": True,
},
{
    "keywords": [
        "repository",
        "query",
        "database",
        "crud",
        "fetch",
        "retrieve",
        "persist",
        "save",
        "update",
        "delete",
    ],
    "need_repositories": True,
    },
    {
    "keywords": [
        "email",
        "sms",
        "notification",
        "webhook",
        "external",
        "third-party",
        "integration",
        "payment",
        "provider",
    ],
    "need_integrations": True,
    },
    {
    "keywords": [
        "documentation",
        "architecture",
        "design",
        "adr",
        "system",
    ],
    "need_documentation": True,
    },
]

class RequirementAnalyzer(AgentStep):

    name = "Requirement Planner"

    required_context: set[str] = set()

    def execute(
        self,
        ctx: AnalysisContext | Requirement,
    ) -> ContextPlan:

        if hasattr(ctx, "requirement_text"):
            text = ctx.requirement_text.lower()
        elif hasattr(ctx, "title"):
            criteria_str = " ".join(getattr(ctx, "acceptance_criteria", []) or [])
            text = f"{getattr(ctx, 'title', '')} {getattr(ctx, 'description', '')} {criteria_str}".lower()
        else:
            text = str(ctx).lower()

        plan = ContextPlan()

        for rule in PLANNING_RULES:
            self._apply_rule(
                text=text,
                plan=plan,
                rule=rule,
            )

        plan.keywords = list(
            dict.fromkeys(plan.keywords)
        )

        if isinstance(ctx, AnalysisContext):
            ctx.context_plan = plan

        return plan

    def _apply_rule(
        self,
        text: str,
        plan: ContextPlan,
        rule: dict,
    ) -> None:

        keywords = rule["keywords"]

        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword in text
        ]

        if not matched_keywords:
            return

        if rule.get("need_entities"):
            plan.need_entities = True

        if rule.get("need_endpoints"):
            plan.need_endpoints = True

        if rule.get("need_models"):
            plan.need_models = True

        if rule.get("need_openapi"):
            plan.need_openapi = True

        if rule.get("need_business_logic"):
            plan.need_business_logic = True

        if rule.get("need_repositories"):
            plan.need_repositories = True

        if rule.get("need_integrations"):
            plan.need_integrations = True

        if rule.get("need_documentation"):
            plan.need_documentation = True

        plan.keywords.extend(
            matched_keywords
        )