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

class ImpactAgent:

    def __init__(self):

        self.planner = RequirementAnalyzer()
        self.retriever = ContextRetriever()
        self.entity_analyzer = EntityAnalyzer()
        self.endpoint_analyzer = EndpointAnalyzer()
        self.blast_radius_analyzer = BlastRadiusAnalyzer()
        self.report_builder = ReportBuilder()

    def run(
        self,
        requirement: Requirement,
    ):

        ctx = AnalysisContext(requirement=requirement)

        self.planner.analyze(ctx)
        self.retriever.retrieve(ctx)
        self.entity_analyzer.analyze(ctx)
        self.endpoint_analyzer.analyze(ctx)
        self.blast_radius_analyzer.analyze(ctx)
        return self.report_builder.build(ctx)


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

    result = agent.run(requirement)

    print(result)