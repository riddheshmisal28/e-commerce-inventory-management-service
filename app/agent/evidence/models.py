from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class EvidenceType(str, Enum):
    """Types of evidence for impacts"""
    REQUIREMENT_MENTION = "requirement_mention"  # Keyword in requirement
    SCHEMA_FIELD = "schema_field"  # Field exists in database schema
    CODE_FIELD = "code_field"  # Field exists in code (AST)
    CODE_METHOD = "code_method"  # Method exists in code
    CODE_IMPORT = "code_import"  # Library/module imported
    ANNOTATION = "annotation"  # Type annotation fact
    DECORATOR = "decorator"  # Decorator fact (@property, @validator, etc.)
    CALL_SITE = "call_site"  # Function/method is called
    INHERITANCE = "inheritance"  # Class inherits from parent
    RESPONSE_SCHEMA = "response_schema"  # OpenAPI response schema

@dataclass
class Evidence:
    """Single piece of evidence"""
    type: EvidenceType
    component: str  # What entity/field/method
    file_path: Optional[str]
    line_number: Optional[int]
    description: str
    confidence: float  # 0.0-1.0: certainty of this fact

@dataclass
class ImpactEvidence:
    """Evidence backing an impact"""
    impact_id: str
    requirement_evidence: List[Evidence]  # From requirement text
    schema_evidence: List[Evidence]  # From database schema
    code_evidence: List[Evidence]  # From AST/call graph
    external_evidence: List[Evidence]  # From dependencies/config

    def total_evidence_weight(self) -> float:
        """Sum confidence of all evidence"""
        all_evidence = (
            self.requirement_evidence
            + self.schema_evidence
            + self.code_evidence
            + self.external_evidence
        )
        if not all_evidence:
            return 0.0
        return sum(e.confidence for e in all_evidence) / len(all_evidence)

    def has_code_evidence(self) -> bool:
        """True if backed by actual code facts"""
        return len(self.code_evidence) > 0

    def is_speculative(self) -> bool:
        """True if only from requirement mention (no code evidence)"""
        return len(self.code_evidence) == 0