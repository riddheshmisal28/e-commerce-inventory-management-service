import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.agent.models import (
    AnalysisContext,
    Requirement,
)
from app.agent.llm.analyzers.llm_requirement_planner import (
    LLMRequirementPlanner,
)
from app.agent.retrievers.context_retriever import (
    ContextRetriever,
)
from app.agent.analyzers.blast_radius import (
    BlastRadiusAnalyzer,
)
from app.agent.builders.report_builder import (
    ReportBuilder,
)
from app.agent.core.pipeline_executor import (
    PipelineExecutor,
)
from app.agent.reasoning.impact_reasoner import (
    ImpactReasoner,
)
from app.agent.validators.impact_validator import (
    ImpactValidator,
)
from app.agent.steps.semantic_impact_refiner import (
    SemanticImpactRefiner,
)
from app.agent.validators.grounding_validator import (
    GroundingValidator,
)

class ImpactAgent:

    def __init__(self, on_event=None):
        self.executor = PipelineExecutor(on_event=on_event)

        self.pipeline = [
            LLMRequirementPlanner(),
            ContextRetriever(),
            ImpactReasoner(),
            ImpactValidator(),
            GroundingValidator(),
            SemanticImpactRefiner(),
            BlastRadiusAnalyzer(),
            ReportBuilder(),
        ]

    def run(
        self,
        requirement: Requirement,
    ):
        ctx = AnalysisContext(
            requirement=requirement,
        )

        result = self.executor.run(
            self.pipeline,
            ctx,
        )

        return result


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
            "Duplicate alerts should not be generated within 24 hours.",
        ],
    )

    agent = ImpactAgent()

    result = agent.run(
        requirement,
    )

    print(result.model_dump_json(indent=2))

    # print(
    #     json.dumps(
    #         result.agent_run,
    #         indent=2,
    #     )
    # )