import os
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
        base_url: str | None = None,
        timeout: int = 600,
        json_mode: bool = False,
        temperature: float = 0,
        think: bool = False,
        num_predict: int = 2048,
    ):

        self.model = model
        resolved_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_URL")
            or "http://localhost:11434"
        )
        self.base_url = resolved_url.rstrip("/")
        self.timeout = timeout
        self.json_mode = json_mode
        self.temperature = temperature
        self.think = think
        self.num_predict = num_predict
        self.last_input_tokens: int | None = None
        self.last_output_tokens: int | None = None
        self.last_total_tokens: int | None = None

    def generate(
        self,
        prompt: str,
    ) -> str:
        logger.info("Sending prompt to Ollama...")
        logger.info("Prompt: %s", prompt)
        self.last_input_tokens = None
        self.last_output_tokens = None
        self.last_total_tokens = None
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

        self.last_input_tokens = data.get("prompt_eval_count")
        self.last_output_tokens = data.get("eval_count")
        if (
            self.last_input_tokens is not None
            and self.last_output_tokens is not None
        ):
            self.last_total_tokens = (
                self.last_input_tokens
                + self.last_output_tokens
            )

        logger.info(
            "Ollama usage metadata",
            extra={
                "model": self.model,
                "prompt_eval_count": self.last_input_tokens,
                "eval_count": self.last_output_tokens,
                "total_tokens": self.last_total_tokens,
            },
        )

        logger.info("Response: %s", data["response"])
        # print(data["response"])

        return data["response"]