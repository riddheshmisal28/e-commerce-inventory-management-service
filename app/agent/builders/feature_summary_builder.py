def build_feature_summary(requirement):

    business_goal = (
        requirement.description.strip()
        .replace("\n", " ")
    )

    return {
        "name": requirement.title,
        "business_goal": business_goal
    }