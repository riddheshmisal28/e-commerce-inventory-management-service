from app.agent.core.agent_step import AgentStep
from app.agent.context_client import EngineeringContextClient
from app.agent.models import AnalysisContext, EngineeringContext


class ContextRetriever(AgentStep):

    name = "Context Retriever"

    def __init__(self):
        self.client = EngineeringContextClient()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        plan = ctx.context_plan

        if plan is None:
            raise ValueError(
                "ContextPlan must be generated before retrieving context."
            )

        context = EngineeringContext()

        if plan.need_entities:
            context.entities = self.client.get_entities()
            context.retrieved_sources.append("entities")

        if plan.need_endpoints:
            context.endpoints = self.client.get_endpoints()
            context.retrieved_sources.append("endpoints")

        if plan.need_models:
            context.models = self.client.get_models()
            context.retrieved_sources.append("models")

        ctx.engineering_context = context