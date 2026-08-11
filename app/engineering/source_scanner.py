from pathlib import Path


class SourceScanner:

    def __init__(
        self,
        root_dir: str = ".",
    ):
        self.root_dir = Path(root_dir)

    def search(
        self,
        keywords: list[str],
    ) -> list[dict]:

        if not keywords:
            return []

        results = []

        for file_path in self._get_python_files():

            try:
                content = file_path.read_text(
                    encoding="utf-8"
                )
            except (UnicodeDecodeError, OSError):
                continue

            content_lower = content.lower()

            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower() in content_lower
            ]

            if not matched_keywords:
                continue

            results.append(
                {
                    "file": str(file_path),
                    "keywords": matched_keywords,
                }
            )

        return results

    def _get_python_files(self):

        excluded = {
            ".venv",
            "venv",
            "__pycache__",
            ".git",
        }

        for path in self.root_dir.rglob("*.py"):

            if any(
                part in excluded
                for part in path.parts
            ):
                continue

            yield path