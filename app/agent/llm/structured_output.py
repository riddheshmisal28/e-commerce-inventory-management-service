import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

class StructuredOutputParser:
    """
    Parses and validates structured responses returned by an LLM.

    Responsibilities:
    - Extract JSON from the raw LLM response.
    - Remove common formatting such as markdown code fences.
    - Unwrap known response wrappers.
    - Validate the resulting payload using the supplied Pydantic model.

    This class intentionally does not contain schema-specific logic.
    The supplied Pydantic model is responsible for validating the
    structure and fields of the response.
    """

    def parse(
        self,
        response: str,
        output_model: type[BaseModel],
    ) -> BaseModel:

        if not response or not response.strip():
            raise ValueError(
                "LLM response is empty."
            )

        json_data = self._extract_json(
            response,
        )

        json_data = self._normalize(
            json_data,
        )

        try:
            return output_model.model_validate(
                json_data,
            )

        except ValidationError as exc:
            raise ValueError(
                f"Failed to parse LLM response into "
                f"{output_model.__name__}.\n"
                f"Validation errors:\n{exc}\n"
                f"Response:\n{response}"
            ) from exc

    def _extract_json(
        self,
        response: str,
    ) -> dict[str, Any]:

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
        # Try parsing the complete response first
        # ---------------------------------------------------------

        try:
            json_data = json.loads(
                cleaned,
            )

        except json.JSONDecodeError:

            # -----------------------------------------------------
            # Find the start of the first JSON object and use
            # raw_decode so that trailing text (extra prose, a
            # second JSON block, etc.) after the closing brace
            # does not cause "Extra data" errors.
            # -----------------------------------------------------

            start = cleaned.find("{")

            if start == -1:
                raise ValueError(
                    "No JSON object found in LLM response."
                )

            try:
                decoder = json.JSONDecoder()
                json_data, _ = decoder.raw_decode(
                    cleaned,
                    start,
                )

            except json.JSONDecodeError as exc:
                raise ValueError(
                    "LLM response contains malformed JSON."
                ) from exc

        if not isinstance(json_data, dict):
            raise ValueError(
                "LLM response must contain a JSON object."
            )

        return json_data

    def _normalize(
        self,
        json_data: dict[str, Any],
    ) -> dict[str, Any]:

        """
        Unwrap common LLM response containers.

        Example:

            {
                "result": {
                    "need_entities": true
                }
            }

        becomes:

            {
                "need_entities": true
            }

        The method is intentionally generic because different
        structured-output models may use different wrapper names.
        """

        wrappers = (
            "impact_analysis_requirements",
            "result",
            "data",
            "response",
            "output",
        )

        for wrapper in wrappers:

            wrapped_data = json_data.get(
                wrapper,
            )

            if isinstance(
                wrapped_data,
                dict,
            ):
                return wrapped_data

        return json_data