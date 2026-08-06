from models import (
    AnalysisContext,
    Requirement,
)

from analyzers.requirement_analyzer import RequirementAnalyzer
from retrievers.context_retriever import ContextRetriever
from analyzers.entity_analyzer import EntityAnalyzer
from analyzers.endpoint_analyzer import EndpointAnalyzer
from analyzers.blast_radius import BlastRadiusAnalyzer
from builders.report_builder import ReportBuilder

from core.pipeline_executor import PipelineExecutor


class ImpactAgent:

    def __init__(self):

        self.executor = PipelineExecutor()

        self.pipeline = [
            RequirementAnalyzer(),
            ContextRetriever(),
            EntityAnalyzer(),
            EndpointAnalyzer(),
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

    print(result.model_dump())