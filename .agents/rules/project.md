---
trigger: always_on
---

# Inventory Management Service — Project Rules



## Project



This is a Python 3.11 FastAPI Inventory Management Service using:



- FastAPI

- Pydantic

- SQLAlchemy / PostgreSQL

- Elasticsearch

- Ollama

- MCP

- Docker

- pytest



Follow the existing project structure, implementation patterns, and tests.



## General Rules



Before making changes:



1. Inspect the existing implementation and related tests.

2. Search for reusable utilities and existing patterns.

3. Understand callers and dependencies.

4. Make the smallest change required.

5. Add or update tests for behavior changes.



Prefer simple, focused, typed Python code.



Avoid:



- Unrelated refactoring.

- Unnecessary dependencies.

- Duplicate utilities.

- Changing unrelated files.

- Breaking existing APIs or behavior.



---



## Impact Analysis Agent



The Impact Analysis Agent is under `app/agent/`.



The pipeline is:



```text

Requirement

↓

LLM Requirement Planner

↓

Context Retriever

↓

Impact Reasoner

↓

Impact Validator

↓

Blast Radius Analyzer

↓

Report Builder



Pipeline state is shared through AnalysisContext.

Maintain this separation of responsibilities.

PipelineExecutor

File:

app/agent/core/pipeline_executor.py

PipelineExecutor is responsible only for orchestration:





Step execution/order.



Context-based step skipping.



Lifecycle hooks.



Execution metrics.



Error handling.

PipelineResult.

Lifecycle hooks:



before_pipeline

before_step

after_step

on_error

after_pipeline

Do not put business or impact-analysis logic inside PipelineExecutor.

LLM Architecture

LLM code is under:

app/agent/llm/

Use the existing provider abstraction:



LLMClient

↓

BaseLLMProvider

↓

OllamaProvider



New providers should implement BaseLLMProvider.

Keep prompt construction under:

app/agent/llm/prompts/

Do not couple pipeline logic directly to Ollama.

LLM Requirement Planner

LLMRequirementPlanner produces a ContextPlan.

The existing behavior is:



LLM Planner

↓ success

ContextPlan



LLM failure

↓

RequirementAnalyzer fallback



Preserve the rule-based fallback when the LLM is unavailable, malformed, or fails validation.

Structured LLM Output

Treat LLM responses as untrusted data.

Use StructuredOutputParser and Pydantic validation.

Handle:





Invalid JSON.



Markdown code fences.



Response wrappers.



Missing fields.



Incorrect types.



Schema mismatches.



Validation errors.

Never silently accept invalid structured output.

Engineering Context

Engineering discovery APIs are under:

app/engineering/

The agent may retrieve:





Entities and fields.



API endpoints.



Pydantic models.



OpenAPI information.



Business logic.



Repositories.



Integrations.



Components.



Documentation.

Use the existing context_client.py and ContextRetriever.

When changing Engineering Context API schemas, check all agent consumers.

Impact Reasoner

File:

app/agent/reasoning/impact_reasoner.py

ImpactReasoner performs a single holistic LLM analysis using the requirement and retrieved engineering context.

It produces:

ImpactReasoningResult

The LLM must only reference artifacts present in the supplied engineering context.

Do not allow fabricated:





Entities.



Fields.



Endpoints.



Models.



Repositories.



Integrations.



Components.

Impact Validator

File:

app/agent/validators/impact_validator.py

Always validate LLM output against real engineering context before generating the report.

Validate:





Entity existence.



Field operations.



Endpoint existence.



Model existence.



Business logic components.



Repositories.



Integrations.



Generic components.

Preserve existing semantic matching such as FIELD_ALIASES.

Do not bypass the validator.

Blast Radius and Reporting

Blast Radius Analyzer must operate on validated impacts.

It should aggregate, deduplicate, and assign meaningful severity.

ReportBuilder assembles the final ImpactAnalysisReport.

Keep report generation separate from pipeline orchestration and LLM reasoning.

Models

Important models include:



Requirement

ContextPlan

EngineeringContext

ImpactReasoningResult

AnalysisContext

ImpactAnalysisReport

PipelineResult

LLMInteraction

Before modifying a model, search all usages and update affected tests.

Error Handling

Follow existing logging and exception patterns.





Do not silently swallow errors.



Avoid unnecessary broad except Exception.



Preserve useful exception context.



Preserve LLM fallback behavior.



Represent pipeline failures through PipelineResult.

Do not log credentials, API keys, passwords, or secrets.

Inventory Domains

Domain code is under:



app/category/

app/product/

app/sku/

Follow existing domain patterns.

For Product changes, consider Elasticsearch synchronization and search behavior.

For API changes, consider OpenAPI and Engineering Context consumers.

Do not break MCP integration at /mcp.

Testing

Tests are under:

tests/

Use pytest and existing test conventions.

For pipeline/LLM changes, test relevant:





Success and failure paths.



Step skipping.



Lifecycle hooks.



Execution metrics.



LLM fallback.



Invalid structured output.



Validation failures.



Hallucinated impacts.



Report generation.

Mock Ollama, HTTP, PostgreSQL, and Elasticsearch dependencies in unit tests where appropriate.

Change Scope

Keep changes focused.

Do not:





Refactor unrelated code.



Add unnecessary dependencies.



Rewrite working modules.



Change public contracts without checking consumers.



Remove existing fallback behavior without explicit justification.

The existing code and tests are the primary source of truth.

Final Verification

Before completing a change:





Review modified files.



Check for unintended changes.



Run relevant tests.



Verify imports and types.



Check affected callers.



Verify Pydantic/LLM schemas.



Verify pipeline error and fallback behavior.



Ensure no secrets were introduced. 

Pipeline state is shared through AnalysisContext. Maintain this separation of responsibilities.

PipelineExecutor
File: app/agent/core/pipeline_executor.py

PipelineExecutor is responsible only for orchestration:

Step execution/order.

Context-based step skipping.

Lifecycle hooks.

Execution metrics.

Error handling.

PipelineResult.

Lifecycle hooks:

before_pipeline

before_step

after_step

on_error

after_pipeline

Do not put business or impact-analysis logic inside PipelineExecutor.

LLM Architecture
LLM code is under: app/agent/llm/

Use the existing provider abstraction:

Plaintext
LLMClient
    ↓
BaseLLMProvider
    ↓
OllamaProvider
New providers should implement BaseLLMProvider.

Keep prompt construction under: app/agent/llm/prompts/

Do not couple pipeline logic directly to Ollama.

LLM Requirement Planner
LLMRequirementPlanner produces a ContextPlan.

The existing behavior is:

Plaintext
LLM Planner
    ↓ (success)
ContextPlan

LLM failure
    ↓
RequirementAnalyzer fallback
Preserve the rule-based fallback when the LLM is unavailable, malformed, or fails validation.

Structured LLM Output
Treat LLM responses as untrusted data. Use StructuredOutputParser and Pydantic validation.

Handle:

Invalid JSON.

Markdown code fences.

Response wrappers.

Missing fields.

Incorrect types.

Schema mismatches.

Validation errors.

Never silently accept invalid structured output.

Engineering Context
Engineering discovery APIs are under: app/engineering/

The agent may retrieve:

Entities and fields.

API endpoints.

Pydantic models.

OpenAPI information.

Business logic.

Repositories.

Integrations.

Components.

Documentation.

Use the existing context_client.py and ContextRetriever. When changing Engineering Context API schemas, check all agent consumers.

Impact Reasoner
File: app/agent/reasoning/impact_reasoner.py

ImpactReasoner performs a single holistic LLM analysis using the requirement and retrieved engineering context. It produces ImpactReasoningResult.

The LLM must only reference artifacts present in the supplied engineering context. Do not allow fabricated:

Entities.

Fields.

Endpoints.

Models.

Repositories.

Integrations.

Components.

Impact Validator
File: app/agent/validators/impact_validator.py

Always validate LLM output against real engineering context before generating the report.

Validate:

Entity existence.

Field operations.

Endpoint existence.

Model existence.

Business logic components.

Repositories.

Integrations.

Generic components.

Preserve existing semantic matching such as FIELD_ALIASES. Do not bypass the validator.

Blast Radius and Reporting
Blast Radius Analyzer must operate on validated impacts. It should aggregate, deduplicate, and assign meaningful severity.

ReportBuilder assembles the final ImpactAnalysisReport. Keep report generation separate from pipeline orchestration and LLM reasoning.

Models
Important models include:

Requirement

ContextPlan

EngineeringContext

ImpactReasoningResult

AnalysisContext

ImpactAnalysisReport

PipelineResult

LLMInteraction

Before modifying a model, search all usages and update affected tests.

Error Handling
Follow existing logging and exception patterns:

Do not silently swallow errors.

Avoid unnecessary broad except Exception.

Preserve useful exception context.

Preserve LLM fallback behavior.

Represent pipeline failures through PipelineResult.

Do not log credentials, API keys, passwords, or secrets.

Inventory Domains
Domain code is under:

app/category/

app/product/

app/sku/

Follow existing domain patterns:

For Product changes, consider Elasticsearch synchronization and search behavior.

For API changes, consider OpenAPI and Engineering Context consumers.

Do not break MCP integration at /mcp.

Testing
Tests are under: tests/

Use pytest and existing test conventions. For pipeline/LLM changes, test relevant:

Success and failure paths.

Step skipping.

Lifecycle hooks.

Execution metrics.

LLM fallback.

Invalid structured output.

Validation failures.

Hallucinated impacts.

Report generation.

Mock Ollama, HTTP, PostgreSQL, and Elasticsearch dependencies in unit tests where appropriate.

Change Scope
Keep changes focused. Do not:

Refactor unrelated code.

Add unnecessary dependencies.

Rewrite working modules.

Change public contracts without checking consumers.

Remove existing fallback behavior without explicit justification.

The existing code and tests are the primary source of truth.

Final Verification
Before completing a change:

Review modified files.

Check for unintended changes.

Run relevant tests.

Verify imports and types.

Check affected callers.

Verify Pydantic/LLM schemas.

Verify pipeline error and fallback behavior.

Ensure no secrets were introduced.
"""

file_name = "inventory_management_project_rules.md"
with open(file_name, "w", encoding="utf-8") as f:
f.write(content)

print(f"File created successfully: {file_name}")


```text?code_stdout&code_event_index=1
File created successfully: inventory_management_project_rules.md

Your Markdown file is ready

MD icon
inventory_management_project_rules
 MD 
Open
Here is the formatted content of the Project Rules document:

Markdown
# Inventory Management Service — Project Rules

## Project

This is a Python 3.11 FastAPI Inventory Management Service using:

- FastAPI
- Pydantic
- SQLAlchemy / PostgreSQL
- Elasticsearch
- Ollama
- MCP
- Docker
- pytest

Follow the existing project structure, implementation patterns, and tests.

## General Rules

Before making changes:

1. Inspect the existing implementation and related tests.
2. Search for reusable utilities and existing patterns.
3. Understand callers and dependencies.
4. Make the smallest change required.
5. Add or update tests for behavior changes.

Prefer simple, focused, typed Python code.

Avoid:

- Unrelated refactoring.
- Unnecessary dependencies.
- Duplicate utilities.
- Changing unrelated files.
- Breaking ex