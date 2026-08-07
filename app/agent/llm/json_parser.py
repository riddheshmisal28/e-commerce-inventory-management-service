import json
import re


class LLMJsonParser:

    def parse(
        self,
        response: str,
    ) -> dict:

        cleaned = response.strip()

        # Remove markdown code fences
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
                    "No valid JSON found in LLM response."
                )

            return json.loads(
                match.group()
            )