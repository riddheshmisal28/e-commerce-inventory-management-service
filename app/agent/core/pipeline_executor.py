import time

from app.agent.core.agent_step import AgentStep
from app.agent.models import (
    AnalysisContext,
    PipelineResult,
)
from app.core.logger import get_logger
from app.agent.observability.agent_run_tracker import AgentRunTracker


logger = get_logger(__name__)


class PipelineExecutor:

    def __init__(
        self,
        run_tracker: AgentRunTracker | None = None,
    ):
        self.run_tracker = run_tracker or AgentRunTracker()
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

            if not self._should_execute(
                step,
                ctx,
            ):
                step_trace = self.run_tracker.start_step(
                    step.name,
                )
                self.run_tracker.end_step(
                    step_trace,
                    status="skipped",
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
            )

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

                self.run_tracker.end_step(
                    step_trace,
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