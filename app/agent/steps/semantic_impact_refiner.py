import logging

from app.agent.core.agent_step import AgentStep
from app.agent.llm.client import LLMClient
from app.agent.llm.structured_output import StructuredOutputParser
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
                "No candidate impacts available for semantic refinement."
            )
            return

        prompt = self._build_prompt(
            ctx,
            impacts,
        )

        llm_response = self.client.generate(
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
            },
        )

        self._apply_result(
            ctx,
            impacts,
            result,
        )

        self._log_final_counts(ctx)

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

        data = impact.model_dump()

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

==========================================================
SCORING
==========================================================

relevance_score:

0.90 - 1.00
Directly required by the requirement.

0.75 - 0.89
Strongly implied by the requirement and supported by context.

0.50 - 0.74
Potentially relevant but requires some engineering inference.

0.00 - 0.49
Weak, unrelated, or speculative.

confidence:

0.90 - 1.00
Strong engineering evidence directly supports the impact.

0.75 - 0.89
Good engineering evidence with minor inference.

0.50 - 0.74
Some evidence exists but the relationship is uncertain.

0.00 - 0.49
Insufficient or speculative evidence.

==========================================================
IMPORTANT DISTINCTION
==========================================================

relevance_score answers:

"How strongly does this impact relate to the requirement?"

confidence answers:

"How strongly does the available engineering evidence
support this impact?"

These values do not need to be equal.

==========================================================
DECISION RULE
==========================================================

Keep an impact only when:

relevance_score >= 0.50

AND

confidence >= 0.50

Otherwise:

keep = false

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

You MUST return exactly one decision for every
impact_id.

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
            ]
        }}
    ]
}}

OUTPUT REQUIREMENTS:

- Exactly one decision per candidate.
- Do not omit any candidate.
- Do not duplicate an impact_id.
- Do not create an impact_id that was not supplied.
- impact_id must be an integer.
- Do not return category.
- Do not return artifact.
- Do not return change_type.
- The application already owns those fields.
- Return ONLY the JSON object.
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
        # Count validation
        # --------------------------------------------------------------

        if len(result.decisions) != len(impacts):

            raise ValueError(
                "Semantic Impact Refiner decision count mismatch. "
                f"Expected {len(impacts)}, "
                f"received {len(result.decisions)}."
            )

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