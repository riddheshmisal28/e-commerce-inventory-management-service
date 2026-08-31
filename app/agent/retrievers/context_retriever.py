import time
from typing import Optional

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

    required_context: set[str] = set()

    # TTL-based cache configuration (in seconds)
    DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        self.client = EngineeringContextClient()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Optional[dict] = None
        self._cache_timestamp: Optional[float] = None

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        plan = ctx.context_plan

        if plan is None:
            raise ValueError(
                "ContextPlan must be generated before retrieving context."
            )

        # Check if cached context is still valid
        cached_context = self._get_cached_context()
        if cached_context is not None:
            ctx.engineering_context = cached_context
            ctx.engineering_context.retrieved_sources.append("__cached__")
            return

        context = EngineeringContext()

        keywords = self._get_keywords(
            ctx,
        )

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

            context.endpoints = self.client.get_endpoints(
            )

            context.retrieved_sources.append(
                "endpoints",
            )

        # ---------------------------------------------------------
        # Pydantic request/response models
        # ---------------------------------------------------------

        if plan.need_models:

            context.models = self.client.get_models(
            )

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
                    keywords=keywords,
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
                    keywords=keywords,
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
                    keywords=keywords,
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
                    keywords=keywords,
                )
            )

            context.retrieved_sources.append(
                "documentation",
            )

        # ---------------------------------------------------------
        # Engineering components
        # ---------------------------------------------------------

        if plan.need_components:

            context.components = (
                self.client.get_components(
                    keywords=keywords,
                )
            )

            context.retrieved_sources.append(
                "components",
            )

        # ---------------------------------------------------------
        # Cache the retrieved context
        # ---------------------------------------------------------

        self._set_cache(context)

        # ---------------------------------------------------------
        # Store retrieved engineering context
        # ---------------------------------------------------------

        ctx.engineering_context = context

    def _get_cached_context(self) -> Optional[EngineeringContext]:
        """
        Retrieve cached context if it exists and hasn't expired.
        
        Returns None if cache is empty or expired.
        """
        if self._cache is None or self._cache_timestamp is None:
            return None

        # Check if cache has expired
        elapsed = time.time() - self._cache_timestamp
        if elapsed > self.cache_ttl_seconds:
            self._cache = None
            self._cache_timestamp = None
            return None

        # Return a copy of cached context to avoid external mutations
        try:
            return EngineeringContext(**self._cache)
        except Exception:
            # If cache is corrupted, clear it
            self._cache = None
            self._cache_timestamp = None
            return None

    def _set_cache(self, context: EngineeringContext) -> None:
        """
        Cache the engineering context with current timestamp.
        """
        self._cache = context.model_dump() if hasattr(context, "model_dump") else context.__dict__
        self._cache_timestamp = time.time()

    def invalidate_cache(self) -> None:
        """
        Manually invalidate the cache (e.g., on codebase changes).
        """
        self._cache = None
        self._cache_timestamp = None

    @staticmethod
    def _get_keywords(
        ctx: AnalysisContext,
    ) -> list[str]:

        """
        Return planner-generated keywords.

        If the LLM planner returns no keywords, use a small
        deterministic fallback based on the requirement.

        This prevents keyword-dependent context retrieval
        from silently returning no results.
        """

        plan = ctx.context_plan

        if plan is not None and plan.keywords:

            return list(
                dict.fromkeys(
                    keyword.strip().lower()
                    for keyword in plan.keywords
                    if keyword and keyword.strip()
                )
            )

        return ContextRetriever._fallback_keywords(
            ctx,
        )

    @staticmethod
    def _fallback_keywords(
        ctx: AnalysisContext,
    ) -> list[str]:

        """
        Deterministic fallback keywords.

        This is intentionally conservative. It should provide
        useful retrieval terms without trying to perform impact
        analysis.
        """

        requirement = ctx.requirement

        text_parts = [
            getattr(requirement, "title", "") or "",
            getattr(requirement, "description", "") or "",
        ]

        acceptance_criteria = getattr(
            requirement,
            "acceptance_criteria",
            None,
        )

        if acceptance_criteria:

            if isinstance(
                acceptance_criteria,
                list,
            ):
                text_parts.extend(
                    str(item)
                    for item in acceptance_criteria
                )

            else:
                text_parts.append(
                    str(acceptance_criteria)
                )

        text = " ".join(text_parts).lower()

        # Domain-specific terms that are useful for retrieval.
        #
        # This is NOT intended to determine impacts.
        known_terms = [
            "sku",
            "stock",
            "quantity",
            "threshold",
            "inventory",
            "alert",
            "notification",
            "product",
            "order",
            "inactive",
            "email",
            "sms",
            "event",
            "scheduler",
            "worker",
            "duplicate",
        ]

        return [
            keyword
            for keyword in known_terms
            if keyword in text
        ]