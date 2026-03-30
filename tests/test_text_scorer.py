"""
Tests for persona_browser/text_scorer.py

TDD: all tests written first. Uses mocked LLM (no real API calls).
Fixtures loaded from fixtures/ directory.
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_FIXTURES = os.path.join(_PROJECT, "fixtures")
_RUBRICS = os.path.join(_PROJECT, "rubrics")

# ---------------------------------------------------------------------------
# Fixture loading helpers
# ---------------------------------------------------------------------------


def _load_navigator_output():
    with open(os.path.join(_FIXTURES, "sample_navigator_output.json")) as f:
        return json.load(f)


def _load_codeintel():
    with open(os.path.join(_FIXTURES, "sample_codeintel.json")) as f:
        return json.load(f)


def _load_rubric():
    with open(os.path.join(_FIXTURES, "sample_rubric.md")) as f:
        return f.read()


def _load_pb_rubric():
    with open(os.path.join(_RUBRICS, "pb-feature-rubric.md")) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Mock LLM factory
# ---------------------------------------------------------------------------

_VALID_MOCK_RESPONSE = json.dumps({
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "Every input field has a visible, associated label",
            "result": "PASS",
            "evidence": "Navigator described 3 labeled fields: Full Name, Email Address, Password",
            "confidence": "high"
        },
        {
            "feature": "forms",
            "criterion": "Submitting an empty required field triggers a validation error",
            "result": "UNKNOWN",
            "evidence": "Navigator did not test empty submission; no empty-submit action in observations",
            "confidence": "low"
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "The page renders a form with exactly three visible input fields",
            "result": "PASS",
            "evidence": "Navigator saw 3 fields matching spec: Full Name, Email Address, Password",
            "confidence": "high"
        },
        {
            "criterion": "Submitting the form with a valid unique name, email and password navigates to /dashboard",
            "result": "PASS",
            "evidence": "Navigator confirmed redirect to /dashboard after successful POST /api/auth/register (201)",
            "confidence": "high"
        }
    ]
})


def _make_mock_llm(response_text: str):
    """Create a mock LLM that returns the given text."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=response_text))
    return mock


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def navigator_output():
    return _load_navigator_output()


@pytest.fixture
def pages(navigator_output):
    return navigator_output["pages"]


@pytest.fixture
def codeintel():
    return _load_codeintel()


@pytest.fixture
def rubric_text():
    return _load_rubric()


@pytest.fixture
def pb_rubric_text():
    return _load_pb_rubric()


@pytest.fixture
def experience(navigator_output):
    return navigator_output.get("experience")


@pytest.fixture
def mock_llm():
    return _make_mock_llm(_VALID_MOCK_RESPONSE)


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

from persona_browser.text_scorer import score_text


# ---------------------------------------------------------------------------
# 1. Returns a list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_returns_list(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# 2. 1 input page → 1 result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_one_page_one_result(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    single_page = pages[:1]
    result = await score_text(
        pages=single_page,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    assert len(result) == 1


# ---------------------------------------------------------------------------
# 3. Result has page_id matching input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_result_has_page_id(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    input_ids = {p["id"] for p in pages}
    result_ids = {r["page_id"] for r in result}
    assert input_ids == result_ids


# ---------------------------------------------------------------------------
# 4. Result has pb_criteria list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_result_has_pb_criteria(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    for item in result:
        assert "pb_criteria" in item
        assert isinstance(item["pb_criteria"], list)


# ---------------------------------------------------------------------------
# 5. Result has consumer_criteria list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_result_has_consumer_criteria(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    for item in result:
        assert "consumer_criteria" in item
        assert isinstance(item["consumer_criteria"], list)


# ---------------------------------------------------------------------------
# 6. Each criterion has result, evidence, confidence fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_criterion_has_fields(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    for item in result:
        for criterion in item["pb_criteria"]:
            assert "result" in criterion, f"pb_criteria entry missing 'result': {criterion}"
            assert "evidence" in criterion, f"pb_criteria entry missing 'evidence': {criterion}"
            assert "confidence" in criterion, f"pb_criteria entry missing 'confidence': {criterion}"
        for criterion in item["consumer_criteria"]:
            assert "result" in criterion, f"consumer_criteria entry missing 'result': {criterion}"
            assert "evidence" in criterion, f"consumer_criteria entry missing 'evidence': {criterion}"
            assert "confidence" in criterion, f"consumer_criteria entry missing 'confidence': {criterion}"


# ---------------------------------------------------------------------------
# 7. Result values are PASS / FAIL / UNKNOWN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_result_values_valid(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    VALID = {"PASS", "FAIL", "UNKNOWN"}
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    for item in result:
        for criterion in item["pb_criteria"] + item["consumer_criteria"]:
            assert criterion["result"] in VALID, (
                f"Invalid result '{criterion['result']}'; must be one of {VALID}"
            )


# ---------------------------------------------------------------------------
# 8. Confidence values are high / medium / low
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_confidence_values_valid(pages, rubric_text, pb_rubric_text, codeintel, mock_llm):
    VALID = {"high", "medium", "low"}
    result = await score_text(
        pages=pages,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=mock_llm,
    )
    for item in result:
        for criterion in item["pb_criteria"] + item["consumer_criteria"]:
            assert criterion["confidence"] in VALID, (
                f"Invalid confidence '{criterion['confidence']}'; must be one of {VALID}"
            )


# ---------------------------------------------------------------------------
# 9. JSON parse fallback — when LLM returns non-JSON, all criteria UNKNOWN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_json_parse_fallback(pages, rubric_text, pb_rubric_text, codeintel):
    bad_llm = _make_mock_llm("Sorry, I cannot evaluate this page right now.")
    single_page = pages[:1]
    result = await score_text(
        pages=single_page,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
        llm=bad_llm,
    )
    assert len(result) == 1
    item = result[0]
    # All criteria should be UNKNOWN when parsing fails
    for criterion in item["pb_criteria"] + item["consumer_criteria"]:
        assert criterion["result"] == "UNKNOWN", (
            f"Expected UNKNOWN on parse failure, got: {criterion['result']}"
        )
    # At least one criterion should contain a parse-failure note
    all_evidence = [c.get("evidence", "") + c.get("note", "") for c in item["pb_criteria"] + item["consumer_criteria"]]
    assert any("could not be parsed" in ev.lower() or "parse" in ev.lower() for ev in all_evidence), (
        "Expected a 'could not be parsed' note in at least one criterion"
    )


# ---------------------------------------------------------------------------
# 10. No LLM raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_text_no_llm_raises(pages, rubric_text, pb_rubric_text, codeintel):
    with pytest.raises(ValueError, match="LLM is required"):
        await score_text(
            pages=pages,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            codeintel=codeintel,
            llm=None,
        )
