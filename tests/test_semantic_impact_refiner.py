import pytest
from unittest.mock import MagicMock
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


def create_refiner():
    return SemanticImpactRefiner()


def create_candidate():
    return DataModelImpact(
        entity="skus",
        change_type="BUSINESS_RULE",
        change="Evaluate quantity against a configurable threshold.",
        reason=(
            "The requirement explicitly requires evaluating SKU quantity "
            "against a configurable threshold."
        ),
        evidence=["The skus entity contains the quantity field."],
        relevance_score=0.9,
        confidence=1.0,
        relevance="HIGH",
    )


def create_decision(
    keep=True,
    relevance_score=1.0,
    confidence=0.75,
    support_level="STRONGLY_IMPLIED",
):
    return SemanticImpactDecision(
        impact_id=0,
        keep=keep,
        relevance_score=relevance_score,
        confidence=confidence,
        relevance="HIGH",
        reason=(
            "The requirement explicitly establishes the quantity-threshold "
            "business rule. The skus entity contains quantity and is a "
            "reasonable representation of the affected business concept."
        ),
        evidence=["The skus entity contains the quantity field."],
        support_level=support_level,
        rejection_reason=None,
        requirement_alignment=1.0,
        artifact_alignment=0.8,
        change_alignment=1.0,
        evidence_strength=0.6,
    )


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


def test_required_quantity_threshold_rule_stays_kept_as_strongly_implied():
    refiner = create_refiner()
    candidate = create_candidate()
    decision = create_decision()

    refiner._validate_decisions(
        [{"impact_id": 0, "category": "entity", "artifact": "skus", "change_type": "BUSINESS_RULE"}],
        SemanticImpactRefinementResult(decisions=[decision]),
    )

    summary = SemanticImpactRefiner._summarize_refinement([decision])

    assert candidate.entity == "skus"
    assert candidate.change == "Evaluate quantity against a configurable threshold."
    assert decision.keep is True
    assert decision.support_level == "STRONGLY_IMPLIED"
    assert decision.rejection_reason is None
    assert summary["impacts_after"] == 1
    assert summary["strongly_implied_count"] == 1


def test_explicit_business_rule_is_kept_despite_incomplete_ownership_evidence():
    refiner = create_refiner()

    ctx = MagicMock(spec=AnalysisContext)

    ctx.entity_impacts = [create_candidate()]
    ctx.endpoint_impacts = []
    ctx.model_impacts = []
    ctx.business_logic_impacts = []
    ctx.repository_impacts = []
    ctx.integration_impacts = []
    ctx.component_impacts = []
    ctx.llm_interactions = []
    ctx.refinement_decisions = []

    ctx.requirement = MagicMock()
    ctx.requirement.title = "Low Stock Alert"
    ctx.requirement.description = (
        "Notify inventory managers when a SKU's quantity "
        "falls below its configured threshold."
    )
    ctx.requirement.acceptance_criteria = [
        "Evaluate SKU quantity against its configured threshold."
    ]

    decision = create_decision()

    refiner.client.generate_with_retry = MagicMock(
        return_value=MagicMock(
            provider="ollama",
            model="qwen3:8b",
            response='{"decisions": []}',
            duration_ms=100,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
    )

    refiner.output_parser.parse = MagicMock(
        return_value=SemanticImpactRefinementResult(decisions=[decision])
    )

    refiner.execute(ctx)

    assert len(ctx.entity_impacts) == 1

    impact = ctx.entity_impacts[0]

    assert impact.entity == "skus"
    assert impact.change_type == "BUSINESS_RULE"
    assert impact.change == (
        "Evaluate quantity against a configurable threshold."
    )
    assert impact.relevance_score == 1.0
    assert impact.confidence == 0.75


def test_plausible_implementation_is_rejected():
    refiner = create_refiner()

    ctx = MagicMock(spec=AnalysisContext)

    ctx.entity_impacts = []
    ctx.endpoint_impacts = []
    ctx.model_impacts = []
    ctx.business_logic_impacts = [
        MagicMock(
            component="SKUService",
            change_type="BUSINESS_RULE",
            change="Add email notification retry mechanism.",
            reason="SKUService handles SKU operations.",
            evidence=["SKUService handles SKU creation and updates."],
            relevance_score=0.5,
            confidence=0.8,
            relevance="MEDIUM",
        )
    ]
    ctx.repository_impacts = []
    ctx.integration_impacts = []
    ctx.component_impacts = []
    ctx.llm_interactions = []
    ctx.refinement_decisions = []

    ctx.requirement = MagicMock()
    ctx.requirement.title = "Low Stock Alert"
    ctx.requirement.description = (
        "Notify inventory managers when a SKU's quantity "
        "falls below its configured threshold."
    )
    ctx.requirement.acceptance_criteria = []

    decision = SemanticImpactDecision(
        impact_id=0,
        keep=False,
        relevance_score=0.35,
        confidence=0.4,
        relevance="LOW",
        reason=(
            "The candidate describes a possible notification implementation "
            "rather than a requirement-mandated change."
        ),
        evidence=["SKUService handles SKU creation and updates."],
        support_level="SPECULATIVE",
        rejection_reason=(
            "The requirement requires a low-stock notification but does not "
            "require an email retry mechanism specifically. The proposed "
            "change is a plausible implementation choice."
        ),
        requirement_alignment=0.4,
        artifact_alignment=0.6,
        change_alignment=0.3,
        evidence_strength=0.4,
    )

    refiner.output_parser.parse = MagicMock(
        return_value=SemanticImpactRefinementResult(decisions=[decision])
    )

    refiner.client.generate_with_retry = MagicMock(
        return_value=MagicMock(
            provider="ollama",
            model="qwen3:8b",
            response="{}",
            duration_ms=100,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
    )

    refiner.execute(ctx)

    assert len(ctx.business_logic_impacts) == 0


def test_explicit_requirement_can_be_kept_with_low_evidence_strength():
    refiner = create_refiner()

    decision = SemanticImpactDecision(
        impact_id=0,
        keep=True,
        relevance_score=1.0,
        confidence=0.5,
        relevance="HIGH",
        reason="The business rule is explicitly required.",
        evidence=["The skus entity contains the quantity field."],
        support_level="STRONGLY_IMPLIED",
        rejection_reason=None,
        requirement_alignment=1.0,
        artifact_alignment=0.8,
        change_alignment=1.0,
        evidence_strength=0.5,
    )

    result = SemanticImpactRefinementResult(decisions=[decision])

    refiner._validate_decisions(
        [
            {
                "impact_id": 0,
                "category": "entity",
                "artifact": "skus",
                "change_type": "BUSINESS_RULE",
            }
        ],
        result,
    )


def test_direct_support_requires_all_alignment_scores_above_0_90():
    refiner = create_refiner()

    decision = create_decision(
        support_level="DIRECT",
    )
    decision.evidence_strength = 0.70

    result = SemanticImpactRefinementResult(decisions=[decision])

    with pytest.raises(ValueError, match="support_level DIRECT"):
        refiner._validate_decisions(
            [
                {
                    "impact_id": 0,
                    "category": "entity",
                    "artifact": "skus",
                    "change_type": "BUSINESS_RULE",
                }
            ],
            result,
        )


def test_direct_support_is_valid_when_all_scores_are_high():
    refiner = create_refiner()

    decision = create_decision(
        support_level="DIRECT",
    )
    decision.requirement_alignment = 1.0
    decision.artifact_alignment = 0.95
    decision.change_alignment = 1.0
    decision.evidence_strength = 0.95

    result = SemanticImpactRefinementResult(decisions=[decision])

    refiner._validate_decisions(
        [
            {
                "impact_id": 0,
                "category": "entity",
                "artifact": "skus",
                "change_type": "BUSINESS_RULE",
            }
        ],
        result,
    )


def test_missing_impact_id_is_rejected():
    refiner = create_refiner()

    result = SemanticImpactRefinementResult(decisions=[])

    impacts = [
        {
            "impact_id": 0,
            "category": "entity",
            "artifact": "skus",
            "change_type": "BUSINESS_RULE",
        }
    ]

    with pytest.raises(ValueError, match="Missing impact_ids"):
        refiner._validate_decisions(
            impacts,
            result,
        )


def test_duplicate_impact_id_is_rejected():
    refiner = create_refiner()

    decision1 = create_decision()
    decision2 = create_decision()

    result = SemanticImpactRefinementResult(decisions=[decision1, decision2])

    impacts = [
        {
            "impact_id": 0,
            "category": "entity",
            "artifact": "skus",
            "change_type": "BUSINESS_RULE",
        },
        {
            "impact_id": 1,
            "category": "entity",
            "artifact": "products",
            "change_type": "BUSINESS_RULE",
        },
    ]

    with pytest.raises(ValueError, match="duplicate"):
        refiner._validate_decisions(
            impacts,
            result,
        )


def test_apply_result_removes_rejected_impacts():
    refiner = create_refiner()

    impact = create_candidate()

    ctx = MagicMock(spec=AnalysisContext)

    ctx.entity_impacts = [impact]
    ctx.endpoint_impacts = []
    ctx.model_impacts = []
    ctx.business_logic_impacts = []
    ctx.repository_impacts = []
    ctx.integration_impacts = []
    ctx.component_impacts = []

    decision = SemanticImpactDecision(
        impact_id=0,
        keep=False,
        relevance_score=0.3,
        confidence=0.3,
        relevance="LOW",
        reason="Not required.",
        evidence=[],
        support_level="SPECULATIVE",
        rejection_reason="The candidate is speculative.",
        requirement_alignment=0.3,
        artifact_alignment=0.4,
        change_alignment=0.3,
        evidence_strength=0.2,
    )

    result = SemanticImpactRefinementResult(decisions=[decision])

    impacts = refiner._collect_impacts(ctx)

    refiner._apply_result(
        ctx,
        impacts,
        result,
    )

    assert ctx.entity_impacts == []


def test_apply_result_keeps_and_updates_impact():
    refiner = create_refiner()

    impact = create_candidate()

    ctx = MagicMock(spec=AnalysisContext)

    ctx.entity_impacts = [impact]
    ctx.endpoint_impacts = []
    ctx.model_impacts = []
    ctx.business_logic_impacts = []
    ctx.repository_impacts = []
    ctx.integration_impacts = []
    ctx.component_impacts = []

    decision = create_decision()

    result = SemanticImpactRefinementResult(decisions=[decision])

    impacts = refiner._collect_impacts(ctx)

    refiner._apply_result(
        ctx,
        impacts,
        result,
    )

    assert len(ctx.entity_impacts) == 1
    assert ctx.entity_impacts[0].relevance_score == 1.0
    assert ctx.entity_impacts[0].confidence == 0.75


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
