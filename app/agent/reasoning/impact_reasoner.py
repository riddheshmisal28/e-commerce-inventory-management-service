from app.agent.core.agent_step import AgentStep
from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
from app.agent.models import (
    AnalysisContext,
    DataModelImpact,
    ApiMutation,
    ModelImpact,
    ComponentImpact,
    LLMInteraction,
    ImpactReasoningResult,
)
from app.core.logger import get_logger


logger = get_logger(__name__)


class ImpactReasoner(AgentStep):

    name = "Impact Reasoner"

    required_context: set[str] = set()

    _MAX_ATTEMPTS = 3

    def __init__(self):
        self.client = LLMClient(json_mode=True)
        self.output_parser = StructuredOutputParser()

    # ==========================================================
    # EXECUTION
    # ==========================================================

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        prompt = self._build_prompt(ctx)

        last_exc: Exception | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):

            llm_response = self.client.generate(prompt)

            ctx.llm_interactions.append(
                LLMInteraction(
                    step=self.name,
                    provider=llm_response.provider,
                    model=llm_response.model,
                    prompt=prompt,
                    response=llm_response.response,
                    duration_ms=llm_response.duration_ms,
                )
            )

            try:

                result = self.output_parser.parse(
                    llm_response.response,
                    ImpactReasoningResult,
                )

                self._apply_grounded_impacts(
                    ctx,
                    result,
                )

                return

            except ValueError as exc:

                last_exc = exc

                logger.warning(
                    "Impact Reasoner attempt %d/%d failed "
                    "to parse LLM response: %s",
                    attempt,
                    self._MAX_ATTEMPTS,
                    exc,
                )

        raise ValueError(
            f"Impact Reasoner failed after "
            f"{self._MAX_ATTEMPTS} attempts. "
            f"Last error: {last_exc}"
        ) from last_exc

    # ==========================================================
    # PROMPT
    # ==========================================================

    def _build_prompt(
        self,
        ctx: AnalysisContext,
    ) -> str:

        return f"""
You are a Senior Software Architect performing
grounded engineering impact analysis.

Your task is to identify engineering impacts caused
by the requirement.

==========================================================
CRITICAL GROUNDING PRINCIPLE
==========================================================

You may ONLY use artifacts that already exist in the
AVAILABLE ENGINEERING CONTEXT.

You MUST NOT invent:

- tables
- database entities
- API endpoints
- Pydantic models
- services
- classes
- functions
- repositories
- integrations
- application components

You MAY propose changes to existing artifacts.

For example:

Existing table:
skus

Existing column:
quantity

Requirement:
"Notify managers when stock falls below a configurable
threshold."

Valid impact:

{{
    "entity": "skus",
    "change_type": "BUSINESS_RULE",
    "change": "Evaluate quantity against a configurable threshold.",
    "reason": "The requirement explicitly depends on SKU quantity.",
    "evidence": [
        "The skus entity contains the quantity field."
    ]
}}

Invalid impact:

{{
    "entity": "inventory_alerts",
    "change_type": "ADD_FIELD"
}}

because inventory_alerts does not exist in the supplied context.

==========================================================
REQUIREMENT
==========================================================

Title:

{ctx.requirement.title}

Description:

{ctx.requirement.description}

Acceptance Criteria:

{self._format_acceptance_criteria(
    ctx.requirement.acceptance_criteria
)}

==========================================================
AVAILABLE ENGINEERING CONTEXT
==========================================================

------------------------------
DATABASE ENTITIES
------------------------------

{self._format_context(
    ctx.engineering_context.entities,
)}

------------------------------
API ENDPOINTS
------------------------------

{self._format_context(
    ctx.engineering_context.endpoints,
)}

------------------------------
PYDANTIC MODELS
------------------------------

{self._format_context(
    ctx.engineering_context.models,
)}

------------------------------
BUSINESS LOGIC
------------------------------

{self._format_context(
    ctx.engineering_context.business_logic,
)}

------------------------------
REPOSITORIES
------------------------------

{self._format_context(
    ctx.engineering_context.repositories,
)}

------------------------------
INTEGRATIONS
------------------------------

{self._format_context(
    ctx.engineering_context.integrations,
)}

------------------------------
APPLICATION COMPONENTS
------------------------------

{self._format_context(
    ctx.engineering_context.components,
)}

==========================================================
STRICT GROUNDING RULES
==========================================================

1. Every artifact MUST already exist in the supplied context.

2. Artifact names MUST match the context exactly.

3. Do not create a new artifact just because the requirement
   needs functionality that does not currently exist.

4. If a required artifact does not exist in context,
   DO NOT report it.

5. If a category has no retrieved context, return [].

6. Existing database entities may receive:
   - ADD_FIELD
   - MODIFY_FIELD
   - BUSINESS_RULE
   - RELATIONSHIP
   - CONSTRAINT

7. Existing business logic may receive:
   - ADD_RULE
   - MODIFY_RULE
   - VALIDATION
   - WORKFLOW
   - CALCULATION
   - STATE_TRANSITION

8. Existing repositories may receive:
   - QUERY
   - CREATE
   - UPDATE
   - DELETE
   - FILTER
   - TRANSACTION

9. Existing integrations may receive:
   - ADD_INTEGRATION
   - MODIFY_INTEGRATION
   - NOTIFICATION
   - EVENT
   - API_CALL

10. Existing components may receive:
   - ADD_COMPONENT
   - MODIFY_COMPONENT
   - CONFIGURATION
   - SCHEDULER
   - WORKER
   - QUEUE

==========================================================
API RULE
==========================================================

Only report an API impact when the endpoint itself exists
in the supplied context.

DO NOT invent:

/inventory/low-stock

/stock-alerts

or any other endpoint.

If the requirement needs a new endpoint but no corresponding
endpoint exists in context:

return:

"api_interface_mutations": []

==========================================================
MODEL RULE
==========================================================

Only report models that exist in context.

Do not invent:

ProductResponse
SKUResponse

unless they are explicitly present in the model context.

==========================================================
BUSINESS LOGIC RULE
==========================================================

Only report business logic components that exist in context.

For example, if:

SKUService

exists in the context, it may be impacted.

But:

stock_threshold_service

must NOT be created unless it already exists.

==========================================================
REPOSITORY RULE
==========================================================

Only report repositories that exist in context.

For example:

SKURepository

is valid only if it exists in the retrieved repository context.

Do not invent:

skus_repository
products_repository

==========================================================
INTEGRATION RULE
==========================================================

Only report integrations explicitly present in context.

Do not invent:

email_service
notification_service
event_bus
sms_provider

unless they exist in the supplied integration context.

==========================================================
COMPONENT RULE
==========================================================

Only report application components explicitly present
in context.

Do not invent:

stock_worker
inventory_manager
stock_threshold_scheduler

unless they already exist in the component context.

==========================================================
EVIDENCE RULES
==========================================================

Every impact MUST contain concrete engineering evidence.

GOOD:

"The skus entity contains the quantity field."

"The SKUService handles SKU creation."

"The SKURepository retrieves SKU records."

"The inventory endpoint exposes SKU information."

BAD:

"This would probably be used."

"This is commonly used."

"The name sounds related."

"This could be implemented here."

"The requirement mentions inventory."

==========================================================
IMPORTANT
==========================================================

Do NOT create impacts merely because an artifact is related
to the same business domain.

For example:

Requirement:
"Notify managers when SKU quantity falls below threshold."

Context:

products
categories
skus

Only "skus" should be considered impacted if the context
shows that it contains quantity.

Do NOT automatically impact:

products
categories

just because they are inventory-related.

==========================================================
FINAL VALIDATION
==========================================================

Before returning each impact, verify:

1. Does the artifact exist in context?

2. Does the artifact name exactly match context?

3. Is it directly related to the requirement?

4. Is there concrete engineering evidence?

5. Is the change type appropriate?

6. Am I inventing anything?

If ANY answer is NO:

DO NOT RETURN THE IMPACT.

==========================================================
OUTPUT
==========================================================

Return exactly one JSON object.

Use ONLY these fields.

Database:

data_model_impacts:
entity
change_type
change
reason
evidence

API:

api_interface_mutations:
endpoint
change_type
details
reason
evidence

Models:

model_impacts:
model
change_type
change
reason
evidence

Business logic:

business_logic_impacts:
component
change_type
change
reason
evidence

Repositories:

repository_impacts:
component
change_type
change
reason
evidence

Integrations:

integration_impacts:
component
change_type
change
reason
evidence

Components:

component_impacts:
component
change_type
change
reason
evidence

==========================================================
RETURN
==========================================================

{{
    "data_model_impacts": [],
    "api_interface_mutations": [],
    "model_impacts": [],
    "business_logic_impacts": [],
    "repository_impacts": [],
    "integration_impacts": [],
    "component_impacts": []
}}

Return ONLY JSON.
"""

    # ==========================================================
    # APPLY GROUNDED IMPACTS
    # ==========================================================

    def _apply_grounded_impacts(
        self,
        ctx: AnalysisContext,
        result: ImpactReasoningResult,
    ) -> None:

        ctx.entity_impacts = self._filter_entity_impacts(
            ctx,
            result.data_model_impacts,
        )

        ctx.endpoint_impacts = self._filter_endpoint_impacts(
            ctx,
            result.api_interface_mutations,
        )

        ctx.model_impacts = self._filter_model_impacts(
            ctx,
            result.model_impacts,
        )

        ctx.business_logic_impacts = self._filter_component_impacts(
            ctx,
            result.business_logic_impacts,
            category="business_logic",
        )

        ctx.repository_impacts = self._filter_component_impacts(
            ctx,
            result.repository_impacts,
            category="repository",
        )

        ctx.integration_impacts = self._filter_component_impacts(
            ctx,
            result.integration_impacts,
            category="integration",
        )

        ctx.component_impacts = self._filter_component_impacts(
            ctx,
            result.component_impacts,
            category="component",
        )

        self._log_grounding_summary(ctx)

    # ==========================================================
    # ENTITY
    # ==========================================================

    def _filter_entity_impacts(
        self,
        ctx: AnalysisContext,
        impacts: list[DataModelImpact],
    ) -> list[DataModelImpact]:

        known = self._build_known_identifiers(
            ctx.engineering_context.entities,
            self._entity_identifier,
        )

        logger.debug(
            "Known database entities: %s",
            sorted(known),
        )

        result = []

        for impact in impacts:

            identifier = self._normalize_identifier(
                impact.entity
            )

            if identifier not in known:

                logger.warning(
                    "Rejecting ungrounded entity impact: %s. "
                    "Known entities: %s",
                    impact.entity,
                    sorted(known),
                )

                continue

            result.append(impact)

        return result

    # ==========================================================
    # ENDPOINT
    # ==========================================================

    def _filter_endpoint_impacts(
        self,
        ctx: AnalysisContext,
        impacts: list[ApiMutation],
    ) -> list[ApiMutation]:

        known = self._build_known_identifiers(
            ctx.engineering_context.endpoints,
            self._endpoint_identifier,
        )

        logger.debug(
            "Known endpoints: %s",
            sorted(known),
        )

        result = []

        for impact in impacts:

            identifier = self._normalize_identifier(
                impact.endpoint
            )

            if identifier not in known:

                logger.warning(
                    "Rejecting ungrounded endpoint impact: %s. "
                    "Known endpoints: %s",
                    impact.endpoint,
                    sorted(known),
                )

                continue

            result.append(impact)

        return result

    # ==========================================================
    # MODEL
    # ==========================================================

    def _filter_model_impacts(
        self,
        ctx: AnalysisContext,
        impacts: list[ModelImpact],
    ) -> list[ModelImpact]:

        known = self._build_known_identifiers(
            ctx.engineering_context.models,
            self._model_identifier,
        )

        logger.debug(
            "Known models: %s",
            sorted(known),
        )

        result = []

        for impact in impacts:

            identifier = self._normalize_identifier(
                impact.model
            )

            if identifier not in known:

                logger.warning(
                    "Rejecting ungrounded model impact: %s. "
                    "Known models: %s",
                    impact.model,
                    sorted(known),
                )

                continue

            result.append(impact)

        return result

    # ==========================================================
    # COMPONENT BASED IMPACTS
    # ==========================================================

    def _filter_component_impacts(
        self,
        ctx: AnalysisContext,
        impacts: list[ComponentImpact],
        category: str,
    ) -> list[ComponentImpact]:

        context_items = self._get_context_items(
            ctx,
            category,
        )

        known = self._build_known_identifiers(
            context_items,
            self._component_identifier,
        )

        logger.debug(
            "Known %s components: %s",
            category,
            sorted(known),
        )

        result = []

        for impact in impacts:

            identifier = self._normalize_identifier(
                impact.component
            )

            if identifier not in known:

                logger.warning(
                    "Rejecting ungrounded %s impact: %s. "
                    "Known artifacts: %s",
                    category,
                    impact.component,
                    sorted(known),
                )

                continue

            result.append(impact)

        return result

    # ==========================================================
    # KNOWN IDENTIFIER BUILDER
    # ==========================================================

    def _build_known_identifiers(
        self,
        items: list,
        identifier_fn,
    ) -> set[str]:

        known = set()

        for item in items or []:

            identifier = identifier_fn(item)

            if not identifier:
                continue

            normalized = self._normalize_identifier(
                identifier
            )

            if normalized:
                known.add(normalized)

        return known

    # ==========================================================
    # CONTEXT HELPERS
    # ==========================================================

    def _get_context_items(
        self,
        ctx: AnalysisContext,
        category: str,
    ) -> list:

        if category == "business_logic":
            return ctx.engineering_context.business_logic or []

        if category == "repository":
            return ctx.engineering_context.repositories or []

        if category == "integration":
            return ctx.engineering_context.integrations or []

        if category == "component":
            return ctx.engineering_context.components or []

        return []

    # ==========================================================
    # GENERIC VALUE EXTRACTION
    # ==========================================================

    def _get_value(
        self,
        item,
        attributes: tuple[str, ...],
    ) -> str | None:

        if item is None:
            return None

        # ------------------------------------------------------
        # Dictionary
        # ------------------------------------------------------

        if isinstance(item, dict):

            for attribute in attributes:

                value = item.get(attribute)

                if value is not None:
                    return str(value)

            return None

        # ------------------------------------------------------
        # Pydantic model
        # ------------------------------------------------------

        if hasattr(item, "model_dump"):

            try:

                data = item.model_dump()

                for attribute in attributes:

                    value = data.get(attribute)

                    if value is not None:
                        return str(value)

            except Exception:
                pass

        # ------------------------------------------------------
        # Normal Python object
        # ------------------------------------------------------

        for attribute in attributes:

            value = getattr(
                item,
                attribute,
                None,
            )

            if value is not None:
                return str(value)

        return None

    # ==========================================================
    # IDENTIFIERS
    # ==========================================================

    def _entity_identifier(
        self,
        entity,
    ) -> str:

        value = self._get_value(
            entity,
            (
                "name",
                "entity",
                "table",
                "table_name",
                "entity_name",
            ),
        )

        return value or ""

    def _endpoint_identifier(
        self,
        endpoint,
    ) -> str:

        value = self._get_value(
            endpoint,
            (
                "path",
                "endpoint",
                "route",
                "url",
                "name",
            ),
        )

        return value or ""

    def _model_identifier(
        self,
        model,
    ) -> str:

        value = self._get_value(
            model,
            (
                "name",
                "model",
                "model_name",
            ),
        )

        return value or ""

    def _component_identifier(
        self,
        component,
    ) -> str:

        value = self._get_value(
            component,
            (
                "name",
                "component",
                "class_name",
                "function",
                "function_name",
                "service",
                "repository",
                "integration",
            ),
        )

        return value or ""

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    def _normalize_identifier(
        self,
        value,
    ) -> str:

        if value is None:
            return ""

        value = str(value).strip()

        # Remove accidental surrounding quotes.
        value = value.strip("\"'")

        # Normalize whitespace.
        value = " ".join(
            value.split()
        )

        return value.lower()

    # ==========================================================
    # DEBUGGING
    # ==========================================================

    def _log_grounding_summary(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Grounded impact summary: "
            "entities=%d, endpoints=%d, models=%d, "
            "business_logic=%d, repositories=%d, "
            "integrations=%d, components=%d",
            len(ctx.entity_impacts),
            len(ctx.endpoint_impacts),
            len(ctx.model_impacts),
            len(ctx.business_logic_impacts),
            len(ctx.repository_impacts),
            len(ctx.integration_impacts),
            len(ctx.component_impacts),
        )

    # ==========================================================
    # FORMATTING
    # ==========================================================

    def _format_context(
        self,
        items: list,
    ) -> str:

        if not items:
            return "No context retrieved."

        formatted_items = []

        for item in items:

            # --------------------------------------------------
            # Pydantic model
            # --------------------------------------------------

            if hasattr(item, "model_dump"):

                try:
                    item = item.model_dump()
                except Exception:
                    pass

            # --------------------------------------------------
            # Dictionary
            # --------------------------------------------------

            if isinstance(item, dict):

                # Entity
                if (
                    "name" in item
                    and "columns" in item
                ):

                    columns = item.get(
                        "columns",
                        [],
                    )

                    if isinstance(columns, list):
                        columns = ", ".join(
                            str(column)
                            for column in columns
                        )

                    formatted_items.append(
                        f"Table: {item['name']}\n"
                        f"Columns: {columns}"
                    )

                # Endpoint
                elif (
                    "path" in item
                    and "methods" in item
                ):

                    methods = item.get(
                        "methods",
                        [],
                    )

                    if isinstance(methods, list):
                        methods = ", ".join(
                            str(method)
                            for method in methods
                        )

                    formatted_items.append(
                        f"Endpoint: {item['path']} "
                        f"({methods})"
                    )

                # Model
                elif (
                    "name" in item
                    and "schema" in item
                ):

                    formatted_items.append(
                        f"Model: {item['name']}\n"
                        f"Schema: {item['schema']}"
                    )

                # Generic component
                elif (
                    "component" in item
                ):

                    component = item.get(
                        "component"
                    )

                    comp_type = item.get(
                        "type",
                        "component",
                    )

                    file_path = item.get(
                        "file",
                        "unknown file",
                    )

                    formatted_items.append(
                        f"- {component} "
                        f"({comp_type}) "
                        f"in {file_path}"
                    )

                # Generic name
                elif "name" in item:

                    formatted_items.append(
                        str(item)
                    )

                else:

                    formatted_items.append(
                        str(item)
                    )

                continue

            # --------------------------------------------------
            # Pydantic / Python object fallback
            # --------------------------------------------------

            formatted_items.append(
                str(item)
            )

        return "\n\n".join(
            formatted_items
        )

    # ==========================================================
    # ACCEPTANCE CRITERIA
    # ==========================================================

    def _format_acceptance_criteria(
        self,
        criteria: list[str],
    ) -> str:

        if not criteria:
            return "- None provided"

        return "\n".join(
            f"- {item}"
            for item in criteria
        )