"""
persona_browser/pipeline.py

Full pipeline orchestrator: navigator -> parallel scorers -> score reconciler -> final report.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from .config import Config, ScoringLLMConfig, load_config
from .agent import run_navigator
from .scorer_runner import run_scorers
from .score_reconciler import reconcile_scores

logger = logging.getLogger(__name__)


async def run_pipeline(
    persona_path: str,
    url: str,
    objectives: str,
    config: Config,
    codeintel_path: str,
    rubric_path: str,
    scope: str = "task",
    task_id: str = "",
    form_data: str = "",
    manifest_path: str = "",
    screenshots_dir: str = "",
    record_video_dir: str = "",
    app_domains: list | None = None,
) -> dict:
    """Run the full persona browser testing pipeline.

    Steps:
        1. Run navigator -> navigator_output
        2. Run scorers in parallel (network verifier + text scorer + visual scorer)
        3. Reconcile scores -> final report

    Returns dict matching schemas/final-report.schema.json.
    """
    pipeline_start = time.time()

    # Load inputs
    codeintel = _load_json_file(codeintel_path)
    if codeintel is None:
        return _error_report(
            f"codeintel file not found or invalid: {codeintel_path}",
            persona_path, url,
        )

    rubric_text = _load_text_file(rubric_path)
    if rubric_text is None:
        return _error_report(
            f"Rubric file not found: {rubric_path}",
            persona_path, url,
        )

    pb_rubric_path = Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md"
    pb_rubric_text = _load_text_file(str(pb_rubric_path))
    if pb_rubric_text is None:
        return _error_report(
            f"PB feature rubric not found: {pb_rubric_path}",
            persona_path, url,
        )

    manifest: dict | None = None
    if manifest_path:
        manifest = _load_json_file(manifest_path)

    # Create scoring LLMs
    text_llm, visual_llm, reconciler_llm = _create_scoring_llms(config)
    # Step 1: Navigator
    nav_report = await run_navigator(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        config=config,
        scope=scope,
        task_id=task_id,
        form_data=form_data,
        manifest_path=manifest_path,
        screenshots_dir=screenshots_dir,
        record_video_dir=record_video_dir,
        app_domains=app_domains,
    )

    nav_status = nav_report.get("status", "")
    if nav_status in ("ERROR", "SKIP"):
        return nav_report

    # Navigator output is the report itself (merged structure)
    navigator_output = nav_report

    # Step 2: Scorers (parallel)
    scorer_results = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        manifest=manifest,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    # Step 3: Reconciler
    try:
        final_report = await reconcile_scores(
            text_scores=scorer_results.get("text_scores", {"error": "no text scores"}),
            visual_scores=scorer_results.get("visual_scores", {"error": "no visual scores"}),
            network_verification=scorer_results.get("network_verification", {}),
            navigator_output=navigator_output,
            manifest=manifest,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            llm=reconciler_llm,
        )
        final_report["elapsed_seconds"] = round(time.time() - pipeline_start, 1)
        return final_report

    except Exception as e:
        logger.error("Reconciler failed: %s", e)
        return _partial_report(
            navigator_output=navigator_output,
            scorer_results=scorer_results,
            elapsed=time.time() - pipeline_start,
            error=str(e),
        )

def run_pipeline_sync(persona_path: str, url: str, objectives: str, **kwargs) -> dict:
    """Synchronous wrapper for run_pipeline."""
    return asyncio.run(run_pipeline(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        **kwargs,
    ))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_json_file(path: str) -> dict | None:
    """Load and parse a JSON file. Returns None on failure."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load JSON %s: %s", path, e)
        return None


def _load_text_file(path: str) -> str | None:
    """Load a text file. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to load text file %s: %s", path, e)
        return None

def _create_scoring_llms(config: Config) -> tuple:
    """Create LLM instances for text scorer, visual scorer, and reconciler.

    Returns (text_llm, visual_llm, reconciler_llm).
    Each can be None if the API key is missing.
    """
    def _make_llm(scoring_config: ScoringLLMConfig):
        try:
            api_key = os.environ.get(scoring_config.api_key_env, "")
            if not api_key:
                logger.warning(
                    "Missing API key %s for model %s -- scorer will be skipped",
                    scoring_config.api_key_env, scoring_config.model,
                )
                return None

            try:
                from browser_use.llm.litellm.chat import ChatLiteLLM
                return ChatLiteLLM(
                    model=f"openrouter/{scoring_config.model}",
                    api_key=api_key,
                    api_base=scoring_config.endpoint,
                    temperature=scoring_config.temperature,
                )
            except ImportError:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=scoring_config.model,
                    api_key=api_key,
                    base_url=scoring_config.endpoint,
                    temperature=scoring_config.temperature,
                )
        except Exception as e:
            logger.warning("Failed to create LLM for %s: %s", scoring_config.model, e)
            return None

    return (
        _make_llm(config.scoring.text_scorer),
        _make_llm(config.scoring.visual_scorer),
        _make_llm(config.scoring.reconciler),
    )

def _error_report(error: str, persona: str, url: str) -> dict:
    """Create a minimal error report."""
    return {
        "status": "ERROR",
        "error": error,
        "elapsed_seconds": 0,
        "persona": persona,
        "url": url,
    }


def _partial_report(
    navigator_output: dict,
    scorer_results: dict,
    elapsed: float,
    error: str,
) -> dict:
    """Create a partial report when reconciler fails."""
    report = {
        "version": "1.1",
        "status": "PARTIAL",
        "elapsed_seconds": round(elapsed, 1),
        "persona": navigator_output.get("persona", ""),
        "url": navigator_output.get("url", ""),
        "error": f"Reconciler failed: {error}",
        "manifest_coverage": navigator_output.get("manifest_coverage", {}),
        "pages": [],
        "summary": {
            "pb_criteria_total": 0, "pb_criteria_passed": 0,
            "pb_criteria_failed": 0, "pb_criteria_unknown": 0,
            "consumer_criteria_total": 0, "consumer_criteria_passed": 0,
            "consumer_criteria_failed": 0,
            "verification_tasks_total": 0, "verification_tasks_passed": 0,
            "verification_tasks_failed": 0,
            "network_issues": 0, "total_discrepancies": 0,
            "deal_breakers_triggered": [], "pages_with_failures": [],
            "pages_clean": [],
        },
    }

    nv = scorer_results.get("network_verification", {})
    if isinstance(nv, dict) and "error" not in nv:
        report["network_verification"] = {
            "_source": "Network Verifier (deterministic module -- not LLM)",
            **nv,
        }

    if navigator_output.get("experience"):
        report["experience"] = navigator_output["experience"]
    if navigator_output.get("agent_result"):
        report["agent_result"] = navigator_output["agent_result"]

    return report
