from app.agent.models import LLMResponse
import time
from app.agent.llm.providers.base_provider import BaseLLMProvider
from app.agent.llm.providers.ollama_provider import OllamaProvider
from app.core.logger import get_logger

logger = get_logger(__name__)

class LLMClient:

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        json_mode: bool = False,
    ):

        self.provider = provider or OllamaProvider(
            json_mode=json_mode,
        )

    def generate(
        self,
        prompt: str,
    ) -> LLMResponse:

        start = time.perf_counter()

        response = self.provider.generate(prompt)

        duration = (time.perf_counter() - start) * 1000

        return LLMResponse(
            provider=self.provider.provider_name,
            model=self.provider.model,
            response=response,
            duration_ms=duration,
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