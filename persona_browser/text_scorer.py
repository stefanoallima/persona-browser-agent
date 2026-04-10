"""
persona_browser/text_scorer.py

LLM-based Text Scorer.

Evaluates PB rubric and consumer rubric criteria from the navigator's TEXT
observations (descriptions, actions, error messages), network_log, and
codeintel.  Does NOT see screenshots.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def score_text(
    pages: list[dict],
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    experience: dict | None = None,
    llm=None,
) -> list[dict]:
    """Score each page's text observations against rubric criteria.

    Parameters
    ----------
    pages:
        List of page dicts from navigator output.  Each should have at minimum
        ``id``, ``observations``, and ``network_log`` keys.
    rubric_text:
        Consumer rubric as a markdown string.
    pb_rubric_text:
        PB feature rubric as a markdown string.
    codeintel:
        Full codeintel dict (pages, api_endpoints, auth, data_flows, …).
    experience:
        Optional navigator experience section dict.
    llm:
        LangChain-compatible LLM instance that supports ``ainvoke``.
        Must not be None.

    Returns
    -------
    List of per-page dicts matching schemas/text-scorer-output.schema.json.

    Raises
    ------
    ValueError
        If ``llm`` is None.
    """
    if llm is None:
        raise ValueError("LLM is required for text scoring")

    results: list[dict] = []

    for page in pages:
        page_id = page.get("id", "unknown")
        scored = await _score_page(
            page=page,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            codeintel=codeintel,
            experience=experience,
            llm=llm,
        )
        scored["page_id"] = page_id
        results.append(scored)

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _score_page(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    experience: dict | None,
    llm,
) -> dict:
    """Score a single page and return a dict (without page_id — caller sets it)."""
    prompt = _build_prompt(page, rubric_text, pb_rubric_text, codeintel, experience)

    # Retry with exponential backoff for transient LLM failures
    last_error = None
    for attempt in range(3):
        try:
            response = await llm.ainvoke(prompt)
            break
        except Exception as e:
            last_error = e
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                logger.warning("Text scorer LLM call failed (attempt %d/3), retrying in %ds: %s", attempt + 1, wait, e)
                await asyncio.sleep(wait)
    else:
        logger.error("Text scorer LLM call failed after 3 attempts: %s", last_error)
        raise last_error

    raw_text: str = response.content if hasattr(response, "content") else str(response)

    parsed = _parse_llm_response(raw_text)
    return parsed


def _build_prompt(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    experience: dict | None,
) -> str:
    """Build the scoring prompt for a single page."""
    page_id = page.get("id", "unknown")
    observations = page.get("observations", {})
    description = observations.get("description", "")
    actions = observations.get("actions", [])
    network_log = page.get("network_log", [])

    # Format actions as a readable list
    actions_text = "\n".join(
        f"  Step {a.get('step', '?')}: {a.get('action', '')} → {a.get('result', '')}"
        for a in actions
    )

    # Format network log entries
    network_text = "\n".join(
        f"  {e.get('method', '')} {e.get('url', '')} → {e.get('status', '')} "
        f"({e.get('timing_ms', '')}ms) | {e.get('response_summary', '')}"
        for e in network_log
    )

    # Find codeintel for this page
    codeintel_pages = codeintel.get("pages", [])
    page_codeintel = next(
        (p for p in codeintel_pages if p.get("id") == page_id), None
    )
    codeintel_section = json.dumps(page_codeintel, indent=2) if page_codeintel else "N/A"

    # Include API endpoints relevant to this page (based on network_log URLs)
    page_urls = {e.get("url", "") for e in network_log}
    api_endpoints = codeintel.get("api_endpoints", [])
    relevant_endpoints = [
        ep for ep in api_endpoints
        if any(ep.get("path", "") in url for url in page_urls)
    ]
    endpoints_section = json.dumps(relevant_endpoints, indent=2) if relevant_endpoints else "N/A"

    # Experience (if available)
    experience_section = json.dumps(experience, indent=2) if experience else "N/A"

    prompt = f"""You are a QA scoring agent. Evaluate the following page based ONLY on text observations.
You do NOT have access to screenshots. Evaluate spatial layout criteria as UNKNOWN.

## Page ID
{page_id}

## Navigator Description
{description}

## Navigator Actions
{actions_text}

## Network Log
{network_text}

## Codeintel for this page
{codeintel_section}

## Relevant API Endpoints
{endpoints_section}

## Navigator Experience (if available)
{experience_section}

---

## Consumer Rubric
{rubric_text}

---

## PB Feature Rubric
{pb_rubric_text}

---

## Instructions

Evaluate each criterion relevant to this page. For each criterion:
- Set `result` to: PASS, FAIL, or UNKNOWN
  - PASS: text observations clearly confirm the criterion is met
  - FAIL: text observations clearly indicate the criterion is not met
  - UNKNOWN: insufficient text evidence (e.g. visual-only criteria like spatial layout, colours, icons)
- Set `evidence`: what the navigator observed that supports the judgment
- Set `confidence`: high (clear evidence), medium (some ambiguity), low (insufficient info)
- Use codeintel to compare against expected behaviour when available
- Skip purely visual-only PB criteria (e.g. forms.error_near_field, forms.submit_visible, forms.loading_state, baseline.readable, baseline.no_broken_assets, baseline.responsive)

Return a single JSON object with exactly two top-level keys:
- `pb_criteria`: array of objects with fields: feature, criterion, result, evidence, confidence
- `consumer_criteria`: array of objects with fields: criterion, result, evidence, confidence

Example output:
{{
  "pb_criteria": [
    {{"feature": "forms", "criterion": "Every input field has a visible, associated label", "result": "PASS", "evidence": "Navigator described 3 labeled fields", "confidence": "high"}}
  ],
  "consumer_criteria": [
    {{"criterion": "Signup form has name, email, password fields", "result": "PASS", "evidence": "Navigator saw 3 fields matching spec", "confidence": "high"}}
  ]
}}

Output ONLY the JSON object. No preamble, no explanation outside the JSON.
"""
    return prompt


def _parse_llm_response(raw_text: str) -> dict:
    """Parse the LLM's response, with fallback to UNKNOWN on failure.

    Attempts:
    1. Direct JSON parse
    2. Extract JSON from markdown code fences (```json ... ```)
    3. Fallback: return UNKNOWN for all criteria with a parse-failure note
    """
    # Attempt 1: direct JSON parse
    stripped = raw_text.strip()
    try:
        parsed = json.loads(stripped)
        return _normalise_parsed(parsed)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        candidate = match.group(1).strip()
        try:
            parsed = json.loads(candidate)
            return _normalise_parsed(parsed)
        except json.JSONDecodeError:
            pass

    # Fallback: return UNKNOWN for all criteria
    fallback_note = "LLM response could not be parsed"
    return {
        "pb_criteria": [
            {
                "feature": "unknown",
                "criterion": "All PB criteria",
                "result": "UNKNOWN",
                "evidence": fallback_note,
                "confidence": "low",
                "note": fallback_note,
            }
        ],
        "consumer_criteria": [
            {
                "criterion": "All consumer criteria",
                "result": "UNKNOWN",
                "evidence": fallback_note,
                "confidence": "low",
                "note": fallback_note,
            }
        ],
    }


def _normalise_parsed(parsed: dict) -> dict:
    """Normalise the parsed LLM response to ensure required fields exist."""
    pb_criteria = parsed.get("pb_criteria", [])
    consumer_criteria = parsed.get("consumer_criteria", [])

    # Ensure each entry has the required fields, filling defaults if missing
    normalised_pb = []
    for item in pb_criteria:
        normalised_pb.append({
            "feature": item.get("feature", "unknown"),
            "criterion": item.get("criterion", ""),
            "result": _validate_result(item.get("result", "UNKNOWN")),
            "evidence": item.get("evidence", ""),
            "confidence": _validate_confidence(item.get("confidence", "low")),
            **{k: v for k, v in item.items() if k not in
               {"feature", "criterion", "result", "evidence", "confidence"}},
        })

    normalised_consumer = []
    for item in consumer_criteria:
        normalised_consumer.append({
            "criterion": item.get("criterion", ""),
            "result": _validate_result(item.get("result", "UNKNOWN")),
            "evidence": item.get("evidence", ""),
            "confidence": _validate_confidence(item.get("confidence", "low")),
            **{k: v for k, v in item.items() if k not in
               {"criterion", "result", "evidence", "confidence"}},
        })

    return {
        "pb_criteria": normalised_pb,
        "consumer_criteria": normalised_consumer,
    }


def _validate_result(value: str) -> str:
    """Return value if valid, else UNKNOWN."""
    if value in {"PASS", "FAIL", "UNKNOWN"}:
        return value
    return "UNKNOWN"


def _validate_confidence(value: str) -> str:
    """Return value if valid, else low."""
    if value in {"high", "medium", "low"}:
        return value
    return "low"
