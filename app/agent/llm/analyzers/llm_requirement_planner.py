from app.agent.analyzers.requirement_analyzer import (
    RequirementAnalyzer,
)

from app.agent.llm.client import LLMClient
from app.agent.llm.prompts.planner_prompt import (
    PlannerPromptBuilder,
)
from app.agent.llm.structured_output import (
    StructuredOutputParser,
)

from app.agent.models import (
    AnalysisContext,
    ContextPlan,
    LLMInteraction,
)

class LLMRequirementPlanner:

    name = "LLM Requirement Planner"

    def __init__(self):
        self.client = LLMClient()

        self.prompt_builder = PlannerPromptBuilder()

        self.output_parser = StructuredOutputParser()

        # Rule-based fallback used when the LLM planner
        # fails or returns an invalid structured response.
        self.fallback_planner = RequirementAnalyzer()

    def execute(
        self,
        ctx: AnalysisContext,
    ) -> None:

        prompt = self.prompt_builder.build(
            ctx.requirement,
        )

        try:
            llm_response = self.client.generate(
                prompt,
            )

            # Store the LLM interaction for traceability,
            # debugging, and analysis.
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

            # StructuredOutputParser is responsible for:
            # 1. Parsing the LLM response
            # 2. Validating it against ContextPlan
            # 3. Returning a valid ContextPlan instance
            ctx.context_plan = self.output_parser.parse(
                llm_response.response,
                ContextPlan,
            )

        except Exception as ex:

            # Fall back to deterministic planning when:
            # - LLM invocation fails
            # - LLM returns invalid JSON
            # - ContextPlan validation fails
            ctx.context_plan = self.fallback_planner.analyze(
                ctx.requirement,
            )

            print(
                f"LLM planning failed. "
                f"Using rule-based planner.\n{ex}"
            )