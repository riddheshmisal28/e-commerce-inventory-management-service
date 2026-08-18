from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

class FeatureSummary(BaseModel):
    name: str
    business_goal: str

class Requirement(BaseModel):
    title: str
    description: str
    acceptance_criteria: list[str]

class BlastRadius(BaseModel):
    component: str
    reason: str
    severity: str = "Low"

class DataModelImpact(BaseModel):
    entity: str
    change_type: str
    change: str
    reason: str | None = None
    relevance_score: float | None = None
    confidence: float | None = None
    relevance: str | None = None
    evidence: list[str] = Field(
        default_factory=list,
    )

class ApiMutation(BaseModel):
    endpoint: str
    change_type: str
    details: str
    reason: str | None = None
    relevance_score: float | None = None
    confidence: float | None = None
    relevance: str | None = None
    evidence: list[str] = Field(
        default_factory=list,
    )

class ModelImpact(BaseModel):
    model: str
    change_type: str
    change: str
    reason: str | None = None
    relevance_score: float | None = None
    confidence: float | None = None
    relevance: str | None = None
    evidence: list[str] = Field(
        default_factory=list,
    )

class ComponentImpact(BaseModel):
    component: str
    impact_type: str
    change: str
    reason: str | None = None
    relevance_score: float | None = None
    confidence: float | None = None
    relevance: str | None = None
    evidence: list[str] = Field(
        default_factory=list,
    )

class LLMImpactAnalysis(BaseModel):
    model_impacts: list[ModelImpact] = Field(
        default_factory=list,
    )
    business_logic_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    repository_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    integration_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    component_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    endpoint_impacts: list[ApiMutation] = Field(
        default_factory=list,
    )
    reasoning: list[str] = Field(
        default_factory=list,
    )

class BDDScenario(BaseModel):
    scenario: str
    given: str
    when: str
    then: str

class TestScenarios(BaseModel):
    happy_path: list[str]
    negative_cases: list[str]
    edge_cases: list[str]

class ImpactAnalysisReport(BaseModel):
    feature_summary: FeatureSummary
    component_blast_radius: list[BlastRadius]
    data_model_impact: list[DataModelImpact]
    api_interface_mutations: list[ApiMutation]
    model_impacts: list[ModelImpact] = Field(
        default_factory=list,
    )
    business_logic_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    repository_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    integration_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    component_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    clarification_questions: list[str]
    test_scenarios: TestScenarios
    bdd_scenarios: list[BDDScenario]

class ContextPlan(BaseModel):
    need_entities: bool = False
    need_endpoints: bool = False
    need_models: bool = False
    need_openapi: bool = False
    need_business_logic: bool = False
    need_repositories: bool = False
    need_integrations: bool = False
    need_components: bool = False
    need_documentation: bool = False
    keywords: list[str] = Field(
        default_factory=list,
    )

class EngineeringContext(BaseModel):
    entities: list[Any] = Field(
        default_factory=list,
    )
    endpoints: list[Any] = Field(
        default_factory=list,
    )
    models: list[Any] = Field(
        default_factory=list,
    )
    openapi: dict[str, Any] = Field(
        default_factory=dict,
    )
    business_logic: list[Any] = Field(
        default_factory=list,
    )
    repositories: list[Any] = Field(
        default_factory=list,
    )
    integrations: list[Any] = Field(
        default_factory=list,
    )
    components: list[Any] = Field(
        default_factory=list,
    )
    documentation: list[Any] = Field(
        default_factory=list,
    )
    retrieved_sources: list[str] = Field(
        default_factory=list,
    )

class AnalysisContext(BaseModel):
    requirement: Requirement
    context_plan: ContextPlan | None = None
    engineering_context: EngineeringContext = Field(
        default_factory=EngineeringContext,
    )
    entity_impacts: list[DataModelImpact] = Field(
        default_factory=list,
    )
    endpoint_impacts: list[ApiMutation] = Field(
        default_factory=list,
    )
    model_impacts: list[ModelImpact] = Field(
        default_factory=list,
    )
    business_logic_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    repository_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    integration_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    component_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    blast_radius: list[BlastRadius] = Field(
        default_factory=list,
    )
    report: ImpactAnalysisReport | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    execution_history: list[str] = Field(
        default_factory=list,
    )
    execution_metrics: dict[str, float] = Field(
        default_factory=dict,
    )
    llm_interactions: list["LLMInteraction"] = Field(
        default_factory=list,
    )
    pipeline_result: "PipelineResult | None" = None

    @property
    def requirement_text(self) -> str:
        return f"""
        {self.requirement.title}

        {self.requirement.description}

        {' '.join(self.requirement.acceptance_criteria)}
        """.lower()

class PipelineResult(BaseModel):
    success: bool
    total_duration_ms: float
    executed_steps: list[str] = Field(
        default_factory=list,
    )
    execution_metrics: dict[str, float] = Field(
        default_factory=dict,
    )
    report: ImpactAnalysisReport | None = None
    error: str | None = None

class LLMInteraction(BaseModel):
    step: str
    provider: str
    model: str
    prompt: str
    response: str
    duration_ms: float
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
    )

class LLMResponse(BaseModel):
    provider: str
    model: str
    response: str
    duration_ms: float

class ImpactReasoningResult(BaseModel):
    data_model_impacts: list[DataModelImpact] = Field(
        default_factory=list,
    )
    api_interface_mutations: list[ApiMutation] = Field(
        default_factory=list,
    )
    model_impacts: list[ModelImpact] = Field(
        default_factory=list,
    )
    business_logic_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    repository_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    integration_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )
    component_impacts: list[ComponentImpact] = Field(
        default_factory=list,
    )

class SemanticImpactDecision(BaseModel):
    category: str
    artifact: str
    change_type: str
    keep: bool
    relevance_score: float
    confidence: float
    relevance: str
    reason: str
    evidence: list[str] = Field(
        default_factory=list,
    )

class SemanticImpactRefinementResult(BaseModel):
    decisions: list[SemanticImpactDecision] = Field(
        default_factory=list,
    )