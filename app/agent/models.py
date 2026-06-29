from pydantic import BaseModel

class FeatureSummary(BaseModel):
    name: str
    business_goal: str

class BlastRadius(BaseModel):
    component: str
    reason: str

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
    keywords: list[str] = []