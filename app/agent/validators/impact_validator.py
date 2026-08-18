import re

from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext


FIELD_ALIASES = {
    "quantity": {
        "quantity",
        "stock",
        "inventory",
        "available",
        "amount",
        "units",
    },
    "threshold": {
        "threshold",
        "limit",
        "minimum",
        "maximum",
        "min",
        "max",
    },
    "notification": {
        "alert",
        "notification",
        "notify",
        "warning",
        "message",
    },
}


RELEVANCE_THRESHOLDS = {
    "high": 0.75,
    "medium": 0.50,
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

            relevance_score = (
                self._calculate_entity_relevance(
                    ctx,
                    impact,
                    entity,
                )
            )

            confidence = (
                self._calculate_entity_confidence(
                    impact,
                    entity,
                )
            )

            self._set_scores(
                impact,
                relevance_score,
                confidence,
            )

            if (
                relevance_score
                >= RELEVANCE_THRESHOLDS["medium"]
            ):
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

    def _calculate_entity_relevance(
        self,
        ctx: AnalysisContext,
        impact,
        entity: dict,
    ) -> float:

        requirement = self._normalize_text(
            ctx.requirement_text,
        )

        requirement_tokens = self._tokens(
            requirement,
        )

        change_tokens = self._tokens(
            impact.change,
        )

        reason_tokens = self._tokens(
            impact.reason,
        )

        entity_name = self._normalize_text(
            entity.get("name", ""),
        )

        entity_tokens = self._tokens(
            entity_name,
        )

        requirement_concepts = (
            self._extract_concepts(requirement)
        )

        change_concepts = (
            self._extract_concepts(impact.change)
        )

        score = 0.0

        if change_tokens & requirement_tokens:
            score += 0.30

        if change_concepts & requirement_concepts:
            score += 0.30

        if reason_tokens & requirement_tokens:
            score += 0.20

        if entity_tokens & requirement_tokens:
            score += 0.10

        if self._field_change_matches_requirement(
            ctx,
            entity,
            impact,
        ):
            score += 0.10

        return min(score, 1.0)

    def _calculate_entity_confidence(
        self,
        impact,
        entity: dict,
    ) -> float:

        evidence = getattr(
            impact,
            "evidence",
            [],
        )

        score = 0.0

        if evidence:
            score += 0.40

        if self._entity_has_matching_field(
            entity,
            impact.change,
        ):
            score += 0.30

        if impact.change_type in {
            "MODIFY_FIELD",
            "REMOVE_FIELD",
        }:
            if self._field_exists(
                entity,
                impact.change,
            ):
                score += 0.20

        if impact.change_type == "ADD_FIELD":
            if not self._field_exists(
                entity,
                impact.change,
            ):
                score += 0.20

        if impact.reason:
            score += 0.10

        return min(score, 1.0)

    def _validate_endpoint_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        endpoints = (
            ctx.engineering_context.endpoints
        )

        if not endpoints:
            ctx.endpoint_impacts.clear()
            return

        valid_impacts = []

        for impact in ctx.endpoint_impacts:

            endpoint = self._find_endpoint(
                endpoints,
                impact.endpoint,
            )

            if not endpoint:
                continue

            relevance_score = (
                self._calculate_endpoint_relevance(
                    ctx,
                    impact,
                    endpoint,
                )
            )

            confidence = (
                self._calculate_endpoint_confidence(
                    impact,
                    endpoint,
                )
            )

            self._set_scores(
                impact,
                relevance_score,
                confidence,
            )

            if (
                relevance_score
                >= RELEVANCE_THRESHOLDS["medium"]
            ):
                valid_impacts.append(impact)

        ctx.endpoint_impacts = valid_impacts

    def _calculate_endpoint_relevance(
        self,
        ctx: AnalysisContext,
        impact,
        endpoint: dict,
    ) -> float:

        requirement = self._normalize_text(
            ctx.requirement_text,
        )

        endpoint_text = self._normalize_text(
            self._endpoint_identifier(endpoint),
        )

        details = self._normalize_text(
            getattr(impact, "details", ""),
        )

        reason = self._normalize_text(
            impact.reason,
        )

        requirement_tokens = self._tokens(
            requirement,
        )

        endpoint_tokens = self._tokens(
            endpoint_text,
        )

        detail_tokens = self._tokens(
            details,
        )

        reason_tokens = self._tokens(
            reason,
        )

        score = 0.0

        if detail_tokens & requirement_tokens:
            score += 0.35

        if reason_tokens & requirement_tokens:
            score += 0.25

        if endpoint_tokens & requirement_tokens:
            score += 0.20

        endpoint_concepts = (
            self._extract_concepts(endpoint_text)
        )

        requirement_concepts = (
            self._extract_concepts(requirement)
        )

        if endpoint_concepts & requirement_concepts:
            score += 0.20

        return min(score, 1.0)

    def _calculate_endpoint_confidence(
        self,
        impact,
        endpoint: dict,
    ) -> float:

        evidence = getattr(
            impact,
            "evidence",
            [],
        )

        score = 0.0

        if evidence:
            score += 0.40

        if self._endpoint_has_details(
            endpoint,
        ):
            score += 0.20

        if impact.reason:
            score += 0.20

        if impact.change_type in {
            "MODIFY_ENDPOINT",
            "REMOVE_ENDPOINT",
        }:
            score += 0.20

        return min(score, 1.0)

    def _validate_model_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        models = ctx.engineering_context.models

        if not models:
            ctx.model_impacts.clear()
            return

        valid_impacts = []

        for impact in ctx.model_impacts:

            model = self._find_model(
                models,
                impact.model,
            )

            if not model:
                continue

            relevance_score = (
                self._calculate_model_relevance(
                    ctx,
                    impact,
                    model,
                )
            )

            confidence = (
                self._calculate_model_confidence(
                    impact,
                    model,
                )
            )

            self._set_scores(
                impact,
                relevance_score,
                confidence,
            )

            if (
                relevance_score
                >= RELEVANCE_THRESHOLDS["medium"]
            ):
                valid_impacts.append(impact)

        ctx.model_impacts = valid_impacts

    def _calculate_model_relevance(
        self,
        ctx: AnalysisContext,
        impact,
        model: dict,
    ) -> float:

        requirement = self._normalize_text(
            ctx.requirement_text,
        )

        model_name = self._normalize_text(
            model.get("name", ""),
        )

        change = self._normalize_text(
            impact.change,
        )

        reason = self._normalize_text(
            impact.reason,
        )

        requirement_tokens = self._tokens(
            requirement,
        )

        score = 0.0

        if (
            self._tokens(model_name)
            & requirement_tokens
        ):
            score += 0.20

        if (
            self._tokens(change)
            & requirement_tokens
        ):
            score += 0.30

        if (
            self._tokens(reason)
            & requirement_tokens
        ):
            score += 0.20

        if (
            self._extract_concepts(change)
            & self._extract_concepts(requirement)
        ):
            score += 0.30

        return min(score, 1.0)

    def _calculate_model_confidence(
        self,
        impact,
        model: dict,
    ) -> float:

        evidence = getattr(
            impact,
            "evidence",
            [],
        )

        score = 0.0

        if evidence:
            score += 0.40

        if self._model_contains_change(
            model,
            impact.change,
        ):
            score += 0.30

        if impact.reason:
            score += 0.20

        if impact.change_type:
            score += 0.10

        return min(score, 1.0)

    def _validate_component_impacts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        self._filter_components(
            ctx,
            ctx.business_logic_impacts,
            ctx.engineering_context.business_logic,
        )

        self._filter_components(
            ctx,
            ctx.repository_impacts,
            ctx.engineering_context.repositories,
        )

        self._filter_components(
            ctx,
            ctx.integration_impacts,
            ctx.engineering_context.integrations,
        )

        self._filter_components(
            ctx,
            ctx.component_impacts,
            ctx.engineering_context.components,
        )

    def _filter_components(
        self,
        ctx: AnalysisContext,
        impacts: list,
        context_items: list,
    ) -> None:

        if not context_items:
            impacts.clear()
            return

        valid_impacts = []

        for impact in impacts:

            component = self._find_component(
                context_items,
                impact.component,
            )

            if not component:
                continue

            relevance_score = (
                self._calculate_component_relevance(
                    ctx,
                    impact,
                    component,
                )
            )

            confidence = (
                self._calculate_component_confidence(
                    impact,
                    component,
                )
            )

            self._set_scores(
                impact,
                relevance_score,
                confidence,
            )

            if (
                relevance_score
                >= RELEVANCE_THRESHOLDS["medium"]
            ):
                valid_impacts.append(impact)

        impacts[:] = valid_impacts

    def _calculate_component_relevance(
        self,
        ctx: AnalysisContext,
        impact,
        component: dict,
    ) -> float:

        requirement = self._normalize_text(
            ctx.requirement_text,
        )

        component_name = self._normalize_text(
            component.get("component", ""),
        )

        change = self._normalize_text(
            impact.change,
        )

        reason = self._normalize_text(
            impact.reason,
        )

        requirement_tokens = self._tokens(
            requirement,
        )

        score = 0.0

        if (
            self._tokens(component_name)
            & requirement_tokens
        ):
            score += 0.20

        if (
            self._tokens(change)
            & requirement_tokens
        ):
            score += 0.30

        if (
            self._tokens(reason)
            & requirement_tokens
        ):
            score += 0.20

        if (
            self._extract_concepts(change)
            & self._extract_concepts(requirement)
        ):
            score += 0.30

        return min(score, 1.0)

    def _calculate_component_confidence(
        self,
        impact,
        component: dict,
    ) -> float:

        evidence = getattr(
            impact,
            "evidence",
            [],
        )

        score = 0.0

        if evidence:
            score += 0.40

        if component:
            score += 0.20

        if impact.reason:
            score += 0.20

        if impact.change:
            score += 0.20

        return min(score, 1.0)

    def _field_change_matches_requirement(
        self,
        ctx: AnalysisContext,
        entity: dict,
        impact,
    ) -> bool:

        requirement_concepts = (
            self._extract_concepts(
                ctx.requirement_text,
            )
        )

        change_concepts = (
            self._extract_concepts(
                impact.change,
            )
        )

        if change_concepts & requirement_concepts:
            return True

        return self._requirement_depends_on_field(
            ctx.requirement_text,
            entity,
            impact.change,
        )

    def _entity_has_matching_field(
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

        change_text = self._normalize_text(
            change,
        )

        return any(
            column in change_text
            for column in columns
        )

    def _model_contains_change(
        self,
        model: dict,
        change: str,
    ) -> bool:

        change_tokens = self._tokens(
            change,
        )

        model_text = " ".join(
            str(value)
            for value in model.values()
        )

        model_tokens = self._tokens(
            model_text,
        )

        return bool(
            change_tokens & model_tokens
        )

    def _endpoint_has_details(
        self,
        endpoint: dict,
    ) -> bool:

        return len(endpoint) > 1

    def _set_scores(
        self,
        impact,
        relevance_score: float,
        confidence: float,
    ) -> None:

        impact.relevance_score = round(
            relevance_score,
            2,
        )

        impact.confidence = round(
            confidence,
            2,
        )

        if (
            relevance_score
            >= RELEVANCE_THRESHOLDS["high"]
        ):
            impact.relevance = "HIGH"

        elif (
            relevance_score
            >= RELEVANCE_THRESHOLDS["medium"]
        ):
            impact.relevance = "MEDIUM"

        else:
            impact.relevance = "LOW"

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

        change_text = self._normalize_text(
            change,
        )

        requirement_concepts = (
            self._extract_concepts(
                requirement,
            )
        )

        for column in columns:

            if column not in change_text:
                continue

            aliases = FIELD_ALIASES.get(
                column,
                {column},
            )

            if aliases & requirement_concepts:
                return True

        return False

    def _extract_concepts(
        self,
        text: str,
    ) -> set[str]:

        tokens = self._tokens(text)

        concepts = set()

        for concept, aliases in FIELD_ALIASES.items():

            if tokens & aliases:
                concepts.add(concept)

        return concepts

    def _tokens(
        self,
        text: str,
    ) -> set[str]:

        return {
            token
            for token in re.findall(
                r"[a-zA-Z0-9_]+",
                str(text or "").lower(),
            )
            if len(token) > 2
        }

    def _normalize_text(
        self,
        text: str,
    ) -> str:

        return re.sub(
            r"\s+",
            " ",
            str(text or "").lower().strip(),
        )

    def _find_entity(
        self,
        entities: list,
        entity_name: str,
    ) -> dict | None:

        target = entity_name.lower()

        for entity in entities:

            if (
                entity.get("name", "").lower()
                == target
            ):
                return entity

        return None

    def _find_endpoint(
        self,
        endpoints: list,
        endpoint_name: str,
    ) -> dict | None:

        target = endpoint_name.lower()

        for endpoint in endpoints:

            if (
                self._endpoint_identifier(
                    endpoint,
                ).lower()
                == target
            ):
                return endpoint

        return None

    def _find_model(
        self,
        models: list,
        model_name: str,
    ) -> dict | None:

        target = model_name.lower()

        for model in models:

            if (
                model.get("name", "").lower()
                == target
            ):
                return model

        return None

    def _find_component(
        self,
        components: list,
        component_name: str,
    ) -> dict | None:

        target = component_name.lower()

        for component in components:

            if (
                component.get(
                    "component",
                    "",
                ).lower()
                == target
            ):
                return component

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

        change_text = self._normalize_text(
            change,
        )

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