from app.agent.models import LLMResponse
import time
from app.agent.llm.providers.base_provider import BaseLLMProvider
from app.agent.llm.providers.ollama_provider import OllamaProvider

class LLMClient:

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
    ):

        self.provider = provider or OllamaProvider()

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