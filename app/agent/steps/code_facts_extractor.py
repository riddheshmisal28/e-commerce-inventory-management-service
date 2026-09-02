from pathlib import Path
from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext
from app.agent.code_analysis.ast_parser import ASTFactsExtractor
from app.core.logger import get_logger

logger = get_logger(__name__)


class CodeFactsExtractor(AgentStep):
    """
    Extract pure code facts (classes, methods, fields, imports) from all entity source files.
    
    Facts are AST-derived only - no inference or decision-making.
    Results cached in ctx.code_facts for use by analyzers.
    """

    name = "Code Facts Extractor"

    required_context = {"entities"}

    def execute(self, ctx: AnalysisContext) -> None:
        """
        Extract code facts for each entity.
        
        Stores results in:
        - ctx.code_facts: dict[entity_name] -> ModuleFacts
        """
        ctx.code_facts = {}

        if not hasattr(ctx, "engineering_context") or not ctx.engineering_context.entities:
            logger.warning("No entities found in context")
            return

        for entity in ctx.engineering_context.entities:
            entity_name = entity.get("name", "")
            file_path = entity.get("file_path") or self._resolve_model_path(entity_name)

            if not entity_name:
                logger.debug("Skipping entity: missing name")
                continue

            if not file_path:
                logger.debug(f"Skipping entity '{entity_name}': source file not found")
                continue

            self._extract_facts_for_entity(ctx, entity_name, file_path)

        logger.info(f"Extracted code facts for {len(ctx.code_facts)} entities")

    @staticmethod
    def _resolve_model_path(entity_name: str) -> str | None:
        """Resolve a database table name to its conventional model module."""
        if not entity_name:
            return None

        root_dir = Path(__file__).resolve().parents[3]
        normalized_name = entity_name.lower()
        candidates = [normalized_name]

        if normalized_name.endswith("ies"):
            candidates.append(f"{normalized_name[:-3]}y")
        elif normalized_name.endswith("s"):
            candidates.append(normalized_name[:-1])

        for module_name in candidates:
            model_path = root_dir / "app" / module_name / "model.py"
            if model_path.exists():
                return str(model_path)

        return None

    def _extract_facts_for_entity(
        self, ctx: AnalysisContext, entity_name: str, file_path: str
    ) -> None:
        """Extract facts from a single entity's source file."""
        try:
            # Read source code
            source_path = Path(file_path)
            if not source_path.exists():
                logger.warning(f"Source file not found: {file_path}")
                return

            source = source_path.read_text()

            # Extract facts using AST parser
            extractor = ASTFactsExtractor(file_path, source)
            facts = extractor.analyze()

            # Cache facts
            ctx.code_facts[entity_name] = facts

            # Log what was found
            num_classes = len(facts.classes)
            num_functions = len(facts.functions)
            num_imports = len(facts.imports)
            logger.info(
                f"Entity '{entity_name}': "
                f"classes={num_classes}, "
                f"functions={num_functions}, "
                f"imports={num_imports}"
            )

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to extract facts from {file_path}: {e}")
