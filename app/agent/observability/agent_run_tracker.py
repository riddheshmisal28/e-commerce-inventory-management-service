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


def attach_step_metadata(
    metadata: Dict[str, Any],
) -> bool:
    step = _current_step.get()
    if step is None:
        return False

    step.metadata.update(metadata)
    return True


class AgentRunTracker:
    def __init__(self):
        self.run: Optional[AgentRunTrace] = None
        self._run_start: Optional[float] = None
        self._step_start: ContextVar[Optional[float]] = ContextVar(
            f"agent_run_step_start_{id(self)}",
            default=None,
        )
        self._step_token: ContextVar[Optional[Token]] = ContextVar(
            f"agent_run_step_token_{id(self)}",
            default=None,
        )

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
        self._step_start.set(time.perf_counter())
        self._step_token.set(_current_step.set(step))

        return step

    def end_step(
        self,
        step: StepTrace,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        step_start = self._step_start.get()
        if step_start is None:
            return

        step.ended_at = datetime.now(timezone.utc)
        step.duration_ms = (
            time.perf_counter() - step_start
        ) * 1000

        step.status = status
        step.error = error

        if metadata:
            step.metadata.update(metadata)

        step_token = self._step_token.get()
        if step_token is not None:
            _current_step.reset(step_token)
            self._step_token.set(None)

        self._step_start.set(None)

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
            "started_at": self.run.started_at.isoformat() if self.run.started_at else None,
            "ended_at": self.run.ended_at.isoformat() if self.run.ended_at else None,
            "total_duration_ms": self.run.total_duration_ms,
            "steps": [
                {
                    "step_name": step.step_name,
                    "duration_ms": step.duration_ms,
                    "status": step.status,
                    "metrics": step.metadata,
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