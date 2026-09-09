from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    """Metrics produced by earlier pipeline steps for execution decisions."""

    impact_count: int = 0
    impacts_generated: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    grounded_count: int = 0
    ungrounded_count: int = 0
    grounding_rate: float | None = None
    validator_acceptance_rate: float | None = None
    avg_relevance: float | None = None
    avg_confidence: float | None = None
    previous_refinement_statistics: dict[str, float | int] = field(
        default_factory=dict,
    )