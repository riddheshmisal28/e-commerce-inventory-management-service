from pydantic import BaseModel


class ImpactedComponent(BaseModel):
    name: str
    reason: str


class DataModelImpact(BaseModel):
    entity: str
    change: str


class ApiMutation(BaseModel):
    endpoint: str
    change: str


class ImpactAnalysis(BaseModel):
    requirement: str
    impacted_components: list[ImpactedComponent]
    data_model_impact: list[DataModelImpact]
    api_mutations: list[ApiMutation]