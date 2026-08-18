# Inventory Management Service

A FastAPI-based inventory management service with PostgreSQL persistence, Elasticsearch search support, and an agentic/MCP interface for intelligent impact analysis — now powered by LLM-driven planning via Ollama.

## Features

- **Category CRUD**: Manage product categories.
- **Product CRUD**: Manage products, including search and filter capabilities.
- **SKU CRUD**: Manage Stock Keeping Units.
- **Elasticsearch Integration**: Product search and sync capabilities.
- **PostgreSQL Database**: Persistent storage via SQLAlchemy.
- **Correlation ID Middleware**: Structured logging and tracing across services.
- **Model Context Protocol (MCP)**: Dynamic exposure of application tools and schemas to LLMs.
- **Engineering Context API**: Special metadata endpoints to inspect database tables, models, and routes.
- **Agentic Impact Analysis**: A 6-step pipeline engine — with LLM-powered reasoning, grounding validation, and rule-based fallback — that processes requirement documents and produces comprehensive impact reports (blast radius, contract mutations, data schemas, BDD test scenarios).

## Tech Stack

- **Python 3.11**
- **FastAPI**
- [fastapi-mcp](https://github.com/augmentcode/fastapi-mcp) (Model Context Protocol)
- **SQLAlchemy** (PostgreSQL database driver)
- **Elasticsearch** (Search and sync engine)
- **Ollama** (Local LLM inference — default model: `llama3.2:3b`)
- **Pydantic** (Data validation & structured output parsing)
- **Docker / Docker Compose**

---

## Getting Started

### Prerequisites

- Python 3.11
- Docker
- Docker Compose
- [Ollama](https://ollama.com/) (for LLM-powered requirement planning and impact reasoning)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root with the following values:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=example
POSTGRES_DB=inventory
DATABASE_URL=postgresql+psycopg2://postgres:example@db/inventory
ELASTICSEARCH_URL=http://elasticsearch:9200
```

> **Note**: When running locally without Docker, adjust `DATABASE_URL` and `ELASTICSEARCH_URL` to point to your local PostgreSQL and Elasticsearch instances.

### Run with Docker Compose

Start the application and supporting services:

```bash
docker-compose up --build
```

Access the app at `http://localhost:8000`.

### Run Locally

Start PostgreSQL and Elasticsearch separately, then run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

The API is exposed with these top-level routes:

### Categories

- `POST /categories/` – Create a category
- `GET /categories/` – List all categories
- `GET /categories/{category_id}` – Get a category by ID
- `PUT /categories/{category_id}` – Update a category
- `DELETE /categories/{category_id}` – Delete a category

### Products

- `POST /products` – Create a product
- `GET /products` – List products with optional `search`, `category_id`, `page`, `page_size`
- `GET /products/search?q=...` – Search products via Elasticsearch
- `GET /products/{product_id}` – Get a product by ID
- `DELETE /products/{product_id}` – Delete a product
- `POST /products/sync` – Sync product data to Elasticsearch

### SKUs

- `POST /skus` – Create a SKU
- `PUT /skus/{sku_id}` – Update a SKU
- `DELETE /skus/{sku_id}` – Delete a SKU
- `GET /skus/product/{product_id}` – List SKUs for a product

### Engineering Context (Discovery APIs)

These endpoints provide metadata about the system's endpoints, schemas, and database tables to power LLM analysis. Defined in `app/engineering/api.py`.

- `GET /engineering/openapi` – Get the raw OpenAPI specification
- `GET /engineering/endpoints` – List all registered API endpoints (paths & methods)
- `GET /engineering/endpoints/search?keyword=...` – Search endpoint paths by keyword
- `GET /engineering/endpoints/details?path=...` – Get the complete OpenAPI definition for a path
- `GET /engineering/entities` – List all database tables and columns
- `GET /engineering/entities/details?table_name=...` – Detailed metadata for a table (column types, nullability)
- `GET /engineering/models` – List SQLAlchemy models and their columns

---

## Model Context Protocol (MCP) & Impact Agent

This project includes Model Context Protocol (MCP) server support and an automated developer agent to analyze codebase impact for new requirements.

### 1. Model Context Protocol (MCP)

By integrating `fastapi-mcp`, the application acts as an MCP server. LLMs and developer agents (e.g., Cursor, Claude Desktop, or custom MCP clients) can automatically interface with the running service.
- The MCP server is mounted at: `http://localhost:8000/mcp`

### 2. Impact Analysis Agent

Located in the `app/agent` directory, this is a modular, object-oriented pipeline engine that processes requirement documents and automatically generates an **Impact Analysis Report** outlining the blast radius of changes.

#### Pipeline Architecture & Flow

The `ImpactAgent` orchestrates a **6-step pipeline** via `PipelineExecutor`. Each step implements the `AgentStep` interface, receives a shared `AnalysisContext`, and updates it in place:

| # | Step | Module | Responsibility |
|---|------|--------|----------------|
| 1 | **LLM Requirement Planner** | `llm/analyzers/llm_requirement_planner.py` | Uses an LLM (Ollama) to determine which engineering context types are needed. Falls back to rule-based `RequirementAnalyzer` on failure. |
| 2 | **Context Retriever** | `retrievers/context_retriever.py` | Queries the running FastAPI app via `context_client.py` to fetch entities, endpoints, models, OpenAPI spec, business logic, repositories, integrations, components, and documentation — driven by the `ContextPlan`. |
| 3 | **Impact Reasoner** | `reasoning/impact_reasoner.py` | Sends the full engineering context and requirement to the LLM and receives a structured `ImpactReasoningResult` covering all impact categories (entities, endpoints, models, business logic, repositories, integrations, components) in a single grounded LLM call. |
| 4 | **Impact Validator** | `validators/impact_validator.py` | Cross-references each LLM-produced impact against the real engineering context. Filters out hallucinated entities, non-existent endpoints, invalid field operations, and fabricated components. |
| 5 | **Blast Radius Analyzer** | `analyzers/blast_radius.py` | Aggregates all validated, layer-specific impacts into a unified, deduplicated blast radius with severity levels. |
| 6 | **Report Builder** | `builders/report_builder.py` | Assembles all findings into an `ImpactAnalysisReport`. |

#### Impact Reasoner

`ImpactReasoner` (`reasoning/impact_reasoner.py`) is the core LLM analysis step. It:

- Constructs a detailed prompt containing the full requirement (title, description, acceptance criteria) and the complete engineering context (entities with columns, endpoints, Pydantic models, OpenAPI spec, business logic, repositories, integrations, and application components).
- Enforces **strict grounding rules** in the prompt: the LLM must only reference artifacts that exist in the supplied context and must never invent entities, fields, endpoints, or components.
- Parses the LLM response into an `ImpactReasoningResult` (via `StructuredOutputParser`) and writes all impact categories directly into the shared `AnalysisContext`.
- Records the full LLM interaction (prompt, response, provider, model, duration) in `ctx.llm_interactions`.

#### Impact Validator

`ImpactValidator` (`validators/impact_validator.py`) is a post-LLM grounding step that ensures result quality:

- **Entity validation**: Checks that each reported entity exists in the retrieved context. For `ADD_FIELD`, verifies the field does not already exist. For `REMOVE_FIELD`, verifies the field exists and that the requirement does not actually depend on it (using `FIELD_ALIASES` for semantic matching). For `MODIFY_FIELD`, verifies the field exists.
- **Endpoint validation**: Filters out any endpoint impacts referencing paths not present in the retrieved endpoint context.
- **Model validation**: Filters out any Pydantic model impacts referencing models not present in the retrieved model context.
- **Component validation**: Validates business logic, repository, integration, and generic component impacts against their respective retrieved context lists.

#### LLM Integration

The agent uses a **pluggable LLM provider architecture**:

```
app/agent/llm/
├── client.py                # LLMClient — entry point for LLM calls
├── constants.py             # Default model (llama3.2:3b) and provider (ollama)
├── json_parser.py           # LLMJsonParser — raw JSON extraction
├── structured_output.py     # StructuredOutputParser — JSON extraction + Pydantic validation
├── analyzers/
│   └── llm_requirement_planner.py   # LLM-based planning step (with rule-based fallback)
├── prompts/
│   └── planner_prompt.py    # Detailed prompt engineering for the planner
└── providers/
    ├── base_provider.py     # BaseLLMProvider — abstract interface
    └── ollama_provider.py   # OllamaProvider — Ollama REST API integration
```

**Key design decisions:**

- **LLM-first, rule-based fallback**: The `LLMRequirementPlanner` calls the LLM to produce a `ContextPlan`. If the LLM is unavailable, returns malformed JSON, or fails Pydantic validation, the system automatically falls back to the deterministic `RequirementAnalyzer`.
- **Single-call LLM reasoning**: `ImpactReasoner` consolidates all impact categories into a single LLM call with a richly structured prompt, replacing the previous per-concern analyzer chain. This reduces latency and gives the LLM holistic context.
- **Post-LLM validation**: `ImpactValidator` acts as a grounding filter after the LLM step, removing any hallucinated or contextually invalid impacts before they propagate to the blast radius or report.
- **Structured output parsing**: `StructuredOutputParser` strips markdown code fences, extracts JSON, unwraps common LLM response wrappers (`result`, `data`, `response`, `output`), and validates against the target Pydantic model.
- **Traceability**: Every LLM interaction (prompt, response, provider, model, duration) is recorded in `ctx.llm_interactions` for debugging and analysis.
- **Provider abstraction**: New LLM providers can be added by implementing `BaseLLMProvider` and injecting them into `LLMClient`.

#### Key Models

| Model | Purpose |
|-------|---------|
| `Requirement` | Input: title, description, acceptance criteria |
| `ContextPlan` | LLM planner output: which context types to retrieve |
| `EngineeringContext` | Holds all retrieved context (entities, endpoints, models, etc.) |
| `ImpactReasoningResult` | Structured LLM output from `ImpactReasoner`: all impact categories |
| `AnalysisContext` | Shared pipeline state passed between all steps |
| `ImpactAnalysisReport` | Final output report |
| `PipelineResult` | Pipeline execution result: success, metrics, report, error |
| `LLMInteraction` | Recorded LLM call: step, provider, model, prompt, response, duration |

#### Report Contents

The final `ImpactAnalysisReport` includes:

- **Feature Summary**: Clear business goals.
- **Component Blast Radius**: Impacted system layers with severity (Low / Medium / High).
- **Data Model Impact**: Database schema updates.
- **API Mutations**: Endpoint schema and contract changes.
- **Model Impacts**: Pydantic request/response model changes.
- **Business Logic Impacts**: Affected services, rules, and workflows.
- **Repository Impacts**: Data-access layer changes.
- **Integration Impacts**: External service and third-party changes.
- **Component Impacts**: Generic architectural component changes.
- **Clarification Questions**: Outstanding product and design questions.
- **Test Scenarios**: Structured happy path, negative, and edge test cases.
- **BDD Scenarios**: Given/When/Then scenarios.

#### Pipeline Executor

`PipelineExecutor` provides lifecycle hooks and execution metrics:

- **Lifecycle hooks**: `before_pipeline`, `before_step`, `after_step`, `on_error`, `after_pipeline`
- **Metrics**: Per-step timing (`ctx.execution_metrics`) and total pipeline duration
- **Result**: `PipelineResult` with success status, executed steps, metrics, and the final report

#### Running the Impact Agent

**Prerequisites:**
1. The FastAPI service must be running on port 8000.
2. Ollama must be running locally on port 11434 with the `llama3.2:3b` model pulled.

```bash
# Pull the model (first time only)
ollama pull llama3.2:3b
```

**On PowerShell (Windows):**
```powershell
$env:PYTHONPATH="app/agent"
python app/agent/impact_agent.py
```

**On Bash (Linux/macOS):**
```bash
PYTHONPATH=app/agent python app/agent/impact_agent.py
```

> **Note**: If Ollama is unavailable, the agent automatically falls back to the rule-based `RequirementAnalyzer` and the pipeline continues without interruption.

---

## Project Structure

```
inventory-management-service/
├── app/
│   ├── main.py                         # FastAPI application entry point
│   ├── agent/                          # Impact Analysis Agent
│   │   ├── impact_agent.py             # ImpactAgent orchestrator (6-step pipeline)
│   │   ├── models.py                   # Pydantic domain models (Requirement, AnalysisContext, ImpactReasoningResult, Reports, etc.)
│   │   ├── context_client.py           # HTTP client for Engineering Context APIs
│   │   ├── core/
│   │   │   ├── agent_step.py           # AgentStep — abstract base class for pipeline steps
│   │   │   ├── pipeline_executor.py    # PipelineExecutor — lifecycle, metrics, error handling
│   │   │   └── logger.py              # Agent-specific logger
│   │   ├── reasoning/
│   │   │   └── impact_reasoner.py      # ImpactReasoner — single LLM call for all impact categories
│   │   ├── validators/
│   │   │   └── impact_validator.py     # ImpactValidator — post-LLM grounding & hallucination filter
│   │   ├── analyzers/
│   │   │   ├── requirement_analyzer.py # Rule-based requirement analysis (fallback planner)
│   │   │   ├── entity_analyzer.py      # Rule-based database schema impact (fallback)
│   │   │   ├── endpoint_analyzer.py    # Rule-based API endpoint impact (fallback)
│   │   │   ├── model_analyzer.py       # Rule-based Pydantic model impact (fallback)
│   │   │   ├── openapi_analyzer.py     # OpenAPI contract analysis (fallback)
│   │   │   ├── business_logic_analyzer.py  # Rule-based business rule impact (fallback)
│   │   │   ├── repository_analyzer.py  # Rule-based data-access layer impact (fallback)
│   │   │   ├── integration_analyzer.py # Rule-based external integration impact (fallback)
│   │   │   ├── component_impact_analyzer.py # Rule-based component impact (fallback)
│   │   │   └── blast_radius.py         # Blast radius aggregation & deduplication
│   │   ├── builders/
│   │   │   ├── report_builder.py       # Final report assembly
│   │   │   ├── feature_summary_builder.py
│   │   │   ├── clarification_builder.py
│   │   │   ├── test_scenario_builder.py
│   │   │   └── bdd_builder.py
│   │   ├── retrievers/
│   │   │   └── context_retriever.py    # Plan-driven engineering context retrieval
│   │   └── llm/
│   │       ├── client.py               # LLMClient — unified LLM interface
│   │       ├── constants.py            # Model & provider defaults
│   │       ├── json_parser.py          # Raw JSON extraction from LLM responses
│   │       ├── structured_output.py    # JSON extraction + Pydantic validation
│   │       ├── analyzers/
│   │       │   └── llm_requirement_planner.py  # LLM-based context planner
│   │       ├── prompts/
│   │       │   └── planner_prompt.py   # Prompt engineering for the planner
│   │       └── providers/
│   │           ├── base_provider.py    # BaseLLMProvider — abstract interface
│   │           └── ollama_provider.py  # Ollama REST API provider
│   ├── category/                       # Category domain (models, routes, service)
│   ├── product/                        # Product domain (models, routes, service)
│   ├── sku/                            # SKU domain (models, routes, service)
│   ├── engineering/                    # Engineering Context discovery APIs
│   ├── core/                           # Shared core (database, config, logger)
│   └── middleware/                     # Correlation ID middleware
├── tests/                              # Unit tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## API Docs

Interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

Run unit tests with:

```bash
venv\Scripts\pytest
```

## Notes

- The app initializes the database schema on startup.
- The product search endpoint depends on Elasticsearch being available.
- Docker Compose includes `db` and `elasticsearch` services and mounts the project into the container for local development.
- The Impact Agent requires the FastAPI service to be running for engineering context retrieval.
- LLM integration is optional — the agent degrades gracefully to rule-based analysis when Ollama is unavailable.
- `ImpactReasoner` and `ImpactValidator` work in tandem: the reasoner produces LLM-grounded impacts; the validator ensures they reference real artifacts from the engineering context before they reach the report.
