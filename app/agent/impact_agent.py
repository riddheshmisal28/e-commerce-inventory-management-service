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
from app.agent.steps.code_facts_extractor import (
    CodeFactsExtractor,
)
from app.agent.steps.dependency_graph_builder import (
    DependencyGraphBuilderStep,
)
from app.agent.steps.evidence_collection import (
    EvidenceCollectionStep,
)

class ImpactAgent:

    def __init__(self, on_event=None):
        self.executor = PipelineExecutor(on_event=on_event)

        self.pipeline = [
            LLMRequirementPlanner(),
            ContextRetriever(),
            CodeFactsExtractor(),
            DependencyGraphBuilderStep(),     
            EvidenceCollectionStep(),          
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
        id="low-stock-alert",
        title="Low Stock Alert",
        tag="Inventory & Notifications",
        description=(
            "Notify inventory managers when a SKU's quantity falls below "
            "its configured threshold. The system must evaluate the SKU "
            "quantity against the configured threshold and send a notification "
            "when the condition is met."
        ),
        acceptance_criteria=[
            "Trigger an alert when a SKU's quantity is below its configured threshold.",
            "Do not trigger an alert when the SKU's quantity is equal to or above its configured threshold.",
            "The alert must notify the inventory manager.",
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