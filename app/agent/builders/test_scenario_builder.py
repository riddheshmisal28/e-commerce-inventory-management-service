def build_test_scenarios(
    requirement
):

    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    scenarios = {
        "happy_path": [],
        "negative_cases": [],
        "edge_cases": []
    }

    if "stock" in text:

        scenarios["happy_path"].extend([
            "Alert generated when quantity falls below threshold",
            "Threshold updated successfully"
        ])

        scenarios["negative_cases"].extend([
            "Negative threshold value provided",
            "Inactive SKU receives alert"
        ])

        scenarios["edge_cases"].extend([
            "Quantity exactly equals threshold",
            "Concurrent inventory updates"
        ])

    return scenarios