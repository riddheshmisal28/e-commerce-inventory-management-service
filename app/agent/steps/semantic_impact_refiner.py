import logging

from app.agent.core.agent_step import AgentStep
from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
from app.agent.observability.agent_run_tracker import attach_step_metadata
from app.agent.execution.execution_policy import ExecutionPolicy
from app.agent.models import (
    AnalysisContext,
    ComponentImpact,
    DataModelImpact,
    ApiMutation,
    ModelImpact,
    LLMInteraction,
    SemanticImpactDecision,
    SemanticImpactRefinementResult,
)


logger = logging.getLogger(__name__)

SUPPORT_LEVELS = {
    "DIRECT",
    "STRONGLY_IMPLIED",
    "WEAKLY_SUPPORTED",
    "SPECULATIVE",
    "UNSPECIFIED",
}


class SemanticImpactRefiner(AgentStep):

    name = "Semantic Impact Refiner"

    # This step depends on the analysis outputs produced by earlier
    # impact-analysis stages, not on ContextPlan keys. The pipeline gate
    # expects ContextPlan fields like need_entities / need_endpoints, so
    # using AnalysisContext attribute names here incorrectly causes it to
    # skip this step. Leave the gate open so the step can run whenever the
    # pipeline reaches it.
    required_context: set[str] = set()

    def __init__(self):
        self.client = LLMClient(json_mode=True)
        self.output_parser = StructuredOutputParser()
        self.execution_policy = ExecutionPolicy()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts = self._collect_impacts(ctx)

        logger.info(
            "Semantic Impact Refiner started",
            extra={
                "candidate_count": len(impacts),
            },
        )

        if not impacts:
            logger.info(
                "No candidate impacts available for semantic refinement. Skipping step."
            )
            attach_step_metadata(
                {
                    "step_decision": "SKIP",
                    "skip_reason": "zero_impacts",
                    "impacts_before": 0,
                    "impacts_after": 0,
                }
            )
            return

        prompt = self._build_prompt(
            ctx,
            impacts,
        )

        llm_response = self.client.generate_with_retry(
            prompt,
        )

        ctx.llm_interactions.append(
            LLMInteraction(
                step=self.name,
                provider=llm_response.provider,
                model=llm_response.model,
                prompt=prompt,
                response=llm_response.response,
                duration_ms=llm_response.duration_ms,
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                total_tokens=llm_response.total_tokens,
                tokens_per_second = (
                    llm_response.output_tokens / (llm_response.duration_ms / 1000)
                )
            )
        )

        logger.info(
            "Semantic Impact Refiner LLM completed",
            extra={
                "candidate_count": len(impacts),
                "duration_ms": llm_response.duration_ms,
            },
        )

        result = self.output_parser.parse(
            llm_response.response,
            SemanticImpactRefinementResult,
        )

        self._validate_decisions(
            impacts,
            result,
        )

        refinement_quality = self._summarize_refinement(
            result.decisions,
        )
        attach_step_metadata(
            {
                "refinement_quality": refinement_quality,
            }
        )

        logger.info(
            "Semantic Impact Refiner decisions received",
            extra={
                "candidate_count": len(impacts),
                "decision_count": len(result.decisions),
                "kept_count": sum(
                    1
                    for decision in result.decisions
                    if decision.keep
                ),
                "rejected_count": sum(
                    1
                    for decision in result.decisions
                    if not decision.keep
                ),
                "refinement_quality": refinement_quality,
            },
        )

        self._apply_result(
            ctx,
            impacts,
            result,
        )

        # Persist refinement decisions for traceability
        ctx.refinement_decisions = result.decisions

        self._log_final_counts(ctx)

    @staticmethod
    def _summarize_refinement(
        decisions: list[SemanticImpactDecision],
    ) -> dict:

        kept = [
            decision
            for decision in decisions
            if decision.keep
        ]

        removed = [
            decision
            for decision in decisions
            if not decision.keep
        ]

        def average(
            items: list[SemanticImpactDecision],
            field: str,
        ) -> float:

            if not items:
                return 0.0

            return sum(
                getattr(item, field)
                for item in items
            ) / len(items)

        return {
            "impacts_before": len(decisions),
            "impacts_after": len(kept),
            "impacts_kept": len(kept),
            "impacts_removed": len(removed),
            "keep_rate": (
                len(kept) / len(decisions)
                if decisions
                else 0.0
            ),
            "avg_relevance_score": average(
                decisions,
                "relevance_score",
            ),
            "avg_confidence": average(
                decisions,
                "confidence",
            ),
            "kept_avg_relevance": average(
                kept,
                "relevance_score",
            ),
            "kept_avg_confidence": average(
                kept,
                "confidence",
            ),
            "removed_avg_relevance": average(
                removed,
                "relevance_score",
            ),
            "removed_avg_confidence": average(
                removed,
                "confidence",
            ),
            "direct_support_count": sum(
                decision.support_level == "DIRECT"
                for decision in decisions
            ),
            "strongly_implied_count": sum(
                decision.support_level == "STRONGLY_IMPLIED"
                for decision in decisions
            ),
            "weakly_supported_count": sum(
                decision.support_level == "WEAKLY_SUPPORTED"
                for decision in decisions
            ),
            "speculative_count": sum(
                decision.support_level == "SPECULATIVE"
                for decision in decisions
            ),
            "rejection_by_reason": (
                SemanticImpactRefiner._rejection_by_reason(
                    removed
                )
            ),
        }

    @staticmethod
    def _rejection_by_reason(
        decisions: list[SemanticImpactDecision],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        for decision in decisions:
            reason = decision.rejection_reason or "unspecified"
            counts[reason] = counts.get(reason, 0) + 1

        return counts

    # ------------------------------------------------------------------
    # Candidate collection
    # ------------------------------------------------------------------

    def _collect_impacts(
        self,
        ctx: AnalysisContext,
    ) -> list[dict]:

        impacts: list[dict] = []

        categories = [
            (
                "entity",
                ctx.entity_impacts,
            ),
            (
                "endpoint",
                ctx.endpoint_impacts,
            ),
            (
                "model",
                ctx.model_impacts,
            ),
            (
                "business_logic",
                ctx.business_logic_impacts,
            ),
            (
                "repository",
                ctx.repository_impacts,
            ),
            (
                "integration",
                ctx.integration_impacts,
            ),
            (
                "component",
                ctx.component_impacts,
            ),
        ]

        for category, category_impacts in categories:

            for impact in category_impacts:

                serialized = self._serialize_impact(
                    category,
                    impact,
                )

                serialized["impact_id"] = len(impacts)

                impacts.append(
                    serialized
                )

        return impacts

    def _serialize_impact(
        self,
        category: str,
        impact,
    ) -> dict:

        if hasattr(impact, "model_dump") and callable(impact.model_dump):
            data = impact.model_dump()
            if not isinstance(data, dict):
                data = {}
        elif hasattr(impact, "__dict__"):
            data = {
                key: value
                for key, value in impact.__dict__.items()
                if not key.startswith("_")
            }
        else:
            data = {}

        if not data:
            data = {
                key: getattr(impact, key)
                for key in (
                    "entity",
                    "endpoint",
                    "model",
                    "component",
                    "change_type",
                    "change",
                    "reason",
                    "evidence",
                    "relevance_score",
                    "confidence",
                    "relevance",
                )
                if hasattr(impact, key)
            }

        data["category"] = category

        data["artifact"] = self._get_artifact(
            category,
            impact,
        )

        return data

    def _get_artifact(
        self,
        category: str,
        impact,
    ) -> str:

        if category == "entity":
            return impact.entity

        if category == "endpoint":
            return impact.endpoint

        if category == "model":
            return impact.model

        if category in {
            "business_logic",
            "repository",
            "integration",
            "component",
        }:
            return impact.component

        raise ValueError(
            f"Unsupported impact category: {category}"
        )

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        ctx: AnalysisContext,
        impacts: list[dict],
    ) -> str:

        return f"""
You are a Senior Software Architect performing semantic
validation of engineering impact candidates.

The candidates below were already generated by an impact
analysis stage and passed deterministic engineering-context
validation.

Your task is NOT to generate new impacts.

Your task is to independently determine whether each
candidate impact is genuinely required by the requirement.

Evaluate every candidate through this chain, in order:

Requirement
    -> Candidate change
    -> Artifact
    -> Change type
    -> Evidence

==========================================================
SEMANTIC NECESSITY
==========================================================

The candidate does NOT need to be stated word-for-word in the
requirement.

Keep a candidate when the requirement either:

- explicitly requires the proposed change, OR
- makes the proposed change a necessary semantic consequence
  of the required business behavior.

A necessary semantic consequence is different from a merely a plausible implementation choice, and a merely plausible implementation choice must be rejected even when it seems reasonable.

Use the following distinction:

EXPLICIT:
The requirement directly states the behavior or change.

NECESSARY SEMANTIC CONSEQUENCE:
The requirement does not name the exact artifact or change,
but the proposed change is necessary to fulfill the required
business behavior using the supplied engineering context.

PLAUSIBLE IMPLEMENTATION:
The proposed change is one possible way to implement the
requirement, but the requirement does not require that
specific approach.

UNSUPPORTED:
The candidate has insufficient evidence or no meaningful
semantic relationship to the requirement.

Keep EXPLICIT and NECESSARY SEMANTIC CONSEQUENCE impacts.

Reject PLAUSIBLE IMPLEMENTATION and UNSUPPORTED impacts.

Do not interpret "not explicitly stated" as automatically
meaning "speculative".

==========================================================
VALIDATION CHAIN
==========================================================

Evaluate each candidate through all of these dimensions:

1. REQUIREMENT ALIGNMENT

Does the requirement explicitly require this impact, or does
the requirement necessarily imply it?

A candidate may have high requirement alignment even when the
exact artifact or implementation detail is not explicitly
named, provided the candidate is a necessary semantic
consequence of the required behavior.

2. ARTIFACT ALIGNMENT

Does the supplied artifact represent the business concept,
behavior, or responsibility affected by the requirement?

Artifact existence alone is NOT sufficient.

3. CHANGE ALIGNMENT

Does the proposed change on the artifact logically follow from
the requirement?

Do not keep an impact merely because the artifact is related
to the requirement.

4. EVIDENCE STRENGTH

Does the supplied engineering evidence specifically support
the proposed change on the proposed artifact?

Evidence must support the specific impact, not merely establish
that the artifact exists or is generally related to the domain.

For example:

"SKUService handles SKU creation and updates"

proves that SKUService exists and handles SKU operations, but
does NOT by itself prove that SKUService must implement
low-stock alert logic.

Do not assign high evidence_strength merely because an
artifact exists or is generally related to the domain.

==========================================================
STRICT RULES
==========================================================

1. NEVER create a new impact.

2. NEVER create a new impact_id.

3. NEVER modify an impact_id.

4. You MUST return exactly one decision for every candidate.

5. Every candidate impact_id MUST appear exactly once.

6. You MUST preserve the semantic identity of the candidate.

7. The application owns:
   - category
   - artifact
   - change_type

8. You only decide:
   - keep
   - relevance_score
   - confidence
   - relevance
   - reason
   - evidence
   - support_level
   - rejection_reason
   - requirement_alignment
   - artifact_alignment
   - change_alignment
   - evidence_strength

9. NEVER invent an artifact.

10. NEVER infer an impact solely from keyword similarity.

11. An artifact existing in engineering context does NOT
    automatically mean it is affected.

12. A field existing on an entity does NOT automatically
    mean the field is impacted.

13. Reject speculative impacts.

14. Reject impacts caused only by generic architectural
    assumptions.

15. Prefer rejecting a weak impact over retaining a
    speculative impact.

16. Evidence must be specific and grounded in the supplied
    engineering context.

17. Evidence must support the proposed CHANGE on the proposed
    ARTIFACT, not merely prove that the artifact exists.

18. support_level must be one of:

    DIRECT:
    The requirement explicitly requires the candidate change,
    and the candidate artifact is a direct representation or
    owner of the affected business behavior.

    The supplied engineering evidence directly supports the
    artifact/change assignment.

    STRONGLY_IMPLIED:
    The requirement does not necessarily name the exact artifact
    or change representation, but the candidate change is a
    necessary semantic consequence of the required behavior.

    The candidate artifact must be a reasonable representation of
    the affected business concept.

    Engineering context may provide direct, partial, or indirect
    support for the artifact assignment. The evidence does not need
    to prove that the artifact is the exact implementation owner.

    Low evidence_strength affects confidence but does not invalidate
    semantic necessity.

    WEAKLY_SUPPORTED:
    The candidate has some semantic relationship to the requirement,
    but the change is not clearly necessary, OR the candidate
    artifact has only weak relevance to the required business
    behavior.

    Weak engineering evidence alone does not make an explicitly
    required business rule weakly supported.

    SPECULATIVE:
    The impact is merely a possible implementation choice,
    generic architectural assumption, or unsupported inference.

19. Rejected impacts MUST include a non-empty
    rejection_reason.

20. Kept impacts MUST set rejection_reason to null.

21. Assess requirement_alignment, artifact_alignment,
    change_alignment, and evidence_strength independently on a
    0.0 to 1.0 scale BEFORE determining support_level.

22. Do not assign DIRECT from confidence alone.

23. Weak evidence MUST prevent DIRECT support even when
    confidence is high.

24. A candidate can be semantically relevant even if the
    requirement does not explicitly name the exact artifact,
    provided the artifact is a necessary and supported
    representation of the required business behavior.

25. Do not treat a possible implementation approach as a
    necessary semantic consequence.

26. Do not reject an impact solely because the requirement
    does not use the exact terminology used by the artifact,
    field, or change description.

==========================================================
SCORING
==========================================================

relevance_score answers:

"How strongly does this impact relate to the requirement,
including necessary semantic consequences?"

Use:

0.90 - 1.00
The impact is explicitly required by the requirement or is an
unavoidable semantic consequence of the required behavior.

0.75 - 0.89
The impact is strongly implied and is necessary or strongly
supported by the requirement and engineering context.

0.50 - 0.74
The impact is potentially relevant but requires meaningful
engineering inference. Keep only if the inference represents a
necessary consequence rather than an optional implementation
choice.

0.00 - 0.49
The impact is weak, unrelated, speculative, or merely one
possible implementation choice.

confidence answers:

"How strongly does the available engineering evidence support
the specific proposed impact?"

Use:

0.90 - 1.00
The supplied engineering evidence directly supports the
specific proposed change on the artifact.

0.75 - 0.89
The evidence strongly supports the change, with only minor
inference required.

0.50 - 0.74
Some relevant evidence exists, but the artifact/change
relationship is uncertain or incomplete.

0.00 - 0.49
The evidence does not adequately support the proposed change
or is speculative.

==========================================================
NUMERICAL THRESHOLDS
==========================================================

These are consistency checks, not the primary semantic gate.

1. EXPLICITLY REQUIRED BUSINESS RULE

If the candidate directly represents a condition, calculation,
validation, trigger, state transition, or business rule stated
in the requirement:

    keep = true

provided the candidate artifact is a reasonable representation
of the business concept.

Low evidence_strength does NOT automatically cause rejection.

The requirement itself establishes the semantic necessity of the
business rule.

2. NECESSARY SEMANTIC CONSEQUENCE

If the candidate is not explicitly stated but is necessary to
fulfill the required business behavior:

    keep = true

provided the candidate artifact is reasonably connected to the
required behavior.

3. PLAUSIBLE IMPLEMENTATION

If the candidate represents only one possible implementation
approach and is not required by the requirement:

    keep = false

even when the artifact is technically capable of implementing it.

4. UNSUPPORTED ARTIFACT

If the candidate artifact has no meaningful relationship to the
required business behavior:

    keep = false

5. RELEVANCE SCORE

If relevance_score < 0.50:

    keep = false

The candidate is not sufficiently related to the requirement.

6. CONFIDENCE

confidence measures engineering evidence strength.

Low confidence does NOT automatically imply rejection when the
requirement explicitly establishes the semantic change.

For explicitly required business rules:

    semantic necessity has priority over evidence confidence.

For inferred changes:

    both semantic necessity and reasonable artifact support are
    required.

7. IMPORTANT

Do NOT use confidence as a substitute for semantic necessity.

Do NOT reject an explicitly required business rule solely because
the engineering context does not prove the exact implementation
owner.

==========================================================
IMPORTANT DISTINCTION
==========================================================

relevance_score and confidence are independent.

relevance_score measures:

    Requirement -> Candidate semantic change

confidence measures:

    Engineering evidence -> Candidate artifact/change assignment

These values do NOT need to be equal.

A requirement can strongly establish that a business rule,
condition, validation, calculation, or state transition is
required even when the available engineering context does not
prove exactly where that behavior should be implemented.

For example:

Requirement:
"Trigger an alert when SKU quantity is below its configured
threshold."

Candidate:
"Evaluate SKU quantity against its configured threshold."

The requirement directly establishes the semantic necessity of
the quantity-vs-threshold rule.

Therefore:

    requirement_alignment = HIGH
    change_alignment = HIGH

If the candidate artifact is `skus` because `skus.quantity`
exists and the artifact represents SKU quantity, then:

    artifact_alignment = MEDIUM or HIGH

If the engineering context does not explicitly show that `skus`
owns the alert or threshold evaluation logic:

    evidence_strength = LOW or MEDIUM

This MUST NOT automatically cause rejection.

The missing evidence concerns artifact ownership, not semantic
necessity.

Do not require engineering evidence to independently prove a
business rule that is already explicitly established by the
requirement.

Engineering evidence should determine how confidently the
candidate can be attributed to the proposed artifact.

==========================================================
DECISION RULE
==========================================================

Evaluate candidates in two separate stages.

STAGE 1 — SEMANTIC NECESSITY

First determine whether the proposed CHANGE is required by the
requirement.

Keep the candidate when:

1. The requirement explicitly requires the change, OR
2. The change is a necessary semantic consequence of the
   required business behavior.

Reject when:

1. The change is merely a plausible implementation choice, OR
2. The change has no meaningful semantic relationship to the
   requirement.

STAGE 2 — ARTIFACT ASSIGNMENT

If the semantic change is required, evaluate whether the
candidate artifact is a reasonable representation or owner of
that change.

Artifact evidence affects:

- artifact_alignment
- evidence_strength
- confidence
- support_level

Artifact evidence MUST NOT override explicit semantic necessity
when the artifact is a reasonable representation of the business
concept affected by the requirement.

For example:

Requirement:
"Evaluate SKU quantity against a configurable threshold."

Candidate:

    category = entity
    artifact = skus
    change = Evaluate quantity against a configurable threshold.

Engineering context:

    skus.quantity exists.

Correct reasoning:

    The quantity-threshold rule is explicitly established by the
    requirement.

    The `skus` entity represents SKU quantity and therefore is a
    reasonable artifact associated with the required behavior.

    The evidence does not prove that `skus` is the exact
    implementation owner of the rule.

Therefore the candidate may be KEPT with:

    high requirement_alignment
    medium/high artifact_alignment
    high change_alignment
    low/medium evidence_strength
    STRONGLY_IMPLIED support_level

Do NOT reject this candidate solely because the engineering
context does not prove implementation ownership.

Reject the candidate only when the artifact itself is not a
reasonable representation or owner of the required behavior.

IMPORTANT:

"Insufficient evidence that this artifact owns the behavior"

is NOT equivalent to:

"This candidate is semantically unnecessary."

Only the latter is sufficient for semantic rejection.

==========================================================
REQUIREMENT
==========================================================

Title:

{ctx.requirement.title}

Description:

{ctx.requirement.description}

Acceptance Criteria:

{self._format_acceptance_criteria(
    ctx.requirement.acceptance_criteria
)}

==========================================================
CANDIDATE IMPACTS
==========================================================

Each candidate contains an immutable impact_id.

You MUST return exactly one decision for every impact_id.

{self._format_impacts(impacts)}

==========================================================
OUTPUT
==========================================================

Return exactly one JSON object:

{{
    "decisions": [
        {{
            "impact_id": 0,
            "keep": true,
            "relevance_score": 0.0,
            "confidence": 0.0,
            "relevance": "HIGH",
            "reason": "semantic explanation",
            "evidence": [
                "specific supporting engineering evidence"
            ],
            "support_level": "DIRECT",
            "rejection_reason": null,
            "requirement_alignment": 0.0,
            "artifact_alignment": 0.0,
            "change_alignment": 0.0,
            "evidence_strength": 0.0
        }}
    ]
}}

==========================================================
OUTPUT REQUIREMENTS
==========================================================

- Return ONLY the JSON object.
- Exactly one decision per candidate.
- Do not omit any candidate.
- Do not duplicate an impact_id.
- Do not create an impact_id that was not supplied.
- impact_id must be an integer.
- Do not return category.
- Do not return artifact.
- Do not return change_type.
- Preserve the candidate's semantic identity.
- support_level describes the strongest justified level of
  semantic and engineering support across the:

  Requirement -> Change -> Artifact -> Evidence chain.

  Semantic necessity and engineering evidence must be evaluated
  independently.

  A candidate may be STRONGLY_IMPLIED even when evidence_strength
  is below 0.75, provided that:

  - requirement_alignment is high,
  - change_alignment is high,
  - artifact_alignment is reasonable,
  - and the candidate represents required business behavior.

  Do not reject or downgrade an explicitly required business rule
  solely because engineering evidence does not prove exact
  implementation ownership.
- Low evidence_strength must not automatically downgrade or reject
  an explicitly required semantic business rule when the candidate
  artifact is a reasonable representation of the affected business
  concept.
- rejection_reason must explain specifically why a rejected
  candidate failed that chain.
- Kept impacts must have rejection_reason = null.
- Rejected impacts must have a non-empty rejection_reason.
- requirement_alignment, artifact_alignment,
  change_alignment, and evidence_strength must each be between
  0.0 and 1.0.
- Do not use confidence as a substitute for evidence_strength.
- Do not treat artifact existence as proof that the artifact
  requires modification.
"""
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_decisions(
        self,
        impacts: list[dict],
        result: SemanticImpactRefinementResult,
    ) -> None:

        candidate_ids = {
            impact["impact_id"]
            for impact in impacts
        }

        decision_ids = [
            decision.impact_id
            for decision in result.decisions
        ]

        decision_id_set = set(
            decision_ids
        )

        # --------------------------------------------------------------
        # Duplicate decisions
        # --------------------------------------------------------------

        duplicates = {
            impact_id
            for impact_id in decision_ids
            if decision_ids.count(impact_id) > 1
        }

        if duplicates:

            raise ValueError(
                "Semantic Impact Refiner returned duplicate "
                f"decisions for impact_ids: "
                f"{sorted(duplicates)}"
            )

        # --------------------------------------------------------------
        # Missing decisions
        # --------------------------------------------------------------

        missing_ids = (
            candidate_ids
            - decision_id_set
        )

        if missing_ids:

            raise ValueError(
                "Semantic Impact Refiner returned incomplete "
                f"decisions. Missing impact_ids: "
                f"{sorted(missing_ids)}"
            )

        # --------------------------------------------------------------
        # Unexpected decisions
        # --------------------------------------------------------------

        unexpected_ids = (
            decision_id_set
            - candidate_ids
        )

        if unexpected_ids:

            raise ValueError(
                "Semantic Impact Refiner returned decisions "
                f"for unknown impact_ids: "
                f"{sorted(unexpected_ids)}"
            )

        # --------------------------------------------------------------
        # Count validation
        # --------------------------------------------------------------

        if len(result.decisions) != len(impacts):

            raise ValueError(
                "Semantic Impact Refiner decision count mismatch. "
                f"Expected {len(impacts)}, "
                f"received {len(result.decisions)}."
            )

        for decision in result.decisions:
            if not 0.0 <= decision.relevance_score <= 1.0:
                raise ValueError(
                    f"Invalid relevance_score for impact_id={decision.impact_id}: "
                    f"{decision.relevance_score}. Expected a value between 0 and 1."
                )

            if not 0.0 <= decision.confidence <= 1.0:
                raise ValueError(
                    f"Invalid confidence for impact_id={decision.impact_id}: "
                    f"{decision.confidence}. Expected a value between 0 and 1."
                )

            for field in (
                "requirement_alignment",
                "artifact_alignment",
                "change_alignment",
                "evidence_strength",
            ):
                value = getattr(decision, field)
                if not 0.0 <= value <= 1.0:
                    raise ValueError(
                        f"Invalid {field} for impact_id={decision.impact_id}: "
                        f"{value}. Expected a value between 0 and 1."
                    )

            # ----------------------------------------------------------
            # Semantic consistency
            # ----------------------------------------------------------

            if (
                decision.keep
                and decision.relevance_score < 0.50
            ):
                raise ValueError(
                    f"Kept impact_id={decision.impact_id} has "
                    f"relevance_score={decision.relevance_score}. "
                    "Kept impacts must have relevance_score >= 0.50."
                )

            # A candidate can have strong semantic alignment while
            # still being rejected because the artifact assignment
            # is wrong. Therefore this is intentionally a warning,
            # not a hard failure.
            if (
                not decision.keep
                and decision.relevance_score >= 0.90
                and decision.requirement_alignment >= 0.90
                and decision.change_alignment >= 0.90
            ):
                logger.warning(
                    "Rejected impact has strong semantic alignment",
                    extra={
                        "impact_id": decision.impact_id,
                        "relevance_score": (
                            decision.relevance_score
                        ),
                        "requirement_alignment": (
                            decision.requirement_alignment
                        ),
                        "artifact_alignment": (
                            decision.artifact_alignment
                        ),
                        "change_alignment": (
                            decision.change_alignment
                        ),
                        "evidence_strength": (
                            decision.evidence_strength
                        ),
                        "support_level": (
                            decision.support_level
                        ),
                        "rejection_reason": (
                            decision.rejection_reason
                        ),
                    },
                )
            if decision.support_level not in SUPPORT_LEVELS:
                raise ValueError(
                    f"Invalid support_level for impact_id={decision.impact_id}: "
                    f"{decision.support_level}. Expected one of "
                    f"{sorted(SUPPORT_LEVELS)}."
                )

            # ----------------------------------------------------------
            # Compare LLM support level with deterministic assessment.
            #
            # This is intentionally a warning for now. We want to
            # observe the model's behavior across multiple requirements
            # before making this a hard validation rule.
            # ----------------------------------------------------------

            expected_support_level = (
                self._expected_support_level(
                    decision
                )
            )

            if (
                decision.keep
                and decision.support_level
                != expected_support_level
            ):
                logger.warning(
                    "LLM support level differs from deterministic "
                    "alignment assessment",
                    extra={
                        "impact_id": decision.impact_id,
                        "llm_support_level": (
                            decision.support_level
                        ),
                        "expected_support_level": (
                            expected_support_level
                        ),
                        "requirement_alignment": (
                            decision.requirement_alignment
                        ),
                        "artifact_alignment": (
                            decision.artifact_alignment
                        ),
                        "change_alignment": (
                            decision.change_alignment
                        ),
                        "evidence_strength": (
                            decision.evidence_strength
                        ),
                    },
                )

            if decision.support_level != expected_support_level:
                raise ValueError(
                    f"Inconsistent support_level {decision.support_level} for "
                    f"impact_id={decision.impact_id}. "
                    f"LLM returned {decision.support_level}, "
                    f"but alignment scores imply {expected_support_level}. "
                    f"support_level {expected_support_level}"
                )

            if not decision.keep and not decision.rejection_reason:
                raise ValueError(
                    f"Rejected impact_id={decision.impact_id} must include "
                    "a rejection_reason."
                )

            if decision.keep and decision.rejection_reason:
                raise ValueError(
                    f"Kept impact_id={decision.impact_id} must not include "
                    "a rejection_reason."
                )

    @staticmethod
    def _expected_support_level(
        decision: SemanticImpactDecision,
    ) -> str:

        requirement = decision.requirement_alignment
        artifact = decision.artifact_alignment
        change = decision.change_alignment
        evidence = decision.evidence_strength

        # --------------------------------------------------------------
        # DIRECT
        # --------------------------------------------------------------
        #
        # Requirement clearly requires the change AND the engineering
        # evidence directly supports the artifact/change assignment.
        #

        if (
            requirement >= 0.90
            and artifact >= 0.90
            and change >= 0.90
            and evidence >= 0.90
        ):
            return "DIRECT"

        # --------------------------------------------------------------
        # STRONGLY IMPLIED
        # --------------------------------------------------------------
        #
        # The business behavior is clearly required, but exact
        # implementation ownership requires some inference.
        #

        if (
            requirement >= 0.85
            and change >= 0.85
            and artifact >= 0.50
        ):
            return "STRONGLY_IMPLIED"

        # --------------------------------------------------------------
        # WEAKLY SUPPORTED
        # --------------------------------------------------------------

        if (
            requirement >= 0.50
            and artifact >= 0.50
            and change >= 0.50
            and evidence >= 0.50
        ):
            return "WEAKLY_SUPPORTED"

        # --------------------------------------------------------------
        # SPECULATIVE
        # --------------------------------------------------------------

        return "SPECULATIVE"

    # ------------------------------------------------------------------
    # Apply result
    # ------------------------------------------------------------------

    def _apply_result(
        self,
        ctx: AnalysisContext,
        impacts: list[dict],
        result: SemanticImpactRefinementResult,
    ) -> None:

        decisions = {
            decision.impact_id: decision
            for decision in result.decisions
        }

        # --------------------------------------------------------------
        # Build impact-id mapping
        # --------------------------------------------------------------

        impact_map = {
            impact["impact_id"]: impact
            for impact in impacts
        }

        # --------------------------------------------------------------
        # Apply decisions category by category
        # --------------------------------------------------------------

        ctx.entity_impacts = (
            self._apply_entity_decisions(
                ctx.entity_impacts,
                decisions,
                impact_map,
            )
        )

        ctx.endpoint_impacts = (
            self._apply_endpoint_decisions(
                ctx.endpoint_impacts,
                decisions,
                impact_map,
            )
        )

        ctx.model_impacts = (
            self._apply_model_decisions(
                ctx.model_impacts,
                decisions,
                impact_map,
            )
        )

        ctx.business_logic_impacts = (
            self._apply_component_decisions(
                ctx.business_logic_impacts,
                "business_logic",
                decisions,
                impact_map,
            )
        )

        ctx.repository_impacts = (
            self._apply_component_decisions(
                ctx.repository_impacts,
                "repository",
                decisions,
                impact_map,
            )
        )

        ctx.integration_impacts = (
            self._apply_component_decisions(
                ctx.integration_impacts,
                "integration",
                decisions,
                impact_map,
            )
        )

        ctx.component_impacts = (
            self._apply_component_decisions(
                ctx.component_impacts,
                "component",
                decisions,
                impact_map,
            )
        )

    # ------------------------------------------------------------------
    # Entity
    # ------------------------------------------------------------------

    def _apply_entity_decisions(
        self,
        impacts: list[DataModelImpact],
        decisions: dict[int, SemanticImpactDecision],
        impact_map: dict[int, dict],
    ) -> list[DataModelImpact]:

        result = []

        for impact in impacts:

            impact_id = self._find_impact_id(
                "entity",
                impact.entity,
                impact.change_type,
                impact_map,
            )

            decision = self._get_required_decision(
                impact_id,
                decisions,
                impact,
            )

            if not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(
                impact
            )

        return result

    # ------------------------------------------------------------------
    # Endpoint
    # ------------------------------------------------------------------

    def _apply_endpoint_decisions(
        self,
        impacts: list[ApiMutation],
        decisions: dict[int, SemanticImpactDecision],
        impact_map: dict[int, dict],
    ) -> list[ApiMutation]:

        result = []

        for impact in impacts:

            impact_id = self._find_impact_id(
                "endpoint",
                impact.endpoint,
                impact.change_type,
                impact_map,
            )

            decision = self._get_required_decision(
                impact_id,
                decisions,
                impact,
            )

            if not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(
                impact
            )

        return result

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    def _apply_model_decisions(
        self,
        impacts: list[ModelImpact],
        decisions: dict[int, SemanticImpactDecision],
        impact_map: dict[int, dict],
    ) -> list[ModelImpact]:

        result = []

        for impact in impacts:

            impact_id = self._find_impact_id(
                "model",
                impact.model,
                impact.change_type,
                impact_map,
            )

            decision = self._get_required_decision(
                impact_id,
                decisions,
                impact,
            )

            if not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(
                impact
            )

        return result

    # ------------------------------------------------------------------
    # Component-based impacts
    # ------------------------------------------------------------------

    def _apply_component_decisions(
        self,
        impacts: list[ComponentImpact],
        category: str,
        decisions: dict[int, SemanticImpactDecision],
        impact_map: dict[int, dict],
    ) -> list[ComponentImpact]:

        result = []

        for impact in impacts:

            impact_id = self._find_impact_id(
                category,
                impact.component,
                impact.change_type,
                impact_map,
            )

            decision = self._get_required_decision(
                impact_id,
                decisions,
                impact,
            )

            if not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(
                impact
            )

        return result

    # ------------------------------------------------------------------
    # Find impact ID
    # ------------------------------------------------------------------

    def _find_impact_id(
        self,
        category: str,
        artifact: str,
        change_type: str,
        impact_map: dict[int, dict],
    ) -> int:

        matching_ids = []

        for impact_id, candidate in impact_map.items():

            if (
                candidate["category"] == category
                and candidate["artifact"].lower()
                == artifact.lower()
                and candidate["change_type"]
                == change_type
            ):
                matching_ids.append(
                    impact_id
                )

        if not matching_ids:

            raise ValueError(
                "Unable to find candidate impact for "
                f"category={category}, "
                f"artifact={artifact}, "
                f"change_type={change_type}"
            )

        if len(matching_ids) > 1:

            raise ValueError(
                "Multiple candidate impacts found for "
                f"category={category}, "
                f"artifact={artifact}, "
                f"change_type={change_type}. "
                f"Matching IDs={matching_ids}"
            )

        return matching_ids[0]

    # ------------------------------------------------------------------
    # Required decision
    # ------------------------------------------------------------------

    def _get_required_decision(
        self,
        impact_id: int,
        decisions: dict[int, SemanticImpactDecision],
        impact,
    ) -> SemanticImpactDecision:

        decision = decisions.get(
            impact_id
        )

        if not decision:

            raise ValueError(
                "Missing semantic decision for "
                f"impact_id={impact_id}, "
                f"impact={impact.model_dump()}"
            )

        return decision

    # ------------------------------------------------------------------
    # Update impact
    # ------------------------------------------------------------------

    def _update_impact(
        self,
        impact,
        decision: SemanticImpactDecision,
    ) -> None:

        impact.relevance_score = (
            decision.relevance_score
        )

        impact.confidence = (
            decision.confidence
        )

        impact.relevance = (
            decision.relevance
        )

        impact.reason = (
            decision.reason
        )

        impact.evidence = (
            decision.evidence
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_final_counts(
        self,
        ctx: AnalysisContext,
    ) -> None:

        logger.info(
            "Semantic Impact Refiner completed",
            extra={
                "entity_impacts": len(
                    ctx.entity_impacts
                ),
                "endpoint_impacts": len(
                    ctx.endpoint_impacts
                ),
                "model_impacts": len(
                    ctx.model_impacts
                ),
                "business_logic_impacts": len(
                    ctx.business_logic_impacts
                ),
                "repository_impacts": len(
                    ctx.repository_impacts
                ),
                "integration_impacts": len(
                    ctx.integration_impacts
                ),
                "component_impacts": len(
                    ctx.component_impacts
                ),
            },
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_impacts(
        self,
        impacts: list[dict],
    ) -> str:

        if not impacts:
            return "No candidate impacts."

        formatted = []

        for impact in impacts:

            formatted.append(
                f"""
IMPACT ID: {impact["impact_id"]}

Category:
{impact["category"]}

Artifact:
{impact["artifact"]}

Change Type:
{impact["change_type"]}

Change:
{impact.get("change", "")}

Reason:
{impact.get("reason", "")}

Existing Evidence:
{self._format_evidence(
    impact.get("evidence", [])
)}
""".strip()
            )

        return "\n\n------------------------------\n\n".join(
            formatted
        )

    def _format_evidence(
        self,
        evidence: list[str],
    ) -> str:

        if not evidence:
            return "No evidence provided."

        return "\n".join(
            f"- {item}"
            for item in evidence
        )

    def _format_acceptance_criteria(
        self,
        criteria: list[str],
    ) -> str:

        if not criteria:
            return "- None provided"

        return "\n".join(
            f"- {item}"
            for item in criteria
        )