from app.agent.core.agent_step import AgentStep

from app.agent.context_client import (
EngineeringContextClient,
)

from app.agent.models import (
AnalysisContext,
EngineeringContext,
)

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

        # ---------------------------------------------------------
        # Database entities
        # ---------------------------------------------------------

        if plan.need_entities:

            context.entities = self.client.get_entities()

            context.retrieved_sources.append(
                "entities",
            )

        # ---------------------------------------------------------
        # API endpoints
        # ---------------------------------------------------------

        if plan.need_endpoints:

            context.endpoints = self.client.get_endpoints()

            context.retrieved_sources.append(
                "endpoints",
            )

        # ---------------------------------------------------------
        # Pydantic request/response models
        # ---------------------------------------------------------

        if plan.need_models:

            context.models = self.client.get_models()

            context.retrieved_sources.append(
                "models",
            )

        # ---------------------------------------------------------
        # OpenAPI specification
        # ---------------------------------------------------------

        if plan.need_openapi:

            context.openapi = self.client.get_openapi()

            context.retrieved_sources.append(
                "openapi",
            )

        # ---------------------------------------------------------
        # Business logic
        # ---------------------------------------------------------

        if plan.need_business_logic:

            context.business_logic = (
                self.client.get_business_logic(
                    keywords=plan.keywords,
                )
            )

            context.retrieved_sources.append(
                "business_logic",
            )

        # ---------------------------------------------------------
        # Repository / data-access logic
        # ---------------------------------------------------------

        if plan.need_repositories:

            context.repositories = (
                self.client.get_repositories(
                    keywords=plan.keywords,
                )
            )

            context.retrieved_sources.append(
                "repositories",
            )

        # ---------------------------------------------------------
        # External integrations
        # ---------------------------------------------------------

        if plan.need_integrations:

            context.integrations = (
                self.client.get_integrations(
                    keywords=plan.keywords,
                )
            )

            context.retrieved_sources.append(
                "integrations",
            )

        # ---------------------------------------------------------
        # Engineering documentation
        # ---------------------------------------------------------

        if plan.need_documentation:

            context.documentation = (
                self.client.get_documentation(
                    keywords=plan.keywords,
                )
            )

            context.retrieved_sources.append(
                "documentation",
            )


        # ---------------------------------------------------------
        # Engineering components
        # ---------------------------------------------------------

        if plan.need_components:

            context.components = self.client.get_components(
                keywords=plan.keywords,
            )

            context.retrieved_sources.append(
                "components",
            )
        ctx.engineering_context = context