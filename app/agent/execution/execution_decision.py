from dataclasses import dataclass


@dataclass
class ExecutionDecision:
    should_execute: bool
    policy: str
    reason: str
    confidence: float
    inputs: dict[str, object]