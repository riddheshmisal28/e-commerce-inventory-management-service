"""
Integration tests for Phase 1 & 2: AST Facts Extraction + Evidence Collection
"""

import pytest
from pathlib import Path
from app.agent.code_analysis.ast_parser import (
    ASTFactsExtractor,
    FieldType,
    ModuleFacts,
)
from app.agent.code_analysis.dependency_graph import DependencyGraphBuilder
from app.agent.evidence.models import Evidence, EvidenceType, ImpactEvidence


class TestASTFactsExtractor:
    """Test Phase 1: AST Facts Extraction"""

    def test_extract_simple_class(self):
        """Test extracting a simple class with fields"""
        source = """
class SKU:
    sku_id: int
    quantity: int
    name: str
    
    def get_quantity(self) -> int:
        return self.quantity
"""
        extractor = ASTFactsExtractor("test.py", source)
        facts = extractor.analyze()

        assert "SKU" in facts.classes
        sku_class = facts.classes["SKU"]

        # Check fields
        assert "sku_id" in sku_class.fields
        assert sku_class.fields["sku_id"].type_enum == FieldType.INT
        assert sku_class.fields["quantity"].type_enum == FieldType.INT
        assert sku_class.fields["name"].type_enum == FieldType.STR

        # Check methods
        assert "get_quantity" in sku_class.methods
        assert sku_class.methods["get_quantity"].return_type == "int"

    def test_extract_decorated_class(self):
        """Test extracting class with decorators"""
        source = """
from pydantic import BaseModel

@pydantic.dataclasses.dataclass
class Product(BaseModel):
    product_id: int
    name: str
"""
        extractor = ASTFactsExtractor("test.py", source)
        facts = extractor.analyze()

        assert "Product" in facts.classes
        product = facts.classes["Product"]
        assert "pydantic.dataclasses.dataclass" in product.decorators or len(product.decorators) > 0
        assert "BaseModel" in product.base_classes

    def test_extract_imports(self):
        """Test extracting import statements"""
        source = """
import os
from typing import Optional, List
from sqlalchemy import Column, Integer
"""
        extractor = ASTFactsExtractor("test.py", source)
        facts = extractor.analyze()

        assert "os" in facts.dependencies
        assert "typing" in facts.dependencies
        assert "sqlalchemy" in facts.dependencies

    def test_extract_functions(self):
        """Test extracting module-level functions"""
        source = """
async def process_requirement(text: str) -> dict:
    return {"status": "processed"}
    
def validate_input(data: dict) -> bool:
    return len(data) > 0
"""
        extractor = ASTFactsExtractor("test.py", source)
        facts = extractor.analyze()

        assert "process_requirement" in facts.functions
        assert facts.functions["process_requirement"].is_async
        assert facts.functions["process_requirement"].return_type == "dict"

        assert "validate_input" in facts.functions
        assert not facts.functions["validate_input"].is_async

    def test_extract_methods_with_decorators(self):
        """Test extracting methods with decorators"""
        source = """
class SKURepository:
    @property
    def count(self) -> int:
        return len(self.items)
    
    @staticmethod
    def validate_sku(sku: str) -> bool:
        return len(sku) > 0
"""
        extractor = ASTFactsExtractor("test.py", source)
        facts = extractor.analyze()

        sku_repo = facts.classes["SKURepository"]
        assert "property" in sku_repo.methods["count"].decorators
        assert "staticmethod" in sku_repo.methods["validate_sku"].decorators


class TestDependencyGraphBuilder:
    """Test Phase 1: Dependency Graph Building"""

    def test_add_entities_and_edges(self):
        """Test adding entities and call edges"""
        builder = DependencyGraphBuilder()

        builder.add_entity("SKU", "entity", "app/sku/model.py")
        builder.add_entity("Product", "entity", "app/product/model.py")
        builder.add_entity("create_sku", "function", "app/sku/service.py")

        builder.add_call_edge("create_sku", "SKU", line_number=42)
        builder.add_import_edge("create_sku", "sqlalchemy")

        graph_facts = builder.build()

        # Check nodes
        assert len(graph_facts.nodes) == 3
        assert "entity:SKU" in graph_facts.nodes

        # Check edges
        assert len(graph_facts.edges) == 2

    def test_blast_radius_calculation(self):
        """Test blast radius calculation"""
        builder = DependencyGraphBuilder()

        # Create a dependency chain: A → B → C
        builder.add_entity("A", "function")
        builder.add_entity("B", "function")
        builder.add_entity("C", "function")
        builder.add_entity("D", "function")

        builder.add_call_edge("A", "B")
        builder.add_call_edge("B", "C")
        builder.add_call_edge("D", "B")

        # If A changes, it affects B and C (forward)
        affected_by_a = builder.get_blast_radius("A")
        assert "A" in affected_by_a
        assert "B" in affected_by_a
        assert "C" in affected_by_a

        # If B changes, it affects A, C, and D (forward + backward)
        affected_by_b = builder.get_blast_radius("B")
        assert "B" in affected_by_b
        assert "C" in affected_by_b
        assert "D" in affected_by_b
        assert "A" in affected_by_b

    def test_find_path(self):
        """Test finding path between nodes"""
        builder = DependencyGraphBuilder()

        builder.add_entity("A", "function")
        builder.add_entity("B", "function")
        builder.add_entity("C", "function")

        builder.add_call_edge("A", "B")
        builder.add_call_edge("B", "C")

        path = builder.find_path("A", "C")
        assert path == ["A", "B", "C"]


class TestEvidenceCollection:
    """Test Phase 2: Evidence Collection"""

    def test_evidence_types(self):
        """Test that all evidence types are defined"""
        assert hasattr(EvidenceType, "REQUIREMENT_MENTION")
        assert hasattr(EvidenceType, "SCHEMA_FIELD")
        assert hasattr(EvidenceType, "CODE_FIELD")
        assert hasattr(EvidenceType, "CODE_METHOD")

    def test_evidence_creation(self):
        """Test creating an evidence object"""
        evidence = Evidence(
            type=EvidenceType.CODE_FIELD,
            component="SKU.quantity",
            file_path="app/sku/model.py",
            line_number=42,
            description="Field 'quantity' exists in SKU class",
            confidence=1.0,
        )

        assert evidence.type == EvidenceType.CODE_FIELD
        assert evidence.confidence == 1.0
        assert evidence.component == "SKU.quantity"

    def test_impact_evidence_aggregation(self):
        """Test aggregating evidence for an impact"""
        impact_evidence = ImpactEvidence(
            impact_id="entity:SKU",
            requirement_evidence=[
                Evidence(
                    type=EvidenceType.REQUIREMENT_MENTION,
                    component="SKU",
                    file_path=None,
                    line_number=None,
                    description="Requirement mentions SKU",
                    confidence=0.8,
                )
            ],
            schema_evidence=[
                Evidence(
                    type=EvidenceType.SCHEMA_FIELD,
                    component="SKU",
                    file_path="app/sku/model.py",
                    line_number=None,
                    description="SKU exists in schema",
                    confidence=1.0,
                )
            ],
            code_evidence=[
                Evidence(
                    type=EvidenceType.CODE_FIELD,
                    component="SKU",
                    file_path="app/sku/model.py",
                    line_number=10,
                    description="SKU class defined",
                    confidence=1.0,
                )
            ],
            external_evidence=[],
        )

        # Test aggregation
        total_weight = impact_evidence.total_evidence_weight()
        assert 0.9 < total_weight <= 1.0  # High confidence

        # Test evidence presence checks
        assert impact_evidence.has_code_evidence()
        assert not impact_evidence.is_speculative()

    def test_speculative_evidence(self):
        """Test detecting speculative impacts (no code evidence)"""
        impact_evidence = ImpactEvidence(
            impact_id="entity:NonExistent",
            requirement_evidence=[
                Evidence(
                    type=EvidenceType.REQUIREMENT_MENTION,
                    component="NonExistent",
                    file_path=None,
                    line_number=None,
                    description="Requirement mentions NonExistent",
                    confidence=0.6,
                )
            ],
            schema_evidence=[],
            code_evidence=[],  # No code evidence!
            external_evidence=[],
        )

        # Should be marked as speculative
        assert impact_evidence.is_speculative()
        assert not impact_evidence.has_code_evidence()
        assert impact_evidence.total_evidence_weight() == 0.6


class TestIntegrationPhase1And2:
    """Integration tests for Phase 1 + 2"""

    def test_ast_extraction_to_evidence_pipeline(self):
        """Test complete flow: Extract AST facts → Create evidence"""
        source = """
class Product:
    product_id: int
    name: str
    sku_id: int
"""
        # Phase 1: Extract facts
        extractor = ASTFactsExtractor("app/product/model.py", source)
        facts = extractor.analyze()

        # Verify facts were extracted
        assert "Product" in facts.classes
        product_fact = facts.classes["Product"]
        assert len(product_fact.fields) == 3

        # Phase 2: Simulate evidence collection based on facts
        # (In real scenario, this would correlate with requirement)
        code_evidence_list = []
        for field_name, field_fact in product_fact.fields.items():
            code_evidence_list.append(
                Evidence(
                    type=EvidenceType.CODE_FIELD,
                    component=f"Product.{field_name}",
                    file_path=facts.file_path,
                    line_number=field_fact.line_number,
                    description=f"Field '{field_name}' exists with type {field_fact.type_annotation}",
                    confidence=1.0,
                )
            )

        # Verify evidence was collected
        assert len(code_evidence_list) == 3
        assert all(e.confidence == 1.0 for e in code_evidence_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
