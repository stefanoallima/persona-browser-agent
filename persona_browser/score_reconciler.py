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
import re


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

    Maps auth_flow_verification fields to structured V1-V4 format.
    Uses manifest verification_tasks as the definitive list when present.
    """
    auth_flow = navigator_output.get("auth_flow_verification", {})
    results: list[dict] = []

    # Mapping from manifest verification_task types to auth_flow_verification fields
    type_to_auth_field = {
        "data_persistence": "persistence_after_refresh",
        "auth_persistence": "persistence_after_refresh",
        "auth_boundary": "post_auth_access",
    }

    if manifest and "verification_tasks" in manifest:
        for vtask in manifest["verification_tasks"]:
            vid = vtask["id"]
            vtype = vtask["type"]
            auth_field = type_to_auth_field.get(vtype)
            evidence_value = auth_flow.get(auth_field) if auth_field and auth_flow else None

            if evidence_value and isinstance(evidence_value, str) and evidence_value.strip():
                results.append({
                    "id": vid,
                    "type": vtype,
                    "result": "PASS",
                    "evidence": evidence_value,
                })
            else:
                results.append({
                    "id": vid,
                    "type": vtype,
                    "result": "FAIL",
                    "evidence": "Verification task not performed by navigator",
                })
    elif auth_flow:
        if auth_flow.get("persistence_after_refresh"):
            results.append({
                "id": "V1",
                "type": "data_persistence",
                "result": "PASS",
                "evidence": auth_flow["persistence_after_refresh"],
            })
            results.append({
                "id": "V3",
                "type": "auth_persistence",
                "result": "PASS",
                "evidence": auth_flow["persistence_after_refresh"],
            })
        if auth_flow.get("post_auth_access"):
            results.append({
                "id": "V4",
                "type": "auth_boundary",
                "result": "PASS",
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
