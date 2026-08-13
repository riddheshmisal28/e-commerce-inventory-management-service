import ast
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
                source = file_path.read_text(
                    encoding="utf-8"
                )
                tree = ast.parse(source)
            except (
                UnicodeDecodeError,
                OSError,
                SyntaxError,
            ):
                continue

            file_results = self._scan_file(
                file_path,
                tree,
                source,
                keywords,
            )

            results.extend(file_results)

        return results

    def _scan_file(
        self,
        file_path: Path,
        tree: ast.AST,
        source: str,
        keywords: list[str],
    ) -> list[dict]:

        results = []

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.ClassDef,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            source_segment = ast.get_source_segment(
                source,
                node,
            )

            if not source_segment:
                continue

            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower()
                in source_segment.lower()
            ]

            if not matched_keywords:
                continue

            node_type = (
                "class"
                if isinstance(node, ast.ClassDef)
                else "function"
            )

            results.append(
                {
                    "file": str(file_path),
                    "type": node_type,
                    "name": node.name,
                    "line": node.lineno,
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