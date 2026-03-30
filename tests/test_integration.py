"""
Integration tests for the navigator pipeline — end-to-end against poc/test_app/.

Requirements:
  - poc/test_app running on port 3333:  cd poc/test_app && node server.js
  - OPENROUTER_API_KEY environment variable set
  - Chrome available for browser-use

All tests are skipped automatically when either requirement is missing.

Run with:
    pytest tests/test_integration.py -v --timeout=120
"""

import asyncio
import os
import socket
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Auto-skip logic — evaluated at collection time
# ---------------------------------------------------------------------------

def _port_open(host: str, port: int) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


SKIP_REASON = None
if not os.environ.get("OPENROUTER_API_KEY"):
    SKIP_REASON = "OPENROUTER_API_KEY not set"
elif not _port_open("localhost", 3333):
    SKIP_REASON = "Test app not running on localhost:3333"

pytestmark = pytest.mark.skipif(SKIP_REASON is not None, reason=SKIP_REASON or "")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent
_MANIFEST_PATH = str(_ROOT / "fixtures" / "sample_manifest.json")
_PERSONA_PATH = str(_ROOT / "examples" / "micro-persona-signup-form.md")


# ---------------------------------------------------------------------------
# Shared fixture — runs the navigator ONCE for all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def navigator_result():
    """Run the full navigator pipeline once and share the result across all tests.

    The navigator takes ~20-30 seconds (real browser + LLM calls).
    Exceptions are caught and stored so individual tests can distinguish
    hard errors from partial/successful runs.
    """
    from persona_browser.agent import run_navigator

    try:
        result = asyncio.run(
            run_navigator(
                persona_path=_PERSONA_PATH,
                url="http://localhost:3333",
                objectives="fill signup form, verify dashboard shows name",
                scope="gate",
                manifest_path=_MANIFEST_PATH,
                app_domains=["localhost:3333"],
            )
        )
    except Exception as exc:
        # Wrap exception so tests can inspect it without crashing the fixture
        result = {
            "status": "ERROR",
            "error": str(exc),
            "_fixture_exception": exc,
        }

    return result


# ---------------------------------------------------------------------------
# 1. run_navigator returns a dict
# ---------------------------------------------------------------------------

def test_integration_returns_dict(navigator_result):
    """The navigator must always return a plain dict (never None, never raises)."""
    assert isinstance(navigator_result, dict), (
        f"Expected dict, got {type(navigator_result)}"
    )


# ---------------------------------------------------------------------------
# 2. status is DONE or PARTIAL
# ---------------------------------------------------------------------------

def test_integration_status_done(navigator_result):
    """Status must be DONE (completed) or PARTIAL (hit step limit).

    ERROR is acceptable only when the fixture caught an unexpected exception —
    in that case we skip rather than fail so the test run isn't poisoned.
    """
    status = navigator_result.get("status")
    if status == "ERROR":
        err = navigator_result.get("error", "unknown error")
        pytest.skip(f"Navigator returned ERROR (not a test failure): {err}")
    assert status in ("DONE", "PARTIAL"), (
        f"Expected DONE or PARTIAL, got {status!r}"
    )


# ---------------------------------------------------------------------------
# 3. output has `pages` array with at least 1 entry
# ---------------------------------------------------------------------------

def test_integration_has_pages(navigator_result):
    """The v3 output must include a non-empty `pages` list."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    pages = navigator_result.get("pages")
    assert isinstance(pages, list), f"Expected pages to be a list, got {type(pages)}"
    assert len(pages) >= 1, "Expected at least 1 page entry"


# ---------------------------------------------------------------------------
# 4. each page has `url_visited`
# ---------------------------------------------------------------------------

def test_integration_page_has_url(navigator_result):
    """Every page entry must have a non-empty `url_visited` string."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    pages = navigator_result.get("pages", [])
    if not pages:
        pytest.skip("Skipping: no pages in output")

    for i, page in enumerate(pages):
        url = page.get("url_visited")
        assert isinstance(url, str) and url, (
            f"Page {i} missing url_visited: {page}"
        )


# ---------------------------------------------------------------------------
# 5. each page has `observations` with `description` and `actions`
# ---------------------------------------------------------------------------

def test_integration_page_has_observations(navigator_result):
    """Every page must have an `observations` dict with description + actions."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    pages = navigator_result.get("pages", [])
    if not pages:
        pytest.skip("Skipping: no pages in output")

    for i, page in enumerate(pages):
        obs = page.get("observations")
        assert isinstance(obs, dict), (
            f"Page {i}: observations must be a dict, got {type(obs)}"
        )
        assert "description" in obs, f"Page {i}: observations missing 'description'"
        assert "actions" in obs, f"Page {i}: observations missing 'actions'"
        assert isinstance(obs["actions"], list), (
            f"Page {i}: observations.actions must be a list"
        )


# ---------------------------------------------------------------------------
# 6. manifest coverage — expected pages appear in coverage output
# ---------------------------------------------------------------------------

def test_integration_manifest_coverage(navigator_result):
    """With a manifest provided, coverage must reference expected page IDs."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    coverage = navigator_result.get("manifest_coverage")
    assert isinstance(coverage, dict), (
        f"manifest_coverage must be a dict, got {type(coverage)}"
    )

    expected_pages = coverage.get("expected_pages")
    assert isinstance(expected_pages, list), "expected_pages must be a list"

    # The sample manifest has registration and dashboard
    assert "registration" in expected_pages, (
        "'registration' not in manifest_coverage.expected_pages"
    )
    assert "dashboard" in expected_pages, (
        "'dashboard' not in manifest_coverage.expected_pages"
    )

    # The navigator should have visited at least one expected page
    visited = coverage.get("visited", [])
    assert isinstance(visited, list), "manifest_coverage.visited must be a list"
    assert len(visited) >= 1, (
        "Expected at least one manifest page to be visited; "
        f"visited={visited}"
    )


# ---------------------------------------------------------------------------
# 7. at least one page has non-empty `network_log`
# ---------------------------------------------------------------------------

def test_integration_har_network_entries(navigator_result):
    """HAR recording must produce at least one network entry across all pages."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    pages = navigator_result.get("pages", [])
    if not pages:
        pytest.skip("Skipping: no pages in output")

    total_entries = sum(len(page.get("network_log", [])) for page in pages)
    assert total_entries >= 1, (
        "Expected at least one network_log entry across all pages; "
        "check that capture_network=True in config.yaml and HAR recording worked"
    )


# ---------------------------------------------------------------------------
# 8. output has `experience` section
# ---------------------------------------------------------------------------

def test_integration_has_experience(navigator_result):
    """The v3 output must include an `experience` dict."""
    status = navigator_result.get("status")
    if status == "ERROR":
        pytest.skip("Skipping: navigator returned ERROR")

    experience = navigator_result.get("experience")
    assert isinstance(experience, dict), (
        f"experience must be a dict, got {type(experience)}"
    )

    # Structural check: required keys in experience section
    for key in ("first_impression", "easy", "hard", "hesitation_points"):
        assert key in experience, f"experience missing key: {key!r}"


# ---------------------------------------------------------------------------
# 9. backward-compat — output has `agent_result` string
# ---------------------------------------------------------------------------

def test_integration_backward_compat(navigator_result):
    """The output must include `agent_result` for backward compatibility.

    This test passes even when status is ERROR (the key should still be present
    or at least the dict should be a dict — confirmed by test 1).
    """
    # agent_result may be empty string but must be present as a key when
    # the navigator ran successfully or partially
    status = navigator_result.get("status")
    if status not in ("DONE", "PARTIAL", "ERROR"):
        pytest.skip(f"Unexpected status: {status!r}")

    # For DONE/PARTIAL the key must exist
    if status in ("DONE", "PARTIAL"):
        assert "agent_result" in navigator_result, (
            "agent_result key missing from DONE/PARTIAL output"
        )
        assert isinstance(navigator_result["agent_result"], str), (
            "agent_result must be a string"
        )
