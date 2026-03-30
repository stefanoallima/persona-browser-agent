"""
Tests for persona_browser/visual_scorer.py

Uses mocked LLM to avoid real multimodal calls.
All 8 tests follow the pattern: mock LLM → call score_visual → assert output structure.
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from persona_browser.codeintel_filter import filter_codeintel_for_visual


# ---------------------------------------------------------------------------
# Helper — build a mock LLM that returns a fixed response text
# ---------------------------------------------------------------------------

def _make_mock_llm(response_text: str):
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=response_text))
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_LLM_RESPONSE = json.dumps({
    "features_detected": ["forms", "cta"],
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "Every field has a visible label",
            "result": "PASS",
            "evidence": "Screenshot shows 3 fields with labels",
            "confidence": "high",
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "Signup form has 3 fields",
            "result": "PASS",
            "evidence": "3 input fields visible",
            "confidence": "high",
        }
    ],
})

SAMPLE_RUBRIC = "## Consumer Rubric\n- Signup form has 3 fields\n"
SAMPLE_PB_RUBRIC = "## PB Rubric\n- Every field has a visible label\n"

SAMPLE_CODEINTEL = {
    "pages": [
        {
            "id": "registration",
            "purpose": "New user signup",
            "elements": {
                "forms": [
                    {
                        "id": "registerForm",
                        "fields": [{"name": "email", "type": "email", "required": True, "label": "Email"}],
                        "submit_button": {"text": "Register", "type": "submit"},
                        "api_call": {"method": "POST", "endpoint": "/api/auth/register"},
                        "on_success": {"redirect": "/dashboard"},
                    }
                ]
            },
            "design_tokens": {"primary_color": "#667eea"},
        }
    ],
    "api_endpoints": [],
    "auth": {},
    "data_flows": [],
}


@pytest.fixture
def filtered_codeintel():
    return filter_codeintel_for_visual(SAMPLE_CODEINTEL)


@pytest.fixture
def screenshot_file(tmp_path):
    """Create a real (tiny) PNG file on disk."""
    # Minimal 1x1 white PNG bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    p = tmp_path / "screenshot.png"
    p.write_bytes(png_bytes)
    return str(p)


@pytest.fixture
def single_page(screenshot_file):
    return [
        {
            "id": "registration",
            "url_visited": "http://localhost:3333/register",
            "screenshot": screenshot_file,
        }
    ]


@pytest.fixture
def mock_llm():
    return _make_mock_llm(MOCK_LLM_RESPONSE)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_visual_returns_list(single_page, filtered_codeintel, mock_llm):
    """score_visual must return a list."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_score_visual_one_page_one_result(single_page, filtered_codeintel, mock_llm):
    """1 input page → 1 output result."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert len(result) == 1


@pytest.mark.asyncio
async def test_score_visual_result_has_page_id(single_page, filtered_codeintel, mock_llm):
    """Each result dict must have a page_id matching the input page's id."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert result[0]["page_id"] == "registration"


@pytest.mark.asyncio
async def test_score_visual_has_features_detected(single_page, filtered_codeintel, mock_llm):
    """Each result must include features_detected as a list."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert "features_detected" in result[0]
    assert isinstance(result[0]["features_detected"], list)


@pytest.mark.asyncio
async def test_score_visual_has_pb_criteria(single_page, filtered_codeintel, mock_llm):
    """Each result must include pb_criteria as a list."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert "pb_criteria" in result[0]
    assert isinstance(result[0]["pb_criteria"], list)


@pytest.mark.asyncio
async def test_score_visual_has_consumer_criteria(single_page, filtered_codeintel, mock_llm):
    """Each result must include consumer_criteria as a list."""
    from persona_browser.visual_scorer import score_visual

    result = await score_visual(
        pages=single_page,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=mock_llm,
    )
    assert "consumer_criteria" in result[0]
    assert isinstance(result[0]["consumer_criteria"], list)


@pytest.mark.asyncio
async def test_score_visual_missing_screenshot_returns_unknown(filtered_codeintel):
    """Page with a non-existent screenshot path → all UNKNOWN, features_detected=[], no LLM call."""
    from persona_browser.visual_scorer import score_visual

    # LLM mock that would fail if called (should NOT be called)
    never_llm = AsyncMock()
    never_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM should not be called"))

    page_no_screenshot = [
        {
            "id": "registration",
            "url_visited": "http://localhost:3333/register",
            "screenshot": "/nonexistent/path/screenshot.png",
        }
    ]

    result = await score_visual(
        pages=page_no_screenshot,
        rubric_text=SAMPLE_RUBRIC,
        pb_rubric_text=SAMPLE_PB_RUBRIC,
        codeintel=filtered_codeintel,
        llm=never_llm,
    )

    assert len(result) == 1
    page_result = result[0]
    assert page_result["page_id"] == "registration"
    assert page_result["features_detected"] == []
    # All pb_criteria results should be UNKNOWN
    for criterion in page_result["pb_criteria"]:
        assert criterion["result"] == "UNKNOWN"
    # All consumer_criteria results should be UNKNOWN
    for criterion in page_result["consumer_criteria"]:
        assert criterion["result"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_score_visual_no_llm_raises(single_page, filtered_codeintel):
    """Calling score_visual without an LLM must raise ValueError."""
    from persona_browser.visual_scorer import score_visual

    with pytest.raises(ValueError):
        await score_visual(
            pages=single_page,
            rubric_text=SAMPLE_RUBRIC,
            pb_rubric_text=SAMPLE_PB_RUBRIC,
            codeintel=filtered_codeintel,
            llm=None,
        )
