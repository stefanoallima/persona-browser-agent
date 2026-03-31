# Phase 5b: CDP Port Export + SPA Fallback + Spot Check Coverage

**Date**: 2026-03-31
**Status**: PARTIALLY IMPLEMENTED — Item 3 (Spot Check Coverage) done. Items 1-2 blocked on browser lifecycle decision.
**Depends on**: Phase 4 (pipeline complete)
**Source**: `docs/pb-fixes-from-cross-review.md` (L4, M2) + `docs/sudd_feedback.md`

---

## Goal

Three small, independent improvements to the existing pipeline. Each is a surgical edit, not a redesign.

---

## 1. CDP Port in Navigator Output

### Problem
SUDD's gate (Step 2b) needs to pass PB's Chrome CDP port to ux-tester for Playwright-over-CDP connection. The architecture specifies `cdp_port` in the output but the pipeline doesn't write it.

### Fix

**File**: `persona_browser/pipeline.py`

After navigator runs, extract the CDP port from the BrowserSession and include it in the report:

```python
# In run_pipeline(), after navigator completes:
cdp_port = None
if hasattr(navigator_session, 'cdp_url'):
    # Extract port from CDP URL (e.g., "http://localhost:9222" → 9222)
    from urllib.parse import urlparse
    parsed = urlparse(navigator_session.cdp_url)
    cdp_port = parsed.port

# Include in final report
final_report["cdp_port"] = cdp_port
```

**File**: `schemas/final-report.schema.json` — add `cdp_port` field (integer, nullable).

**Test**: `test_pipeline.py` — verify `cdp_port` present in output when browser session has CDP URL.

---

## 2. SPA Fallback: CDP DOM Mutation Signals

### Problem
`output_parser.py` page grouping uses `model_thoughts()` text to detect "new page context" when URLs don't change in SPAs. This is LLM interpretation inside a supposedly deterministic parser.

### Fix

**File**: `persona_browser/output_parser.py`

Supplement URL-based page grouping with CDP `DOM.documentUpdated` events as a primary SPA page-change signal.

```python
# During navigation, register CDP event listener
# (requires access to CDP session — pass through from BrowserSession)

class PageGrouper:
    def __init__(self, history, manifest=None, dom_events=None):
        self.history = history
        self.manifest = manifest
        self.dom_events = dom_events or []  # list of {timestamp, event_type}

    def group_pages(self):
        # Primary: URL changes
        # Secondary (SPA): DOM.documentUpdated events at timestamps between steps
        # Tertiary (fallback): model_thoughts() content-change detection
        ...
```

**Where DOM events come from**: During navigator execution, register a CDP listener for `DOM.documentUpdated`. Record timestamps. Pass the event list to `output_parser.py` alongside the `AgentHistoryList`.

**File**: `persona_browser/agent.py` — register `DOM.documentUpdated` listener on CDP session, collect events, pass to output parser.

**Graceful fallback**: If DOM events aren't available (CDP session closed, listener failed), fall back to existing `model_thoughts()` heuristic. No regression.

**Tests**:
- `test_spa_page_grouping_with_dom_events` — DOM event at T=5.2s splits pages even though URL stayed same
- `test_spa_fallback_without_dom_events` — falls back to model_thoughts when no events available
- `test_url_change_takes_precedence` — URL change creates new page even without DOM event

---

## 3. Spot Check Coverage Metric

### Problem
SUDD's ux-tester spot check only covers Playwright-verifiable criteria. If PB hallucinations happen on non-verifiable criteria (spatial, color, subjective), the spot check is blind. There's no metric showing this gap.

### Fix

**File**: `persona_browser/score_reconciler.py` — add `spot_check_eligibility` to output

In `_compute_summary()`, classify each criterion as Playwright-verifiable or not:

```python
VERIFIABLE_FEATURES = {"element_count", "visibility", "text_content", "form_submission", "element_existence", "link_targets"}
NON_VERIFIABLE_FEATURES = {"spatial_relationship", "color_match", "visual_hierarchy", "subjective_ux"}

def _compute_spot_check_eligibility(reconciled_pages):
    total = 0
    verifiable = 0
    non_verifiable_list = []
    for page in reconciled_pages:
        for c in page.get("pb_criteria", []) + page.get("consumer_criteria", []):
            total += 1
            criterion = c.get("criterion", "").lower()
            # Heuristic: spatial/color/visual/aesthetic terms → non-verifiable
            if any(term in criterion for term in ["near", "color", "prominent", "hierarchy", "aesthetic", "readable", "contrast"]):
                non_verifiable_list.append(c.get("criterion", ""))
            else:
                verifiable += 1
    return {
        "total_criteria": total,
        "playwright_verifiable": verifiable,
        "non_verifiable": total - verifiable,
        "non_verifiable_criteria": non_verifiable_list,
    }
```

Add to final report `summary.spot_check_eligibility`.

SUDD's ux-tester can then report: "Spot check covered 4 of 12 verifiable criteria (33%). 6 criteria are non-verifiable (spatial/color)."

**Tests**:
- `test_spot_check_eligibility_classification` — spatial criteria classified as non-verifiable
- `test_spot_check_eligibility_all_verifiable` — simple form app → all verifiable

---

## Implementation Order

All three are independent:

```
1. CDP Port (smallest — 1 function + schema field)
2. Spot Check Coverage (small — 1 function + summary field)
3. SPA Fallback (medium — CDP listener + parser enhancement)
```

---

## Cost

All deterministic. $0.00 LLM cost.
