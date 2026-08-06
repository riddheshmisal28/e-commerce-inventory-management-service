from core.agent_step import AgentStep
from models import (
    AnalysisContext,
    ImpactAnalysisReport,
)

from builders.feature_summary_builder import build_feature_summary
from builders.clarification_builder import build_clarification_questions
from builders.test_scenario_builder import build_test_scenarios
from builders.bdd_builder import build_bdd_scenarios


class ReportBuilder(AgentStep):

    name = "Report Builder"

    def execute(
        self,
        ctx: AnalysisContext,
    ):

        ctx.report = ImpactAnalysisReport(
            feature_summary=build_feature_summary(
                ctx.requirement
            ),
            component_blast_radius=ctx.blast_radius,
            potential_data_model_impact=ctx.entity_impacts,
            api_interface_mutations=ctx.endpoint_impacts,
            clarification_questions=build_clarification_questions(
                ctx.requirement
            ),
            test_scenarios=build_test_scenarios(
                ctx.requirement
            ),
            bdd_scenarios=build_bdd_scenarios(
                ctx.requirement
            ),
        )

        return ctx.report