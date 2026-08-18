import requests

from app.core.logger import get_logger

from app.agent.llm.constants import llm_model
from app.agent.llm.providers.base_provider import BaseLLMProvider


logger = get_logger(__name__)

class OllamaProvider(BaseLLMProvider):
    provider_name: str = "ollama"

    def __init__(
        self,
        model: str = llm_model,
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
    ):

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
    ) -> str:
        logger.info("Sending prompt to Ollama...")
        logger.info("Prompt: %s", prompt)
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        logger.info("Response: %s", data["response"])
        print(data["response"])

        return data["response"]