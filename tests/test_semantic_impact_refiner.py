from app.agent.core.pipeline_executor import PipelineExecutor
from app.agent.models import (
    AnalysisContext,
    ContextPlan,
    Requirement,
    SemanticImpactRefinementResult,
)
from app.agent.steps.semantic_impact_refiner import SemanticImpactRefiner


def test_semantic_impact_refiner_runs_without_context_plan_gate():
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Low stock alert",
            description="Notify users when stock drops below a threshold.",
            acceptance_criteria=[
                "Alert is sent when stock is below threshold.",
            ],
        ),
        context_plan=ContextPlan(),
    )

    result = PipelineExecutor().run(
        [SemanticImpactRefiner()],
        ctx,
    )

    assert result.success is True
    assert "Semantic Impact Refiner" in ctx.execution_history


def test_semantic_decision_model_accepts_llm_contract_without_metadata_fields():
    result = SemanticImpactRefinementResult.model_validate(
        {
            "decisions": [
                {
                    "impact_id": 0,
                    "keep": True,
                    "relevance_score": 0.9,
                    "confidence": 0.8,
                    "relevance": "HIGH",
                    "reason": "Directly required by the requirement.",
                    "evidence": ["The requirement explicitly calls for this behavior."],
                }
            ]
        }
    )

    assert result.decisions[0].impact_id == 0
    assert result.decisions[0].keep is True
