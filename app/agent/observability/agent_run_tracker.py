import time
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.agent.observability.models import (
    AgentRunTrace,
    LLMTrace,
    StepTrace,
)


_current_step: ContextVar[Optional[StepTrace]] = ContextVar(
    "current_agent_step",
    default=None,
)


def attach_llm_trace(trace: LLMTrace) -> bool:
    step = _current_step.get()
    if step is None:
        return False

    step.llm_calls.append(trace)
    return True


class AgentRunTracker:
    def __init__(self):
        self.run: Optional[AgentRunTrace] = None
        self._run_start: Optional[float] = None
        self._step_start: Optional[float] = None
        self._step_token: Optional[Token] = None

    def start_run(
        self,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentRunTrace:
        now = datetime.now(timezone.utc)

        self._run_start = time.perf_counter()

        self.run = AgentRunTrace(
            run_id=str(uuid.uuid4()),
            started_at=now,
            metadata=metadata or {},
        )

        return self.run

    def start_step(
        self,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StepTrace:
        if self.run is None:
            raise RuntimeError("Agent run has not been started")

        step = StepTrace(
            step_name=step_name,
            started_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        self.run.steps.append(step)
        self._step_start = time.perf_counter()
        self._step_token = _current_step.set(step)

        return step

    def end_step(
        self,
        step: StepTrace,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._step_start is None:
            return

        step.ended_at = datetime.now(timezone.utc)
        step.duration_ms = (
            time.perf_counter() - self._step_start
        ) * 1000

        step.status = status
        step.error = error

        if metadata:
            step.metadata.update(metadata)

        if self._step_token is not None:
            _current_step.reset(self._step_token)
            self._step_token = None

        self._step_start = None

    def end_run(
        self,
        status: str = "success",
        error: Optional[str] = None,
    ) -> AgentRunTrace:
        if self.run is None:
            raise RuntimeError("Agent run has not been started")

        self.run.ended_at = datetime.now(timezone.utc)

        if self._run_start is not None:
            self.run.total_duration_ms = (
                time.perf_counter() - self._run_start
            ) * 1000

        self.run.status = status
        self.run.error = error

        return self.run

    def summary(self) -> Dict[str, Any]:
        if self.run is None:
            raise RuntimeError("Agent run has not been started")

        return {
            "run_id": self.run.run_id,
            "status": self.run.status,
            "total_duration_ms": self.run.total_duration_ms,
            "steps": [
                {
                    "step_name": step.step_name,
                    "duration_ms": step.duration_ms,
                    "status": step.status,
                    "llm_calls": [
                        {
                            "provider": llm_call.provider,
                            "model": llm_call.model,
                            "duration_ms": llm_call.duration_ms,
                            "prompt_chars": llm_call.prompt_chars,
                            "response_chars": llm_call.response_chars,
                            "status": llm_call.status,
                            "error": llm_call.error,
                            "input_tokens": llm_call.input_tokens,
                            "output_tokens": llm_call.output_tokens,
                            "total_tokens": llm_call.total_tokens,
                            "tokens_per_second": llm_call.tokens_per_second,
                        }
                        for llm_call in step.llm_calls
                    ],
                }
                for step in self.run.steps
            ],
        }