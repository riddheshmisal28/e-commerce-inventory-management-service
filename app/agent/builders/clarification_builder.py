from pydantic import BaseModel, Field

from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
from app.agent.models import AnalysisContext, LLMInteraction, Requirement


class ClarificationQuestionSet(BaseModel):
    clarification_questions: list[str] = Field(
        default_factory=list,
    )


class ClarificationPromptBuilder:

    def build(
        self,
        requirement: Requirement,
    ) -> str:
        return f"""
You are a Senior Product Requirements Analyst.

Your task is to generate a small set of precise clarification questions
for a software requirement.

Return EXACTLY ONE JSON object with this schema:

{{
  "clarification_questions": [
    "Question 1",
    "Question 2"
  ]
}}

Do NOT return markdown, commentary, explanations, or any text outside the JSON.
Keep the questions short, specific, and actionable.

Requirement title:
{requirement.title}

Requirement description:
{requirement.description}

Acceptance criteria:
{' '.join(requirement.acceptance_criteria)}

Generate only the few highest-value questions that would materially reduce
ambiguity before implementation begins.
"""


class LLMClarificationBuilder:

    name = "LLM Clarification Builder"

    def __init__(self):
        self.client = LLMClient(json_mode=True)
        self.prompt_builder = ClarificationPromptBuilder()
        self.output_parser = StructuredOutputParser()

    def execute(
        self,
        requirement: Requirement,
        ctx: AnalysisContext | None = None,
    ) -> list[str]:
        prompt = self.prompt_builder.build(requirement)

        try:
            llm_response = self.client.generate(prompt)

            if ctx is not None:
                ctx.llm_interactions.append(
                    LLMInteraction(
                        step=self.name,
                        provider=getattr(llm_response, "provider", "ollama"),
                        model=getattr(llm_response, "model", ""),
                        prompt=prompt,
                        response=getattr(llm_response, "response", ""),
                        duration_ms=getattr(llm_response, "duration_ms", 0.0),
                        input_tokens=getattr(llm_response, "input_tokens", None),
                        output_tokens=getattr(llm_response, "output_tokens", None),
                        total_tokens=getattr(llm_response, "total_tokens", None),
                        tokens_per_second=getattr(llm_response, "tokens_per_second", None),
                    )
                )

            parsed = self.output_parser.parse(
                llm_response.response,
                ClarificationQuestionSet,
            )
            questions = self._normalize_questions(parsed.clarification_questions)
            if questions:
                return questions

            raise ValueError("LLM returned no clarification questions.")

        except Exception as exc:
            fallback_questions = _build_heuristic_questions(requirement)
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
            return fallback_questions

    @staticmethod
    def _normalize_questions(
        questions: list[str] | None,
    ) -> list[str]:
        if not questions:
            return []

        normalized = []
        for question in questions:
            if question is None:
                continue
            cleaned = str(question).strip()
            if cleaned:
                normalized.append(cleaned)

        return list(dict.fromkeys(normalized))


def _build_heuristic_questions(
    requirement: Requirement,
) -> list[str]:
    text = f"""
    {requirement.title}
    {requirement.description}
    {' '.join(requirement.acceptance_criteria)}
    """.lower()

    questions = []

    if "threshold" in text:
        questions.append(
            "Should thresholds be configurable per SKU or globally?"
        )

    if "alert" in text or "notify" in text or "notification" in text:
        questions.append(
            "How should alerts be delivered (email, SMS, in-app)?"
        )

        questions.append(
            "Should alerts be re-triggered after stock is replenished?"
        )

    if not questions:
        questions.append(
            "What business decision or rule needs to be clarified before implementation?"
        )

    return questions


def build_clarification_questions(
    requirement: Requirement,
    ctx: AnalysisContext | None = None,
) -> list[str]:
    return LLMClarificationBuilder().execute(requirement, ctx=ctx)