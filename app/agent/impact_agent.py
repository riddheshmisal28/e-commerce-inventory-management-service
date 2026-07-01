from models import (
    ImpactAnalysisReport,
    Requirement
)
from builders.feature_summary_builder import (
    build_feature_summary
)

from builders.clarification_builder import (
    build_clarification_questions
)

from builders.test_scenario_builder import (
    build_test_scenarios
)

from builders.bdd_builder import (
    build_bdd_scenarios
)

from analyzers.entity_analyzer import analyze_entities
from analyzers.endpoint_analyzer import analyze_endpoints
from analyzers.blast_radius import build_blast_radius
from analyzers.requirement_analyzer import analyze_requirement

from retrievers.context_retriever import retrieve_context


def build_requirement_text(
    requirement: Requirement
) -> str:
    return f"""
    {requirement.title}

    {requirement.description}

    {' '.join(requirement.acceptance_criteria)}
    """

class ImpactAgent:

    def run(
        self,
        requirement: Requirement
    ):

        plan = analyze_requirement(
            requirement
        )

        context = retrieve_context(
            plan
        )

        requirement_text = build_requirement_text(
            requirement
        )

        entity_impacts = analyze_entities(
            requirement_text,
            context.entities
        )

        endpoint_impacts = analyze_endpoints(
            requirement_text,
            context.endpoints
        )

        feature_summary = (
            build_feature_summary(
                requirement
            )
        )

        clarification_questions = (
            build_clarification_questions(
                requirement
            )
        )

        test_scenarios = (
            build_test_scenarios(
                requirement
            )
        )

        bdd_scenarios = (
            build_bdd_scenarios(
                requirement
            )
        )

        blast_radius = (
            build_blast_radius(
                entity_impacts,
                endpoint_impacts
            )
        )

        report = ImpactAnalysisReport(
            feature_summary=feature_summary,
            component_blast_radius=blast_radius,
            potential_data_model_impact=entity_impacts,
            api_interface_mutations=endpoint_impacts,
            clarification_questions=clarification_questions,
            test_scenarios=test_scenarios,
            bdd_scenarios=bdd_scenarios
        )

        return report.model_dump()

if __name__ == "__main__":

    requirement = Requirement(
        title="Low Stock Alert",
        description="""
        Notify inventory managers when stock
        falls below a configurable threshold.
        """,
        acceptance_criteria=[
            "Alert should trigger when quantity is below threshold.",
            "Alert should not trigger for inactive products.",
            "Threshold should be configurable per SKU.",
            "Duplicate alerts should not be generated within 24 hours."
        ]
    )

    agent = ImpactAgent()

    result = agent.run(
        requirement
    )

    print(result)