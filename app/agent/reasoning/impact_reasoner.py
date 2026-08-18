from app.agent.core.agent_step import AgentStep
from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
from app.agent.models import (
    AnalysisContext,
    ImpactReasoningResult,
    LLMInteraction,
)


class ImpactReasoner(AgentStep):

    name = "Impact Reasoner"

    required_context: set[str] = set()

    def __init__(self):
        self.client = LLMClient()
        self.output_parser = StructuredOutputParser()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        prompt = self._build_prompt(ctx)

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

        result = self.output_parser.parse(
            llm_response.response,
            ImpactReasoningResult,
        )

        ctx.entity_impacts = result.data_model_impacts
        ctx.endpoint_impacts = result.api_interface_mutations
        ctx.model_impacts = result.model_impacts
        ctx.business_logic_impacts = (
            result.business_logic_impacts
        )
        ctx.repository_impacts = (
            result.repository_impacts
        )
        ctx.integration_impacts = (
            result.integration_impacts
        )
        ctx.component_impacts = (
            result.component_impacts
        )

    def _build_prompt(
        self,
        ctx: AnalysisContext,
    ) -> str:

        return f"""
You are a Senior Software Architect performing
grounded engineering impact analysis.

Your task is to identify concrete engineering impacts
caused by the requirement.

You MUST reason only from the requirement and the
engineering context provided below.

Every reported impact must have a direct and defensible
relationship to the requirement.

Do not report an artifact merely because:

- its name is lexically similar to the requirement
- it exists in the engineering context
- it could theoretically be involved
- it is commonly used for similar features
- it might be useful in a future implementation

Do not invent engineering artifacts.

Do not invent entities.

Do not invent entity fields.

Do not invent endpoints.

Do not invent Pydantic models.

Do not invent business logic components.

Do not invent repositories.

Do not invent integrations.

Do not invent application components.

Every reported artifact MUST exist in the corresponding
engineering context.

Prefer fewer accurate impacts over many speculative impacts.

If there is insufficient evidence for an impact,
return an empty list for that category.

Return exactly one JSON object.

Do not return markdown.
Do not return ```json.
Do not include explanations outside the JSON object.

==========================================================
OUTPUT SCHEMA
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

==========================================================
DATA MODEL IMPACTS
==========================================================

Use data_model_impacts for database entities and
persisted application data.

Each item:

{{
    "entity": "exact existing entity name",
    "change_type": "ADD_FIELD | MODIFY_FIELD | REMOVE_FIELD | BUSINESS_RULE | RELATIONSHIP | CONSTRAINT",
    "change": "specific technical change",
    "reason": "why the entity is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

CHANGE TYPE RULES:

ADD_FIELD:
Use ONLY when the requirement requires a new persisted
field that does not currently exist.

MODIFY_FIELD:
Use when an existing field's type, validation,
meaning, or behavior changes.

REMOVE_FIELD:
Use ONLY when the requirement explicitly requires an
existing field to be removed, deleted, deprecated,
or no longer persisted.

BUSINESS_RULE:
Use when existing persisted data is used by a new or
modified business rule without necessarily changing
the database schema.

RELATIONSHIP:
Use when entity relationships change.

CONSTRAINT:
Use when database constraints change.

IMPORTANT:

If an existing field is used by the requirement,
DO NOT classify it as REMOVE_FIELD.

Example:

Existing entity:

skus
- id
- quantity
- active

Requirement:

"Notify managers when quantity falls below a threshold."

Correct:

{{
    "entity": "skus",
    "change_type": "BUSINESS_RULE",
    "change": "Use quantity when evaluating low stock conditions.",
    "reason": "The requirement depends on the existing quantity field.",
    "evidence": [
        "The skus entity contains the quantity field."
    ]
}}

Incorrect:

{{
    "entity": "skus",
    "change_type": "REMOVE_FIELD",
    "change": "quantity"
}}

Do not report unrelated fields merely because they belong
to the same entity.

For example, if the requirement concerns stock quantity,
do not report fields such as description, category, title,
or metadata unless the engineering context explicitly
connects them to the requirement.

==========================================================
API INTERFACE MUTATIONS
==========================================================

Use api_interface_mutations only when an existing
endpoint is affected or a new endpoint is explicitly
required.

Each item:

{{
    "endpoint": "exact endpoint from context",
    "change_type": "ADD_ENDPOINT | MODIFY_ENDPOINT | REMOVE_ENDPOINT",
    "details": "specific API change",
    "reason": "why the endpoint is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

Do not create API impacts merely because the feature
contains business logic.

Do not report an endpoint only because its name contains
a keyword from the requirement.

==========================================================
MODEL IMPACTS
==========================================================

Use model_impacts for Pydantic request and response
models.

Each item:

{{
    "model": "exact existing model name",
    "change_type": "ADD_FIELD | MODIFY_FIELD | REMOVE_FIELD | VALIDATION",
    "change": "specific model change",
    "reason": "why the model is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

Only use model names present in the supplied model context.

Do not report a model merely because it contains a field
with a similar name to a requirement concept.

==========================================================
BUSINESS LOGIC IMPACTS
==========================================================

Use business_logic_impacts for services, business rules,
workflows, calculations, validations, and state transitions.

Each item:

{{
    "component": "exact existing business logic component",
    "impact_type": "ADD_RULE | MODIFY_RULE | VALIDATION | WORKFLOW | CALCULATION | STATE_TRANSITION",
    "change": "specific behavioral change",
    "reason": "why the component is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

The component MUST exactly match a component present
in the Business Logic context.

Never use:

- function names not present in context
- inferred function names
- internal helper names
- "_infer_impacts"
- generic names such as "service"
- invented class names

If no matching business logic component exists,
return [] rather than inventing one.

==========================================================
REPOSITORY IMPACTS
==========================================================

Use repository_impacts for database access and
persistence implementation.

Each item:

{{
    "component": "exact existing repository",
    "impact_type": "QUERY | CREATE | UPDATE | DELETE | FILTER | TRANSACTION",
    "change": "specific repository change",
    "reason": "why the repository is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

The repository MUST exist in the supplied context.

Do not report a repository merely because the feature
uses persisted data.

There must be evidence that the repository participates
in the affected data flow.

==========================================================
INTEGRATION IMPACTS
==========================================================

Use integration_impacts for external systems
and third-party services.

Each item:

{{
    "component": "exact existing integration",
    "impact_type": "ADD_INTEGRATION | MODIFY_INTEGRATION | NOTIFICATION | EVENT | API_CALL",
    "change": "specific integration change",
    "reason": "why the integration is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

Do not invent an email provider, SMS provider,
notification service, event broker, or external API.

If the requirement says "send an alert" but no
integration exists in the supplied context,
do not invent one.

Return [].

==========================================================
COMPONENT IMPACTS
==========================================================

Use component_impacts for application or architectural
components.

Each item:

{{
    "component": "exact existing component",
    "impact_type": "ADD_COMPONENT | MODIFY_COMPONENT | CONFIGURATION | SCHEDULER | WORKER | QUEUE",
    "change": "specific required change",
    "reason": "why the component is affected",
    "evidence": [
        "specific engineering-context evidence supporting the impact"
    ]
}}

The component MUST exist in the supplied context.

==========================================================
EVIDENCE RULES
==========================================================

Every impact must provide evidence.

Evidence must come from the supplied engineering context.

Good evidence:

- An existing entity contains the affected field.
- An existing service explicitly uses the affected entity.
- An existing repository accesses the affected entity.
- An existing endpoint exposes the affected model.
- An existing integration is already responsible for the
  required external behavior.
- An existing component explicitly participates in the
  affected workflow.

Bad evidence:

- "This would probably be used."
- "This is commonly used for this feature."
- "The component name sounds related."
- "The requirement mentions a similar word."
- "This could be implemented here."

Do not create an impact without concrete evidence.

==========================================================
GROUNDING RULES
==========================================================

1. Use exact artifact names from the supplied context.

2. Never invent an artifact.

3. Never infer an artifact name from a requirement.

4. Never use internal helper functions as engineering
   components.

5. Never use Python function names as business components
   unless they are explicitly represented as engineering
   components in the context.

6. Never invent database fields.

7. If a field exists and the requirement uses it,
   do not classify it as REMOVE_FIELD.

8. A new field may be suggested only as ADD_FIELD.

9. If the requirement requires a new component but no
   matching component exists in the supplied context,
   do not fabricate a component name.

10. Missing context means insufficient evidence.
    It does NOT mean that the artifact does not exist.

11. If there is insufficient evidence for an impact,
    return an empty list for that category.

12. Prefer fewer accurate impacts over many speculative
    impacts.

13. Every impact must have a clear relationship to the
    requirement.

14. The existence of an artifact is NOT sufficient evidence
    that the artifact is impacted.

15. A shared entity does NOT mean every field of that entity
    is impacted.

16. Do not infer impact from keyword overlap alone.

17. Do not determine blast radius.

18. Do not assign severity.

19. Do not assign relevance_score.

20. Do not assign confidence.

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

Only the artifacts listed below may be referenced.

------------------------------
DATABASE ENTITIES
------------------------------

{self._format_entities(
    ctx.engineering_context.entities
)}

------------------------------
API ENDPOINTS
------------------------------

{self._format_generic_context(
    ctx.engineering_context.endpoints
)}

------------------------------
PYDANTIC MODELS
------------------------------

{self._format_generic_context(
    ctx.engineering_context.models
)}

------------------------------
OPENAPI
------------------------------

{ctx.engineering_context.openapi}

------------------------------
BUSINESS LOGIC
------------------------------

{self._format_generic_context(
    ctx.engineering_context.business_logic
)}

------------------------------
REPOSITORIES
------------------------------

{self._format_generic_context(
    ctx.engineering_context.repositories
)}

------------------------------
INTEGRATIONS
------------------------------

{self._format_generic_context(
    ctx.engineering_context.integrations
)}

------------------------------
APPLICATION COMPONENTS
------------------------------

{self._format_generic_context(
    ctx.engineering_context.components
)}

------------------------------
DOCUMENTATION
------------------------------

{self._format_generic_context(
    ctx.engineering_context.documentation
)}

==========================================================
FINAL VERIFICATION
==========================================================

Before producing each impact, verify:

1. Does the artifact exist in the supplied context?

2. Does the artifact name exactly match the context?

3. Is the impact directly supported by the requirement?

4. Is there concrete engineering evidence?

5. Is the selected change_type appropriate?

6. Is the impact more than simple keyword similarity?

7. Am I inventing anything?

8. Could this impact be removed without losing a
   requirement-driven engineering change?

If any answer is NO, do not report the impact.

Return ONLY the JSON object.
"""

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

    def _format_entities(
        self,
        entities: list,
    ) -> str:

        if not entities:
            return "No entity context retrieved."

        formatted = []

        for entity in entities:

            if not isinstance(entity, dict):
                formatted.append(
                    str(entity)
                )
                continue

            name = entity.get(
                "name",
                "Unknown",
            )

            columns = entity.get(
                "columns",
                [],
            )

            formatted.append(
                f"Entity: {name}\n"
                f"Columns: {self._format_columns(columns)}"
            )

        return "\n\n".join(formatted)

    def _format_columns(
        self,
        columns: list,
    ) -> str:

        if not columns:
            return "None provided"

        formatted = []

        for column in columns:

            if isinstance(column, dict):

                name = column.get(
                    "name",
                    "Unknown",
                )

                column_type = column.get(
                    "type",
                )

                if column_type:
                    formatted.append(
                        f"- {name} ({column_type})"
                    )
                else:
                    formatted.append(
                        f"- {name}"
                    )

            else:
                formatted.append(
                    f"- {column}"
                )

        return "\n".join(formatted)

    def _format_generic_context(
        self,
        items: list,
    ) -> str:

        if not items:
            return "No context retrieved."

        formatted = []

        for item in items:

            if isinstance(item, dict):
                formatted.append(
                    self._format_dict(item)
                )
            else:
                formatted.append(
                    str(item)
                )

        return "\n\n".join(formatted)

    def _format_dict(
        self,
        item: dict,
    ) -> str:

        lines = []

        for key, value in item.items():

            if isinstance(value, list):

                lines.append(
                    f"{key}:"
                )

                for entry in value:
                    lines.append(
                        f"  - {entry}"
                    )

            else:

                lines.append(
                    f"{key}: {value}"
                )

        return "\n".join(lines)