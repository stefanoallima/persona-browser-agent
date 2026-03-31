# PB Implementation Fixes — From Cross-Document Review

**Date**: 2026-03-31
**Source**: `sudd2/feedback_browser_use.md` (cross-document architecture review)
**Status**: PARTIALLY APPLIED (2026-03-31) — Phase 4 fixes done, remaining items deferred to Phase 6+

---

## Context

A cross-document review of the v3.1 architecture + Phase 4 implementation plan found 9 PB-repo issues. These are tracked here with implementation guidance so they don't get lost between sessions.

---

## HIGH — Fix During Implementation

### H2: V1 and V3 verification tasks map to same navigator field

**Phase**: 4 (Score Reconciler)
**File**: `persona_browser/score_reconciler.py` → `_evaluate_verification_tasks()`

**Problem**: Both `data_persistence` (V1) and `auth_persistence` (V3) map to `persistence_after_refresh`. They always produce the same result. But V1 tests "user data survives refresh" while V3 tests "auth session survives refresh." If the page shows cached data but the session is dead, this mapping can't distinguish them.

**Fix**: Navigator output needs separate observation fields:
- V1 check: "Is the user's submitted data still displayed after refresh?" → check page content
- V3 check: "Is the user still authenticated after refresh?" → check if protected API calls still return 200 (from network_log) or if page redirects to login

In `_evaluate_verification_tasks()`:
- V1 (`data_persistence`): verify from navigator observations that specific content (name, email) is still present
- V3 (`auth_persistence`): verify from network_log that post-refresh API calls to protected endpoints still return 200 (not 401)

### H3: Fallback discards agreed scorer results

**Phase**: 4 (Score Reconciler)
**File**: `persona_browser/score_reconciler.py` → `_fallback_page()`

**Problem**: When the reconciler LLM returns garbage JSON, `_fallback_page()` sets ALL criteria to `reconciled: "UNKNOWN"` — even when both scorers agreed (both PASS or both FAIL). This throws away reliable evidence.

**Fix**:
```python
def _fallback_page(self, text_scores, visual_scores):
    results = []
    for criterion in all_criteria:
        text = text_scores.get(criterion)
        visual = visual_scores.get(criterion)
        if text == visual and text is not None:
            # Both agree — preserve the agreement
            results.append({
                "criterion": criterion,
                "reconciled": text,  # both said the same thing
                "confidence": "high",
                "note": "Fallback: LLM reconciliation failed, preserving scorer agreement"
            })
        else:
            # Disagree or one missing — mark unknown
            results.append({
                "criterion": criterion,
                "reconciled": "UNKNOWN",
                "confidence": "low",
                "note": "Fallback: LLM reconciliation failed, scorers disagreed"
            })
    return results
```

### H4: Missing disagreement test case in fixtures

**Phase**: 3-4 (Scorers + Score Reconciler)
**File**: `golden-tests/` or `tests/fixtures/`

**Problem**: Test fixtures have both-agree, one-UNKNOWN, and one-scorer-only cases. But NO genuine disagreement (text PASS, visual FAIL on same criterion). The reconciler's most complex logic — "is this criterion spatial (trust visual) or behavioral (trust text)?" — is never tested.

**Fix**: Add to test fixtures:
```json
{
  "criterion": "Error message appears near the triggering field",
  "text_result": "UNKNOWN",
  "text_evidence": "Navigator reported error appeared but did not specify spatial position",
  "visual_result": "FAIL",
  "visual_evidence": "Screenshot shows error banner at page top, ~300px from fields",
  "expected_reconciled": "FAIL",
  "expected_confidence": "high",
  "expected_reasoning": "Spatial criterion — trust visual scorer"
}
```

Also add: text-PASS/visual-FAIL on non-spatial criterion (e.g., "form has required field markers") to test the behavioral-vs-spatial routing.

---

## MEDIUM — Fix During Implementation

### M2: Spot check coverage metric

**Phase**: 6 (SUDD gate integration) or Phase 4 (if adding to PB output)
**File**: ux-tester output format

**Problem**: Spot check only covers Playwright-verifiable criteria (element counts, visibility, text). Cannot verify spatial relationships, color, design compliance. If PB hallucinations happen on non-verifiable criteria, spot check won't catch them.

**Fix**: Add `spot_check_coverage_pct` to ux-tester output:
```json
{
  "spot_check_results": [...],
  "spot_check_coverage": {
    "total_pb_criteria": 18,
    "playwright_verifiable": 12,
    "checked": 4,
    "coverage_of_verifiable_pct": 33,
    "unverifiable_criteria": ["error near field", "button color matches design", "..."]
  }
}
```
This makes the spot check's blind spots transparent in the gate report.

---

## LOW — Fix Opportunistically

### L1: elapsed_seconds set by both reconciler and pipeline

**Phase**: 4
**File**: `persona_browser/score_reconciler.py`

**Problem**: `reconcile_scores()` starts a timer, then `pipeline.py` overwrites `elapsed_seconds` with its own timer. Works correctly but fragile if reconciler is called directly.

**Fix**: Remove timer from `reconcile_scores()`. Let `pipeline.py` own the timing.

### L4: SPA fallback heuristic — supplement with CDP DOM mutation

**Phase**: 2 (Navigator / output_parser.py)
**File**: `persona_browser/output_parser.py`

**Problem**: Page grouping uses `model_thoughts()` text to detect "new page context" when URLs don't change. This is LLM interpretation inside a supposedly deterministic parser.

**Fix**: Supplement with CDP DOM mutation signals. browser-use v0.12+ uses CDP — register `DOM.documentUpdated` event listener. When the entire DOM is replaced (SPA navigation), this fires reliably. Use as primary SPA page-change signal; fall back to `model_thoughts()` only if DOM events aren't available.

### L5: Phase 4 plan is code-heavy

**Phase**: Post-Phase 4

**Problem**: ~1200 lines of inline Python in the plan doc. Once implemented, plan diverges from repo immediately.

**Fix**: After Phase 4 implementation, archive the plan doc. Don't maintain it — the code is the source of truth. Add a note: "Implementation complete — see `persona_browser/` for current code."

### L6: Model names may be speculative

**Phase**: Before Phase 1

**Problem**: "GLM 5-turbo" and "Gemini 3 Flash" may not exist as exact model IDs at implementation time.

**Fix**: In arch v3.1, add capability requirements alongside each model name:

| Agent | Model | Capability Requirements |
|---|---|---|
| Text Scorer | GLM 5-turbo | Text-only, structured JSON output, <$0.01/call, >8K context |
| Visual Scorer | Gemini 3 Flash | Multimodal (vision), structured JSON output, <$0.05/call, image input |
| Score Reconciler | Sonnet | Strong reasoning, structured JSON output, <$0.15/call, >32K context |
| Navigator | Gemini Flash | Multimodal, browser-use compatible, <$0.08/call |

This way, if model names change, the capability spec tells you what to substitute.

---

## Implementation Status

```
DONE   Phase 4:  H2 (V1/V3 separation) — commit 0b7e00b
DONE   Phase 4:  H3 (fallback preserves agreements) — commit 0b7e00b
DONE   Phase 4:  L1 (timer cleanup) — commit 0b7e00b
DONE   Phase 3:  H4 (disagreement test fixture) — added during Phase 4 implementation

DEFERRED  Phase 2:  L4 (SPA fallback CDP supplement)
DEFERRED  Phase 6:  M2 (spot check coverage metric)
DEFERRED  L5 (archive plan doc — code is source of truth)
DEFERRED  L6 (capability requirements — model name validation)
```
