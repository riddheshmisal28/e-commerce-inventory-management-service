from app.agent.core.agent_step import AgentStep
from app.agent.execution.execution_context import ExecutionContext
from app.agent.execution.execution_decision import ExecutionDecision
from app.agent.execution.execution_policy import ExecutionPolicy
from app.agent.models import AnalysisContext


class DecisionGate:
    """Builds deterministic decisions for steps with execution policies."""

    def __init__(self, policy: ExecutionPolicy | None = None):
        self.policy = policy or ExecutionPolicy()

    def decide(
        self,
        step: AgentStep | str,
        ctx: AnalysisContext,
    ) -> ExecutionDecision | None:
        """
        Evaluate execution decision for a step.
        
        If the step is Semantic Impact Refiner or provides an execution policy,
        evaluate the decision. Otherwise return None.
        """
        step_name = step if isinstance(step, str) else getattr(step, "name", str(step))

        if step_name != "Semantic Impact Refiner" and not getattr(step, "execution_policy", None):
            return None

        policy = getattr(step, "execution_policy", None) or self.policy
        return policy.decide(
            step_name,
            self._evaluate(ctx),
        )

    @staticmethod
    def _evaluate(ctx: AnalysisContext) -> ExecutionContext:
        step_metrics = ctx.metadata.get("step_metrics", {})
        reasoner_metrics = step_metrics.get("Impact Reasoner", {})
        validator_metrics = step_metrics.get("Impact Validator", {})
        grounding_metrics = step_metrics.get("Grounding Validator", {})
        impacts = [
            *ctx.entity_impacts,
            *ctx.endpoint_impacts,
            *ctx.model_impacts,
            *ctx.business_logic_impacts,
            *ctx.repository_impacts,
            *ctx.integration_impacts,
            *ctx.component_impacts,
        ]
        relevance = [
            impact.relevance_score
            for impact in impacts
            if impact.relevance_score is not None
        ]
        confidence = [
            impact.confidence
            for impact in impacts
            if impact.confidence is not None
        ]

        return ExecutionContext(
            impact_count=len(impacts),
            impacts_generated=reasoner_metrics.get(
                "impacts_generated",
                len(impacts),
            ),
            accepted_count=validator_metrics.get(
                "accepted",
                len(impacts),
            ),
            rejected_count=validator_metrics.get(
                "rejected",
                0,
            ),
            grounded_count=grounding_metrics.get(
                "grounded",
                len(impacts),
            ),
            ungrounded_count=grounding_metrics.get(
                "ungrounded",
                0,
            ),
            grounding_rate=grounding_metrics.get(
                "grounding_rate",
            ),
            validator_acceptance_rate=(
                validator_metrics.get("accepted", len(impacts))
                / (
                    validator_metrics.get("accepted", len(impacts))
                    + validator_metrics.get("rejected", 0)
                )
                if (
                    validator_metrics.get("accepted", len(impacts))
                    + validator_metrics.get("rejected", 0)
                )
                else None
            ),
            avg_relevance=(sum(relevance) / len(relevance) if relevance else None),
            avg_confidence=(sum(confidence) / len(confidence) if confidence else None),
            previous_refinement_statistics=ctx.metadata.get(
                "previous_refinement_statistics",
                {},
            ),
        )