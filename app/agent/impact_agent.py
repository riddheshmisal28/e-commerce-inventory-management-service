from context_client import (
    get_endpoints,
    get_entities
)

def collect_context():

    return {
        "endpoints": get_endpoints(),
        "entities": get_entities()
    }

def analyze_requirement(
    requirement: str,
    context: dict
):
    impacted = []

    req = requirement.lower()

    entities = context["entities"]

    for entity in entities:

        columns = [
            column.lower()
            for column in entity["columns"]
        ]

        if "stock" in req and "quantity" in columns:

            impacted.append(
                {
                    "name": entity["name"],
                    "reason": "Contains quantity field used for inventory tracking"
                }
            )

    return impacted

def run(requirement: str):

    context = collect_context()

    impacted = analyze_requirement(
        requirement,
        context
    )

    return {
        "requirement": requirement,
        "impacted_components": impacted,
        "available_entities":
            context["entities"]
    }

if __name__ == "__main__":
    result = run(
        "Add low stock alert feature"
    )

    print(result)