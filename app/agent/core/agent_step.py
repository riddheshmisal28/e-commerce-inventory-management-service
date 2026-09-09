from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING

from app.agent.models import AnalysisContext

if TYPE_CHECKING:
    from app.agent.execution.execution_policy import ExecutionPolicy


class AgentStep(ABC):
    """
    Base class for every step in the Impact Analysis pipeline.
    Each step receives the shared AnalysisContext, performs its work,
    and updates the context in-place.
    
    Supports both sync (execute) and async (execute_async) modes.
    If execute_async is implemented, the pipeline can run it in async context.
    """

    name = "Unnamed Step"

    required_context: set[str] = set()

    execution_policy: "ExecutionPolicy | None" = None

    @abstractmethod
    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:
        """
        Execute the pipeline step (synchronous).
        """
        pass

    async def execute_async(
        self,
        ctx: AnalysisContext,
    ) -> None:
        """
        Execute the pipeline step asynchronously (optional).
        
        By default, this wraps the sync execute() in asyncio.to_thread
        to avoid blocking the event loop. Override to provide native async support.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.execute,
            ctx,
        )