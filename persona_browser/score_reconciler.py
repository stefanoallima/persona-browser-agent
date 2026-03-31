"""
persona_browser/score_reconciler.py

Score Reconciler -- reconciles text scorer, visual scorer, and network verifier
outputs into a final report.

Three phases:
1. Deterministic pre-processing (manifest coverage, verification tasks, scorer availability)
2. LLM-based per-page score reconciliation (parallel) -- added in Task 4
3. Deterministic post-processing (assemble report, compute summary)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1: Deterministic Pre-Processing
# ---------------------------------------------------------------------------


def _check_manifest_coverage(navigator_output: dict, manifest: dict | None) -> dict:
    """Compare navigator's visited pages against manifest expectations.

    Uses the navigator's own manifest_coverage if present, otherwise
    derives from manifest pages list vs navigator page IDs.
    """
    nav_coverage = navigator_output.get("manifest_coverage", {})

    if nav_coverage:
        return {
            "expected_pages": nav_coverage.get("expected_pages", []),
            "visited": nav_coverage.get("visited", []),
            "not_visited": nav_coverage.get("not_visited", []),
            "unexpected_pages": nav_coverage.get("unexpected_pages", []),
        }

    # Derive from manifest + navigator pages
    nav_page_ids = [p.get("id", "") for p in navigator_output.get("pages", [])]

    if manifest is None:
        return {
            "expected_pages": [],
            "visited": nav_page_ids,
            "not_visited": [],
            "unexpected_pages": [],
        }

    manifest_page_ids = [p.get("id", "") for p in manifest.get("pages", [])]
    visited = [pid for pid in manifest_page_ids if pid in nav_page_ids]
    not_visited = [pid for pid in manifest_page_ids if pid not in nav_page_ids]
    unexpected = [pid for pid in nav_page_ids if pid not in manifest_page_ids]

    return {
        "expected_pages": manifest_page_ids,
        "visited": visited,
        "not_visited": not_visited,
        "unexpected_pages": unexpected,
    }


def _evaluate_verification_tasks(
    navigator_output: dict, manifest: dict | None
) -> list[dict]:
    """Extract and normalize verification task results from navigator output.

    V1 (data_persistence) checks page CONTENT after refresh — is submitted data
    still displayed? Uses auth_flow_verification.persistence_after_refresh.

    V3 (auth_persistence) checks NETWORK LOG after refresh — do protected API
    calls still return 200? Uses network_log entries with "refresh" in trigger.
    Falls back to auth_flow text if network_log has no refresh entries.

    V4 (auth_boundary) checks post_auth_access from auth_flow_verification.
    """
    auth_flow = navigator_output.get("auth_flow_verification", {})
    results: list[dict] = []

    # Flatten network_log from all pages
    all_network_log: list[dict] = []
    for page in navigator_output.get("pages", []):
        all_network_log.extend(page.get("network_log", []))

    if manifest and "verification_tasks" in manifest:
        for vtask in manifest["verification_tasks"]:
            vid = vtask["id"]
            vtype = vtask["type"]

            if vtype == "data_persistence":
                # V1: content check — is submitted data still displayed after refresh?
                evidence = auth_flow.get("persistence_after_refresh")
                if evidence and isinstance(evidence, str) and evidence.strip():
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Content check: {evidence}",
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Data persistence not verified -- no refresh observation from navigator",
                    })

            elif vtype == "auth_persistence":
                # V3: network check — do protected API calls return 200 after refresh?
                post_refresh_calls = [
                    entry for entry in all_network_log
                    if "refresh" in entry.get("trigger", "").lower()
                    and entry.get("status", 0) in range(200, 300)
                ]
                if post_refresh_calls:
                    evidence = "; ".join(
                        f"{c.get('method', '')} {c.get('url', '')} -> {c.get('status', '')}"
                        for c in post_refresh_calls
                    )
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Auth persists: {evidence}",
                    })
                elif auth_flow.get("persistence_after_refresh"):
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Auth check (text fallback): {auth_flow['persistence_after_refresh']}",
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Auth persistence not verified -- no post-refresh API calls in network log",
                    })

            elif vtype == "auth_boundary":
                evidence = auth_flow.get("post_auth_access")
                if evidence and isinstance(evidence, str) and evidence.strip():
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": evidence,
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Auth boundary not verified by navigator",
                    })

            else:
                results.append({
                    "id": vid, "type": vtype, "result": "FAIL",
                    "evidence": f"Unknown verification type: {vtype}",
                })

    elif auth_flow:
        # No manifest -- derive basic checks from auth_flow_verification
        if auth_flow.get("persistence_after_refresh"):
            results.append({
                "id": "V1", "type": "data_persistence", "result": "PASS",
                "evidence": f"Content: {auth_flow['persistence_after_refresh']}",
            })
            # V3 from network_log if available
            post_refresh_ok = any(
                "refresh" in e.get("trigger", "").lower() and e.get("status", 0) in range(200, 300)
                for e in all_network_log
            )
            if post_refresh_ok:
                refresh_entries = [
                    e for e in all_network_log
                    if "refresh" in e.get("trigger", "").lower() and e.get("status", 0) in range(200, 300)
                ]
                evidence = "; ".join(
                    f"{e.get('method', '')} {e.get('url', '')} -> {e.get('status', '')}"
                    for e in refresh_entries
                )
                results.append({
                    "id": "V3", "type": "auth_persistence", "result": "PASS",
                    "evidence": f"Auth persists: {evidence}",
                })
            else:
                results.append({
                    "id": "V3", "type": "auth_persistence", "result": "PASS",
                    "evidence": f"Auth check (text fallback): {auth_flow['persistence_after_refresh']}",
                })
        if auth_flow.get("post_auth_access"):
            results.append({
                "id": "V4", "type": "auth_boundary", "result": "PASS",
                "evidence": auth_flow["post_auth_access"],
            })

    return results

def _classify_scorer_availability(text_scores, visual_scores) -> str:
    """Determine which scorers produced valid results.

    Returns one of: "both", "text_only", "visual_only", "neither".
    A scorer result is invalid if it's a dict with an "error" key.
    """
    text_ok = isinstance(text_scores, list) and len(text_scores) > 0
    visual_ok = isinstance(visual_scores, list) and len(visual_scores) > 0

    if text_ok and visual_ok:
        return "both"
    elif text_ok:
        return "text_only"
    elif visual_ok:
        return "visual_only"
    else:
        return "neither"


# ---------------------------------------------------------------------------
# Phase 3: Deterministic Post-Processing
# ---------------------------------------------------------------------------


def _compute_summary(
    reconciled_pages: list[dict],
    network_verification: dict,
    verification_tasks: list[dict],
) -> dict:
    """Compute aggregate summary stats deterministically."""
    pb_total = pb_passed = pb_failed = pb_unknown = 0
    con_total = con_passed = con_failed = 0
    total_discrepancies = 0
    all_deal_breakers: list[str] = []
    pages_with_failures: list[str] = []
    pages_clean: list[str] = []

    for page in reconciled_pages:
        page_id = page.get("id", "unknown")
        page_has_failure = False

        for c in page.get("pb_criteria", []):
            pb_total += 1
            r = c.get("reconciled", "UNKNOWN")
            if r == "PASS":
                pb_passed += 1
            elif r == "FAIL":
                pb_failed += 1
                page_has_failure = True
            else:
                pb_unknown += 1
            if c.get("discrepancy"):
                total_discrepancies += 1

        for c in page.get("consumer_criteria", []):
            con_total += 1
            r = c.get("reconciled", "UNKNOWN")
            if r == "PASS":
                con_passed += 1
            elif r == "FAIL":
                con_failed += 1
                page_has_failure = True
            if c.get("discrepancy"):
                total_discrepancies += 1

        deal_breakers = page.get("deal_breakers", [])
        if deal_breakers:
            page_has_failure = True
            all_deal_breakers.extend(deal_breakers)

        if page_has_failure:
            pages_with_failures.append(page_id)
        else:
            pages_clean.append(page_id)

    net_deal_breakers = network_verification.get("deal_breakers", [])
    all_deal_breakers.extend(net_deal_breakers)
    network_issues = len(network_verification.get("issues", []))

    vt_total = len(verification_tasks)
    vt_passed = sum(1 for v in verification_tasks if v.get("result") == "PASS")
    vt_failed = vt_total - vt_passed

    return {
        "pb_criteria_total": pb_total,
        "pb_criteria_passed": pb_passed,
        "pb_criteria_failed": pb_failed,
        "pb_criteria_unknown": pb_unknown,
        "consumer_criteria_total": con_total,
        "consumer_criteria_passed": con_passed,
        "consumer_criteria_failed": con_failed,
        "verification_tasks_total": vt_total,
        "verification_tasks_passed": vt_passed,
        "verification_tasks_failed": vt_failed,
        "network_issues": network_issues,
        "total_discrepancies": total_discrepancies,
        "deal_breakers_triggered": all_deal_breakers,
        "pages_with_failures": pages_with_failures,
        "pages_clean": pages_clean,
    }

def _assemble_final_report(
    navigator_output: dict,
    reconciled_pages: list[dict],
    network_verification: dict,
    manifest_coverage: dict,
    verification_tasks: list[dict],
    elapsed_seconds: float,
) -> dict:
    """Assemble the final report from all pipeline components.

    Merges navigator metadata with reconciled scoring results.
    Returns dict matching schemas/final-report.schema.json.
    """
    summary = _compute_summary(reconciled_pages, network_verification, verification_tasks)

    report: dict = {
        "version": "1.1",
        "status": navigator_output.get("status", "DONE"),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "persona": navigator_output.get("persona", ""),
        "url": navigator_output.get("url", ""),
        "manifest_coverage": manifest_coverage,
        "pages": reconciled_pages,
        "summary": summary,
    }

    if navigator_output.get("scope"):
        report["scope"] = navigator_output["scope"]
    if navigator_output.get("agent_result"):
        report["agent_result"] = navigator_output["agent_result"]
    if navigator_output.get("experience"):
        report["experience"] = navigator_output["experience"]

    net_with_source = {"_source": "Network Verifier (deterministic module -- not LLM)"}
    net_with_source.update(network_verification)
    report["network_verification"] = net_with_source

    if verification_tasks:
        report["verification_tasks"] = verification_tasks
    if navigator_output.get("screenshots"):
        report["screenshots"] = navigator_output["screenshots"]
    if navigator_output.get("video"):
        report["video"] = navigator_output["video"]

    return report


# ---------------------------------------------------------------------------
# Phase 2: LLM-Based Per-Page Score Reconciliation
# ---------------------------------------------------------------------------


def _build_reconciliation_prompt(
    page_id: str,
    text_page: dict | None,
    visual_page: dict | None,
    network_verification: dict,
    rubric_text: str,
    pb_rubric_text: str,
    availability: str,
) -> str:
    """Build the LLM prompt for reconciling scores on one page."""

    if availability == "both":
        mode_instructions = (
            "You have BOTH text-scorer and visual-scorer results for this page.\n"
            "When the two scorers agree, keep their shared result with confidence: high.\n"
            "When they disagree, apply these rules:\n"
            "  - For spatial/visual criteria (layout, positioning, colours, contrast): trust the visual scorer.\n"
            "  - For behavioural criteria (redirects, form submissions, data flow): trust the text scorer.\n"
            "  - If a deal-breaker criterion has any FAIL, set reconciled to FAIL and flag it.\n"
            "  - Set confidence to medium when you override one scorer.\n"
            "  - When one scorer says PASS/FAIL and the other says UNKNOWN, trust the one with a definitive result (confidence: medium).\n"
            "  - When both say UNKNOWN, keep UNKNOWN with confidence: low.\n"
        )
    elif availability == "text_only":
        mode_instructions = (
            "You have ONLY text-scorer results (no visual scorer) for this page.\n"
            "Trust the text scorer results. Set confidence to medium for text-based criteria,\n"
            "and low for criteria that really need visual confirmation.\n"
        )
    elif availability == "visual_only":
        mode_instructions = (
            "You have ONLY visual-scorer results (no text scorer) for this page.\n"
            "Trust the visual scorer results. Set confidence to medium for visual-based criteria,\n"
            "and low for criteria that really need behavioural/text confirmation.\n"
        )
    else:
        mode_instructions = "No scorer results available. Return UNKNOWN for all criteria.\n"

    text_json = json.dumps(text_page, indent=2) if text_page else "null"
    visual_json = json.dumps(visual_page, indent=2) if visual_page else "null"

    net_issues = network_verification.get("issues", [])
    net_deal_breakers = network_verification.get("deal_breakers", [])
    network_context = (
        f"Network issues: {json.dumps(net_issues)}\n"
        f"Network deal-breakers: {json.dumps(net_deal_breakers)}"
    )

    prompt = f"""You are a QA score reconciler. Reconcile the scoring results for page "{page_id}".

## Mode
{mode_instructions}

## Reconciliation Rules Summary
| Text     | Visual   | Reconciled              | Confidence |
|----------|----------|-------------------------|------------|
| PASS     | PASS     | PASS                    | high       |
| FAIL     | FAIL     | FAIL                    | high       |
| PASS     | FAIL     | LLM decides (spatial->visual, behavioural->text) | medium |
| FAIL     | PASS     | LLM decides (spatial->visual, behavioural->text) | medium |
| scored   | UNKNOWN  | Trust scored one        | medium     |
| UNKNOWN  | scored   | Trust scored one        | medium     |
| UNKNOWN  | UNKNOWN  | UNKNOWN                 | low        |
| one-scorer-only | - | Trust that scorer       | medium     |
| Disagree on deal-breaker | - | FAIL + flag    | low        |

## Text Scorer Results
{text_json}

## Visual Scorer Results
{visual_json}

## Network Verification Context
{network_context}

## Consumer Rubric
{rubric_text}

## PB Feature Rubric
{pb_rubric_text}

## Output Format

Return a single JSON object with exactly three top-level keys:
- `pb_criteria`: array of objects, each with: feature, criterion, text_result, visual_result, reconciled (PASS/FAIL/UNKNOWN), confidence (high/medium/low), evidence, discrepancy (string or null)
- `consumer_criteria`: array of objects, each with: criterion, text_result, visual_result, reconciled (PASS/FAIL/UNKNOWN), confidence (high/medium/low), evidence, discrepancy (string or null)
- `deal_breakers`: array of strings listing any triggered deal-breakers (empty array if none)

Include ALL criteria from both scorers (deduplicated by criterion text).
For each criterion, set `discrepancy` to a short explanation if the two scorers disagreed, otherwise null.

Output ONLY the JSON object. No preamble, no explanation outside the JSON.
"""
    return prompt


def _parse_reconciliation_response(raw_text: str) -> dict | None:
    """
    Parse the LLM JSON response for reconciliation.

    Attempts:
    1. Direct json.loads()
    2. Extract from markdown code block
    Returns None on failure.
    """
    stripped = raw_text.strip()

    # Attempt 1: direct JSON parse
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: extract from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _fallback_page(
    page_id: str,
    text_page: dict | None,
    visual_page: dict | None,
) -> dict:
    """Fallback when LLM reconciliation fails. Preserves scorer agreements.

    When both scorers agree on a criterion (both PASS or both FAIL),
    the agreement is preserved with high confidence. Disagreements and
    single-scorer results are set to UNKNOWN with low confidence.
    """
    # Index scorer results by criterion key
    text_pb: dict[str, dict] = {}
    text_con: dict[str, dict] = {}
    visual_pb: dict[str, dict] = {}
    visual_con: dict[str, dict] = {}

    if text_page and isinstance(text_page, dict):
        for c in text_page.get("pb_criteria", []):
            key = f"{c.get('feature', '')}:{c.get('criterion', '')}"
            text_pb[key] = c
        for c in text_page.get("consumer_criteria", []):
            text_con[c.get("criterion", "")] = c

    if visual_page and isinstance(visual_page, dict):
        for c in visual_page.get("pb_criteria", []):
            key = f"{c.get('feature', '')}:{c.get('criterion', '')}"
            visual_pb[key] = c
        for c in visual_page.get("consumer_criteria", []):
            visual_con[c.get("criterion", "")] = c

    pb_criteria: list[dict] = []
    for key in set(text_pb.keys()) | set(visual_pb.keys()):
        t = text_pb.get(key)
        v = visual_pb.get(key)
        t_result = t["result"] if t else None
        v_result = v["result"] if v else None
        ref = t or v

        if t_result and v_result and t_result == v_result and t_result != "UNKNOWN":
            pb_criteria.append({
                "feature": ref.get("feature", "unknown"),
                "criterion": ref.get("criterion", ""),
                "text_result": t_result,
                "visual_result": v_result,
                "reconciled": t_result,
                "confidence": "high",
                "evidence": f"Fallback: both scorers agree {t_result}",
                "discrepancy": None,
            })
        else:
            pb_criteria.append({
                "feature": ref.get("feature", "unknown"),
                "criterion": ref.get("criterion", ""),
                "text_result": t_result or "UNKNOWN",
                "visual_result": v_result or "UNKNOWN",
                "reconciled": "UNKNOWN",
                "confidence": "low",
                "evidence": "Fallback: LLM reconciliation failed, scorers disagreed or unavailable",
                "discrepancy": "LLM reconciliation unavailable",
            })

    consumer_criteria: list[dict] = []
    for key in set(text_con.keys()) | set(visual_con.keys()):
        t = text_con.get(key)
        v = visual_con.get(key)
        t_result = t["result"] if t else None
        v_result = v["result"] if v else None
        ref = t or v

        if t_result and v_result and t_result == v_result and t_result != "UNKNOWN":
            consumer_criteria.append({
                "criterion": ref.get("criterion", ""),
                "text_result": t_result,
                "visual_result": v_result,
                "reconciled": t_result,
                "confidence": "high",
                "evidence": f"Fallback: both scorers agree {t_result}",
                "discrepancy": None,
            })
        else:
            consumer_criteria.append({
                "criterion": ref.get("criterion", ""),
                "text_result": t_result or "UNKNOWN",
                "visual_result": v_result or "UNKNOWN",
                "reconciled": "UNKNOWN",
                "confidence": "low",
                "evidence": "Fallback: LLM reconciliation failed",
                "discrepancy": "LLM reconciliation unavailable",
            })

    return {
        "page_id": page_id,
        "pb_criteria": pb_criteria,
        "consumer_criteria": consumer_criteria,
        "deal_breakers": [],
    }


async def _reconcile_page(
    page_id: str,
    text_page: dict | None,
    visual_page: dict | None,
    network_verification: dict,
    rubric_text: str,
    pb_rubric_text: str,
    availability: str,
    llm=None,
) -> dict:
    """Reconcile scores for one page via LLM.

    Falls back to _fallback_page() when LLM is unavailable,
    availability is 'neither', or LLM response cannot be parsed.
    """
    if availability == "neither" or llm is None:
        return _fallback_page(page_id, text_page, visual_page)

    prompt = _build_reconciliation_prompt(
        page_id=page_id,
        text_page=text_page,
        visual_page=visual_page,
        network_verification=network_verification,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        availability=availability,
    )

    try:
        response = await llm.ainvoke(prompt)
        raw_text: str = response.content if hasattr(response, "content") else str(response)
    except Exception:
        logger.exception("LLM call failed for page %s, using fallback", page_id)
        return _fallback_page(page_id, text_page, visual_page)

    parsed = _parse_reconciliation_response(raw_text)
    if parsed is None:
        logger.warning("Failed to parse LLM response for page %s, using fallback", page_id)
        return _fallback_page(page_id, text_page, visual_page)

    # Ensure text_result and visual_result exist on every criterion
    for criteria_list_key in ("pb_criteria", "consumer_criteria"):
        for c in parsed.get(criteria_list_key, []):
            c.setdefault("text_result", "UNKNOWN")
            c.setdefault("visual_result", "UNKNOWN")

    return {
        "page_id": page_id,
        "pb_criteria": parsed.get("pb_criteria", []),
        "consumer_criteria": parsed.get("consumer_criteria", []),
        "deal_breakers": parsed.get("deal_breakers", []),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def reconcile_scores(
    text_scores: list[dict] | dict,
    visual_scores: list[dict] | dict,
    network_verification: dict,
    navigator_output: dict,
    manifest: dict | None,
    rubric_text: str,
    pb_rubric_text: str,
    llm=None,
) -> dict:
    """Reconcile text, visual, and network scores into a final report.

    Orchestrates Phase 1 (deterministic pre-processing), Phase 2
    (LLM per-page reconciliation), and Phase 3 (assemble final report).

    Timing is owned by the caller (pipeline.py). This function does not
    track elapsed time.
    """
    # --- Phase 1: Deterministic pre-processing ---
    manifest_coverage = _check_manifest_coverage(navigator_output, manifest)
    verification_tasks = _evaluate_verification_tasks(navigator_output, manifest)
    availability = _classify_scorer_availability(text_scores, visual_scores)

    # Build page lookups from scorer outputs
    text_by_page: dict[str, dict] = {}
    visual_by_page: dict[str, dict] = {}

    if isinstance(text_scores, list):
        for page in text_scores:
            pid = page.get("page_id", "")
            if pid:
                text_by_page[pid] = page

    if isinstance(visual_scores, list):
        for page in visual_scores:
            pid = page.get("page_id", "")
            if pid:
                visual_by_page[pid] = page

    # Collect all unique page IDs from both scorers
    all_page_ids: list[str] = []
    seen_ids: set[str] = set()
    for pid in list(text_by_page.keys()) + list(visual_by_page.keys()):
        if pid not in seen_ids:
            all_page_ids.append(pid)
            seen_ids.add(pid)

    # --- Phase 2: LLM per-page reconciliation (parallel) ---
    tasks = []
    for pid in all_page_ids:
        tasks.append(
            _reconcile_page(
                page_id=pid,
                text_page=text_by_page.get(pid),
                visual_page=visual_by_page.get(pid),
                network_verification=network_verification,
                rubric_text=rubric_text,
                pb_rubric_text=pb_rubric_text,
                availability=availability,
                llm=llm,
            )
        )

    reconciled_pages_raw = await asyncio.gather(*tasks)

    # Merge navigator observations and features_detected into reconciled pages,
    # and rename page_id to id for final schema
    nav_pages_by_id: dict[str, dict] = {}
    for nav_page in navigator_output.get("pages", []):
        nav_pages_by_id[nav_page.get("id", "")] = nav_page

    reconciled_pages: list[dict] = []
    for rp in reconciled_pages_raw:
        pid = rp.pop("page_id", "unknown")
        rp["id"] = pid

        # Merge navigator observations
        nav_page = nav_pages_by_id.get(pid, {})
        if nav_page.get("observations"):
            rp["observations"] = nav_page["observations"]
        if nav_page.get("url_visited"):
            rp["url_visited"] = nav_page["url_visited"]

        # Merge features_detected from visual scorer
        visual_page = visual_by_page.get(pid)
        if visual_page and visual_page.get("features_detected"):
            rp["features_detected"] = visual_page["features_detected"]

        reconciled_pages.append(rp)

    # --- Phase 3: Assemble final report ---
    report = _assemble_final_report(
        navigator_output=navigator_output,
        reconciled_pages=reconciled_pages,
        network_verification=network_verification,
        manifest_coverage=manifest_coverage,
        verification_tasks=verification_tasks,
        elapsed_seconds=0,  # caller (pipeline.py) overwrites with real elapsed
    )

    return report
