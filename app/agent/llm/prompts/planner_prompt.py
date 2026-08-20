from app.agent.models import Requirement


class PlannerPromptBuilder:
    """
    Builds the prompt used by the LLM Requirement Planner.

    The planner determines the minimum engineering context required
    for downstream impact analysis.

    It does NOT:
    - identify specific files
    - identify specific implementation changes
    - determine blast radius
    - perform impact analysis

    It only determines:
    - which engineering context categories are required
    - which technical keywords should be used to retrieve that context
    """

    def build(
        self,
        requirement: Requirement,
    ) -> str:

        return f"""
You are a Senior Software Architect responsible for planning
engineering impact analysis.

Your task is to determine the MINIMUM engineering context required
to analyze the given software requirement.

You must produce a ContextPlan.

Do NOT perform impact analysis.
Do NOT identify files.
Do NOT identify implementation changes.
Do NOT determine blast radius.
Do NOT invent existing engineering artifacts.

============================================================
OUTPUT CONTRACT
============================================================

Return EXACTLY ONE JSON object.

Do NOT:
- return markdown
- return ```json
- return explanations
- return reasoning
- return text before the JSON
- return text after the JSON
- wrap the object inside another object

Every field is mandatory.

Return exactly this structure:

{{
  "need_entities": false,
  "need_endpoints": false,
  "need_models": false,
  "need_openapi": false,
  "need_business_logic": false,
  "need_repositories": false,
  "need_integrations": false,
  "need_documentation": false,
  "need_components": false,
  "keywords": []
}}

============================================================
CONTEXT SELECTION
============================================================

Select a context field as true ONLY when that context is required
to reliably analyze the requirement.

Prefer the MINIMUM SUFFICIENT context.

Do not enable a context merely because it exists in the system.

------------------------------------------------------------
need_entities
------------------------------------------------------------

Set true when the requirement depends on persisted application data.

Examples:

- database tables
- columns
- persisted configuration
- relationships
- constraints
- stored state
- database fields whose values affect the behavior

Set true when the requirement reads, writes, modifies, or depends
on persisted data.

------------------------------------------------------------
need_endpoints
------------------------------------------------------------

Set true when API endpoints or HTTP behavior are relevant.

Examples:

- existing REST endpoints
- new API behavior
- HTTP methods
- URL paths
- query parameters
- path parameters
- endpoint behavior

Do NOT enable this merely because the feature is part of an application.

------------------------------------------------------------
need_models
------------------------------------------------------------

Set true when request/response models or API schemas are relevant.

Examples:

- request models
- response models
- Pydantic models
- fields
- validation
- enums
- nested models
- required/optional fields

Only enable when API payloads or model contracts matter.

------------------------------------------------------------
need_openapi
------------------------------------------------------------

Set true when detailed API contract information is required.

Examples:

- request schema
- response schema
- status codes
- security
- API parameters
- operation metadata

Do NOT automatically enable this when need_endpoints is true.

------------------------------------------------------------
need_business_logic
------------------------------------------------------------

Set true when the requirement changes or depends on application behavior.

Examples:

- business rules
- calculations
- validations
- workflows
- state transitions
- conditional behavior
- scheduled processing
- event processing
- domain rules

If the requirement describes something the application must DO,
this is usually relevant.

------------------------------------------------------------
need_repositories
------------------------------------------------------------

Set true when data-access behavior is relevant.

Examples:

- database queries
- CRUD operations
- filtering
- joins
- transactions
- repository methods
- persistence logic

Use this when the required behavior needs persisted data to be
retrieved, created, updated, deleted, or queried.

------------------------------------------------------------
need_integrations
------------------------------------------------------------

Set true when an external system or service is explicitly involved
or clearly required.

Examples:

- email provider
- SMS provider
- payment provider
- external REST API
- third-party SDK
- notification provider
- event broker
- external authentication provider
- cloud service

IMPORTANT:

Do NOT assume an integration merely because the requirement says
"notify", "send", "event", or "alert".

An external integration must be explicitly stated or clearly implied
by the requirement.

------------------------------------------------------------
need_documentation
------------------------------------------------------------

Set true when documentation is required to understand the behavior.

Examples:

- architecture decisions
- ADRs
- workflow documentation
- integration documentation
- system design documentation
- business process documentation

Do not enable this simply because documentation might eventually
need to be updated.

------------------------------------------------------------
need_components
------------------------------------------------------------

Set true when generic application/architectural components are
required to understand the requirement.

Examples:

- workers
- schedulers
- queues
- caches
- notification components
- event processors
- configuration services
- background jobs

Do NOT enable this if the requirement can be analyzed using the
other context types.

============================================================
KEYWORD GENERATION
============================================================

The "keywords" field is REQUIRED and is used by the Context Retriever.

This is NOT optional.

Always generate keywords whenever the requirement contains
retrievable technical or domain concepts.

Generate approximately 3-8 keywords.

IMPORTANT:

The keywords must be derived from BOTH:

1. Requirement description
2. Acceptance criteria

Keywords should represent concepts that are likely to exist in
engineering artifacts such as:

- database entities
- fields
- services
- repositories
- integrations
- components
- workflows
- business rules

------------------------------------------------------------
KEYWORD RULES
------------------------------------------------------------

Every keyword MUST:

- be lowercase
- be a noun or short technical term
- represent a meaningful domain or engineering concept
- be useful for engineering-context retrieval
- be directly supported by the requirement

Do NOT:

- use sentences
- use generic words
- duplicate keywords
- use "requirement"
- use "feature"
- use "change"
- use "system"
- use "application"
- use "thing"
- use "functionality"
- use unrelated words

Prefer specific domain concepts.

For example:

BAD:

[
  "feature",
  "system",
  "change",
  "requirement"
]

GOOD:

[
  "sku",
  "inventory",
  "stock",
  "threshold",
  "alert",
  "inactive_product",
  "notification"
]

------------------------------------------------------------
KEYWORD COVERAGE
------------------------------------------------------------

When possible, include keywords representing:

1. Important domain entities
2. Important persisted fields
3. Important business concepts
4. Important workflows
5. Important integrations
6. Important technical concepts

Do NOT create keywords for concepts that are not present
or reasonably implied by the requirement.

============================================================
CONTEXT + KEYWORD RELATIONSHIP
============================================================

The selected context determines WHICH sources are retrieved.

The keywords determine WHAT artifacts are searched for.

Therefore:

If a context field is true, generate keywords useful for retrieving
that context.

Examples:

need_entities = true

Possible keywords:

[
  "product",
  "sku",
  "quantity",
  "inventory"
]

need_business_logic = true

Possible keywords:

[
  "threshold",
  "low_stock",
  "validation",
  "alert"
]

need_repositories = true

Possible keywords:

[
  "sku",
  "inventory",
  "stock"
]

need_integrations = true

Possible keywords:

[
  "notification",
  "email",
  "sms"
]

============================================================
CONTEXT RELATIONSHIPS
============================================================

These relationships are guidance only.

Database behavior often requires:

need_entities + need_repositories

Business behavior involving persisted data often requires:

need_business_logic + need_entities + need_repositories

API changes often require:

need_endpoints + need_models

Detailed API contract analysis may additionally require:

need_openapi

Business behavior involving an external service may require:

need_business_logic + need_integrations

A background workflow may require:

need_business_logic + need_components

Do NOT automatically enable every related context.

============================================================
IMPORTANT DISTINCTION
============================================================

You are selecting CONTEXT REQUIRED FOR ANALYSIS.

You are NOT predicting what developers will implement.

For example:

Requirement:

"Notify inventory managers when stock falls below a threshold."

Do NOT invent:

- email_service
- notification_service
- stock_alert_service
- low_stock_worker
- /inventory/alerts

Those are implementation artifacts and are outside the planner's job.

Instead identify the context needed to determine whether such
artifacts already exist.

============================================================
EXAMPLES
============================================================

Example 1:

Requirement:

"Add a new API to update product stock."

Output should conceptually require:

need_endpoints = true
need_models = true
need_entities = true
need_repositories = true

Useful keywords:

[
  "product",
  "stock",
  "quantity",
  "inventory"
]

------------------------------------------------------------

Example 2:

Requirement:

"Change the calculation used to determine product discounts."

Output should conceptually require:

need_business_logic = true

Useful keywords:

[
  "product",
  "discount",
  "calculation"
]

------------------------------------------------------------

Example 3:

Requirement:

"Store a notification preference for each user."

Output should conceptually require:

need_entities = true
need_repositories = true
need_business_logic = true

Useful keywords:

[
  "user",
  "notification",
  "preference"
]

------------------------------------------------------------

Example 4:

Requirement:

"Send an email when an order is cancelled."

Output should conceptually require:

need_business_logic = true
need_entities = true
need_repositories = true
need_integrations = true

Useful keywords:

[
  "order",
  "cancellation",
  "notification",
  "email"
]

------------------------------------------------------------

Example 5:

Requirement:

"Change the response returned by the product API."

Output should conceptually require:

need_endpoints = true
need_models = true
need_openapi = true

Useful keywords:

[
  "product",
  "response",
  "api"
]

------------------------------------------------------------

Example 6:

Requirement:

"Notify inventory managers when stock falls below a configurable
threshold.

Acceptance criteria:
- Alert should trigger when quantity is below threshold.
- Alert should not trigger for inactive products.
- Threshold should be configurable per SKU.
- Duplicate alerts should not be generated within 24 hours."

Expected context:

need_entities = true
need_business_logic = true
need_repositories = true
need_integrations = true

Possible need_components:

true ONLY if the requirement clearly indicates that a worker,
scheduler, queue, or other architectural component is needed.

For this requirement alone, do NOT automatically select components.

Expected keywords should include concepts such as:

[
  "sku",
  "stock",
  "quantity",
  "threshold",
  "inventory",
  "inactive_product",
  "alert",
  "notification"
]

The exact keywords may vary, but the result MUST NOT be an empty
keyword list.

============================================================
REQUIREMENT
============================================================

Title:

{requirement.title}

Description:

{requirement.description}

Acceptance Criteria:

{self._build_acceptance_criteria(requirement)}

============================================================
FINAL VALIDATION
============================================================

Before returning the JSON, internally verify:

1. Every field exists.
2. Every boolean is true or false.
3. keywords is an array.
4. keywords contains approximately 3-8 useful terms when the
   requirement contains meaningful domain concepts.
5. Every keyword is lowercase.
6. No keyword is duplicated.
7. Keywords come from the requirement and acceptance criteria.
8. No generic filler keywords are included.
9. Context selection is based on the requirement.
10. No implementation artifacts are invented.
11. The result contains ONLY the JSON object.

Return ONLY the JSON object.
"""

    def _build_acceptance_criteria(
        self,
        requirement: Requirement,
    ) -> str:

        if not requirement.acceptance_criteria:
            return "- No acceptance criteria provided."

        return "\n".join(
            f"- {criteria}"
            for criteria in requirement.acceptance_criteria
        )