def build_clarification_questions(
    requirement
):

    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    questions = []

    if "threshold" in text:
        questions.append(
            "Should thresholds be configurable per SKU or globally?"
        )

    if "alert" in text:
        questions.append(
            "How should alerts be delivered (email, SMS, in-app)?"
        )

        questions.append(
            "Should alerts be re-triggered after stock is replenished?"
        )

    return questions