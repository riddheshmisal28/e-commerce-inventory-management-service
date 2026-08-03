# Inventory Management Service

A FastAPI-based inventory management service with PostgreSQL persistence, Elasticsearch search support, and an agentic/MCP interface for intelligent analysis.

## Features

- **Category CRUD**: Manage product categories.
- **Product CRUD**: Manage products, including search and filter capabilities.
- **SKU CRUD**: Manage Stock Keeping Units.
- **Elasticsearch Integration**: Product search and sync capabilities.
- **PostgreSQL Database**: Persistent storage via SQLAlchemy.
- **Correlation ID Middleware**: Structured logging and tracing across services.
- **Model Context Protocol (MCP)**: Dynamic exposure of application tools and schemas to LLMs.
- **Engineering Context API**: Special metadata endpoints to inspect database tables, models, and routes.
- **Agentic Impact Analysis**: A rule-based engine that processes requirement documents to output comprehensive impact reports (blast radius, contract mutations, data schemas, BDD test scenarios).

## Tech Stack

- **Python 3.11**
- **FastAPI**
- [fastapi-mcp](https://github.com/augmentcode/fastapi-mcp) (Model Context Protocol)
- **SQLAlchemy** (PostgreSQL database driver)
- **Elasticsearch** (Search and sync engine)
- **Docker / Docker Compose**

---

## Getting Started

### Prerequisites

- Python 3.11
- Docker
- Docker Compose

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

These endpoints provide metadata about the system's endpoints, schemas, and database tables to power LLM analysis. Defined in [api.py](file:///c:/Users/riddhesh.misal/OneDrive%20-%20Talentica%20Software%20%28I%29%20Pvt.%20Ltd/Documents/inventory-management-service/app/engineering/api.py).

- `GET /engineering/openapi` – Get the raw OpenAPI specification
- `GET /engineering/endpoints` – List all registered API endpoints (paths & methods)
- `GET /engineering/endpoints/search?keyword=...` – Search endpoint paths by keyword
- `GET /engineering/endpoints/details?path=...` – Get the complete OpenAPI definition for a path
- `GET /engineering/entities` – List all database tables and columns
- `GET /engineering/entities/details?table_name=...` – Detailed metadata for a table (column types, nullability)
- `GET /engineering/models` – List SQLAlchemy models and their columns

---

## Model Context Protocol (MCP) & Impact Agent

This branch introduces Model Context Protocol (MCP) server support and an automated developer sub-agent to analyze codebase impact for new requirements.

### 1. Model Context Protocol (MCP)

By integrating `fastapi-mcp`, the application acts as an MCP server. LLMs and developer agents (e.g., Cursor, Claude Desktop, or custom MCP clients) can automatically interface with the running service.
- The MCP server is mounted at: `http://localhost:8000/mcp`

### 2. Impact Analysis Agent

Located in the [app/agent](file:///c:/Users/riddhesh.misal/OneDrive%20-%20Talentica%20Software%20%28I%29%20Pvt.%20Ltd/Documents/inventory-management-service/app/agent) directory, this is a modular, object-oriented pipeline engine that processes requirement documents and automatically generates an **Impact Analysis Report** outlining the blast radius of changes.

#### Pipeline Architecture & Flow:

The `ImpactAgent` orchestrates a modular multi-component pipeline. Each phase operates on a shared `AnalysisContext` state object:

1. **Requirement Analysis (`RequirementAnalyzer`)**: Analyzes requirement details (using the `Requirement` model in [models.py](file:///c:/Users/riddhesh.misal/OneDrive%20-%20Talentica%20Software%20%28I%29%20Pvt.%20Ltd/Documents/inventory-management-service/app/agent/models.py)) and formulates a `ContextPlan`.
2. **Context Retrieval (`ContextRetriever`)**: Queries the running FastAPI app via [context_client.py](file:///c:/Users/riddhesh.misal/OneDrive%20-%20Talentica%20Software%20%28I%29%20Pvt.%20Ltd/Documents/inventory-management-service/app/agent/context_client.py) to retrieve active endpoints, DB entities, and SQLAlchemy models into `ctx.engineering_context`.
3. **Data Model Analysis (`EntityAnalyzer`)**: Evaluates database schema impacts (`ctx.entity_impacts`).
4. **API Interface Analysis (`EndpointAnalyzer`)**: Evaluates API route and endpoint mutations (`ctx.endpoint_impacts`).
5. **Blast Radius Analysis (`BlastRadiusAnalyzer`)**: Aggregates entity and endpoint impacts to build `ctx.blast_radius`.
6. **Report Generation (`ReportBuilder`)**: Assembles all findings into an `ImpactAnalysisReport` containing:
   - **Feature Summary**: Clear business goals.
   - **Component Blast Radius**: Impacted system components.
   - **Data Model Impact**: Database schema updates.
   - **API mutations**: Endpoint schema changes.
   - **Clarification questions**: Outstanding product and design questions.
   - **Test Scenarios**: Structured happy path, negative, and edge test cases.
   - **BDD Scenarios**: Given/When/Then scenarios.

#### Running the Impact Agent:

Ensure the FastAPI service is running locally on port 8000, then execute:

**On PowerShell (Windows):**
```powershell
$env:PYTHONPATH="app/agent"
python app/agent/impact_agent.py
```

**On Bash (Linux/macOS):**
```bash
PYTHONPATH=app/agent python app/agent/impact_agent.py
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
