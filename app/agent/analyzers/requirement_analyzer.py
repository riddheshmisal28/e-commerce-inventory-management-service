from models import Requirement, ContextPlan

PLANNING_RULES = [
    {
        "keywords": ["stock", "inventory", "quantity", "sku"],
        "need_entities": True,
        "need_endpoints": True,
    },
    {
        "keywords": ["product"],
        "need_entities": True,
        "need_endpoints": True,
    },
    {
        "keywords": ["category"],
        "need_entities": True,
    },
    {
        "keywords": ["api", "request", "response", "endpoint"],
        "need_endpoints": True,
    },
]


class RequirementAnalyzer:

    def analyze(
        self,
        requirement: Requirement,
    ) -> ContextPlan:

        text = self._build_requirement_text(requirement)

        plan = ContextPlan()

        for rule in PLANNING_RULES:
            self._apply_rule(
                text=text,
                plan=plan,
                rule=rule,
            )

        # Remove duplicate keywords while preserving order
        plan.keywords = list(dict.fromkeys(plan.keywords))

        return plan

    def _build_requirement_text(
        self,
        requirement: Requirement,
    ) -> str:

        return f"""
        {requirement.title}

        {requirement.description}

        {' '.join(requirement.acceptance_criteria)}
        """.lower()

    def _apply_rule(
        self,
        text: str,
        plan: ContextPlan,
        rule: dict,
    ):

        keywords = rule["keywords"]

        if not any(keyword in text for keyword in keywords):
            return

        if rule.get("need_entities"):
            plan.need_entities = True

        if rule.get("need_endpoints"):
            plan.need_endpoints = True

        if rule.get("need_models"):
            plan.need_models = True

        if rule.get("need_openapi"):
            plan.need_openapi = True

        if rule.get("need_documentation"):
            plan.need_documentation = True

        plan.keywords.extend(keywords)


def analyze_requirement(
    requirement: Requirement,
) -> ContextPlan:
    """
    Convenience function so existing callers don't break.
    """
    analyzer = RequirementAnalyzer()
    return analyzer.analyze(requirement)