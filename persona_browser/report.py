"""Structured report generation for SUDD integration."""

from enum import Enum
from typing import Dict, Optional


class ReportStatus(str, Enum):
    DONE = "DONE"
    PARTIAL = "PARTIAL"  # Navigator hit max_steps or timeout before completing
    ERROR = "ERROR"
    SKIP = "SKIP"


def create_report(
    status: ReportStatus,
    elapsed: float = 0,
    persona: str = "",
    url: str = "",
    scope: str = "",
    task_id: str = "",
    objectives: str = "",
    agent_result: str = "",
    error: str = "",
    navigator_output: Optional[Dict] = None,
) -> dict:
    """Create a structured report dict for SUDD consumption.

    SUDD agents parse this JSON to incorporate browser-use findings
    into their validation verdicts.

    Args:
        navigator_output: Optional structured v3 output dict from the navigator.
            All keys are merged into the top-level report dict.
    """
    report = {
        "status": status.value,
        "elapsed_seconds": round(elapsed, 1),
        "persona": persona,
        "url": url,
    }

    if scope:
        report["scope"] = scope
    if task_id:
        report["task_id"] = task_id
    if objectives:
        report["objectives"] = objectives
    if agent_result:
        report["agent_result"] = agent_result
    if error:
        report["error"] = error
        report["reason"] = _classify_error(error)

    # Merge navigator structured output (v3) if provided
    if navigator_output:
        report.update(navigator_output)

    return report


def _classify_error(error: str) -> str:
    """Classify error for SUDD routing."""
    lower = error.lower()
    if "api key" in lower or "api_key" in lower or "unauthorized" in lower:
        return "missing_api_key"
    if "not installed" in lower or "import" in lower:
        return "missing_dependency"
    if "max_steps" in lower or "max steps" in lower:
        return "max_steps_reached"
    if "timeout" in lower or "timed out" in lower:
        return "timeout_reached"
    if "connection" in lower or "refused" in lower:
        return "connection_failed"
    if "not found" in lower and "persona" in lower:
        return "missing_persona"
    return "unknown"
