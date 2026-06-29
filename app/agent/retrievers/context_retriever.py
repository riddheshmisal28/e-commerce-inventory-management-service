from context_client import get_entities, get_endpoints, get_models

def retrieve_context(plan):
    context = {}

    if plan.need_entities:
        context["entities"] = get_entities()

    if plan.need_endpoints:
        context["endpoints"] = get_endpoints()

    if plan.need_models:
        context["models"] = get_models()

    return context