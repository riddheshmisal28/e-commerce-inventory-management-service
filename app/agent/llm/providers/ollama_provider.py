import requests

from app.core.logger import get_logger

from app.agent.llm.constants import planner_model
from app.agent.llm.providers.base_provider import BaseLLMProvider


logger = get_logger(__name__)

class OllamaProvider(BaseLLMProvider):
    provider_name: str = "ollama"

    def __init__(
        self,
        model: str = planner_model,
        base_url: str = "http://localhost:11434",
        timeout: int = 600,
        json_mode: bool = False,
        temperature: float = 0,
        think: bool = False,
        num_predict: int = 2048,
    ):

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.json_mode = json_mode
        self.temperature = temperature
        self.think = think
        self.num_predict = num_predict

    def generate(
        self,
        prompt: str,
    ) -> str:
        logger.info("Sending prompt to Ollama...")
        logger.info("Prompt: %s", prompt)
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }

        if self.json_mode:
            payload["format"] = "json"

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        logger.info("Response: %s", data["response"])
        print(data["response"])

        return data["response"]