import json
import re

from pydantic import BaseModel, ValidationError


class StructuredOutputParser:

    def parse(
        self,
        response: str,
        output_model: type[BaseModel],
    ) -> BaseModel:

        json_data = self._extract_json(response)

        json_data = self._normalize(json_data)

        try:
            return output_model.model_validate(json_data)

        except ValidationError as exc:
            raise ValueError(
                f"Failed to parse LLM response into "
                f"{output_model.__name__}.\n"
                f"Response:\n{response}"
            ) from exc

    def _extract_json(
        self,
        response: str,
    ) -> dict:

        cleaned = response.strip()

        cleaned = re.sub(
            r"^```(?:json)?",
            "",
            cleaned,
            flags=re.MULTILINE,
        )

        cleaned = re.sub(
            r"```$",
            "",
            cleaned,
            flags=re.MULTILINE,
        )

        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                cleaned,
                flags=re.DOTALL,
            )

            if not match:
                raise ValueError(
                    "No JSON object found in LLM response."
                )

            return json.loads(match.group())

    def _normalize(
        self,
        json_data: dict,
    ) -> dict:

        #
        # Some models wrap the actual payload.
        #

        wrappers = [
            "impact_analysis_requirements",
            "result",
            "data",
            "response",
            "output",
        ]

        for wrapper in wrappers:

            if (
                wrapper in json_data
                and isinstance(json_data[wrapper], dict)
            ):
                return json_data[wrapper]

        return json_data