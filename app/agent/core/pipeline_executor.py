import time

from app.agent.core.agent_step import AgentStep
from app.agent.models import (
    AnalysisContext,
    PipelineResult,
)
from app.core.logger import get_logger
from app.agent.observability.agent_run_tracker import AgentRunTracker
from app.agent.execution.decision_gate import DecisionGate
from app.agent.execution.execution_policy import decision_metadata


logger = get_logger(__name__)


class PipelineExecutor:

    def __init__(
        self,
        run_tracker: AgentRunTracker | None = None,
        decision_gate: DecisionGate | None = None,
    ):
        self.run_tracker = run_tracker or AgentRunTracker()
        self.decision_gate = decision_gate or DecisionGate()
        self.agent_run = None

    def run(
        self,
        pipeline: list[AgentStep],
        ctx: AnalysisContext,
    ) -> PipelineResult:

        total_start = time.perf_counter()

        self.agent_run = self.run_tracker.start_run(
            metadata={
                "requirement_title": ctx.requirement.title,
                "pipeline_steps": [step.name for step in pipeline],
            },
        )
        ctx.metadata["agent_run"] = self.agent_run

        self.before_pipeline(ctx)

        for step in pipeline:

            execution_decision = self.decision_gate.decide(
                step.name,
                ctx,
            )

            if execution_decision is not None and not execution_decision.should_execute:
                self._record_skipped_step(
                    step.name,
                    decision_metadata(execution_decision),
                )
                self.on_step_skipped(
                    step,
                    ctx,
                )
                continue

            if not self._should_execute(
                step,
                ctx,
            ):
                self._record_skipped_step(
                    step.name,
                    {
                        "execution_decision": {
                            "should_execute": False,
                            "policy": "CONTEXT_NOT_REQUESTED",
                            "reason": (
                                "Required execution context was not requested."
                            ),
                            "confidence": 1.0,
                            "inputs": {},
                        },
                    },
                )
                self.on_step_skipped(
                    step,
                    ctx,
                )
                continue

            start = time.perf_counter()

            self.before_step(
                step,
                ctx,
            )

            step_trace = self.run_tracker.start_step(
                step.name,
                metadata=(
                    decision_metadata(execution_decision)
                    if execution_decision is not None
                    else None
                ),
            )
            impact_snapshot = self._impact_snapshot(ctx)

            try:

                ctx.execution_history.append(
                    step.name,
                )

                step.execute(ctx)

                elapsed = (
                    time.perf_counter()
                    - start
                )

                ctx.execution_metrics[
                    step.name
                ] = elapsed * 1000

                self.after_step(
                    step,
                    ctx,
                    elapsed,
                )

                step_metrics = self._step_metrics(
                    step.name,
                    impact_snapshot,
                    ctx,
                )
                ctx.metadata.setdefault("step_metrics", {})[
                    step.name
                ] = step_metrics

                self.run_tracker.end_step(
                    step_trace,
                    metadata=step_metrics,
                )

            except Exception as exc:

                elapsed = (
                    time.perf_counter()
                    - start
                )

                ctx.execution_metrics[
                    step.name
                ] = elapsed * 1000

                self.on_error(
                    step,
                    ctx,
                    elapsed,
                )

                self.run_tracker.end_step(
                    step_trace,
                    status="failed",
                    error=str(exc),
                    metadata=self._step_metrics(
                        step.name,
                        impact_snapshot,
                        ctx,
                    ),
                )

                self.agent_run = self.run_tracker.end_run(
                    status="failed",
                    error=str(exc),
                )
                ctx.metadata["agent_run"] = self.agent_run

                total_elapsed = (
                    time.perf_counter()
                    - total_start
                )

                result = PipelineResult(
                    success=False,
                    total_duration_ms=(
                        total_elapsed * 1000
                    ),
                    agent_run=self.run_tracker.summary(),
                    executed_steps=(
                        ctx.execution_history.copy()
                    ),
                    execution_metrics=(
                        ctx.execution_metrics.copy()
                    ),
                    report=ctx.report,
                    error=str(exc),
                )

                ctx.pipeline_result = result

                return result

        self.after_pipeline(ctx)

        self.agent_run = self.run_tracker.end_run()
        ctx.metadata["agent_run"] = self.agent_run

        total_elapsed = (
            time.perf_counter()
            - total_start
        )

        result = PipelineResult(
            success=True,
            total_duration_ms=(
                total_elapsed * 1000
            ),
            agent_run=self.run_tracker.summary(),
            executed_steps=(
                ctx.execution_history.copy()
            ),
            execution_metrics=(
                ctx.execution_metrics.copy()
            ),
            report=ctx.report,
        )

        ctx.pipeline_result = result

        return result

    def _record_skipped_step(
        self,
        step_name: str,
        metadata: dict[str, object],
    ) -> None:
        step_trace = self.run_tracker.start_step(
            step_name,
            metadata=metadata,
        )
        self.run_tracker.end_step(
            step_trace,
            status="skipped",
        )

    def _should_execute(
        self,
        step: AgentStep,
        ctx: AnalysisContext,
    ) -> bool:

        required_context = getattr(
            step,
            "required_context",
            set(),
        )

        if not required_context:
            return True

        plan = ctx.context_plan

        if plan is None:
            logger.warning(
                "Skipping step '%s': "
                "ContextPlan is not available.",
                step.name,
            )

            return False

        return all(
            self._context_requested(
                context_type,
                plan,
            )
            for context_type in required_context
        )

    def _context_requested(
        self,
        context_type: str,
        plan,
    ) -> bool:

        attribute = (
            f"need_{context_type}"
        )

        return getattr(
            plan,
            attribute,
            False,
        )

    def before_pipeline(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Starting pipeline execution.",
        )

    def after_pipeline(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Pipeline execution completed.",
        )

    def before_step(
        self,
        step: AgentStep,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Starting step: %s",
            step.name,
        )

    def after_step(
        self,
        step: AgentStep,
        ctx: AnalysisContext,
        elapsed: float,
    ) -> None:

        logger.info(
            "Completed step: %s (%.3f ms)",
            step.name,
            elapsed * 1000,
        )

    def on_step_skipped(
        self,
        step: AgentStep,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Skipping step: %s "
            "(required context not requested)",
            step.name,
        )

    def on_error(
        self,
        step: AgentStep,
        ctx: AnalysisContext,
        elapsed: float,
    ) -> None:

        logger.exception(
            "Step '%s' failed after %.3f ms",
            step.name,
            elapsed * 1000,
        )

    def _impact_snapshot(
        self,
        ctx: AnalysisContext,
    ) -> dict[str, list]:
        return {
            "entity": list(ctx.entity_impacts),
            "endpoint": list(ctx.endpoint_impacts),
            "model": list(ctx.model_impacts),
            "business_logic": list(ctx.business_logic_impacts),
            "repository": list(ctx.repository_impacts),
            "integration": list(ctx.integration_impacts),
            "component": list(ctx.component_impacts),
        }

    def _step_metrics(
        self,
        step_name: str,
        before: dict[str, list],
        ctx: AnalysisContext,
    ) -> dict[str, object]:
        after = self._impact_snapshot(ctx)

        if step_name == "Impact Reasoner":
            impacts = self._flatten_impacts(after)
            confidences = [
                impact.confidence
                for impact in impacts
                if impact.confidence is not None
            ]
            return {
                "impacts_generated": len(impacts),
                "avg_confidence": (
                    sum(confidences) / len(confidences)
                    if confidences
                    else None
                ),
            }

        if step_name in {
            "Impact Validator",
            "Grounding Validator",
        }:
            before_count = len(self._flatten_impacts(before))
            after_count = len(self._flatten_impacts(after))
            rejected = max(before_count - after_count, 0)
            if step_name == "Grounding Validator":
                return {
                    "grounded": after_count,
                    "ungrounded": rejected,
                    "grounding_rate": (
                        after_count / before_count
                        if before_count
                        else None
                    ),
                }

            return {
                "accepted": after_count,
                "rejected": rejected,
                "rejection_rate": (
                    rejected / before_count
                    if before_count
                    else None
                ),
            }

        return {}

    @staticmethod
    def _flatten_impacts(
        impacts: dict[str, list],
    ) -> list:
        return [
            impact
            for category_impacts in impacts.values()
            for impact in category_impacts
        ]