import json
import queue
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.impact_agent import ImpactAgent
from app.agent.models import PipelineResult, Requirement
from app.agent.validators.input_validator import InputValidator
from app.core.logger import get_logger


logger = get_logger(__name__)
validator = InputValidator()

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
    ),
    PresetRequirement(
        id="category-management",
        title="Category Management",
        tag="Catalog Management",
        description="Create, list, update, and delete product categories with an optional description.",
        acceptance_criteria=[
            "Category names must contain between 2 and 255 characters.",
            "A category can be retrieved by its identifier.",
            "Deleting a category should return a successful no-content response.",
        ],
    ),
    PresetRequirement(
        id="product-catalog-search",
        title="Product Catalog Search",
        tag="Product Catalog",
        description="Browse products with pagination and optional search and category filters, and search the catalog by query.",
        acceptance_criteria=[
            "Product listings must include total count, page, and page size.",
            "A category filter should limit results to products in that category.",
            "A search query must contain at least one character.",
        ],
    ),
    PresetRequirement(
        id="sku-inventory-management",
        title="SKU Inventory Management",
        tag="Inventory Operations",
        description="Create and update SKUs for products while tracking SKU codes, prices, and available quantities.",
        acceptance_criteria=[
            "Every SKU must reference an existing product.",
            "SKU price must be greater than zero and quantity cannot be negative.",
            "SKUs can be listed for a specific product.",
        ],
    ),
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


class ValidationResponse(BaseModel):
    """Response model for validation endpoints."""
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DetailedValidationResponse(BaseModel):
    """Detailed response model for comprehensive validation report."""
    valid: bool
    summary: str
    error_count: int
    warning_count: int
    critical_issues: list[str] = Field(default_factory=list)
    errors_by_category: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


@router.post("/validate", response_model=ValidationResponse)
def validate_requirement(requirement: Requirement) -> ValidationResponse:
    """
    Validate a requirement against input guardrails without running the full pipeline.
    
    Returns:
        - valid: True if requirement passes all checks
        - issues: List of validation errors that prevent execution
        - warnings: List of non-critical warnings
    """
    is_valid, errors = validator.validate(requirement)
    
    issues = [f"[{e.category}] {e.message}" for e in errors if e.severity == "error"]
    warnings = [f"[{e.category}] {e.message}" for e in errors if e.severity == "warning"]
    
    logger.info(
        f"Validation check: {'PASS' if is_valid else 'FAIL'} "
        f"({len(issues)} errors, {len(warnings)} warnings)"
    )
    
    return ValidationResponse(
        valid=is_valid,
        issues=issues,
        warnings=warnings,
    )


@router.post("/validation-report", response_model=DetailedValidationResponse)
def get_validation_report(requirement: Requirement) -> DetailedValidationResponse:
    """
    Get a detailed validation report for a requirement.
    
    Returns detailed information about all validation checks including:
    - Overall validity status
    - Breakdown of errors by category (security, clarity, domain_relevance, etc.)
    - Critical issues that prevent execution
    - Non-critical warnings
    """
    report = validator.get_validation_report(requirement)
    
    logger.info(
        f"Detailed validation report: {report['summary']} "
        f"({report['error_count']} errors, {report['warning_count']} warnings)"
    )
    
    return DetailedValidationResponse(
        valid=report["valid"],
        summary=report["summary"],
        error_count=report["error_count"],
        warning_count=report["warning_count"],
        critical_issues=report["critical_issues"],
        errors_by_category=report["errors_by_category"],
        warnings=report["warnings"],
    )



@router.post("/analyze", response_model=PipelineResult)
def analyze_requirement(requirement: Requirement) -> PipelineResult:
    """
    Execute the full Impact Analysis Agent pipeline on a requirement.
    Returns the comprehensive impact analysis report and execution metrics.
    
    Raises:
        HTTPException 400: If input validation fails (guardrails)
        HTTPException 500: If agent analysis fails
    """
    # Validate input against guardrails
    is_valid, errors = validator.validate(requirement)
    
    if not is_valid:
        error_messages = [f"[{e.category}] {e.message}" for e in errors if e.severity == "error"]
        logger.warning(f"Input validation failed: {error_messages}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Input validation failed",
                "reason": "Requirement does not meet input guardrails",
                "issues": error_messages,
            },
        )
    
    try:
        agent = ImpactAgent()
        result = agent.run(requirement)
        return result
    except Exception as exc:
        logger.error(f"Agent analysis failed: {str(exc)}", exc_info=True)
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
    
    Note: Input validation is performed before streaming starts.
    """
    # Validate input against guardrails
    is_valid, errors = validator.validate(requirement)
    
    if not is_valid:
        error_messages = [f"[{e.category}] {e.message}" for e in errors if e.severity == "error"]
        logger.warning(f"Input validation failed in stream: {error_messages}")
        
        def error_stream():
            yield f"event: validation_error\ndata: {json.dumps({{'error': 'Input validation failed', 'issues': error_messages}})}\n\n"
        
        return StreamingResponse(
            error_stream(),
            status_code=400,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    
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
            logger.error(f"Agent stream analysis failed: {str(exc)}", exc_info=True)
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
