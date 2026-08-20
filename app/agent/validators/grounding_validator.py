from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext
from app.core.logger import get_logger


logger = get_logger(__name__)


class GroundingValidator(AgentStep):

    name = "Grounding Validator"

    required_context: set[str] = set()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        ctx.entity_impacts = self._filter_entities(ctx)

        ctx.endpoint_impacts = self._filter_endpoints(ctx)

        ctx.model_impacts = self._filter_models(ctx)

        ctx.business_logic_impacts = (
            self._filter_components(
                ctx,
                "business_logic",
            )
        )

        ctx.repository_impacts = (
            self._filter_components(
                ctx,
                "repository",
            )
        )

        ctx.integration_impacts = (
            self._filter_components(
                ctx,
                "integration",
            )
        )

        ctx.component_impacts = (
            self._filter_components(
                ctx,
                "component",
            )
        )

    # =========================================================
    # ENTITIES
    # =========================================================

    def _filter_entities(
        self,
        ctx: AnalysisContext,
    ) -> list:

        known = {
            self._identifier(
                item,
                ("name", "entity", "table"),
            ).lower()
            for item in ctx.engineering_context.entities
        }

        return [
            impact
            for impact in ctx.entity_impacts
            if self._keep(
                impact.entity,
                known,
                "entity",
            )
        ]

    # =========================================================
    # ENDPOINTS
    # =========================================================

    def _filter_endpoints(
        self,
        ctx: AnalysisContext,
    ) -> list:

        known = {
            self._identifier(
                item,
                ("path", "endpoint", "name"),
            ).lower()
            for item in ctx.engineering_context.endpoints
        }

        return [
            impact
            for impact in ctx.endpoint_impacts
            if self._keep(
                impact.endpoint,
                known,
                "endpoint",
            )
        ]

    # =========================================================
    # MODELS
    # =========================================================

    def _filter_models(
        self,
        ctx: AnalysisContext,
    ) -> list:

        known = {
            self._identifier(
                item,
                ("name", "model"),
            ).lower()
            for item in ctx.engineering_context.models
        }

        return [
            impact
            for impact in ctx.model_impacts
            if self._keep(
                impact.model,
                known,
                "model",
            )
        ]

    # =========================================================
    # COMPONENTS
    # =========================================================

    def _filter_components(
        self,
        ctx: AnalysisContext,
        category: str,
    ) -> list:

        context_items = self._context_items(
            ctx,
            category,
        )

        known = {
            self._identifier(
                item,
                ("name", "component"),
            ).lower()
            for item in context_items
        }

        impacts = self._impact_items(
            ctx,
            category,
        )

        return [
            impact
            for impact in impacts
            if self._keep(
                impact.component,
                known,
                category,
            )
        ]

    # =========================================================
    # CONTEXT MAPPING
    # =========================================================

    def _context_items(
        self,
        ctx: AnalysisContext,
        category: str,
    ) -> list:

        mapping = {
            "business_logic":
                ctx.engineering_context.business_logic,

            "repository":
                ctx.engineering_context.repositories,

            "integration":
                ctx.engineering_context.integrations,

            "component":
                ctx.engineering_context.components,
        }

        return mapping.get(
            category,
            [],
        )

    # =========================================================
    # IMPACT MAPPING
    # =========================================================

    def _impact_items(
        self,
        ctx: AnalysisContext,
        category: str,
    ) -> list:

        mapping = {
            "business_logic":
                ctx.business_logic_impacts,

            "repository":
                ctx.repository_impacts,

            "integration":
                ctx.integration_impacts,

            "component":
                ctx.component_impacts,
        }

        return mapping.get(
            category,
            [],
        )

    # =========================================================
    # GROUNDING CHECK
    # =========================================================

    def _keep(
        self,
        identifier: str,
        known: set[str],
        category: str,
    ) -> bool:

        normalized_identifier = (
            str(identifier or "")
            .strip()
            .lower()
        )

        if not normalized_identifier:
            logger.warning(
                "Rejecting ungrounded %s impact: empty identifier",
                category,
            )
            return False

        if normalized_identifier in known:
            return True

        logger.warning(
            "Rejecting ungrounded %s impact: %s",
            category,
            identifier,
        )

        return False

    # =========================================================
    # IDENTIFIER EXTRACTION
    # =========================================================

    def _identifier(
        self,
        item,
        attributes: tuple[str, ...],
    ) -> str:

        for attribute in attributes:

            value = self._get_value(
                item,
                attribute,
            )

            if value is not None:

                value = str(value).strip()

                if value:
                    return value

        return str(item)

    # =========================================================
    # SAFE DICT / OBJECT ACCESS
    # =========================================================

    @staticmethod
    def _get_value(
        item,
        attribute: str,
    ):
        """
        Support both dictionary-based and object-based
        engineering context.

        EngineeringContextClient currently returns dictionaries,
        while some future context providers may return objects.
        """

        if isinstance(item, dict):
            return item.get(attribute)

        return getattr(
            item,
            attribute,
            None,
        )