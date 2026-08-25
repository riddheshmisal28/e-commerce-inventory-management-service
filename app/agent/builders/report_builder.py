from app.agent.core.agent_step import AgentStep

from app.agent.models import (
    AnalysisContext,
    ImpactAnalysisReport,
)

from app.agent.builders.feature_summary_builder import (
    build_feature_summary,
)

from app.agent.builders.clarification_builder import (
    build_clarification_questions,
)

from app.agent.builders.test_scenario_builder import (
    build_test_and_bdd_scenarios,
)


class ReportBuilder(AgentStep):

    name = "Report Builder"

    required_context: set[str] = set()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> ImpactAnalysisReport:

        test_scenarios, bdd_scenarios = build_test_and_bdd_scenarios(
            ctx.requirement,
            ctx=ctx,
        )

        report = ImpactAnalysisReport(
            feature_summary=build_feature_summary(
                ctx.requirement,
            ),
            component_blast_radius=(
                ctx.blast_radius
            ),
            data_model_impact=(
                ctx.entity_impacts
            ),
            api_interface_mutations=(
                ctx.endpoint_impacts
            ),
            model_impacts=(
                ctx.model_impacts
            ),
            business_logic_impacts=(
                ctx.business_logic_impacts
            ),
            repository_impacts=(
                ctx.repository_impacts
            ),
            integration_impacts=(
                ctx.integration_impacts
            ),
            component_impacts=(
                ctx.component_impacts
            ),
            clarification_questions=(
                build_clarification_questions(
                    ctx.requirement,
                    ctx=ctx,
                )
            ),
            test_scenarios=test_scenarios,
            bdd_scenarios=bdd_scenarios,
        )

        ctx.report = report

        return report