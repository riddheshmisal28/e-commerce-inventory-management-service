from app.agent.models import AnalysisContext


class ImpactPromptBuilder:

    def build(
        self,
        ctx: AnalysisContext,
    ) -> str:

        context = ctx.engineering_context

        return f"""
You are a Senior Software Architect responsible for performing
engineering impact analysis for a software requirement.

Your task is to analyze the requirement using the retrieved engineering
context and identify the changes that may be required across the
application.

You must reason across engineering layers and identify relationships
between impacted components.

Do NOT invent existing files, classes, endpoints, models, repositories,
integrations, or components that are not present in the supplied context.

If an implementation component does not exist in the retrieved context
but appears necessary, clearly indicate that it is a proposed new
component rather than an existing one.

IMPORTANT RULES

1. Return EXACTLY ONE JSON object.
2. Do NOT wrap it inside another object.
3. Do NOT include markdown.
4. Do NOT include ```json.
5. Do NOT include explanatory text outside the JSON.
6. Use only the supplied requirement and engineering context as evidence.
7. Do not assume that every engineering layer requires changes.
8. Return an empty list when no impact is identified for a category.
9. Prefer existing components over proposing new components.
10. Every impact must describe a concrete engineering change.
11. Every impact must explain why the change is required.
12. Avoid duplicate impacts.
13. Distinguish between modifying an existing component and creating
    a new component.
14. Consider dependencies between engineering layers.
15. Do not treat retrieved context as automatically impacted.
16. An engineering component is impacted only when the requirement
    requires a change to its behavior, structure, contract, or data access.
17. Use the requirement description and acceptance criteria together.
18. Be conservative when evidence is insufficient.

RETURN THIS EXACT SCHEMA

{{
    "model_impacts": [],
    "endpoint_impacts": [],
    "business_logic_impacts": [],
    "repository_impacts": [],
    "integration_impacts": [],
    "component_impacts": [],
    "reasoning": []
}}

IMPACT TYPES

MODEL IMPACTS

Use model_impacts for Pydantic request/response models.

Possible change_type values:

- ADD_FIELD
- MODIFY_FIELD
- REMOVE_FIELD
- CHANGE_VALIDATION
- ADD_MODEL
- MODIFY_MODEL
- REMOVE_MODEL

Each model impact must contain:

{{
    "model": "ModelName",
    "change_type": "ADD_FIELD",
    "change": "Add low_stock_threshold field.",
    "reason": "The requirement introduces a configurable threshold."
}}

ENDPOINT IMPACTS

Use endpoint_impacts when an existing API endpoint changes or a new
endpoint is required.

Possible change_type values:

- ADD_ENDPOINT
- MODIFY_ENDPOINT
- REMOVE_ENDPOINT
- CHANGE_REQUEST
- CHANGE_RESPONSE
- CHANGE_VALIDATION

Each endpoint impact must contain:

{{
    "endpoint": "/api/example",
    "change_type": "MODIFY_ENDPOINT",
    "details": "Expose the low-stock threshold configuration.",
    "reason": "The requirement requires threshold configuration through the API."
}}

BUSINESS LOGIC IMPACTS

Use business_logic_impacts for services, domain logic, workflows,
calculations, validations, rules, and application behavior.

Possible impact_type values:

- ADD_RULE
- MODIFY_RULE
- REMOVE_RULE
- ADD_WORKFLOW
- MODIFY_WORKFLOW
- ADD_VALIDATION
- MODIFY_VALIDATION
- MODIFY_SERVICE

Each business logic impact must contain:

{{
    "component": "InventoryService",
    "impact_type": "ADD_RULE",
    "change": "Evaluate inventory quantity against the configured threshold.",
    "reason": "The requirement requires low-stock detection."
}}

REPOSITORY IMPACTS

Use repository_impacts when database access or persistence behavior
must change.

Possible impact_type values:

- ADD_QUERY
- MODIFY_QUERY
- ADD_METHOD
- MODIFY_METHOD
- ADD_PERSISTENCE
- MODIFY_PERSISTENCE
- ADD_TRANSACTION

Each repository impact must contain:

{{
    "component": "SKURepository",
    "impact_type": "MODIFY_QUERY",
    "change": "Retrieve the low-stock threshold along with inventory quantity.",
    "reason": "The business rule requires both values to evaluate stock status."
}}

INTEGRATION IMPACTS

Use integration_impacts when an external service, provider, messaging
system, or third-party system is involved.

Possible impact_type values:

- ADD_INTEGRATION
- MODIFY_INTEGRATION
- REMOVE_INTEGRATION
- MODIFY_CLIENT
- ADD_NOTIFICATION
- MODIFY_NOTIFICATION

Each integration impact must contain:

{{
    "component": "NotificationService",
    "impact_type": "ADD_NOTIFICATION",
    "change": "Send a low-stock notification to inventory managers.",
    "reason": "The requirement explicitly requires inventory managers to be notified."
}}

If no existing integration is present but an external service is clearly
required, identify it as a proposed integration in the change or reason.

COMPONENT IMPACTS

Use component_impacts for application or architectural components
that do not fit specifically into business logic, repositories, or
integrations.

Possible impact_type values:

- ADD_COMPONENT
- MODIFY_COMPONENT
- REMOVE_COMPONENT
- ADD_WORKER
- ADD_SCHEDULER
- MODIFY_CONFIGURATION
- ADD_QUEUE
- MODIFY_QUEUE
- ADD_CACHE

Each component impact must contain:

{{
    "component": "LowStockMonitor",
    "impact_type": "ADD_WORKER",
    "change": "Add a background process to evaluate stock levels.",
    "reason": "The requirement requires stock conditions to be evaluated independently of user requests."
}}

MODEL ANALYSIS RULES

Use the supplied models to determine whether request or response
schemas need modification.

Do not create a model impact simply because a database entity changes.

A database field and an API model field are separate concerns.

Only report a model impact when the requirement affects an API or
application model represented in the supplied model context.

ENTITY EVIDENCE

Database entity impacts are already analyzed separately by the
Entity Analyzer.

Use the entity information as evidence when reasoning about other
layers.

Do not duplicate entity impacts in model_impacts.

API ANALYSIS RULES

Use supplied endpoints and OpenAPI information to determine whether
API changes are necessary.

Do not create an endpoint merely because a feature could theoretically
have an API.

Only identify an API impact when:

- an existing endpoint is affected, or
- the requirement explicitly requires API access, or
- API access is clearly necessary to fulfill the requirement.

BUSINESS LOGIC ANALYSIS RULES

Determine what application behavior must change.

Consider:

- business rules
- calculations
- validations
- workflows
- state transitions
- scheduled processing
- event processing
- service behavior

If an existing business component is supplied in the context and is
relevant, prefer modifying it instead of proposing a new component.

REPOSITORY ANALYSIS RULES

Determine whether existing data-access logic must change.

Consider:

- reading required data
- writing new configuration
- updating state
- filtering
- querying
- transactions
- persistence

Do not report repository changes merely because an entity exists.

INTEGRATION ANALYSIS RULES

Only report an integration when an external system is involved or
clearly required.

Examples include:

- email
- SMS
- payment providers
- third-party APIs
- notification providers
- message brokers
- cloud services
- external authentication

Do not automatically assume an external integration for every
notification or workflow requirement.

COMPONENT ANALYSIS RULES

Consider architectural components when the requirement implies:

- background processing
- scheduled processing
- asynchronous processing
- queues
- workers
- caching
- configuration services
- event processors

Prefer existing components when supplied.

CROSS-LAYER REASONING

Reason about dependencies between layers.

For example:

If the requirement introduces a configurable threshold:

- A database entity may need a new persisted field.
- A repository may need to read or update that field.
- A model may need the field if it is exposed through an API.
- An endpoint may need modification if the threshold is configurable
  through the API.
- Business logic may need to evaluate quantity against the threshold.

Do not automatically report all of these.

Only report the layers supported by the supplied context and requirement.

If the requirement says:

"Notify inventory managers when stock falls below a configurable threshold."

Consider:

1. Existing inventory data must be available.
2. Threshold configuration must exist somewhere.
3. Business logic must evaluate quantity against the threshold.
4. A notification mechanism must exist or be introduced.
5. Repository changes may be required if threshold or alert state
   must be persisted.
6. API/model changes are only required if configuration or alert
   information is exposed through an API.
7. A scheduler or background worker may be required if evaluation
   does not happen as part of an existing inventory workflow.

Do not assume which mechanism is used unless the engineering context
provides evidence.

EXISTING CONTEXT

DATABASE ENTITIES:

{context.entities}

API ENDPOINTS:

{context.endpoints}

PYDANTIC MODELS:

{context.models}

OPENAPI:

{context.openapi}

BUSINESS LOGIC:

{context.business_logic}

REPOSITORIES:

{context.repositories}

INTEGRATIONS:

{context.integrations}

COMPONENTS:

{context.components}

DOCUMENTATION:

{context.documentation}

CURRENT ENTITY IMPACTS:

{ctx.entity_impacts}

CURRENT ENDPOINT IMPACTS:

{ctx.endpoint_impacts}

REQUIREMENT:

Title:
{ctx.requirement.title}

Description:
{ctx.requirement.description}

Acceptance Criteria:

{self._build_acceptance_criteria(ctx)}

CONTEXT PLAN:

{ctx.context_plan}

OUTPUT GUIDANCE

The reasoning field should contain short architectural explanations
for the most important cross-layer relationships identified.

Do not expose hidden chain-of-thought.

Only provide concise conclusions such as:

- "Threshold configuration requires persistence."
- "The existing inventory service already evaluates stock state."
- "No API change is required because threshold configuration is not
  exposed through an API."

Return ONLY the JSON object.
"""

    def _build_acceptance_criteria(
        self,
        ctx: AnalysisContext,
    ) -> str:

        return "\n".join(
            f"- {criteria}"
            for criteria in ctx.requirement.acceptance_criteria
        )