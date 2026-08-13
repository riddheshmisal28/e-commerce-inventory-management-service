from app.agent.models import Requirement

class PlannerPromptBuilder:
    """
    Builds the prompt used by the LLM Requirement Planner.

    The planner determines which types of engineering context are required
    for analyzing a software requirement. It does not perform the impact
    analysis itself.
    """

    def build(
        self,
        requirement: Requirement,
    ) -> str:

        return f"""
    ```

    You are a Senior Software Architect responsible for planning
    engineering impact analysis.

    Your task is to determine ONLY what engineering context is required
    to analyze the given requirement.

    Do NOT perform the impact analysis itself.
    Do NOT identify specific files or implementation changes.
    Do NOT determine the final blast radius.
    ONLY determine which types of engineering context are necessary.

    IMPORTANT RULES

    1. Return EXACTLY ONE JSON object.
    2. Do NOT wrap it inside another object.
    3. Do NOT include markdown.
    4. Do NOT include ```json.
    5. Do NOT explain your reasoning.
    6. Do NOT include any text before or after the JSON.
    7. Every field in the schema is mandatory.
    8. Set a context field to true ONLY when that context is relevant.
    9. Set unrelated context fields to false.
    10. Do not assume every requirement requires every context type.
    11. Use both the requirement description and acceptance criteria.
    12. Prefer the minimum sufficient context required for reliable analysis.

    Return this exact schema:

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

    FIELD DESCRIPTIONS

    * need_entities:

    True when database entities or database schema information is
    relevant to understanding or analyzing the requirement.

    This includes:

    * Database tables
    * Columns
    * Column types
    * Nullable fields
    * Primary keys
    * Foreign keys
    * Relationships
    * Indexes
    * Database constraints
    * Persisted configuration or state

    Set this to true when the requirement reads, writes, modifies,
    or depends on persisted application data.

    * need_endpoints:

    True when REST API endpoints or API behavior are relevant.

    This includes:

    * Existing endpoints
    * New endpoints
    * HTTP methods
    * URL paths
    * Query parameters
    * Path parameters
    * Endpoint behavior
    * Endpoint dependencies

    Set this to true when the requirement affects how clients
    communicate with the application through APIs.

    * need_models:

    True when request/response Pydantic models or their schemas
    and validation rules are relevant.

    This includes:

    * Request models
    * Response models
    * Model fields
    * Field types
    * Required/optional fields
    * Default values
    * Validation rules
    * Nested Pydantic models
    * Enums

    Set this to true when API payloads or API schema contracts
    may be affected.

    * need_openapi:

    True when detailed API contract information is required
    beyond a simple endpoint list.

    This includes:

    * Request definitions
    * Response definitions
    * API parameters
    * Status codes
    * Security definitions
    * Operation metadata
    * API schema relationships

    IMPORTANT:

    Do NOT automatically set this to true just because
    need_endpoints is true.

    Use need_openapi when detailed API contract information
    is necessary to understand the requirement.

    * need_business_logic:

    True when application services, use cases, domain logic,
    business rules, calculations, validations, or workflows
    are relevant.

    This includes:

    * Service classes
    * Use cases
    * Domain services
    * Business rules
    * Calculations
    * Conditional logic
    * Application workflows
    * Business validations
    * State transitions
    * Event processing
    * Scheduled processing

    Set this to true when the requirement changes what the
    application should DO, not merely what data it stores
    or what API exposes it.

    * need_repositories:

    True when database access or data-access implementation
    is relevant.

    This includes:

    * Repository classes
    * Database queries
    * CRUD operations
    * Filtering
    * Joins
    * Transactions
    * Data-access methods
    * Persistence logic

    Set this to true when the requirement requires retrieving,
    creating, updating, deleting, or querying persisted data.

    * need_integrations:

    True when external systems or third-party services are
    relevant to the requirement.

    This includes:

    * External REST APIs
    * Third-party SDKs
    * Notification providers
    * Email providers
    * SMS providers
    * Payment providers
    * Cloud services
    * External authentication providers
    * Messaging systems
    * Event brokers
    * External service clients

    Set this to true ONLY when the requirement explicitly
    involves an external system or when an external dependency
    is clearly required to fulfill the behavior.

    Do NOT assume an integration is required merely because
    the requirement involves notifications, events, or workflows.
    Only select it when the external mechanism is relevant.

    * need_documentation:

    True when architecture, design, or engineering documentation
    is required to understand the requirement.

    This includes:

    * Architecture documentation
    * Design documents
    * ADRs
    * API documentation
    * System design documents
    * Workflow documentation
    * Integration documentation
    * Business process documentation

    Set this to true when the requirement depends on architectural
    decisions, documented workflows, or system behavior that cannot
    reasonably be understood from the other engineering context.

    * need_components:

    True when generic application or architectural components
    are relevant to the requirement.

    This includes:

    * Background workers
    * Schedulers
    * Notification services
    * Event processors
    * Message queues
    * Caches
    * Configuration services
    * Internal application components
    * Other architectural components

    Do not set this to true when the requirement is fully covered
    by entities, endpoints, models, business logic, repositories,
    or integrations.

    * keywords:

    Short technical keywords useful for retrieving engineering context.

    Rules:

    * Use lowercase.
    * Use nouns or short technical terms.
    * Do not use sentences.
    * Do not include duplicates.
    * Prefer domain concepts over generic words.
    * Include important entities, concepts, services, integrations,
        workflows, or technical terms.
    * Generate approximately 3-8 relevant keywords.
    * Do not include unrelated generic words.
    * Avoid words such as "change", "feature", "requirement", or "system"
        unless they are specifically meaningful domain concepts.

    CONTEXT SELECTION GUIDANCE

    Use BOTH the requirement description and acceptance criteria
    when determining the required context.

    Think about the requirement in terms of these questions:

    1. Does it depend on persisted data?
    -> need_entities

    2. Does it change or depend on API behavior?
    -> need_endpoints

    3. Does it change request/response schemas or validation?
    -> need_models

    4. Is detailed API contract information required?
    -> need_openapi

    5. Does it change application behavior, rules, calculations,
    workflows, or validations?
    -> need_business_logic

    6. Does that behavior require database queries or persistence?
    -> need_repositories

    7. Does it communicate with an external system or service?
    -> need_integrations

    8. Is architectural or design documentation necessary
    to understand the requirement?
    -> need_documentation

    CONTEXT RELATIONSHIPS

    The following relationships are useful but NOT mandatory.

    * Database behavior often requires:
    need_entities + need_repositories

    * API changes often require:
    need_endpoints + need_models

    * Detailed API contract analysis may additionally require:
    need_openapi

    * Business behavior involving persisted data often requires:
    need_business_logic + need_entities + need_repositories

    * Business behavior involving an external service often requires:
    need_business_logic + need_integrations

    * A requirement may require multiple context types.

    Do NOT enable a context type merely because another related
    context type is enabled.

    EXAMPLES

    Example 1:

    Requirement:
    "Add a new API to update product stock."

    Likely required:

    * need_endpoints = true
    * need_models = true
    * need_entities = true
    * need_repositories = true

    Reasoning internally:
    The API changes stock, which is persisted data, and therefore
    the data-access layer is likely relevant.

    Example 2:

    Requirement:
    "Change the calculation used to determine product discounts."

    Likely required:

    * need_business_logic = true

    Example 3:

    Requirement:
    "Store a notification preference for each user."

    Likely required:

    * need_entities = true
    * need_business_logic = true
    * need_repositories = true

    Example 4:

    Requirement:
    "Send an email when an order is cancelled."

    Likely required:

    * need_business_logic = true
    * need_integrations = true
    * need_entities = true
    * need_repositories = true

    The integration is required because email is an external service.
    The entity/repository context may be required to determine and
    persist/read the order state.

    Example 5:

    Requirement:
    "Change the response returned by the product API."

    Likely required:

    * need_endpoints = true
    * need_models = true
    * need_openapi = true

    Example 6:

    Requirement:
    "Notify inventory managers when stock falls below a configurable
    threshold."

    Likely required:

    * need_entities = true
    * need_business_logic = true
    * need_repositories = true
    * need_integrations = true

    Potentially required:

    * need_endpoints = true
    * need_models = true

    ONLY if the threshold configuration or alert information is
    created, updated, or exposed through an API.

    Do not automatically enable endpoints merely because a feature
    contains business behavior.

    Example 7:

    Requirement:
    "Document the architecture decision for moving notifications
    from email to an event-driven messaging system."

    Likely required:

    * need_integrations = true
    * need_documentation = true
    * need_business_logic = true

    Example 8:

    Requirement:
    "Add a validation rule that prevents inactive products from
    being ordered."

    Likely required:

    * need_business_logic = true
    * need_entities = true

    Potentially required:

    * need_repositories = true

    if product active state must be retrieved through a repository.

    IMPORTANT

    Select context based on what is necessary to analyze the requirement,
    not based on what context happens to exist in the application.

    The goal is to retrieve the MINIMUM SUFFICIENT engineering context
    needed for reliable impact analysis.

    Requirement Title:
    {requirement.title}

    Requirement Description:
    {requirement.description}

    Acceptance Criteria:

    {self._build_acceptance_criteria(requirement)}

    Return ONLY the JSON object.
    """

    def _build_acceptance_criteria(
        self,
        requirement: Requirement,
    ) -> str:

        return "\\n".join(
            f"- {criteria}"
            for criteria in requirement.acceptance_criteria
        )
