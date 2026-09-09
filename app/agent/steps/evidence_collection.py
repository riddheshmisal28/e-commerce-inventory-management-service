from app.agent.core.agent_step import AgentStep
from app.agent.models import AnalysisContext
from app.agent.evidence.collector import EvidenceCollector
from app.core.logger import get_logger

logger = get_logger(__name__)


class EvidenceCollectionStep(AgentStep):
    """
    Collect multi-source evidence for each entity and component.
    
    Evidence sources:
    - REQUIREMENT_MENTION: Entity mentioned in requirement text
    - SCHEMA_FIELD: Field exists in database schema
    - CODE_FIELD: Field extracted from AST
    - CODE_METHOD: Method extracted from AST
    - CODE_IMPORT: Imports and dependencies
    - Others: decorators, annotations, call sites, inheritance
    
    Results stored in:
    - ctx.entity_evidence: dict[entity_name] -> ImpactEvidence
    - ctx.field_evidence: dict[(entity, field)] -> ImpactEvidence
    
    Evidence confidence (0.0-1.0) is aggregated from all sources.
    """

    name = "Evidence Collection"

    required_context = {"entities"}

    def execute(self, ctx: AnalysisContext) -> None:
        """
        Collect evidence for all entities and their fields.
        
        Requires:
        - ctx.requirement: Requirement with description text
        - ctx.engineering_context.entities: List of entities
        - ctx.code_facts (optional): AST facts for code evidence
        
        Produces:
        - ctx.entity_evidence: dict[entity_name] -> ImpactEvidence
        - ctx.field_evidence: dict[(entity, field)] -> ImpactEvidence
        """
        # Initialize collector
        collector = EvidenceCollector(ctx)

        # Collect evidence for entities
        ctx.entity_evidence = {}
        ctx.field_evidence = {}

        if not hasattr(ctx, "engineering_context") or not ctx.engineering_context.entities:
            logger.warning("No entities found in context")
            return

        for entity in ctx.engineering_context.entities:
            entity_name = entity.get("name", "")

            if not entity_name:
                continue

            # Collect entity-level evidence
            self._collect_entity_evidence(ctx, collector, entity, entity_name)

            # Collect field-level evidence
            self._collect_field_evidence(ctx, collector, entity, entity_name)

        logger.info(
            f"Collected evidence for {len(ctx.entity_evidence)} entities, "
            f"{len(ctx.field_evidence)} fields"
        )

    def _collect_entity_evidence(
        self, ctx: AnalysisContext, collector: EvidenceCollector, entity: dict, entity_name: str
    ) -> None:
        """Collect evidence for an entity."""
        try:
            evidence = collector.collect_entity_evidence(entity_name)

            # Store evidence
            ctx.entity_evidence[entity_name] = evidence

            # Log evidence quality metrics
            weight = evidence.total_evidence_weight()
            has_code = evidence.has_code_evidence()
            is_speculative = evidence.is_speculative()

            status = "✓" if weight > 0.6 else "⚠" if weight > 0.3 else "✗"
            logger.info(
                f"{status} Entity '{entity_name}': "
                f"confidence={weight:.0%}, "
                f"has_code_evidence={has_code}, "
                f"speculative={is_speculative}"
            )

            # Warn about low-evidence entities
            if is_speculative:
                logger.warning(
                    f"Entity '{entity_name}' only mentioned in requirement (no code evidence)"
                )

        except Exception as e:
            logger.warning(f"Failed to collect entity evidence for '{entity_name}': {e}")

    def _collect_field_evidence(
        self, ctx: AnalysisContext, collector: EvidenceCollector, entity: dict, entity_name: str
    ) -> None:
        """Collect evidence for fields within an entity."""
        # Get entity fields from code facts if available
        if not hasattr(ctx, "code_facts") or entity_name not in ctx.code_facts:
            return

        facts = ctx.code_facts[entity_name]

        # Collect evidence for each field in each class
        for class_name, class_fact in facts.classes.items():
            for field_name, field_fact in class_fact.fields.items():
                try:
                    field_evidence = collector.collect_field_evidence(entity_name, field_name)

                    # Store field evidence
                    key = (entity_name, field_name)
                    ctx.field_evidence[key] = field_evidence

                    # Log field evidence
                    weight = field_evidence.total_evidence_weight()
                    if weight > 0.3:  # Only log significant field evidence
                        logger.debug(
                            f"Field '{entity_name}.{field_name}': "
                            f"confidence={weight:.0%}"
                        )

                except Exception as e:
                    logger.debug(f"Failed to collect field evidence for '{entity_name}.{field_name}': {e}")
