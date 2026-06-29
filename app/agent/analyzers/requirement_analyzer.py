from models import Requirement, ContextPlan


def analyze_requirement(
    requirement: Requirement
) -> ContextPlan:

    text = f"""
    {requirement.title}

    {requirement.description}

    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    plan = ContextPlan()

    # ---------- Inventory / Stock ----------
    if any(word in text for word in [
        "stock",
        "inventory",
        "quantity",
        "sku"
    ]):

        plan.need_entities = True
        plan.need_endpoints = True

        plan.keywords.extend([
            "stock",
            "inventory",
            "quantity",
            "sku"
        ])

    # ---------- Product ----------
    if "product" in text:

        plan.need_entities = True
        plan.need_endpoints = True

        plan.keywords.append("product")

    # ---------- Category ----------
    if "category" in text:

        plan.need_entities = True

        plan.keywords.append("category")

    # ---------- Validation/API ----------
    if any(word in text for word in [
        "api",
        "request",
        "response",
        "endpoint"
    ]):

        plan.need_endpoints = True

    return plan