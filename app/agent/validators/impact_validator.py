from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext


FIELD_ALIASES = {
    "quantity": {
        "quantity",
        "stock",
        "inventory",
        "available",
        "amount",
    },
}


class ImpactValidator(AgentStep):

    name = "Impact Validator"

    required_context: set[str] = set()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        self._validate_entity_impacts(ctx)
        self._validate_endpoint_impacts(ctx)
        self._validate_model_impacts(ctx)
        self._validate_component_impacts(ctx)

    def _validate_entity_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        entities = ctx.engineering_context.entities

        valid_entities = {
            entity.get("name", "").lower()
            for entity in entities
            if entity.get("name")
        }

        valid_impacts = []

        for impact in ctx.entity_impacts:

            if impact.entity.lower() not in valid_entities:
                continue

            entity = self._find_entity(
                entities,
                impact.entity,
            )

            if not entity:
                continue

            if not self._is_entity_change_valid(
                ctx,
                impact,
                entity,
            ):
                continue

            valid_impacts.append(impact)

        ctx.entity_impacts = valid_impacts

    def _is_entity_change_valid(
        self,
        ctx: AnalysisContext,
        impact,
        entity: dict,
    ) -> bool:

        change_type = impact.change_type

        if change_type == "REMOVE_FIELD":

            if not self._field_exists(
                entity,
                impact.change,
            ):
                return False

            return not self._requirement_depends_on_field(
                ctx.requirement_text,
                entity,
                impact.change,
            )

        if change_type == "MODIFY_FIELD":

            return self._field_exists(
                entity,
                impact.change,
            )

        if change_type == "ADD_FIELD":

            return not self._field_exists(
                entity,
                impact.change,
            )

        return True

    def _requirement_depends_on_field(
        self,
        requirement: str,
        entity: dict,
        change: str,
    ) -> bool:

        columns = {
            str(column).lower()
            for column in entity.get(
                "columns",
                [],
            )
        }

        change_text = change.lower()

        for column in columns:

            if column not in change_text:
                continue

            aliases = FIELD_ALIASES.get(
                column,
                {column},
            )

            if any(
                alias in requirement
                for alias in aliases
            ):
                return True

        return False

    def _validate_endpoint_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        endpoints = (
            ctx.engineering_context.endpoints
        )

        if not endpoints:
            return

        valid_endpoints = {
            self._endpoint_identifier(
                endpoint,
            ).lower()
            for endpoint in endpoints
        }

        ctx.endpoint_impacts = [
            impact
            for impact in ctx.endpoint_impacts
            if impact.endpoint.lower()
            in valid_endpoints
        ]

    def _validate_model_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        models = ctx.engineering_context.models

        if not models:
            return

        valid_models = {
            model.get("name", "").lower()
            for model in models
            if model.get("name")
        }

        ctx.model_impacts = [
            impact
            for impact in ctx.model_impacts
            if impact.model.lower()
            in valid_models
        ]

    def _validate_component_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        self._filter_components(
            ctx.business_logic_impacts,
            ctx.engineering_context.business_logic,
        )

        self._filter_components(
            ctx.repository_impacts,
            ctx.engineering_context.repositories,
        )

        self._filter_components(
            ctx.integration_impacts,
            ctx.engineering_context.integrations,
        )

        self._filter_components(
            ctx.component_impacts,
            ctx.engineering_context.components,
        )

    def _filter_components(
        self,
        impacts: list,
        context_items: list,
    ) -> None:

        if not context_items:
            impacts.clear()
            return

        valid_components = {
            item.get("component", "").lower()
            for item in context_items
            if item.get("component")
        }

        impacts[:] = [
            impact
            for impact in impacts
            if impact.component.lower()
            in valid_components
        ]

    def _find_entity(
        self,
        entities: list,
        entity_name: str,
    ) -> dict | None:

        for entity in entities:

            if (
                entity.get("name", "").lower()
                == entity_name.lower()
            ):
                return entity

        return None

    def _field_exists(
        self,
        entity: dict,
        change: str,
    ) -> bool:

        columns = {
            str(column).lower()
            for column in entity.get(
                "columns",
                [],
            )
        }

        change_text = change.lower()

        return any(
            column in change_text
            for column in columns
        )

    def _endpoint_identifier(
        self,
        endpoint: dict,
    ) -> str:

        return (
            endpoint.get("path")
            or endpoint.get("name")
            or endpoint.get("endpoint")
            or ""
        )