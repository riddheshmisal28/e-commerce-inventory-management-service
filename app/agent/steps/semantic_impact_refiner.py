from pydantic import BaseModel, Field

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


class SemanticImpactRefiner(AgentStep):

    name = "Semantic Impact Refiner"

    required_context: set[str] = set()

    def __init__(self):
        self.client = LLMClient()
        self.output_parser = StructuredOutputParser()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        impacts = self._collect_impacts(ctx)

        if not impacts:
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
            )
        )

        result = self.output_parser.parse(
            llm_response.response,
            SemanticImpactRefinementResult,
        )

        self._apply_result(
            ctx,
            result,
        )

    def _collect_impacts(
        self,
        ctx: AnalysisContext,
    ) -> list[dict]:

        impacts = []

        for impact in ctx.entity_impacts:
            impacts.append(
                self._serialize_impact(
                    "entity",
                    impact,
                )
            )

        for impact in ctx.endpoint_impacts:
            impacts.append(
                self._serialize_impact(
                    "endpoint",
                    impact,
                )
            )

        for impact in ctx.model_impacts:
            impacts.append(
                self._serialize_impact(
                    "model",
                    impact,
                )
            )

        for impact in ctx.business_logic_impacts:
            impacts.append(
                self._serialize_impact(
                    "business_logic",
                    impact,
                )
            )

        for impact in ctx.repository_impacts:
            impacts.append(
                self._serialize_impact(
                    "repository",
                    impact,
                )
            )

        for impact in ctx.integration_impacts:
            impacts.append(
                self._serialize_impact(
                    "integration",
                    impact,
                )
            )

        for impact in ctx.component_impacts:
            impacts.append(
                self._serialize_impact(
                    "component",
                    impact,
                )
            )

        return impacts

    def _serialize_impact(
        self,
        category: str,
        impact,
    ) -> dict:

        data = impact.model_dump()

        data["category"] = category

        return data

    def _build_prompt(
        self,
        ctx: AnalysisContext,
        impacts: list[dict],
    ) -> str:

        return f"""
You are a Senior Software Architect performing
semantic validation of engineering impacts.

The impacts below were already generated and passed
a deterministic engineering-context validation stage.

Your task is NOT to generate new impacts.

Your task is to independently determine whether each
candidate impact is genuinely required by the requirement.

==========================================================
STRICT RULES
==========================================================

1. NEVER create a new impact.

2. NEVER change the artifact name.

3. NEVER introduce an artifact that is not present
   in the candidate impact.

4. NEVER infer an impact solely from keyword similarity.

5. An artifact existing in the engineering context does
   NOT mean it is affected.

6. A field existing on an entity does NOT mean the field
   is impacted.

7. A candidate must have a meaningful semantic relationship
   with the requirement.

8. The engineering evidence must support the candidate.

9. Reject speculative impacts.

10. Reject impacts caused only by generic architectural
    assumptions.

11. Prefer rejecting a weak impact over retaining a
    speculative impact.

12. You may improve the reason and evidence.

13. You may adjust relevance_score and confidence.

14. You may change relevance to HIGH, MEDIUM, or LOW.

15. You MUST preserve the candidate category.

16. You MUST preserve the candidate artifact.

17. You MUST preserve the candidate change_type.

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
RETRIEVED ENGINEERING CONTEXT
==========================================================

DATABASE ENTITIES:

{self._format_context(
    ctx.engineering_context.entities,
)}

API ENDPOINTS:

{self._format_context(
    ctx.engineering_context.endpoints,
)}

PYDANTIC MODELS:

{self._format_context(
    ctx.engineering_context.models,
)}

BUSINESS LOGIC:

{self._format_context(
    ctx.engineering_context.business_logic,
)}

REPOSITORIES:

{self._format_context(
    ctx.engineering_context.repositories,
)}

INTEGRATIONS:

{self._format_context(
    ctx.engineering_context.integrations,
)}

APPLICATION COMPONENTS:

{self._format_context(
    ctx.engineering_context.components,
)}

==========================================================
CANDIDATE IMPACTS
==========================================================

{self._format_impacts(impacts)}

==========================================================
OUTPUT
==========================================================

Return exactly one JSON object:

{{
    "decisions": [
        {{
            "category": "entity | endpoint | model | business_logic | repository | integration | component",
            "artifact": "exact artifact identifier from candidate",
            "change_type": "exact change_type from candidate",
            "keep": true,
            "relevance_score": 0.0,
            "confidence": 0.0,
            "relevance": "HIGH | MEDIUM | LOW",
            "reason": "semantic explanation",
            "evidence": [
                "specific supporting engineering evidence"
            ]
        }}
    ]
}}

There MUST be exactly one decision for every candidate impact.

Do not create decisions for impacts that were not supplied.

Return ONLY the JSON object.
"""

    def _apply_result(
        self,
        ctx: AnalysisContext,
        result: SemanticImpactRefinementResult,
    ) -> None:

        decisions = {
            (
                decision.category,
                decision.artifact.lower(),
                decision.change_type,
            ): decision
            for decision in result.decisions
        }

        ctx.entity_impacts = (
            self._apply_entity_decisions(
                ctx.entity_impacts,
                decisions,
            )
        )

        ctx.endpoint_impacts = (
            self._apply_endpoint_decisions(
                ctx.endpoint_impacts,
                decisions,
            )
        )

        ctx.model_impacts = (
            self._apply_model_decisions(
                ctx.model_impacts,
                decisions,
            )
        )

        ctx.business_logic_impacts = (
            self._apply_component_decisions(
                ctx.business_logic_impacts,
                "business_logic",
                decisions,
            )
        )

        ctx.repository_impacts = (
            self._apply_component_decisions(
                ctx.repository_impacts,
                "repository",
                decisions,
            )
        )

        ctx.integration_impacts = (
            self._apply_component_decisions(
                ctx.integration_impacts,
                "integration",
                decisions,
            )
        )

        ctx.component_impacts = (
            self._apply_component_decisions(
                ctx.component_impacts,
                "component",
                decisions,
            )
        )

    def _apply_entity_decisions(
        self,
        impacts: list[DataModelImpact],
        decisions: dict,
    ) -> list[DataModelImpact]:

        result = []

        for impact in impacts:

            decision = decisions.get(
                (
                    "entity",
                    impact.entity.lower(),
                    impact.change_type,
                )
            )

            if not decision or not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(impact)

        return result

    def _apply_endpoint_decisions(
        self,
        impacts: list[ApiMutation],
        decisions: dict,
    ) -> list[ApiMutation]:

        result = []

        for impact in impacts:

            decision = decisions.get(
                (
                    "endpoint",
                    impact.endpoint.lower(),
                    impact.change_type,
                )
            )

            if not decision or not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(impact)

        return result

    def _apply_model_decisions(
        self,
        impacts: list[ModelImpact],
        decisions: dict,
    ) -> list[ModelImpact]:

        result = []

        for impact in impacts:

            decision = decisions.get(
                (
                    "model",
                    impact.model.lower(),
                    impact.change_type,
                )
            )

            if not decision or not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(impact)

        return result

    def _apply_component_decisions(
        self,
        impacts: list[ComponentImpact],
        category: str,
        decisions: dict,
    ) -> list[ComponentImpact]:

        result = []

        for impact in impacts:

            decision = decisions.get(
                (
                    category,
                    impact.component.lower(),
                    impact.change_type,
                )
            )

            if not decision or not decision.keep:
                continue

            self._update_impact(
                impact,
                decision,
            )

            result.append(impact)

        return result

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

    def _format_impacts(
        self,
        impacts: list[dict],
    ) -> str:

        if not impacts:
            return "No candidate impacts."

        return "\n\n".join(
            str(impact)
            for impact in impacts
        )

    def _format_context(
        self,
        items: list,
    ) -> str:

        if not items:
            return "No context retrieved."

        return "\n\n".join(
            str(item)
            for item in items
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