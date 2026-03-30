"""
Tests for persona_browser/scorer_runner.py

TDD: all 7 tests written first, then implementation follows.
Uses mocked LLMs (no real API calls) and fixtures from fixtures/ directory.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
RUBRICS = Path(__file__).parent.parent / "rubrics"


def _load(name):
    path = FIXTURES / name
    with open(path) as f:
        return json.load(f) if name.endswith(".json") else f.read()


def _load_pb_rubric():
    with open(RUBRICS / "pb-feature-rubric.md") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------

MOCK_TEXT_RESPONSE = json.dumps({
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "test",
            "result": "PASS",
            "evidence": "ok",
            "confidence": "high",
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "test",
            "result": "PASS",
            "evidence": "ok",
            "confidence": "high",
        }
    ],
})

MOCK_VISUAL_RESPONSE = json.dumps({
    "features_detected": ["forms"],
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "test",
            "result": "PASS",
            "evidence": "ok",
            "confidence": "high",
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "test",
            "result": "PASS",
            "evidence": "ok",
            "confidence": "high",
        }
    ],
})


def _mock_llm(response):
    m = AsyncMock()
    m.ainvoke = AsyncMock(return_value=MagicMock(content=response))
    return m


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def navigator_output():
    return _load("sample_navigator_output.json")


@pytest.fixture
def codeintel():
    return _load("sample_codeintel.json")


@pytest.fixture
def rubric_text():
    return _load("sample_rubric.md")


@pytest.fixture
def pb_rubric_text():
    return _load_pb_rubric()


@pytest.fixture
def text_llm():
    return _mock_llm(MOCK_TEXT_RESPONSE)


@pytest.fixture
def visual_llm():
    return _mock_llm(MOCK_VISUAL_RESPONSE)


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

from persona_browser.scorer_runner import run_scorers


# ---------------------------------------------------------------------------
# Test 1: run_scorers returns a dict with 3 keys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_returns_dict(
    navigator_output, codeintel, rubric_text, pb_rubric_text, text_llm, visual_llm
):
    """run_scorers must return a dict with exactly the 3 expected keys."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )
    assert isinstance(result, dict)
    assert "network_verification" in result
    assert "text_scores" in result
    assert "visual_scores" in result


# ---------------------------------------------------------------------------
# Test 2: network_verification key present and is a dict (not error)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_has_network_verification(
    navigator_output, codeintel, rubric_text, pb_rubric_text, text_llm, visual_llm
):
    """network_verification must be a dict and must not have an 'error' key."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )
    nv = result["network_verification"]
    assert isinstance(nv, dict)
    assert "error" not in nv, f"network_verification should not have an error key: {nv}"


# ---------------------------------------------------------------------------
# Test 3: text_scores key present and is a list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_has_text_scores(
    navigator_output, codeintel, rubric_text, pb_rubric_text, text_llm, visual_llm
):
    """text_scores must be a list."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )
    ts = result["text_scores"]
    assert isinstance(ts, list), f"text_scores should be a list, got: {type(ts)}"


# ---------------------------------------------------------------------------
# Test 4: visual_scores key present and is a list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_has_visual_scores(
    navigator_output, codeintel, rubric_text, pb_rubric_text, text_llm, visual_llm
):
    """visual_scores must be a list."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )
    vs = result["visual_scores"]
    assert isinstance(vs, list), f"visual_scores should be a list, got: {type(vs)}"


# ---------------------------------------------------------------------------
# Test 5: text_llm=None → text_scores has "error" key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_no_text_llm_returns_error(
    navigator_output, codeintel, rubric_text, pb_rubric_text, visual_llm
):
    """When text_llm is None, text_scores should contain an error dict."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=None,
        visual_llm=visual_llm,
    )
    ts = result["text_scores"]
    assert isinstance(ts, dict), f"text_scores should be error dict when no LLM, got: {type(ts)}"
    assert "error" in ts, f"text_scores should have 'error' key when text_llm=None: {ts}"


# ---------------------------------------------------------------------------
# Test 6: visual_llm=None → visual_scores has "error" key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_no_visual_llm_returns_error(
    navigator_output, codeintel, rubric_text, pb_rubric_text, text_llm
):
    """When visual_llm is None, visual_scores should contain an error dict."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=text_llm,
        visual_llm=None,
    )
    vs = result["visual_scores"]
    assert isinstance(vs, dict), f"visual_scores should be error dict when no LLM, got: {type(vs)}"
    assert "error" in vs, f"visual_scores should have 'error' key when visual_llm=None: {vs}"


# ---------------------------------------------------------------------------
# Test 7: network_verification runs even when no LLMs provided
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scorers_network_always_runs(
    navigator_output, codeintel, rubric_text, pb_rubric_text
):
    """Network verifier is deterministic — should run and succeed without LLMs."""
    result = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        text_llm=None,
        visual_llm=None,
    )
    nv = result["network_verification"]
    assert isinstance(nv, dict)
    assert "error" not in nv, f"network_verification should succeed without LLMs: {nv}"
    # Sanity: should have api_calls_total from running against real fixture data
    assert "api_calls_total" in nv, f"Missing api_calls_total in network_verification: {nv}"
