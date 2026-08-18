from abc import ABC, abstractmethod

from app.agent.models import AnalysisContext


class AgentStep(ABC):
    """
    Base class for every step in the Impact Analysis pipeline.
    Each step receives the shared AnalysisContext, performs its work,
    and updates the context in-place.
    """

    name = "Unnamed Step"

    required_context: set[str] = set()

    @abstractmethod
    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:
        """
        Execute the pipeline step.
        """
        pass