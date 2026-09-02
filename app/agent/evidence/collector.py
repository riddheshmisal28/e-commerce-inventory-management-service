from app.agent.models import AnalysisContext
from app.agent.evidence.models import Evidence, ImpactEvidence, EvidenceType
from app.agent.code_analysis.ast_parser import ModuleFacts, ASTFactsExtractor
from typing import Optional
from pathlib import Path

class EvidenceCollector:
    """
    Collect evidence for each potential impact.
    Source: Requirement text + Schema + AST facts + Call graph
    """

    def __init__(self, ctx: AnalysisContext):
        self.ctx = ctx
        self.requirement = ctx.requirement
        self.requirement_text = ctx.requirement.description.lower()
        self._module_facts_cache: dict[str, ModuleFacts] = {}

    def collect_entity_evidence(self, entity_name: str) -> ImpactEvidence:
        """
        Collect evidence that entity should be changed.
        Evidence from:
        - Requirement mentions entity/field keywords
        - Schema shows entity exists
        - Code shows entity has relevant fields
        """
        evidence = ImpactEvidence(
            impact_id=f"entity:{entity_name}",
            requirement_evidence=[],
            schema_evidence=[],
            code_evidence=[],
            external_evidence=[],
        )

        # 1. Requirement evidence
        if self._requirement_mentions(entity_name):
            evidence.requirement_evidence.append(
                Evidence(
                    type=EvidenceType.REQUIREMENT_MENTION,
                    component=entity_name,
                    file_path=None,
                    line_number=None,
                    description=f"Requirement mentions '{entity_name}'",
                    confidence=0.8,
                )
            )

        # 2. Schema evidence (from database schema)
        entity_obj = self._find_entity_in_schema(entity_name)
        if entity_obj:
            evidence.schema_evidence.append(
                Evidence(
                    type=EvidenceType.SCHEMA_FIELD,
                    component=entity_name,
                    file_path=entity_obj.get("file_path"),
                    line_number=None,
                    description=f"Entity '{entity_name}' exists in schema",
                    confidence=1.0,
                )
            )

        # 3. Code evidence (from AST facts)
        module_facts = self._get_module_facts_for_entity(entity_name)
        if module_facts and entity_name in module_facts.classes:
            class_fact = module_facts.classes[entity_name]
            evidence.code_evidence.append(
                Evidence(
                    type=EvidenceType.CODE_FIELD,
                    component=entity_name,
                    file_path=module_facts.file_path,
                    line_number=class_fact.line_number,
                    description=f"Class '{entity_name}' defined in code",
                    confidence=1.0,
                )
            )

        return evidence

    def collect_field_evidence(self, entity_name: str, field_name: str) -> ImpactEvidence:
        """Collect evidence for field addition/modification"""
        evidence = ImpactEvidence(
            impact_id=f"field:{entity_name}.{field_name}",
            requirement_evidence=[],
            schema_evidence=[],
            code_evidence=[],
            external_evidence=[],
        )

        # 1. Requirement implies field need?
        if self._requirement_mentions_concept(field_name):
            evidence.requirement_evidence.append(
                Evidence(
                    type=EvidenceType.REQUIREMENT_MENTION,
                    component=f"{entity_name}.{field_name}",
                    file_path=None,
                    line_number=None,
                    description=f"Requirement implies need for '{field_name}' field",
                    confidence=0.6,  # Lower: it's inferred
                )
            )

        # 2. Field already exists in code?
        module_facts = self._get_module_facts_for_entity(entity_name)
        if module_facts and entity_name in module_facts.classes:
            class_fact = module_facts.classes[entity_name]
            if field_name in class_fact.fields:
                field_fact = class_fact.fields[field_name]
                evidence.code_evidence.append(
                    Evidence(
                        type=EvidenceType.CODE_FIELD,
                        component=f"{entity_name}.{field_name}",
                        file_path=module_facts.file_path,
                        line_number=field_fact.line_number,
                        description=f"Field '{field_name}' already exists with type '{field_fact.type_annotation}'",
                        confidence=1.0,
                    )
                )

        return evidence

    def _requirement_mentions(self, term: str) -> bool:
        """Check if requirement text mentions a term"""
        return term.lower() in self.requirement_text

    def _requirement_mentions_concept(self, concept: str) -> bool:
        """Check if requirement implies a concept"""
        return concept.lower() in self.requirement_text

    def _find_entity_in_schema(self, entity_name: str) -> Optional[dict]:
        """Find entity in engineering context schema"""
        for entity in self.ctx.engineering_context.entities:
            if entity.get("name") == entity_name:
                return entity
        return None

    def _get_module_facts_for_entity(self, entity_name: str) -> Optional[ModuleFacts]:
        """Parse and get AST facts for entity's module"""
        entity_obj = self._find_entity_in_schema(entity_name)
        if not entity_obj:
            return None

        file_path = entity_obj.get("file_path")
        if not file_path or file_path in self._module_facts_cache:
            return self._module_facts_cache.get(file_path)

        try:
            source = Path(file_path).read_text()
            extractor = ASTFactsExtractor(file_path, source)
            facts = extractor.analyze()
            self._module_facts_cache[file_path] = facts
            return facts
        except Exception:
            return None