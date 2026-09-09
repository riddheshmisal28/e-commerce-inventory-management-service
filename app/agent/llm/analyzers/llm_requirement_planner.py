from app.agent.analyzers.requirement_analyzer import (
    RequirementAnalyzer,
)
from app.agent.core.agent_step import AgentStep

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


class LLMRequirementPlanner(AgentStep):

    name = "LLM Requirement Planner"
    required_context: set[str] = set()

    def __init__(self):
        super().__init__()
        self.client = LLMClient(json_mode=True)

        self.prompt_builder = PlannerPromptBuilder()

        self.output_parser = StructuredOutputParser()

        # Deterministic fallback used when the LLM planner
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

            # Store LLM interaction for traceability,
            # debugging, and analysis.
            ctx.llm_interactions.append(
                LLMInteraction(
                    step=self.name,
                    provider=getattr(llm_response, "provider", "ollama"),
                    model=getattr(llm_response, "model", ""),
                    prompt=prompt,
                    response=getattr(llm_response, "response", ""),
                    duration_ms=getattr(llm_response, "duration_ms", 0.0),
                    input_tokens=getattr(llm_response, "input_tokens", None),
                    output_tokens=getattr(llm_response, "output_tokens", None),
                    total_tokens=getattr(llm_response, "total_tokens", None),
                    tokens_per_second=getattr(llm_response, "tokens_per_second", None),
                )
            )

            # Parse and validate the planner response.
            context_plan = self.output_parser.parse(
                llm_response.response,
                ContextPlan,
            )

            # Normalize planner output before storing it.
            self._normalize_context_plan(
                context_plan,
            )

            ctx.context_plan = context_plan

        except Exception as ex:

            # Fall back to deterministic planning when:
            # - LLM invocation fails
            # - LLM returns invalid JSON
            # - ContextPlan validation fails
            ctx.context_plan = self.fallback_planner.execute(
                ctx,
            )

            # print(
            #     "LLM planning failed. "
            #     "Using rule-based planner.\n"
            #     f"{ex}"
            # )

    @staticmethod
    def _normalize_context_plan(
        context_plan: ContextPlan,
    ) -> None:
        """
        Normalize planner output so downstream context retrieval
        receives predictable values.

        This method intentionally does not infer additional
        context types. The LLM planner remains responsible for
        deciding what context is required.
        """

        if context_plan.keywords is None:
            context_plan.keywords = []

        # Normalize keywords:
        # - lowercase
        # - trim whitespace
        # - remove empty values
        # - remove duplicates
        context_plan.keywords = list(
            dict.fromkeys(
                keyword.strip().lower()
                for keyword in context_plan.keywords
                if keyword and keyword.strip()
            )
        )