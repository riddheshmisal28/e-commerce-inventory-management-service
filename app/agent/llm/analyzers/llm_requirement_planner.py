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

        self.fallback_planner = RequirementAnalyzer()

    def execute(
        self,
        ctx: AnalysisContext,
    ):

        prompt = self.prompt_builder.build(
            ctx.requirement,
        )

        try:

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

            ctx.context_plan = self.output_parser.parse(
                llm_response.response,
                ContextPlan,
            )

        except Exception as ex:

            ctx.context_plan = self.fallback_planner.analyze(
                ctx.requirement,
            )

            print(
                f"LLM planning failed. "
                f"Using rule-based planner.\n{ex}"
            )