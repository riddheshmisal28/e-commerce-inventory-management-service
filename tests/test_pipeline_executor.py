from app.agent.core.pipeline_executor import PipelineExecutor
from app.agent.llm.client import LLMClient
from app.agent.models import AnalysisContext, Requirement


class SuccessfulStep:
    name = "Successful Step"
    required_context = set()

    def execute(self, ctx):
        ctx.metadata["step_ran"] = True


class FailingStep:
    name = "Failing Step"
    required_context = set()

    def execute(self, ctx):
        raise RuntimeError("step failed")


class FakeProvider:
    provider_name = "fake"
    model = "test-model"

    def generate(self, prompt):
        return "response"


class LLMCallingStep:
    name = "LLM Calling Step"
    required_context = set()

    def execute(self, ctx):
        LLMClient(provider=FakeProvider()).generate("prompt text")


def build_context():
    return AnalysisContext(
        requirement=Requirement(
            title="Test requirement",
            description="Test description",
            acceptance_criteria=[],
        )
    )


def test_pipeline_executor_records_completed_run_and_steps():
    ctx = build_context()

    result = PipelineExecutor().run(
        [SuccessfulStep()],
        ctx,
    )

    trace = ctx.metadata["agent_run"]
    assert result.success is True
    assert result.agent_run["run_id"] == trace.run_id
    assert result.agent_run["steps"] == [
        {
            "step_name": "Successful Step",
            "duration_ms": result.agent_run["steps"][0]["duration_ms"],
            "status": "success",
            "llm_calls": [],
        }
    ]
    assert trace.status == "success"
    assert trace.ended_at is not None
    assert trace.steps[0].step_name == "Successful Step"
    assert trace.steps[0].status == "success"


def test_pipeline_executor_records_failed_step_and_run():
    ctx = build_context()

    result = PipelineExecutor().run(
        [FailingStep()],
        ctx,
    )

    trace = ctx.metadata["agent_run"]
    assert result.success is False
    assert result.agent_run["status"] == "failed"
    assert trace.status == "failed"
    assert trace.error == "step failed"
    assert trace.steps[0].status == "failed"
    assert trace.steps[0].error == "step failed"


def test_llm_client_attaches_trace_to_active_step():
    ctx = build_context()

    result = PipelineExecutor().run(
        [LLMCallingStep()],
        ctx,
    )

    llm_call = result.agent_run["steps"][0]["llm_calls"][0]
    assert llm_call["provider"] == "fake"
    assert llm_call["model"] == "test-model"
    assert llm_call["prompt_chars"] == len("prompt text")
    assert llm_call["response_chars"] == len("response")
    assert llm_call["status"] == "success"
    assert llm_call["input_tokens"] is None
    assert llm_call["output_tokens"] is None
    assert llm_call["total_tokens"] is None