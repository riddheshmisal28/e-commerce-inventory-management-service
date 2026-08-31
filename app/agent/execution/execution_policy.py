from dataclasses import dataclass

from app.agent.execution.execution_context import ExecutionContext
from app.agent.execution.execution_decision import ExecutionDecision


EvaluationContext = ExecutionContext


@dataclass
class ExecutionPolicyConfig:
    single_impact_confidence_threshold: float = 0.85
    single_impact_relevance_threshold: float = 0.85
    require_full_grounding_for_skip: bool = True


class ExecutionPolicy:
    """Deterministic execution policy for expensive pipeline steps."""

    def __init__(
        self,
        config: ExecutionPolicyConfig | None = None,
    ):
        self.config = config or ExecutionPolicyConfig()

    def decide(
        self,
        step_name: str,
        context: ExecutionContext,
    ) -> ExecutionDecision:
        inputs = self._inputs(context)

        if step_name != "Semantic Impact Refiner":
            return ExecutionDecision(
                should_execute=True,
                reason="No execution policy is configured for this step.",
                confidence=1.0,
                policy="DEFAULT_EXECUTE",
                inputs=inputs,
            )

        if context.impact_count == 0:
            return ExecutionDecision(
                should_execute=False,
                reason="Nothing exists to refine.",
                confidence=1.0,
                policy="NO_IMPACTS",
                inputs=inputs,
            )

        if context.impact_count == 1:
            if (
                (
                    not self.config.require_full_grounding_for_skip
                    or context.grounding_rate == 1.0
                )
                and context.avg_confidence is not None
                and context.avg_confidence
                >= self.config.single_impact_confidence_threshold
                and context.avg_relevance is not None
                and context.avg_relevance
                >= self.config.single_impact_relevance_threshold
            ):
                return ExecutionDecision(
                    should_execute=False,
                    reason="Only one strong grounded impact remains.",
                    confidence=0.91,
                    policy="SINGLE_STRONG_IMPACT",
                    inputs=inputs,
                )

            return ExecutionDecision(
                should_execute=True,
                reason="A single impact does not meet the strong-impact thresholds.",
                confidence=0.85,
                policy="SINGLE_IMPACT_REQUIRES_REFINEMENT",
                inputs=inputs,
            )

        return ExecutionDecision(
            should_execute=True,
            reason="Multiple grounded impacts require semantic relevance filtering.",
            confidence=0.7,
            policy="MULTIPLE_IMPACTS",
            inputs=inputs,
        )

    @staticmethod
    def _inputs(context: ExecutionContext) -> dict[str, object]:
        return {
            "impact_count": context.impact_count,
            "impacts_generated": context.impacts_generated,
            "accepted_count": context.accepted_count,
            "rejected_count": context.rejected_count,
            "grounded_count": context.grounded_count,
            "ungrounded_count": context.ungrounded_count,
            "grounding_rate": context.grounding_rate,
            "validator_acceptance_rate": context.validator_acceptance_rate,
            "avg_relevance": context.avg_relevance,
            "avg_confidence": context.avg_confidence,
            "previous_refinement_statistics": (
                context.previous_refinement_statistics.copy()
            ),
        }

    def should_refine(
        self,
        evaluation: EvaluationContext,
    ) -> ExecutionDecision:
        """Backward-compatible shorthand for the semantic refiner policy."""
        return self.decide(
            "Semantic Impact Refiner",
            evaluation,
        )


def decision_metadata(decision: ExecutionDecision) -> dict[str, object]:
    return {
        "execution_decision": {
            "should_execute": decision.should_execute,
            "policy": decision.policy,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "inputs": decision.inputs,
        },
    }