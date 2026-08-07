from models import Requirement


class PlannerPromptBuilder:

    def build(
        self,
        requirement: Requirement,
    ) -> str:

        return f"""
You are a Senior Software Architect responsible for planning engineering impact analysis.

Your task is to determine ONLY what engineering context is required.

IMPORTANT RULES

1. Return EXACTLY ONE JSON object.
2. Do NOT wrap it inside another object.
3. Do NOT include markdown.
4. Do NOT include ```json.
5. Do NOT explain your reasoning.
6. Do NOT include any text before or after the JSON.
7. Every field in the schema is mandatory.

Return this exact schema:

{{
    "need_entities": true,
    "need_endpoints": true,
    "need_models": false,
    "need_openapi": false,
    "need_documentation": false,
    "keywords": [
        "keyword1",
        "keyword2"
    ]
}}

Field descriptions:

- need_entities:
  True if database entities/tables are required.

- need_endpoints:
  True if REST APIs/endpoints are required.

- need_models:
  True if domain models/classes are required.

- need_openapi:
  True if OpenAPI/Swagger specification is required.

- need_documentation:
  True if architecture or design documents are required.

- keywords:
  Short technical keywords useful for retrieving engineering context.
  Use lowercase.
  Do not use sentences.
  Do not include duplicates.
  Prefer nouns.

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

        return "\n".join(
            f"- {criteria}"
            for criteria in requirement.acceptance_criteria
        )