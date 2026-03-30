"""
persona_browser/visual_scorer.py

Visual Scorer — evaluates PB rubric + consumer rubric criteria from SCREENSHOTS
plus filtered codeintel (visual fields only).

Does NOT see: text observations, network_log, or experience.
Detects features on each page (forms, nav, CTA, etc.) and scores relevant criteria.

The caller (scorer_runner) is responsible for filtering codeintel before calling
this module.  score_visual() uses whatever codeintel dict it receives as-is.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Screenshot loader
# ---------------------------------------------------------------------------


def _load_screenshot_as_data_uri(path: str) -> str | None:
    """Read a PNG screenshot from disk and return as a base64 data URI.

    Returns None if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return None
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict | None:
    """Try to parse JSON from LLM response text.

    Strategy:
    1. Direct JSON parse.
    2. Extract from markdown code block (```json ... ```).
    3. Return None on failure.
    """
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    return None


# ---------------------------------------------------------------------------
# Fallback result builders
# ---------------------------------------------------------------------------


def _unknown_page_result(page_id: str, note: str) -> dict:
    """Return a result dict with empty features_detected and UNKNOWN criteria."""
    return {
        "page_id": page_id,
        "features_detected": [],
        "pb_criteria": [
            {
                "feature": "unknown",
                "criterion": "Visual evaluation not available",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
                "note": note,
            }
        ],
        "consumer_criteria": [
            {
                "criterion": "Visual evaluation not available",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
                "note": note,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_prompt(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
) -> str:
    """Build the text portion of the multimodal prompt for one page."""
    page_id = page.get("id", "unknown")
    url = page.get("url_visited", "")

    # Filter codeintel to the relevant page (if page-level data available)
    page_codeintel = {}
    for ci_page in codeintel.get("pages", []):
        if ci_page.get("id") == page_id:
            page_codeintel = ci_page
            break

    codeintel_summary = json.dumps(page_codeintel, indent=2) if page_codeintel else "(none)"

    prompt = f"""You are a visual QA evaluator examining a browser screenshot.

Page ID: {page_id}
URL: {url}

=== CODEINTEL (visual fields only) ===
{codeintel_summary}

=== CONSUMER RUBRIC ===
{rubric_text}

=== PB FEATURE RUBRIC ===
{pb_rubric_text}

=== INSTRUCTIONS ===
1. Look at the screenshot carefully.
2. Detect which UI features are visible on this page.
   Possible features: forms, navigation, cta, data_display, error_states, modal, table, hero
3. Score each relevant PB rubric criterion you can evaluate visually.
   Focus on visual-only checks: labels_visible, required_marked, error_near_field, submit_visible, etc.
4. Score each consumer rubric criterion that is evaluable from a screenshot.

Respond ONLY with valid JSON in this exact format:
{{
  "features_detected": ["<feature>", ...],
  "pb_criteria": [
    {{
      "feature": "<feature>",
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<what you observed>",
      "confidence": "high" | "medium" | "low"
    }}
  ],
  "consumer_criteria": [
    {{
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<what you observed>",
      "confidence": "high" | "medium" | "low"
    }}
  ]
}}
"""
    return prompt


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


async def score_visual(
    pages: list[dict],
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    llm=None,
) -> list[dict]:
    """Score each page's screenshots against rubric criteria.

    Parameters
    ----------
    pages:
        List of page dicts from navigator output.  Each must have an ``id``
        field and may have a ``screenshot`` field with a file path.
    rubric_text:
        Consumer rubric markdown text.
    pb_rubric_text:
        PB feature rubric markdown text.
    codeintel:
        Already-filtered codeintel dict (visual fields only).
        Call ``codeintel_filter.filter_codeintel_for_visual()`` before passing.
    llm:
        Multimodal LangChain LLM instance.  Must not be None.

    Returns
    -------
    list[dict]
        Per-page results matching visual-scorer-output.schema.json.

    Raises
    ------
    ValueError
        If ``llm`` is None.
    """
    if llm is None:
        raise ValueError(
            "score_visual requires a multimodal LLM instance (llm=). "
            "Pass a configured LangChain ChatOpenAI or equivalent."
        )

    from langchain_core.messages import HumanMessage  # imported here to avoid hard dep at module level

    results: list[dict] = []

    for page in pages:
        page_id = page.get("id", "unknown")
        screenshot_path = page.get("screenshot")

        # -------------------------------------------------------------------
        # Guard: missing or non-existent screenshot → UNKNOWN result, no LLM
        # -------------------------------------------------------------------
        if not screenshot_path:
            results.append(_unknown_page_result(page_id, "Screenshot not available"))
            continue

        data_uri = _load_screenshot_as_data_uri(screenshot_path)
        if data_uri is None:
            results.append(_unknown_page_result(page_id, "Screenshot not available"))
            continue

        # -------------------------------------------------------------------
        # Build multimodal message
        # -------------------------------------------------------------------
        prompt_text = _build_prompt(page, rubric_text, pb_rubric_text, codeintel)

        message = HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": data_uri}},
            {"type": "text", "text": prompt_text},
        ])

        # -------------------------------------------------------------------
        # Call LLM
        # -------------------------------------------------------------------
        response = await llm.ainvoke([message])
        response_text = response.content if hasattr(response, "content") else str(response)

        # -------------------------------------------------------------------
        # Parse response
        # -------------------------------------------------------------------
        parsed = _extract_json(response_text)

        if parsed is None:
            # Fallback: could not parse → all UNKNOWN
            results.append(
                _unknown_page_result(page_id, "Could not parse LLM response as JSON")
            )
            continue

        # Normalise to schema shape
        page_result: dict = {
            "page_id": page_id,
            "features_detected": parsed.get("features_detected", []),
            "pb_criteria": parsed.get("pb_criteria", []),
            "consumer_criteria": parsed.get("consumer_criteria", []),
        }
        results.append(page_result)

    return results
