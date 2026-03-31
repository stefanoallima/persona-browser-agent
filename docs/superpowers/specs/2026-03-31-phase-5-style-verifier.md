# Phase 5: Style Verifier — Deterministic Design Token Verification

**Date**: 2026-03-31
**Status**: SPEC — BLOCKED (CDP timing: navigator closes browser before scorers run; needs browser lifecycle decision)
**Depends on**: Phase 4 (pipeline complete), Phase 2 (navigator CDP access)
**Source**: Project Prism white-box/black-box convergence concept + `brown_prism-cro-enhancements_01`

---

## Goal

Replace LLM-based visual checks for design tokens (colors, fonts, spacing) with deterministic CDP-based math. The visual scorer currently asks an LLM "does the button color match #3B82F6?" — CDP's `CSS.getComputedStyleForNode` gives the exact answer in <15ms for $0.00.

Visual scorer keeps handling: spatial layout, visual hierarchy, aesthetic quality, screenshot-based assessments. Style verifier handles: exact CSS value comparisons.

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module type | Deterministic Python (like network_verifier) | No LLM needed for CSS value comparison |
| Runs when | In parallel with scorers (Phase 2 of pipeline) | Same pattern as network_verifier |
| CDP access | Connect to PB's Chrome via `cdp_port` from navigator output | Same Chrome instance, same rendered state |
| Codeintel required | Yes — needs `design_tokens` from codeintel.json | Without tokens, nothing to compare against |
| Failure mode | Skip gracefully — style verification is supplementary | Visual scorer still covers these checks (less precisely) |

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `persona_browser/style_verifier.py` | CDP-based computed style extraction + comparison |
| `tests/test_style_verifier.py` | Unit tests (mocked CDP responses) |
| `schemas/style-verifier-output.schema.json` | Output schema |
| `fixtures/sample_style_verifier_output.json` | Test fixture |

### Modified Files

| File | Change |
|------|--------|
| `persona_browser/scorer_runner.py` | Add style_verifier to parallel execution |
| `persona_browser/pipeline.py` | Pass style_verifier results to reconciler |
| `persona_browser/score_reconciler.py` | Integrate style verification into reconciliation |
| `schemas/final-report.schema.json` | Add `style_verification` section |

---

## Module: `style_verifier.py`

### Public API

```python
async def verify_styles(
    navigator_output: dict,    # Pages with URLs
    codeintel: dict,           # design_tokens per page
    cdp_port: int,             # Chrome CDP port from navigator
) -> dict:
    """Verify computed CSS values against codeintel design tokens.

    Connects to Chrome via CDP, navigates to each page URL,
    extracts computed styles for key elements, compares against
    codeintel.pages[].design_tokens.

    Returns dict matching schemas/style-verifier-output.schema.json.
    """
```

### What It Checks

For each page in codeintel that has `design_tokens`:

| Token | CDP Method | Comparison |
|-------|-----------|------------|
| `primary_color` | `CSS.getComputedStyleForNode` on primary CTA → `color` or `background-color` | Exact hex match (normalize rgb→hex) |
| `error_color` | Computed style on error elements (if visible) | Exact hex match |
| `font_family` | Computed `font-family` on body or main content | Contains expected font name |
| `border_radius` | Computed `border-radius` on card/button elements | Within 2px tolerance |
| `spacing` | `DOM.getBoxModel` for margin/padding between elements | Within 4px tolerance |

### Element Selection

Uses codeintel `pages[].elements` to identify which DOM nodes to check:
- Forms → check submit button for primary_color, input fields for border_radius
- Navigation → check nav container for font_family
- CTA → check primary CTA for primary_color, font_family

Fallback: if codeintel doesn't specify selectors, use heuristic CSS selectors (`button[type=submit]`, `nav`, `.cta`, `[role=alert]`).

### Output Schema

```json
{
  "status": "DONE",
  "pages_checked": 2,
  "tokens_checked": 8,
  "tokens_matched": 7,
  "tokens_mismatched": 1,
  "per_page": [
    {
      "page_id": "registration",
      "url": "http://localhost:3000/register",
      "checks": [
        {
          "token": "primary_color",
          "expected": "#3B82F6",
          "actual": "#3B82F6",
          "element": "button[type=submit]",
          "property": "background-color",
          "match": true
        },
        {
          "token": "font_family",
          "expected": "Inter",
          "actual": "Inter, sans-serif",
          "element": "body",
          "property": "font-family",
          "match": true
        }
      ]
    }
  ],
  "mismatches": [
    {
      "page_id": "registration",
      "token": "border_radius",
      "expected": "8px",
      "actual": "4px",
      "element": "input[name=email]",
      "property": "border-radius",
      "delta": "4px"
    }
  ]
}
```

### Integration with Score Reconciler

Style verification results feed into the reconciler as supplementary evidence:
- When visual scorer says "button color matches design" (PASS) and style_verifier confirms exact hex match → confidence elevated to "high" (math-verified)
- When visual scorer says PASS but style_verifier shows mismatch → discrepancy flagged, reconciler investigates
- When visual scorer says UNKNOWN on a color criterion → style_verifier result used directly

This does NOT replace the visual scorer — it supplements it with deterministic evidence for token-verifiable checks.

### Graceful Degradation

| Failure | Behavior |
|---------|----------|
| CDP connection fails | Skip style verification, proceed without. Flag in report. |
| Codeintel has no design_tokens | Skip — nothing to verify. |
| Element not found in DOM | Skip that check, note "element not found". |
| Page navigation fails | Skip that page, check remaining pages. |

---

## Test Strategy (~10 tests)

- `test_color_exact_match` — RGB(59,130,246) matches #3B82F6
- `test_color_mismatch` — RGB(34,197,94) does not match #3B82F6
- `test_font_family_contains` — "Inter, sans-serif" matches "Inter"
- `test_border_radius_within_tolerance` — 7px passes for expected 8px (2px tolerance)
- `test_border_radius_outside_tolerance` — 4px fails for expected 8px
- `test_missing_element` — skip with note, don't fail
- `test_no_design_tokens` — return empty results, status DONE
- `test_cdp_connection_failure` — return error status, graceful skip
- `test_multiple_pages` — verify per-page isolation
- `test_output_matches_schema` — validate against style-verifier-output.schema.json

---

## Cost

$0.00 per run (deterministic). Saves ~$0.01-0.03 per gate by offloading color/font/spacing checks from visual scorer's LLM context.
