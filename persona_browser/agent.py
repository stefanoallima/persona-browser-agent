"""Core agent — drives browser-use with the configured LLM."""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional

from .config import Config, load_config
from .llm import create_llm
from .prompts import build_task_prompt
from .report import create_report, ReportStatus


async def run_persona_test(
    persona_path: str,
    url: str,
    objectives: str,
    config: Optional[Config] = None,
    scope: str = "task",
    task_id: str = "",
    form_data: str = "",
    screenshots_dir: str = "",
    record_video_dir: str = "",
) -> dict:
    """Run a browser-use persona test.

    Args:
        persona_path: Path to persona/micro-persona .md file
        url: URL of running application
        objectives: Comma-separated objectives to test
        config: Configuration (loaded from config.yaml if None)
        scope: "task" or "gate"
        task_id: Task ID for per-task tests
        form_data: Optional realistic form data
        screenshots_dir: Override screenshots directory
        record_video_dir: Override video recording directory

    Returns:
        dict with test results (JSON-serializable)
    """
    if config is None:
        config = load_config()

    start_time = time.time()

    # Read persona
    persona_file = Path(persona_path)
    if not persona_file.exists():
        return create_report(
            status=ReportStatus.SKIP,
            error=f"Persona file not found: {persona_path}",
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    persona_text = persona_file.read_text(encoding="utf-8")

    # Create LLM
    try:
        llm = create_llm(config.llm)
    except ValueError as e:
        return create_report(
            status=ReportStatus.SKIP,
            error=str(e),
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    # Build task prompt
    task = build_task_prompt(
        persona_text=persona_text,
        url=url,
        objectives=objectives,
        scope=scope,
        form_data=form_data,
    )

    # Configure browser
    try:
        from browser_use import Agent, Browser
    except ImportError:
        return create_report(
            status=ReportStatus.SKIP,
            error="browser-use not installed. Run: pip install browser-use",
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    browser_kwargs = {}
    vid_dir = record_video_dir or (
        config.browser.record_video_dir if config.browser.record_video else ""
    )
    if vid_dir:
        browser_kwargs["record_video_dir"] = Path(vid_dir)

    browser = Browser(**browser_kwargs)

    # Set up screenshots directory
    ss_dir = screenshots_dir or config.reporting.screenshots_dir
    if ss_dir:
        Path(ss_dir).mkdir(parents=True, exist_ok=True)

    # Run the agent
    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
        )

        result = await agent.run()
        elapsed = time.time() - start_time

        return create_report(
            status=ReportStatus.DONE,
            elapsed=elapsed,
            persona=persona_path,
            url=url,
            scope=scope,
            task_id=task_id,
            objectives=objectives,
            agent_result=str(result),
        )

    except Exception as e:
        elapsed = time.time() - start_time
        return create_report(
            status=ReportStatus.ERROR,
            error=str(e),
            elapsed=elapsed,
            persona=persona_path,
            url=url,
            scope=scope,
            task_id=task_id,
            objectives=objectives,
        )
    finally:
        await browser.close()


def run_sync(
    persona_path: str,
    url: str,
    objectives: str,
    **kwargs,
) -> dict:
    """Synchronous wrapper for run_persona_test."""
    return asyncio.run(run_persona_test(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        **kwargs,
    ))
