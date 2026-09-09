from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LLMTrace:
    provider: str
    model: str
    duration_ms: float = 0.0
    prompt_chars: int = 0
    response_chars: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    tokens_per_second: Optional[float] = None
    status: str = "success"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepTrace:
    step_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "running"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    llm_calls: List[LLMTrace] = field(default_factory=list)


@dataclass
class AgentRunTrace:
    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_duration_ms: float = 0.0
    status: str = "running"
    error: Optional[str] = None
    steps: List[StepTrace] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)