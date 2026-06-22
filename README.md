# Inventory Management Service

A FastAPI-based inventory management service with PostgreSQL persistence and Elasticsearch search support.

## Features

- Category CRUD
- Product CRUD
- SKU CRUD
- Elasticsearch product search and sync
- PostgreSQL database via SQLAlchemy
- Correlation ID middleware and structured logging

## Tech stack

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Elasticsearch
- Docker / Docker Compose

## Getting started

### Prerequisites

- Python 3.11
- Docker
- Docker Compose

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root with the following values:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=example
POSTGRES_DB=inventory
DATABASE_URL=postgresql+psycopg2://postgres:example@db/inventory
ELASTICSEARCH_URL=http://elasticsearch:9200
```

> When running locally without Docker, adjust `DATABASE_URL` and `ELASTICSEARCH_URL` to point at your local PostgreSQL and Elasticsearch instances.

### Run with Docker Compose

Start the application and supporting services:

```bash
docker-compose up --build
```

Access the app at `http://localhost:8000`.

### Run locally

Start PostgreSQL and Elasticsearch separately, then run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API endpoints

The API is exposed with these top-level routes:

### Categories

- `POST /categories/` – create a category
- `GET /categories/` – list all categories
- `GET /categories/{category_id}` – get a category by ID
- `PUT /categories/{category_id}` – update a category
- `DELETE /categories/{category_id}` – delete a category

### Products

- `POST /products` – create a product
- `GET /products` – list products with optional `search`, `category_id`, `page`, `page_size`
- `GET /products/search?q=...` – search products via Elasticsearch
- `GET /products/{product_id}` – get a product by ID
- `DELETE /products/{product_id}` – delete a product
- `POST /products/sync` – sync product data to Elasticsearch

### SKUs

- `POST /skus` – create a SKU
- `PUT /skus/{sku_id}` – update a SKU
- `DELETE /skus/{sku_id}` – delete a SKU
- `GET /skus/product/{product_id}` – list SKUs for a product

## API docs

Interactive Swagger UI is available at:

- `http://localhost:8000/docs`

Alternative ReDoc docs:

- `http://localhost:8000/redoc`

## Testing

Run tests with:

```bash
pytest
```

## Notes

- The app initializes the database schema on startup.
- The product search endpoint depends on Elasticsearch being available.
- Docker Compose includes `db` and `elasticsearch` services and mounts the project into the container for local development.
