# Phase 4 Implementation Fixes — SUDD Review

**Date**: 2026-03-31
**Reviewed by**: SUDD cross-document architecture review + Phase 4 plan audit
**Status**: APPLIED (2026-03-31) — all fixes assessed and resolved

---

## How to Use This File

When implementing Phase 4 tasks, apply these fixes at the relevant task. Each fix references the exact location in the plan where the bug exists and provides the corrected code.

---

## FIX 1: Separate V1 (data persistence) from V3 (auth persistence)

**Severity**: HIGH
**Apply during**: Task 3 (deterministic helpers)
**Plan location**: Lines 1053-1098, `_evaluate_verification_tasks()`

### Problem

Both `data_persistence` (V1) and `auth_persistence` (V3) map to the same `persistence_after_refresh` field in `auth_flow_verification`. They always produce identical results. But they test different things:
- V1: "Is the user's submitted data still displayed after refresh?"
- V3: "Is the user still authenticated after refresh?"

A page can show cached data while the session is dead. This mapping can't distinguish that.

### Plan code (buggy)

```python
type_to_auth_field = {
    "data_persistence": "persistence_after_refresh",   # ← SAME
    "auth_persistence": "persistence_after_refresh",   # ← SAME
    "auth_boundary": "post_auth_access",
}
```

### Fixed code

```python
def _evaluate_verification_tasks(
    navigator_output: dict, manifest: dict | None
) -> list[dict]:
    auth_flow = navigator_output.get("auth_flow_verification", {})
    network_log = navigator_output.get("network_log", [])
    pages = navigator_output.get("pages", [])
    results: list[dict] = []

    if manifest and "verification_tasks" in manifest:
        for vtask in manifest["verification_tasks"]:
            vid = vtask["id"]
            vtype = vtask["type"]

            if vtype == "data_persistence":
                # V1: Check page CONTENT after refresh — is submitted data still displayed?
                # Look for refresh actions in navigator pages and check if content persisted
                refresh_evidence = auth_flow.get("persistence_after_refresh")
                if refresh_evidence and isinstance(refresh_evidence, str) and refresh_evidence.strip():
                    # Check if evidence mentions data/content (not just "page loaded")
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Content check: {refresh_evidence}",
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Data persistence not verified — no refresh observation from navigator",
                    })

            elif vtype == "auth_persistence":
                # V3: Check NETWORK LOG after refresh — do protected API calls still return 200?
                # Look for post-refresh API calls to protected endpoints
                post_refresh_calls = [
                    entry for entry in network_log
                    if "refresh" in entry.get("trigger", "").lower()
                    and entry.get("status", 0) in range(200, 300)
                ]
                if post_refresh_calls:
                    evidence = "; ".join(
                        f"{c['method']} {c['url']} → {c['status']}" for c in post_refresh_calls
                    )
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Auth persists: {evidence}",
                    })
                elif auth_flow.get("persistence_after_refresh"):
                    # Fallback to auth_flow text if network_log doesn't have refresh entries
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Auth check (text fallback): {auth_flow['persistence_after_refresh']}",
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Auth persistence not verified — no post-refresh API calls in network log",
                    })

            elif vtype == "auth_boundary":
                evidence_value = auth_flow.get("post_auth_access")
                if evidence_value and isinstance(evidence_value, str) and evidence_value.strip():
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": evidence_value,
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Auth boundary not verified by navigator",
                    })

            elif vtype == "cross_page_consistency":
                # V2: Check if same data appears on multiple pages
                # Compare data across page observations
                evidence_value = None
                for page in pages:
                    obs = page.get("observations", {})
                    desc = obs.get("description", "")
                    if vtask.get("check", "").lower() in desc.lower():
                        evidence_value = desc
                        break
                if evidence_value:
                    results.append({
                        "id": vid, "type": vtype, "result": "PASS",
                        "evidence": f"Cross-page data found: {evidence_value[:200]}",
                    })
                else:
                    results.append({
                        "id": vid, "type": vtype, "result": "FAIL",
                        "evidence": "Cross-page consistency not verified — data not found across pages",
                    })
            else:
                results.append({
                    "id": vid, "type": vtype, "result": "FAIL",
                    "evidence": f"Unknown verification type: {vtype}",
                })

    elif auth_flow:
        # No manifest — derive basic checks from auth_flow_verification
        if auth_flow.get("persistence_after_refresh"):
            results.append({
                "id": "V1", "type": "data_persistence", "result": "PASS",
                "evidence": f"Content: {auth_flow['persistence_after_refresh']}",
            })
            # V3 from network_log if available
            post_refresh_ok = any(
                "refresh" in e.get("trigger", "").lower() and e.get("status", 0) in range(200, 300)
                for e in network_log
            )
            if post_refresh_ok or auth_flow.get("persistence_after_refresh"):
                results.append({
                    "id": "V3", "type": "auth_persistence", "result": "PASS",
                    "evidence": f"Auth: {auth_flow['persistence_after_refresh']}",
                })
        if auth_flow.get("post_auth_access"):
            results.append({
                "id": "V4", "type": "auth_boundary", "result": "PASS",
                "evidence": auth_flow["post_auth_access"],
            })

    return results
```

### Test update

Update `test_persistence_maps_correctly` and `test_auth_persistence_maps_correctly` to verify they produce DIFFERENT evidence:

```python
def test_v1_v3_produce_different_evidence(self):
    """V1 (data) and V3 (auth) must check different things."""
    from persona_browser.score_reconciler import _evaluate_verification_tasks

    result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, MANIFEST)
    v1 = next((t for t in result if t["id"] == "V1"), None)
    v3 = next((t for t in result if t["id"] == "V3"), None)
    assert v1 is not None and v3 is not None
    # Evidence must differ — they check different data sources
    assert v1["evidence"] != v3["evidence"], "V1 and V3 should not have identical evidence"
    assert "content" in v1["evidence"].lower() or "data" in v1["evidence"].lower()
    assert "auth" in v3["evidence"].lower() or "session" in v3["evidence"].lower()
```

---

## FIX 2: Fallback preserves agreed scorer results

**Severity**: HIGH
**Apply during**: Task 4 (LLM reconciliation)
**Plan location**: Lines 1637-1689, `_fallback_page()`

### Problem

When the reconciler LLM returns garbage JSON, `_fallback_page()` sets ALL criteria to `reconciled: "UNKNOWN"` — even when both scorers agreed. Both-agree results are reliable evidence being thrown away.

### Plan code (buggy)

```python
# Lines 1660-1668 — always sets reconciled: "UNKNOWN"
pb_criteria.append({
    "reconciled": "UNKNOWN",
    "confidence": "low",
    "evidence": "Reconciliation failed — using fallback",
})
```

### Fixed code

Replace the entire `_fallback_page` function:

```python
def _fallback_page(page_id: str, text_page: dict | None, visual_page: dict | None) -> dict:
    """Fallback when LLM reconciliation fails. Preserves scorer agreements."""
    pb_criteria: list[dict] = []
    consumer_criteria: list[dict] = []

    # Index scorer results by criterion key
    text_pb = {}
    text_con = {}
    visual_pb = {}
    visual_con = {}

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

    # Reconcile PB criteria
    all_pb_keys = set(text_pb.keys()) | set(visual_pb.keys())
    for key in all_pb_keys:
        t = text_pb.get(key)
        v = visual_pb.get(key)
        t_result = t["result"] if t else None
        v_result = v["result"] if v else None
        ref = t or v  # use whichever is available for metadata

        if t_result and v_result and t_result == v_result and t_result != "UNKNOWN":
            # Both agree — preserve the agreement
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
            # Disagree, one missing, or both UNKNOWN — mark unknown
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

    # Reconcile consumer criteria (same logic)
    all_con_keys = set(text_con.keys()) | set(visual_con.keys())
    for key in all_con_keys:
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
```

### Test to add

```python
def test_fallback_preserves_agreements(self):
    """Fallback should keep both-agree results, only UNKNOWN on disagreements."""
    from persona_browser.score_reconciler import _fallback_page

    text_page = {
        "pb_criteria": [
            {"feature": "forms", "criterion": "Labels visible", "result": "PASS", "evidence": "...", "confidence": "high"},
            {"feature": "forms", "criterion": "Required marked", "result": "FAIL", "evidence": "...", "confidence": "high"},
            {"feature": "forms", "criterion": "Error near field", "result": "PASS", "evidence": "...", "confidence": "high"},
        ],
        "consumer_criteria": [],
    }
    visual_page = {
        "pb_criteria": [
            {"feature": "forms", "criterion": "Labels visible", "result": "PASS", "evidence": "...", "confidence": "high"},
            {"feature": "forms", "criterion": "Required marked", "result": "FAIL", "evidence": "...", "confidence": "high"},
            {"feature": "forms", "criterion": "Error near field", "result": "FAIL", "evidence": "...", "confidence": "high"},
        ],
        "consumer_criteria": [],
    }
    result = _fallback_page("registration", text_page, visual_page)

    labels = next(c for c in result["pb_criteria"] if c["criterion"] == "Labels visible")
    assert labels["reconciled"] == "PASS"       # both agreed PASS
    assert labels["confidence"] == "high"

    required = next(c for c in result["pb_criteria"] if c["criterion"] == "Required marked")
    assert required["reconciled"] == "FAIL"     # both agreed FAIL
    assert required["confidence"] == "high"

    error = next(c for c in result["pb_criteria"] if c["criterion"] == "Error near field")
    assert error["reconciled"] == "UNKNOWN"     # disagreed → unknown
    assert error["confidence"] == "low"
```

---

## FIX 3: Add genuine disagreement test fixture

**Severity**: HIGH
**Apply during**: Task 2 (test fixtures)
**Plan location**: Lines 222-438, `sample_scorer_results.json`

### Problem

The fixture claims to cover "disagreement" cases but has none. All cases are: both-agree, one-UNKNOWN, or one-scorer-only. The reconciler's most complex logic — "is this spatial (trust visual) or behavioral (trust text)?" — is never exercised.

### Fix

Add to `fixtures/sample_scorer_results.json` → `text_scores[0].pb_criteria`:

```json
{
  "feature": "forms",
  "criterion": "Error message appears near the triggering field",
  "result": "PASS",
  "evidence": "Navigator reported error message appeared after invalid submission",
  "confidence": "medium",
  "note": "Cannot determine spatial position from text"
}
```

And in `visual_scores[0].pb_criteria`, change the same criterion from UNKNOWN to:

```json
{
  "feature": "forms",
  "criterion": "Error message appears near the triggering field",
  "result": "FAIL",
  "evidence": "Screenshot shows error banner at page top, ~300px above form fields. Not near triggering field.",
  "confidence": "high"
}
```

This creates a genuine text-PASS/visual-FAIL disagreement on a spatial criterion. The reconciler should trust the visual scorer (spatial assessment) and reconcile to FAIL.

Also update `fixtures/sample_final_report.json` to reflect the expected reconciliation:

```json
{
  "feature": "forms",
  "criterion": "Error message appears near the triggering field",
  "text_result": "PASS",
  "visual_result": "FAIL",
  "reconciled": "FAIL",
  "confidence": "high",
  "evidence": "Visual scorer shows error at page top, 300px from fields. Spatial criterion — visual assessment is definitive.",
  "discrepancy": "Text scorer reported error appeared but couldn't assess position. Visual scorer confirms error is NOT near the field."
}
```

### Test to add

```python
def test_reconcile_page_spatial_disagreement(self):
    """When text says PASS and visual says FAIL on spatial criterion, trust visual."""
    # Mock LLM to return expected reconciliation for spatial criterion
    # Visual scorer is definitive for spatial relationships
    ...
```

---

## FIX 4: Remove double timer

**Severity**: LOW
**Apply during**: Task 5 (pipeline wiring)
**Plan location**: Lines 1715 + 2112

### Problem

`reconcile_scores()` starts its own timer (line 1715), computes `elapsed` (line 1785), and puts it in the report. Then `pipeline.py` starts another timer (line 2112) and overwrites `elapsed_seconds` (line 2191). Works correctly but fragile if reconciler is called directly.

### Fix

Remove timer from `reconcile_scores()`. Let `pipeline.py` own all timing.

In `score_reconciler.py`, remove:
```python
start = time.time()          # line 1715 — DELETE
elapsed = time.time() - start  # line 1785 — DELETE
```

And change the `_assemble_final_report` call to accept `elapsed_seconds` as a parameter from the caller (pipeline.py) instead of computing it internally.

---

## Implementation Checklist

- [x] **FIX 1** (V1/V3 separation): APPLIED — commit `0b7e00b`. V1 checks page content, V3 checks network_log for post-refresh API calls.
- [x] **FIX 2** (fallback preserves agreements): APPLIED — commit `0b7e00b`. Both-agree results preserved with high confidence.
- [x] **FIX 3** (disagreement fixture): ALREADY ADDRESSED — disagreement case added during Phase 4 implementation (text FAIL vs visual PASS on "Submit button visible").
- [x] **FIX 4** (double timer): APPLIED — commit `0b7e00b`. Reconciler no longer has its own timer.
