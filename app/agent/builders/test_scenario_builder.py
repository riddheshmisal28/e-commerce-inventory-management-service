from pydantic import BaseModel, Field

from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
from app.agent.models import (
    AnalysisContext,
    BDDScenario,
    LLMInteraction,
    Requirement,
    TestScenarios,
)


class BDDScenarioPayload(BaseModel):
    scenario: str
    given: str
    when: str
    then: str


class TestAndBDDScenarioPayload(BaseModel):
    happy_path: list[str] = Field(default_factory=list)
    negative_cases: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    bdd_scenarios: list[BDDScenarioPayload] = Field(default_factory=list)


class TestScenarioPromptBuilder:

    def build(
        self,
        requirement: Requirement,
    ) -> str:
        return f"""
You are a Senior QA Engineer.

Generate concise test scenarios and matching BDD scenarios for the requirement.

Return EXACTLY ONE JSON object with this schema:

{{
  "happy_path": ["scenario 1", "scenario 2"],
  "negative_cases": ["scenario 1"],
  "edge_cases": ["scenario 1"],
  "bdd_scenarios": [
    {{
      "scenario": "Short scenario name",
      "given": "Given condition",
      "when": "When action occurs",
      "then": "Then expected result"
    }}
  ]
}}

Do NOT return markdown, explanations, or text outside the JSON.
Focus on realistic, implementation-relevant scenarios.

Requirement title:
{requirement.title}

Requirement description:
{requirement.description}

Acceptance criteria:
{' '.join(requirement.acceptance_criteria)}
"""


class LLMTestScenarioBuilder:

    name = "LLM Test Scenario Builder"

    def __init__(self):
        self.client = LLMClient(json_mode=True)
        self.prompt_builder = TestScenarioPromptBuilder()
        self.output_parser = StructuredOutputParser()

    def execute(
        self,
        requirement: Requirement,
        ctx: AnalysisContext | None = None,
    ) -> tuple[TestScenarios, list[BDDScenario]]:
        prompt = self.prompt_builder.build(requirement)

        try:
            llm_response = self.client.generate(prompt)

            if ctx is not None:
                ctx.llm_interactions.append(
                    LLMInteraction(
                        step=self.name,
                        provider=llm_response.provider,
                        model=llm_response.model,
                        prompt=prompt,
                        response=llm_response.response,
                        duration_ms=llm_response.duration_ms,
                        input_tokens=llm_response.input_tokens,
                        output_tokens=llm_response.output_tokens,
                        total_tokens=llm_response.total_tokens,
                        tokens_per_second = (
                            llm_response.output_tokens / (llm_response.duration_ms / 1000)
                        )
                    )
                )

            parsed = self.output_parser.parse(
                llm_response.response,
                TestAndBDDScenarioPayload,
            )

            scenarios = self._normalize_scenarios(parsed)
            if (
                scenarios.happy_path
                or scenarios.negative_cases
                or scenarios.edge_cases
                or parsed.bdd_scenarios
            ):
                return scenarios, self._normalize_bdd_scenarios(parsed.bdd_scenarios)

            raise ValueError("LLM returned no scenario output.")

        except Exception as exc:
            fallback_scenarios = _build_heuristic_test_scenarios(requirement)
            fallback_bdd = _build_heuristic_bdd_scenarios(requirement)
            if ctx is not None:
                ctx.llm_interactions.append(
                    LLMInteraction(
                        step=f"{self.name} (fallback)",
                        provider="fallback",
                        model="rule-based",
                        prompt=prompt,
                        response=str(exc),
                        duration_ms=0.0,
                        success=False,
                    )
                )
            return fallback_scenarios, fallback_bdd

    @staticmethod
    def _normalize_scenarios(
        payload: TestAndBDDScenarioPayload,
    ) -> TestScenarios:
        return TestScenarios(
            happy_path=_normalize_list(payload.happy_path),
            negative_cases=_normalize_list(payload.negative_cases),
            edge_cases=_normalize_list(payload.edge_cases),
        )

    @staticmethod
    def _normalize_bdd_scenarios(
        payload: list[BDDScenarioPayload],
    ) -> list[BDDScenario]:
        bdd_scenarios: list[BDDScenario] = []
        for item in payload or []:
            bdd_scenarios.append(
                BDDScenario(
                    scenario=str(item.scenario).strip(),
                    given=str(item.given).strip(),
                    when=str(item.when).strip(),
                    then=str(item.then).strip(),
                )
            )
        return bdd_scenarios


def _normalize_list(items: list[str] | None) -> list[str]:
    if not items:
        return []

    normalized = []
    for item in items:
        cleaned = str(item).strip()
        if cleaned:
            normalized.append(cleaned)
    return list(dict.fromkeys(normalized))


def _build_heuristic_test_scenarios(
    requirement: Requirement,
) -> TestScenarios:
    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    scenarios = TestScenarios(
        happy_path=[],
        negative_cases=[],
        edge_cases=[],
    )

    if "stock" in text or "inventory" in text or "threshold" in text:
        scenarios.happy_path.extend([
            "Alert generated when quantity falls below threshold",
            "Threshold updated successfully",
        ])

        scenarios.negative_cases.extend([
            "Negative threshold value provided",
            "Inactive SKU receives alert",
        ])

        scenarios.edge_cases.extend([
            "Quantity exactly equals threshold",
            "Concurrent inventory updates",
        ])

    if not scenarios.happy_path and not scenarios.negative_cases and not scenarios.edge_cases:
        scenarios.happy_path.append(
            "Core requirement is satisfied under the normal expected flow"
        )
        scenarios.negative_cases.append(
            "Requirement fails when invalid data or unsupported input is provided"
        )
        scenarios.edge_cases.append(
            "Boundary and concurrency conditions are handled without unexpected errors"
        )

    return scenarios


def _build_heuristic_bdd_scenarios(
    requirement: Requirement,
) -> list[BDDScenario]:
    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    if "stock" in text or "inventory" in text or "threshold" in text:
        return [
            BDDScenario(
                scenario="Low stock alert generation",
                given="the SKU quantity is below the configured threshold",
                when="inventory evaluation runs",
                then="a low-stock alert is created for the warehouse team",
            ),
            BDDScenario(
                scenario="Threshold boundary check",
                given="the SKU quantity is exactly equal to the threshold",
                when="inventory evaluation runs",
                then="the system treats it as the configured boundary without triggering an alert",
            ),
        ]

    return [
        BDDScenario(
            scenario="Normal requirement flow",
            given="the required business condition is met",
            when="the process executes",
            then="the expected result is produced",
        )
    ]


def build_test_scenarios(
    requirement: Requirement,
    ctx: AnalysisContext | None = None,
) -> TestScenarios:
    scenarios, _ = LLMTestScenarioBuilder().execute(requirement, ctx=ctx)
    return scenarios


def build_bdd_scenarios(
    requirement: Requirement,
    ctx: AnalysisContext | None = None,
) -> list[BDDScenario]:
    _, bdd_scenarios = LLMTestScenarioBuilder().execute(requirement, ctx=ctx)
    return bdd_scenarios


def build_test_and_bdd_scenarios(
    requirement: Requirement,
    ctx: AnalysisContext | None = None,
) -> tuple[TestScenarios, list[BDDScenario]]:
    return LLMTestScenarioBuilder().execute(requirement, ctx=ctx)