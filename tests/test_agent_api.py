from unittest.mock import MagicMock, patch
from app.agent.models import (
    FeatureSummary,
    ImpactAnalysisReport,
    PipelineResult,
    TestScenarios,
)


def test_agent_health_endpoint(client):
    response = client.get("/agent/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "LLM Requirement Planner" in data["pipeline_steps"]


def test_agent_presets_endpoint(client):
    response = client.get("/agent/presets")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "low-stock-alert" in preset_ids


def test_agent_analyze_endpoint(client):
    fake_result = PipelineResult(
        success=True,
        total_duration_ms=120.5,
        executed_steps=["LLM Requirement Planner", "Report Builder"],
        report=ImpactAnalysisReport(
            feature_summary=FeatureSummary(
                name="Test Feature",
                business_goal="Test Goal",
            ),
            component_blast_radius=[],
            data_model_impact=[],
            api_interface_mutations=[],
            clarification_questions=["What is the threshold?"],
            test_scenarios=TestScenarios(
                happy_path=["Alert sends on low stock"],
                negative_cases=[],
                edge_cases=[],
            ),
            bdd_scenarios=[],
        ),
    )

    with patch("app.agent.api.ImpactAgent.run", return_value=fake_result):
        response = client.post(
            "/agent/analyze",
            json={
                "title": "Low Stock Alert",
                "description": "Notify when quantity is below threshold.",
                "acceptance_criteria": ["Threshold configurable."],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["report"]["feature_summary"]["name"] == "Test Feature"
        assert len(data["report"]["clarification_questions"]) == 1
