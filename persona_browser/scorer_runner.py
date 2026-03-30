"""
persona_browser/scorer_runner.py

Scorer Runner — orchestrates all three scorers in parallel via asyncio.gather().

The three scorers are:
- Network Verifier (deterministic, no LLM)
- Text Scorer (LLM-based, text observations)
- Visual Scorer (LLM-based, multimodal screenshots)

Each scorer's failure is isolated: if one fails, the others still return results.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .network_verifier import verify_network
from .text_scorer import score_text
from .visual_scorer import score_visual
from .codeintel_filter import filter_codeintel_for_visual


async def run_scorers(
    navigator_output: dict,          # Full navigator output (pages, experience, etc.)
    codeintel: dict,                  # Full codeintel.json
    rubric_text: str,                 # Consumer rubric markdown
    pb_rubric_text: str,              # PB feature rubric markdown
    manifest: dict | None = None,
    text_llm=None,                    # LLM for text scorer
    visual_llm=None,                  # LLM for visual scorer (multimodal)
) -> dict:
    """Run all three scorers in parallel and return combined results.

    Parameters
    ----------
    navigator_output:
        Full navigator output dict containing ``pages`` and optionally
        ``experience``.
    codeintel:
        Full codeintel dict (api_endpoints, auth, pages, data_flows, …).
    rubric_text:
        Consumer rubric as a markdown string.
    pb_rubric_text:
        PB feature rubric as a markdown string.
    manifest:
        Optional manifest dict forwarded to the network verifier.
    text_llm:
        LangChain-compatible LLM for the text scorer.  Pass None to skip.
    visual_llm:
        Multimodal LangChain LLM for the visual scorer.  Pass None to skip.

    Returns
    -------
    dict with keys:
        - ``network_verification``: result dict from verify_network
        - ``text_scores``: list of per-page dicts from score_text, or
          ``{"error": "..."}`` if text_llm is None or an exception occurred
        - ``visual_scores``: list of per-page dicts from score_visual, or
          ``{"error": "..."}`` if visual_llm is None or an exception occurred
    """
    pages = navigator_output.get("pages", [])
    experience = navigator_output.get("experience")

    # Flatten network_log from all pages
    all_network_log: list[dict] = []
    for page in pages:
        all_network_log.extend(page.get("network_log", []))

    # Filter codeintel for visual scorer (strips non-visual fields)
    visual_codeintel = filter_codeintel_for_visual(codeintel)

    # -----------------------------------------------------------------------
    # Inner coroutines — each isolates its own errors
    # -----------------------------------------------------------------------

    async def _run_network():
        try:
            return verify_network(all_network_log, codeintel, manifest)
        except Exception as e:
            return {"error": str(e)}

    async def _run_text():
        if text_llm is None:
            return {"error": "No text LLM provided"}
        try:
            return await score_text(
                pages, rubric_text, pb_rubric_text, codeintel, experience, llm=text_llm
            )
        except Exception as e:
            return {"error": str(e)}

    async def _run_visual():
        if visual_llm is None:
            return {"error": "No visual LLM provided"}
        try:
            return await score_visual(
                pages, rubric_text, pb_rubric_text, visual_codeintel, llm=visual_llm
            )
        except Exception as e:
            return {"error": str(e)}

    # Run all three in parallel
    network_result, text_result, visual_result = await asyncio.gather(
        _run_network(), _run_text(), _run_visual()
    )

    return {
        "network_verification": network_result,
        "text_scores": text_result,
        "visual_scores": visual_result,
    }
