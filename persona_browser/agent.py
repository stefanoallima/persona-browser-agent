"""Core agent — drives browser-use with the configured LLM.

v3 rewrite: BrowserSession + BrowserProfile, HAR recording, structured output.
"""

import asyncio
import json
import logging
import os
import time
import tempfile
from pathlib import Path
from typing import Optional

from .config import Config, LLMConfig, get_api_key, load_config
from .prompts import build_task_prompt
from .report import create_report, ReportStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primary async entry point
# ---------------------------------------------------------------------------

async def run_navigator(
    persona_path: str,
    url: str,
    objectives: str,
    config: Optional[Config] = None,
    scope: str = "task",
    task_id: str = "",
    form_data: str = "",
    manifest_path: str = "",
    screenshots_dir: str = "",
    record_video_dir: str = "",
    app_domains: Optional[list] = None,
) -> dict:
    """Run a persona-driven browser navigation session.

    Args:
        persona_path: Path to persona/micro-persona .md file
        url: URL of running application
        objectives: Comma-separated objectives to test
        config: Configuration (loaded from config.yaml if None)
        scope: "task" or "gate"
        task_id: Task ID for per-task tests
        form_data: Optional realistic form data for form filling
        manifest_path: Optional path to manifest JSON file
        screenshots_dir: Override screenshots directory
        record_video_dir: Override video recording directory
        app_domains: Override list of domains to filter HAR entries

    Returns:
        dict with structured v3 results (JSON-serializable)
    """
    if config is None:
        config = load_config()

    start_time = time.time()

    # ── Persona ───────────────────────────────────────────────────────────────
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

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest: Optional[dict] = None
    if manifest_path:
        mp = Path(manifest_path)
        if mp.exists():
            try:
                manifest = json.loads(mp.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to parse manifest %s: %s", manifest_path, exc)

    # ── LLM ───────────────────────────────────────────────────────────────────
    try:
        api_key = get_api_key(config.llm)
    except ValueError as e:
        return create_report(
            status=ReportStatus.SKIP,
            error=str(e),
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    try:
        from browser_use.llm.litellm.chat import ChatLiteLLM

        llm = ChatLiteLLM(
            model=f"openrouter/{config.llm.model}",
            api_key=api_key,
            api_base=config.llm.endpoint,
            temperature=config.llm.temperature,
        )
    except ImportError:
        # Fallback: try langchain_openai (used in unit tests / legacy envs)
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=config.llm.model,
                api_key=api_key,
                base_url=config.llm.endpoint,
                temperature=config.llm.temperature,
            )
            logger.warning(
                "browser_use.llm.litellm.chat not available — falling back to ChatOpenAI"
            )
        except ImportError:
            return create_report(
                status=ReportStatus.SKIP,
                error=(
                    "No LLM backend available. Install one of:\n"
                    "  pip install browser-use        (includes ChatLiteLLM)\n"
                    "  pip install langchain-openai    (ChatOpenAI fallback)"
                ),
                elapsed=0,
                persona=persona_path,
                url=url,
            )
        except Exception as e:
            return create_report(
                status=ReportStatus.SKIP,
                error=f"LLM creation failed (ChatOpenAI fallback): {e}",
                elapsed=0,
                persona=persona_path,
                url=url,
            )
    except Exception as e:
        return create_report(
            status=ReportStatus.SKIP,
            error=f"LLM creation failed: {e}. Provider: {config.llm.provider}, Model: {config.llm.model}",
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    # ── Browser-use import ────────────────────────────────────────────────────
    try:
        from browser_use import Agent
        from browser_use.browser.profile import BrowserProfile
        from browser_use.browser.session import BrowserSession
    except ImportError:
        return create_report(
            status=ReportStatus.SKIP,
            error="browser-use not installed. Run: pip install browser-use",
            elapsed=0,
            persona=persona_path,
            url=url,
        )

    # ── Task prompt ───────────────────────────────────────────────────────────
    task = build_task_prompt(
        persona_text=persona_text,
        url=url,
        objectives=objectives,
        scope=scope,
        form_data=form_data,
        manifest=manifest,
    )

    # ── HAR monkey-patch (must happen BEFORE BrowserSession is created) ───────
    # This patches browser-use's internal _is_https to accept http:// URLs
    # for HAR recording (needed for localhost dev servers). Coupled to
    # browser-use internals — may break on version updates.
    if config.browser.capture_network:
        try:
            import browser_use
            bu_version = getattr(browser_use, "__version__", "unknown")
            import browser_use.browser.watchdogs.har_recording_watchdog as _har_mod
            if not hasattr(_har_mod, "_is_https"):
                logger.warning(
                    "HAR monkey-patch skipped: _is_https not found in browser-use %s. "
                    "HAR recording may not work for http:// URLs.", bu_version
                )
            else:
                _har_mod._is_https = lambda u: bool(
                    u and (u.startswith("https://") or u.startswith("http://"))
                )
        except Exception as exc:
            logger.warning("HAR monkey-patch failed (non-fatal, browser-use may have changed): %s", exc)

    # ── BrowserProfile & BrowserSession ───────────────────────────────────────
    har_path = None
    profile_kwargs: dict = {
        "headless": config.browser.headless,
        "viewport": {"width": config.browser.width, "height": config.browser.height},
    }

    if config.browser.capture_network:
        try:
            har_fd = tempfile.NamedTemporaryFile(suffix=".har", delete=False)
            har_path = har_fd.name
            har_fd.close()  # close fd; browser-use will write to this path
            profile_kwargs["record_har_path"] = har_path
            profile_kwargs["record_har_content"] = "embed"
        except Exception as exc:
            logger.warning("Could not set HAR path (non-fatal): %s", exc)
            har_path = None

    # Screenshots directory
    ss_dir = screenshots_dir or config.reporting.screenshots_dir
    if ss_dir:
        Path(ss_dir).mkdir(parents=True, exist_ok=True)

    profile = BrowserProfile(**profile_kwargs)
    session = BrowserSession(browser_profile=profile)

    # ── Run agent ─────────────────────────────────────────────────────────────
    result = None
    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=session,
            max_steps=config.browser.max_steps,
        )

        timeout_secs = config.browser.timeout_seconds or config.browser.timeout or 300
        try:
            result = await asyncio.wait_for(agent.run(), timeout=timeout_secs)
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error("Navigator timed out after %ds", timeout_secs)
            return create_report(
                status=ReportStatus.ERROR,
                error=f"Navigator timed out after {timeout_secs}s",
                elapsed=elapsed,
                persona=persona_path,
                url=url,
                scope=scope,
                task_id=task_id,
                objectives=objectives,
            )
        elapsed = time.time() - start_time

        # Determine status: PARTIAL if agent did not complete (max_steps hit)
        try:
            completed = result.is_done()
        except Exception:
            completed = True  # assume done if we can't tell

        report_status = ReportStatus.DONE if completed else ReportStatus.PARTIAL

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        logger.error("Agent run failed: %s", error_msg)

        # Build partial output from whatever history is available
        partial_output = None
        if result is not None:
            try:
                partial_output = _build_navigator_output(
                    result=result,
                    har_path=har_path,
                    app_domains=app_domains or config.browser.app_domains,
                    manifest=manifest,
                    persona=persona_path,
                    url=url,
                    scope=scope,
                )
            except Exception as parse_exc:
                logger.warning("Could not build partial output: %s", parse_exc)

        return create_report(
            status=ReportStatus.ERROR,
            error=error_msg,
            elapsed=elapsed,
            persona=persona_path,
            url=url,
            scope=scope,
            task_id=task_id,
            objectives=objectives,
            navigator_output=partial_output,
        )
    finally:
        try:
            await session.stop()
        except Exception as stop_exc:
            logger.warning("Session stop failed (non-fatal): %s", stop_exc)

        # Clean up temp HAR file — always runs, even if har_path was set then
        # recording failed. Prevents temp file accumulation.
        if har_path:
            try:
                Path(har_path).unlink(missing_ok=True)
            except Exception:
                logger.debug("Could not remove temp HAR file: %s", har_path)

    # ── Parse structured v3 output ────────────────────────────────────────────
    navigator_output = _build_navigator_output(
        result=result,
        har_path=har_path,
        app_domains=app_domains or config.browser.app_domains,
        manifest=manifest,
        persona=persona_path,
        url=url,
        scope=scope,
    )

    return create_report(
        status=report_status,
        elapsed=elapsed,
        persona=persona_path,
        url=url,
        scope=scope,
        task_id=task_id,
        objectives=objectives,
        agent_result=navigator_output.get("agent_result", str(result)),
        navigator_output=navigator_output,
    )


# ---------------------------------------------------------------------------
# Internal helper: HAR + history → navigator_output dict
# ---------------------------------------------------------------------------

def _build_navigator_output(
    result,
    har_path: Optional[str],
    app_domains: list,
    manifest: Optional[dict],
    persona: str,
    url: str,
    scope: str,
) -> dict:
    """Parse agent history + HAR into v3 navigator output."""
    from .har_parser import parse_har
    from .output_parser import parse_history

    # Parse HAR (best-effort)
    har_entries: list = []
    if har_path:
        har_file = Path(har_path)
        if har_file.exists():
            try:
                har_entries = parse_har(str(har_path), app_domains=app_domains or None)
            except Exception as exc:
                logger.warning("HAR parse failed (non-fatal): %s", exc)
        else:
            logger.warning("HAR file not created — proceeding without network data")

    return parse_history(
        history=result,
        har_entries=har_entries,
        manifest=manifest,
        persona=persona,
        url=url,
        scope=scope,
    )


# ---------------------------------------------------------------------------
# Backward-compat wrapper: run_persona_test()
# ---------------------------------------------------------------------------

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
    """Backward-compatible wrapper — calls run_navigator() internally.

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
    return await run_navigator(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        config=config,
        scope=scope,
        task_id=task_id,
        form_data=form_data,
        screenshots_dir=screenshots_dir,
        record_video_dir=record_video_dir,
    )


# ---------------------------------------------------------------------------
# Synchronous wrapper: run_sync()
# ---------------------------------------------------------------------------

def run_sync(
    persona_path: str,
    url: str,
    objectives: str,
    **kwargs,
) -> dict:
    """Synchronous wrapper for run_navigator / run_persona_test."""
    return asyncio.run(run_persona_test(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        **kwargs,
    ))
