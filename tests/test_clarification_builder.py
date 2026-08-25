from app.agent.builders.clarification_builder import build_clarification_questions
from app.agent.models import AnalysisContext, Requirement


class FakeLLMResponse:
    provider = "ollama"
    model = "llama3.1"
    response = '{"clarification_questions":["What should the alert threshold be?","How should notifications be delivered?"]}'
    duration_ms = 42.1


def test_build_clarification_questions_uses_llm_and_tracks_interaction(monkeypatch):
    def fake_generate(self, prompt):
        return FakeLLMResponse()

    monkeypatch.setattr(
        "app.agent.builders.clarification_builder.LLMClient.generate",
        fake_generate,
    )

    requirement = Requirement(
        title="Low stock alerts",
        description="Send alerts when inventory falls below the configured threshold.",
        acceptance_criteria=[
            "The system should alert the warehouse team when stock drops below a threshold.",
            "The threshold must be configurable.",
        ],
    )
    ctx = AnalysisContext(requirement=requirement)

    questions = build_clarification_questions(requirement, ctx=ctx)

    assert questions == [
        "What should the alert threshold be?",
        "How should notifications be delivered?",
    ]
    assert len(ctx.llm_interactions) == 1
    assert ctx.llm_interactions[0].step == "LLM Clarification Builder"


def test_build_clarification_questions_falls_back_on_invalid_llm_output(monkeypatch):
    def fake_generate(self, prompt):
        return FakeLLMResponse()

    monkeypatch.setattr(
        "app.agent.builders.clarification_builder.LLMClient.generate",
        fake_generate,
    )

    def fake_parse(self, response, output_model):
        raise ValueError("invalid json")

    monkeypatch.setattr(
        "app.agent.builders.clarification_builder.StructuredOutputParser.parse",
        fake_parse,
    )

    requirement = Requirement(
        title="Inventory threshold alert",
        description="Alert users when items go below a threshold.",
        acceptance_criteria=["Notify team when stock is low."],
    )

    questions = build_clarification_questions(requirement)

    assert "threshold" in " ".join(questions).lower()
