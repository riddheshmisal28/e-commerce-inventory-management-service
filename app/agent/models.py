from pydantic import BaseModel, Field
from typing import Any

class FeatureSummary(BaseModel):
    name: str
    business_goal: str

class BlastRadius(BaseModel):
    component: str
    reason: str
    severity: str = "Low"

class DataModelImpact(BaseModel):
    entity: str
    change: str

class ApiMutation(BaseModel):
    endpoint: str
    change_type: str
    details: str

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
    potential_data_model_impact: list[DataModelImpact]
    api_interface_mutations: list[ApiMutation]
    clarification_questions: list[str]
    test_scenarios: TestScenarios
    bdd_scenarios: list[BDDScenario]

class Requirement(BaseModel):
    title: str
    description: str
    acceptance_criteria: list[str]

class ContextPlan(BaseModel):
    need_entities: bool = False
    need_endpoints: bool = False
    need_models: bool = False
    need_openapi: bool = False
    need_documentation: bool = False
    keywords: list[str] = Field(default_factory=list)

class EngineeringContext(BaseModel):
    entities: list[Any] = Field(default_factory=list)
    endpoints: list[Any] = Field(default_factory=list)
    models: list[Any] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)

class AnalysisContext(BaseModel):
    requirement: Requirement
    context_plan: ContextPlan | None = None
    engineering_context: EngineeringContext = Field(
        default_factory=EngineeringContext
    )
    entity_impacts: list[DataModelImpact] = Field(default_factory=list)
    endpoint_impacts: list[ApiMutation] = Field(default_factory=list)
    blast_radius: list[BlastRadius] = Field(default_factory=list)
    report: ImpactAnalysisReport | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_history: list[str] = Field(default_factory=list)
    execution_metrics: dict[str, float] = Field(default_factory=dict)
    pipeline_result: PipelineResult | None = None
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
    executed_steps: list[str] = Field(default_factory=list)
    execution_metrics: dict[str, float] = Field(default_factory=dict)
    report: ImpactAnalysisReport | None = None
    error: str | None = None

