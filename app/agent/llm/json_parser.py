import json
import re
from typing import Any

class LLMJsonParser:
    """
    Parses JSON responses returned by an LLM.

    The parser is responsible only for extracting valid JSON.
    Schema validation is handled separately by the Pydantic model
    that consumes the parsed dictionary.
    """

    def parse(
        self,
        response: str,
    ) -> dict[str, Any]:

        if not response or not response.strip():
            raise ValueError(
                "LLM response is empty."
            )

        cleaned = response.strip()

        # ---------------------------------------------------------
        # Remove markdown code fences
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        cleaned = cleaned.strip()

        # ---------------------------------------------------------
        # First attempt: parse the complete response
        # ---------------------------------------------------------

        try:
            parsed = json.loads(cleaned)

            if not isinstance(parsed, dict):
                raise ValueError(
                    "LLM response must contain a JSON object."
                )

            return parsed

        except json.JSONDecodeError as exc:
            pass

        # ---------------------------------------------------------
        # Second attempt: extract JSON object from surrounding text
        # ---------------------------------------------------------

        match = re.search(
            r"\{.*\}",
            cleaned,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError(
                "No valid JSON object found in LLM response."
            )

        json_content = match.group()

        try:
            parsed = json.loads(json_content)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM response contains malformed JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "LLM response must contain a JSON object."
            )

        return parsed
