def build_bdd_scenarios(
    requirement
):

    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    scenarios = []

    if "stock" in text:

        scenarios.append(
            {
                "scenario":
                    "Generate Low Stock Alert",

                "given":
                    "SKU quantity is below threshold",

                "when":
                    "Inventory evaluation executes",

                "then":
                    "A low stock alert is generated"
            }
        )

    return scenarios