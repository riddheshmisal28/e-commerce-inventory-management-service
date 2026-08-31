import json
import queue
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.impact_agent import ImpactAgent
from app.agent.models import PipelineResult, Requirement

router = APIRouter(
    prefix="/agent",
    tags=["Impact Analysis Agent"],
)


class PresetRequirement(BaseModel):
    id: str
    title: str
    tag: str
    description: str
    acceptance_criteria: list[str] = Field(
        default_factory=list,
    )


SAMPLE_PRESETS: list[PresetRequirement] = [
    PresetRequirement(
        id="low-stock-alert",
        title="Low Stock Alert",
        tag="Inventory & Notifications",
        description="Notify inventory managers and warehouse supervisors when stock falls below a configurable threshold.",
        acceptance_criteria=[
            "Alert should trigger when quantity is below threshold.",
            "Alert should not trigger for inactive products.",
            "Threshold should be configurable per SKU.",
            "Duplicate alerts should not be generated within 24 hours.",
        ],
    )
]


@router.get("/health")
def agent_health():
    """Health and status check for the Impact Analysis Agent service."""
    return {
        "status": "ready",
        "agent": "Impact Analysis Agent",
        "pipeline_steps": [
            "LLM Requirement Planner",
            "Context Retriever",
            "Impact Reasoner",
            "Impact Validator",
            "Grounding Validator",
            "Semantic Impact Refiner",
            "Blast Radius Analyzer",
            "Report Builder",
        ],
    }


@router.get("/presets", response_model=list[PresetRequirement])
def get_requirement_presets():
    """Get pre-configured software requirement presets for quick testing."""
    return SAMPLE_PRESETS


@router.post("/analyze", response_model=PipelineResult)
def analyze_requirement(requirement: Requirement) -> PipelineResult:
    """
    Execute the full Impact Analysis Agent pipeline on a requirement.
    Returns the comprehensive impact analysis report and execution metrics.
    """
    try:
        agent = ImpactAgent()
        result = agent.run(requirement)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent analysis failed: {str(exc)}",
        ) from exc


@router.post("/analyze/stream")
def analyze_requirement_stream(requirement: Requirement):
    """
    Execute the agent pipeline and stream real-time step lifecycle events:
    - step_start (when a step begins execution)
    - step_complete (when a step succeeds with duration_ms)
    - step_skipped (when a step is skipped)
    - step_error (when a step fails)
    - pipeline_complete (with the final PipelineResult)
    - pipeline_error (if pipeline encounters a fatal failure)
    """
    event_queue: queue.Queue = queue.Queue()

    def on_event(event_type: str, data: dict):
        event_queue.put({"event": event_type, "data": data})

    def run_worker():
        try:
            agent = ImpactAgent(on_event=on_event)
            result = agent.run(requirement)
            event_queue.put(
                {
                    "event": "pipeline_complete",
                    "data": json.loads(result.model_dump_json()),
                }
            )
        except Exception as exc:
            event_queue.put(
                {
                    "event": "pipeline_error",
                    "data": {"error": str(exc)},
                }
            )
        finally:
            event_queue.put(None)

    threading.Thread(target=run_worker, daemon=True).start()

    def event_stream():
        while True:
            item = event_queue.get()
            if item is None:
                break
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
