from app.agent.models import LLMResponse
import time
from app.agent.llm.providers.base_provider import BaseLLMProvider
from app.agent.llm.providers.ollama_provider import OllamaProvider
from app.core.logger import get_logger
from app.agent.llm.constants import planner_model
from app.agent.observability.agent_run_tracker import attach_llm_trace
from app.agent.observability.models import LLMTrace

logger = get_logger(__name__)

class LLMClient:

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        json_mode: bool = False,
        model: str = planner_model,
    ):

        self.provider = provider or OllamaProvider(
            json_mode=json_mode,
            model=model
        )

    def generate(
        self,
        prompt: str,
    ) -> LLMResponse:

        start = time.perf_counter()

        try:
            response = self.provider.generate(prompt)
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self._attach_trace(
                prompt=prompt,
                response="",
                duration_ms=duration,
                status="failed",
                error=str(exc),
            )
            self._log_metrics(
                prompt=prompt,
                response="",
                duration_ms=duration,
                success=False,
            )
            raise

        duration = (time.perf_counter() - start) * 1000

        self._attach_trace(
            prompt=prompt,
            response=response,
            duration_ms=duration,
            status="success",
        )

        self._log_metrics(
            prompt=prompt,
            response=response,
            duration_ms=duration,
            success=True,
        )

        return LLMResponse(
            provider=self.provider.provider_name,
            model=self.provider.model,
            response=response,
            duration_ms=duration,
            input_tokens=getattr(
                self.provider,
                "last_input_tokens",
                None,
            ),
            output_tokens=getattr(
                self.provider,
                "last_output_tokens",
                None,
            ),
            total_tokens=getattr(
                self.provider,
                "last_total_tokens",
                None,
            ),
            tokens_per_second=(
                getattr(
                    self.provider,
                    "last_output_tokens",
                    None,
                ) / (duration / 1000)
                if getattr(
                    self.provider,
                    "last_output_tokens",
                    None,
                ) is not None and duration > 0
                else None
            ),
        )

    def _attach_trace(
        self,
        prompt: str,
        response: str,
        duration_ms: float,
        status: str,
        error: str | None = None,
    ) -> None:
        attach_llm_trace(
            LLMTrace(
                provider=self.provider.provider_name,
                model=self.provider.model,
                duration_ms=duration_ms,
                prompt_chars=len(prompt),
                response_chars=len(response),
                status=status,
                error=error,
                input_tokens=getattr(
                    self.provider,
                    "last_input_tokens",
                    None,
                ),
                output_tokens=getattr(
                    self.provider,
                    "last_output_tokens",
                    None,
                ),
                total_tokens=getattr(
                    self.provider,
                    "last_total_tokens",
                    None,
                ),
                tokens_per_second = (
                    getattr(
                        self.provider,
                        "last_output_tokens",
                        None,
                    ) / (duration_ms / 1000)
                    if getattr(
                        self.provider,
                        "last_output_tokens",
                        None,
                    ) and duration_ms > 0
                    else None
                )
            )
        )

    def _log_metrics(
        self,
        prompt: str,
        response: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        input_tokens = getattr(
            self.provider,
            "last_input_tokens",
            None,
        )
        output_tokens = getattr(
            self.provider,
            "last_output_tokens",
            None,
        )
        total_tokens = getattr(
            self.provider,
            "last_total_tokens",
            None,
        )

        logger.info(
            "LLM call metrics",
            extra={
                "model": self.provider.model,
                "provider": self.provider.provider_name,
                "duration_ms": duration_ms,
                "prompt_chars": len(prompt),
                "response_chars": len(response),
                "success": success,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "tokens_per_second": (
                    output_tokens / (duration_ms / 1000)
                    if output_tokens is not None and duration_ms > 0
                    else None
                ),
            },
        )

    def generate_with_retry(
        self,
        prompt: str,
        max_attempts: int = 3,
        retry_delay_s: float = 1.0,
    ) -> LLMResponse:
        """
        Call generate() and retry on failure.

        Local LLMs (Ollama) sometimes return empty or
        non-JSON responses. Retrying with the same prompt
        is usually sufficient to get a valid response.
        """

        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):

            try:
                return self.generate(prompt)

            except Exception as exc:
                last_exc = exc

                logger.warning(
                    "LLM attempt %d/%d failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )

                if attempt < max_attempts:
                    time.sleep(retry_delay_s)

        raise RuntimeError(
            f"LLM failed after {max_attempts} attempts."
        ) from last_exc