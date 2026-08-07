import time

from app.agent.core.agent_step import AgentStep
from app.core.logger import get_logger
from app.agent.models import (
    AnalysisContext,
    PipelineResult,
)

logger = get_logger(__name__)


class PipelineExecutor:

    def run(
        self,
        pipeline: list[AgentStep],
        ctx: AnalysisContext,
    ) -> PipelineResult:

        total_start = time.perf_counter()

        self.before_pipeline(ctx)

        for step in pipeline:

            start = time.perf_counter()

            self.before_step(
                step,
                ctx,
            )

            try:

                ctx.execution_history.append(
                    step.name
                )

                step.execute(ctx)

                elapsed = (
                    time.perf_counter() - start
                )

                ctx.execution_metrics[
                    step.name
                ] = elapsed

                self.after_step(
                    step,
                    ctx,
                    elapsed,
                )

            except Exception:

                elapsed = (
                    time.perf_counter() - start
                )

                self.on_error(
                    step,
                    ctx,
                    elapsed,
                )

                raise

        self.after_pipeline(ctx)

        total_elapsed = (
            time.perf_counter() - total_start
        )

        result = PipelineResult(
            success=True,
            total_duration_ms=total_elapsed * 1000,
            executed_steps=ctx.execution_history.copy(),
            execution_metrics=ctx.execution_metrics.copy(),
            report=ctx.report,
        )

        ctx.pipeline_result = result

        return result

    def before_pipeline(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Starting pipeline execution."
        )

    def after_pipeline(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Pipeline execution completed."
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