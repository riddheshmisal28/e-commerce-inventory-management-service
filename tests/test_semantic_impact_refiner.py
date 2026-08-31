import pytest

from app.agent.core.pipeline_executor import PipelineExecutor
from app.agent.models import (
    AnalysisContext,
    ContextPlan,
    DataModelImpact,
    Requirement,
    SemanticImpactRefinementResult,
)
from app.agent.steps.semantic_impact_refiner import SemanticImpactRefiner
from app.agent.models import SemanticImpactDecision
from app.agent.execution.execution_policy import (
    EvaluationContext,
    ExecutionPolicyConfig,
    ExecutionPolicy,
)
from app.agent.execution.decision_gate import DecisionGate


class SpySemanticImpactRefiner:
    name = "Semantic Impact Refiner"
    required_context = set()

    def execute(self, ctx):
        ctx.metadata["refiner_ran"] = True


SEMANTIC_ACCURACY_CASES = [
    ("Alert when stock falls below threshold", True, "STRONGLY_IMPLIED", None),
    ("Evaluate quantity against configurable threshold", False, "WEAKLY_SUPPORTED", "IMPLEMENTATION_CHOICE"),
    ("Suppress duplicate alerts for 24 hours", False, "SPECULATIVE", "SPECULATIVE"),
    ("Customer model supports multiple phone numbers", True, "DIRECT", None),
    ("Add Redis cache for phone numbers", False, "SPECULATIVE", "IMPLEMENTATION_CHOICE"),
    ("Add preferred_phone_number to customer data", True, "DIRECT", None),
    ("Track coupon redemption state/history", True, "STRONGLY_IMPLIED", None),
    ("Add Redis caching to checkout", False, "SPECULATIVE", "IMPLEMENTATION_CHOICE"),
    ("Store cancellation reason in order data", True, "DIRECT", None),
    ("Add email notification after successful payment", True, "STRONGLY_IMPLIED", None),
]


def _semantic_accuracy_decision(
    impact_id: int,
    keep: bool,
    support_level: str,
    rejection_reason: str | None,
) -> SemanticImpactDecision:
    score = {
        "DIRECT": 0.95,
        "STRONGLY_IMPLIED": 0.85,
        "WEAKLY_SUPPORTED": 0.6,
        "SPECULATIVE": 0.3,
    }[support_level]

    return SemanticImpactDecision(
        impact_id=impact_id,
        keep=keep,
        relevance_score=score,
        confidence=score,
        relevance="HIGH" if keep else "MEDIUM",
        reason="Semantic accuracy fixture",
        evidence=["Fixture evidence"],
        support_level=support_level,
        rejection_reason=rejection_reason,
        requirement_alignment=score,
        artifact_alignment=score,
        change_alignment=score,
        evidence_strength=score,
    )


@pytest.mark.parametrize(
    "candidate, expected_keep, expected_support, rejection_reason",
    SEMANTIC_ACCURACY_CASES,
)
def test_semantic_accuracy_cases(
    candidate,
    expected_keep,
    expected_support,
    rejection_reason,
):
    decision = _semantic_accuracy_decision(
        SEMANTIC_ACCURACY_CASES.index(
            (candidate, expected_keep, expected_support, rejection_reason)
        ),
        expected_keep,
        expected_support,
        rejection_reason,
    )

    assert decision.keep is expected_keep
    assert decision.support_level == expected_support
    assert decision.rejection_reason == rejection_reason


def test_semantic_accuracy_fixture_validates_and_summarizes_all_cases():
    refiner = SemanticImpactRefiner.__new__(SemanticImpactRefiner)
    decisions = [
        _semantic_accuracy_decision(index, keep, support, reason)
        for index, (_, keep, support, reason) in enumerate(SEMANTIC_ACCURACY_CASES)
    ]

    refiner._validate_decisions(
        [{"impact_id": index} for index in range(len(decisions))],
        SemanticImpactRefinementResult(decisions=decisions),
    )
    summary = SemanticImpactRefiner._summarize_refinement(decisions)

    assert summary["impacts_before"] == 10
    assert summary["impacts_after"] == 6
    assert summary["direct_support_count"] == 3
    assert summary["strongly_implied_count"] == 3
    assert summary["weakly_supported_count"] == 1
    assert summary["speculative_count"] == 3
    assert summary["rejection_by_reason"] == {
        "IMPLEMENTATION_CHOICE": 3,
        "SPECULATIVE": 1,
    }


def test_refiner_prompt_contains_v2_semantic_accuracy_instructions():
    refiner = SemanticImpactRefiner.__new__(SemanticImpactRefiner)
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Alert when stock falls below threshold",
            description="Notify users when stock falls below a threshold.",
            acceptance_criteria=[],
        )
    )

    prompt = refiner._build_prompt(
        ctx,
        [{"impact_id": 0, "category": "entity", "artifact": "skus", "change_type": "UPDATE"}],
    )

    assert "necessary semantic consequence" in prompt
    assert "merely a plausible implementation choice" in prompt
    assert "requirement_alignment" in prompt
    assert "artifact_alignment" in prompt
    assert "change_alignment" in prompt
    assert "evidence_strength" in prompt


def test_semantic_impact_refiner_skips_without_grounded_impacts():
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
    assert "Semantic Impact Refiner" not in ctx.execution_history
    step = result.agent_run["steps"][0]
    assert step["status"] == "skipped"
    decision = step["metrics"]["execution_decision"]
    assert decision["should_execute"] is False
    assert decision["reason"] == "Nothing exists to refine."
    assert decision["confidence"] == 1.0
    assert decision["policy"] == "NO_IMPACTS"
    assert decision["inputs"]["impact_count"] == 0


def test_execution_policy_skips_a_single_high_confidence_impact():
    decision = ExecutionPolicy().decide(
        step_name="Semantic Impact Refiner",
        context=EvaluationContext(
            impact_count=1,
            grounded_count=1,
            grounding_rate=1.0,
            avg_relevance=0.95,
            avg_confidence=0.92,
        ),
    )

    assert decision.should_execute is False
    assert decision.policy == "SINGLE_STRONG_IMPACT"
    assert decision.inputs["impact_count"] == 1


def test_execution_policy_refines_a_single_weak_impact():
    decision = ExecutionPolicy().decide(
        step_name="Semantic Impact Refiner",
        context=EvaluationContext(
            impact_count=1,
            grounded_count=1,
            grounding_rate=1.0,
            avg_relevance=0.84,
            avg_confidence=0.92,
        ),
    )

    assert decision.should_execute is True
    assert decision.policy == "SINGLE_IMPACT_REQUIRES_REFINEMENT"


def test_execution_policy_uses_configurable_strong_impact_thresholds():
    config = ExecutionPolicyConfig(
        single_impact_confidence_threshold=0.95,
        single_impact_relevance_threshold=0.95,
    )
    policy = ExecutionPolicy(config)
    decision = policy.decide(
        step_name="Semantic Impact Refiner",
        context=EvaluationContext(
            impact_count=1,
            grounded_count=1,
            grounding_rate=1.0,
            avg_relevance=0.9,
            avg_confidence=0.9,
        ),
    )

    assert decision.should_execute is True


def test_execution_policy_can_skip_without_full_grounding():
    config = ExecutionPolicyConfig(
        require_full_grounding_for_skip=False,
    )
    decision = ExecutionPolicy(config).decide(
        step_name="Semantic Impact Refiner",
        context=EvaluationContext(
            impact_count=1,
            grounding_rate=0.5,
            avg_relevance=0.9,
            avg_confidence=0.9,
        ),
    )

    assert decision.should_execute is False
    assert decision.policy == "SINGLE_STRONG_IMPACT"


def test_execution_policy_refines_multiple_impacts():
    decision = ExecutionPolicy().decide(
        step_name="Semantic Impact Refiner",
        context=EvaluationContext(
            impact_count=2,
            grounded_count=2,
        ),
    )

    assert decision.should_execute is True
    assert decision.policy == "MULTIPLE_IMPACTS"


def test_pipeline_executor_runs_refiner_for_multiple_impacts():
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Low stock alert",
            description="Notify users when stock drops below a threshold.",
            acceptance_criteria=[],
        ),
        entity_impacts=[
            DataModelImpact(
                entity="Product",
                change_type="UPDATE",
                change="Add stock threshold",
            ),
            DataModelImpact(
                entity="Warehouse",
                change_type="UPDATE",
                change="Track low stock state",
            ),
        ],
    )

    result = PipelineExecutor().run(
        [SpySemanticImpactRefiner()],
        ctx,
    )

    assert result.success is True
    assert ctx.metadata["refiner_ran"] is True
    assert "Semantic Impact Refiner" in ctx.execution_history
    decision = result.agent_run["steps"][0]["metrics"]["execution_decision"]
    assert decision["should_execute"] is True
    assert decision["policy"] == "MULTIPLE_IMPACTS"


def test_test_b_single_obvious_impact_skips_refiner():
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Update product quantity",
            description="Update the product quantity after a stock movement.",
            acceptance_criteria=[],
        ),
        entity_impacts=[
            DataModelImpact(
                entity="Product",
                change_type="UPDATE",
                change="Update quantity",
                relevance_score=0.95,
                confidence=0.95,
            ),
        ],
        metadata={
            "step_metrics": {
                "Impact Reasoner": {"impacts_generated": 1},
                "Impact Validator": {
                    "accepted": 1,
                    "rejected": 0,
                    "rejection_rate": 0.0,
                },
                "Grounding Validator": {
                    "grounded": 1,
                    "ungrounded": 0,
                    "grounding_rate": 1.0,
                },
            },
        },
    )

    result = PipelineExecutor().run(
        [SpySemanticImpactRefiner()],
        ctx,
    )

    assert result.success is True
    assert "refiner_ran" not in ctx.metadata
    assert "Semantic Impact Refiner" not in ctx.execution_history
    step = result.agent_run["steps"][0]
    assert step["status"] == "skipped"
    decision = step["metrics"]["execution_decision"]
    assert decision["should_execute"] is False
    assert decision["policy"] == "SINGLE_STRONG_IMPACT"


def test_test_c_multiple_impacts_refines():
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Update product quantity",
            description="Update the product quantity after a stock movement.",
            acceptance_criteria=[],
        ),
        entity_impacts=[
            DataModelImpact(
                entity="Product",
                change_type="UPDATE",
                change="Update quantity",
                relevance_score=0.95,
                confidence=0.95,
            ),
            DataModelImpact(
                entity="StockMovement",
                change_type="UPDATE",
                change="Record movement",
                relevance_score=0.7,
                confidence=0.75,
            ),
        ],
        metadata={
            "step_metrics": {
                "Impact Reasoner": {"impacts_generated": 2},
                "Impact Validator": {
                    "accepted": 2,
                    "rejected": 0,
                    "rejection_rate": 0.0,
                },
                "Grounding Validator": {
                    "grounded": 2,
                    "ungrounded": 0,
                    "grounding_rate": 1.0,
                },
            },
        },
    )

    result = PipelineExecutor().run(
        [SpySemanticImpactRefiner()],
        ctx,
    )

    assert result.success is True
    assert ctx.metadata["refiner_ran"] is True
    assert "Semantic Impact Refiner" in ctx.execution_history
    decision = result.agent_run["steps"][0]["metrics"]["execution_decision"]
    assert decision["should_execute"] is True
    assert decision["policy"] == "MULTIPLE_IMPACTS"


def test_executor_does_not_add_duplicate_refiner_metrics():
    executor = PipelineExecutor()
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Low stock alert",
            description="Notify users when stock drops below a threshold.",
            acceptance_criteria=[],
        )
    )

    metrics = executor._step_metrics(
        "Semantic Impact Refiner",
        executor._impact_snapshot(ctx),
        ctx,
    )

    assert metrics == {}


def test_decision_gate_consumes_grounding_validator_metrics():
    ctx = AnalysisContext(
        requirement=Requirement(
            title="Low stock alert",
            description="Notify users when stock drops below a threshold.",
            acceptance_criteria=[],
        ),
        metadata={
            "step_metrics": {
                "Impact Reasoner": {"impacts_generated": 3},
                "Impact Validator": {
                    "accepted": 3,
                    "rejected": 0,
                    "rejection_rate": 0,
                },
                "Grounding Validator": {
                    "grounded": 3,
                    "ungrounded": 0,
                    "grounding_rate": 1.0,
                },
            },
        },
    )

    decision = DecisionGate().decide(
        "Semantic Impact Refiner",
        ctx,
    )

    assert decision is not None
    assert decision.inputs["impacts_generated"] == 3
    assert decision.inputs["accepted_count"] == 3
    assert decision.inputs["grounded_count"] == 3
    assert decision.inputs["ungrounded_count"] == 0
    assert decision.inputs["grounding_rate"] == 1.0


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


def test_refinement_summary_calculates_quality_metrics():
    decisions = [
        SemanticImpactDecision(
            impact_id=0,
            keep=True,
            relevance_score=0.9,
            confidence=0.8,
            relevance="HIGH",
            reason="Required",
            support_level="DIRECT",
        ),
        SemanticImpactDecision(
            impact_id=1,
            keep=False,
            relevance_score=0.3,
            confidence=0.4,
            relevance="LOW",
            reason="Speculative",
            support_level="SPECULATIVE",
            rejection_reason="The candidate is not required by the requirement.",
        ),
    ]

    summary = SemanticImpactRefiner._summarize_refinement(decisions)

    assert summary == {
        "impacts_before": 2,
        "impacts_after": 1,
        "impacts_kept": 1,
        "impacts_removed": 1,
        "keep_rate": 0.5,
        "avg_relevance_score": 0.6,
        "avg_confidence": 0.6000000000000001,
        "kept_avg_relevance": 0.9,
        "kept_avg_confidence": 0.8,
        "removed_avg_relevance": 0.3,
        "removed_avg_confidence": 0.4,
        "direct_support_count": 1,
        "strongly_implied_count": 0,
        "weakly_supported_count": 0,
        "speculative_count": 1,
        "rejection_by_reason": {
            "The candidate is not required by the requirement.": 1,
        },
        "direct_support_count": 1,
        "strongly_implied_count": 0,
        "weakly_supported_count": 0,
        "speculative_count": 1,
        "rejection_by_reason": {
            "The candidate is not required by the requirement.": 1,
        },
    }


def test_refinement_summary_handles_empty_decisions():
    summary = SemanticImpactRefiner._summarize_refinement([])

    assert summary["impacts_before"] == 0
    assert summary["impacts_after"] == 0
    assert summary["impacts_kept"] == 0
    assert summary["impacts_removed"] == 0
    assert summary["keep_rate"] == 0.0
    assert summary["avg_confidence"] == 0.0
    assert summary["rejection_by_reason"] == {}


def test_refiner_rejects_direct_support_when_evidence_is_weak():
    refiner = SemanticImpactRefiner.__new__(SemanticImpactRefiner)
    decision = SemanticImpactDecision(
        impact_id=0,
        keep=True,
        relevance_score=0.9,
        confidence=0.9,
        relevance="HIGH",
        reason="The requirement aligns with the candidate.",
        support_level="DIRECT",
        requirement_alignment=0.95,
        artifact_alignment=0.95,
        change_alignment=0.95,
        evidence_strength=0.45,
    )

    with pytest.raises(ValueError, match="support_level"):
        refiner._validate_decisions(
            [{"impact_id": 0}],
            SemanticImpactRefinementResult(decisions=[decision]),
        )


def test_refiner_validates_rejection_reason_and_score_ranges():
    refiner = SemanticImpactRefiner.__new__(SemanticImpactRefiner)
    result = SemanticImpactRefinementResult.model_validate(
        {
            "decisions": [
                {
                    "impact_id": 0,
                    "keep": False,
                    "relevance_score": 0.3,
                    "confidence": 0.4,
                    "relevance": "LOW",
                    "reason": "Speculative",
                    "support_level": "SPECULATIVE",
                    "rejection_reason": "No direct evidence.",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        refiner._validate_decisions(
            [{"impact_id": 0}],
            result.model_copy(
                update={
                    "decisions": [
                        result.decisions[0].model_copy(
                            update={"confidence": 1.1},
                        )
                    ]
                }
            ),
        )

    with pytest.raises(ValueError, match="rejection_reason"):
        refiner._validate_decisions(
            [{"impact_id": 0}],
            result.model_copy(
                update={
                    "decisions": [
                        result.decisions[0].model_copy(
                            update={"rejection_reason": None},
                        )
                    ]
                }
            ),
        )
