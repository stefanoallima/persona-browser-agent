"""Structured report generation for SUDD integration."""

from enum import Enum
from typing import Optional


class ReportStatus(str, Enum):
    DONE = "DONE"
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
) -> dict:
    """Create a structured report dict for SUDD consumption.

    SUDD agents parse this JSON to incorporate browser-use findings
    into their validation verdicts.
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

    return report


def _classify_error(error: str) -> str:
    """Classify error for SUDD routing."""
    lower = error.lower()
    if "api key" in lower or "api_key" in lower or "unauthorized" in lower:
        return "missing_api_key"
    if "not installed" in lower or "import" in lower:
        return "missing_dependency"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "connection" in lower or "refused" in lower:
        return "connection_failed"
    if "not found" in lower and "persona" in lower:
        return "missing_persona"
    return "unknown"
