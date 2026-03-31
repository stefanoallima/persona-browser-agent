# Phase 6: Diff-Aware Retry Optimization

**Date**: 2026-03-31
**Status**: SPEC — DEFERRED (depends on sudd2 code-analyzer which doesn't exist yet; premature without retry usage data)
**Depends on**: Phase 4 (pipeline), Phase 5b (cdp_port export)
**Source**: Project Prism diff-aware targeting concept + `brown_prism-cro-enhancements_01`

---

## Goal

When SUDD retries a gate after code changes, PB currently re-tests ALL pages from scratch (30-90s navigator session). Most pages haven't changed. Diff-aware retry re-tests only changed pages and merges with cached results for unchanged pages. Saves 50-70% of retry time on multi-page apps.

---

## How It Works

```
Retry N:
  SUDD gate detects code changed since last PB run (git SHA differs)

  code-analyzer-reviewer generates manifest_diff:
    changed_pages: ["registration"]     ← code changed in RegisterPage.tsx
    unchanged_pages: ["dashboard", "settings"]  ← no code changes

  Gate calls PB with:
    persona-test --changed-pages "registration" --cache-dir "changes/{id}/browser-cache/{name}/"

  PB navigator:
    - Visits only changed pages (registration)
    - Skips unchanged pages (dashboard, settings)
    - Runs verification tasks that touch changed pages

  PB scorers + reconciler:
    - Score changed pages normally (fresh results)
    - Load cached results for unchanged pages
    - Merge into final report

  Result: 1 page tested instead of 3 → ~60% time saved
```

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Diff granularity | Page-level (not component-level) | Simpler, safer. If any file in a page's component tree changed, the whole page is re-tested. |
| Shared component changes | Mark ALL pages using that component as changed | Err on side of re-testing. Shared component change → could affect any page importing it. |
| Cache location | `changes/{id}/browser-cache/{persona}/` | Already specified in v3.1 architecture for partial retry support. |
| Cache invalidation | Git SHA mismatch OR codeintel changed | If code changed, cache is stale. Also if codeintel re-ran (code-analyzer found new things). |
| No cache on first run | Full test, save to cache | Cache only used on retries. First run is always complete. |

---

## File Changes

### persona-browser-agent repo

#### New/Modified

| File | Change |
|------|--------|
| `persona_browser/cli.py` | Add `--changed-pages` flag (comma-separated page IDs) and `--cache-dir` flag |
| `persona_browser/pipeline.py` | Support partial run: test changed pages, load cached for unchanged, merge results |
| `persona_browser/cache.py` | NEW: cache read/write for navigator output, scorer results, reconciled pages |
| `tests/test_cache.py` | NEW: cache round-trip tests |
| `tests/test_pipeline.py` | Add: `test_pipeline_partial_retry`, `test_pipeline_cache_merge` |

### sudd2 repo (SUDD-side, separate change)

| File | Change |
|------|--------|
| `sudd/agents/code-analyzer-reviewer.md` | Generate `manifest_diff` on retry (changed vs unchanged pages from git diff) |
| `sudd/commands/micro/gate.md` | Pass `--changed-pages` + `--cache-dir` on retry. Merge cached + new results in Step 2e. |

---

## Module: `cache.py`

### Public API

```python
def save_cache(
    cache_dir: str,
    navigator_output: dict,
    scorer_results: dict,
    reconciled_pages: list[dict],
    git_sha: str,
    codeintel_sha: str,
) -> None:
    """Save pipeline results to cache directory for potential reuse on retry."""

def load_cached_pages(
    cache_dir: str,
    page_ids: list[str],
    current_git_sha: str,
    current_codeintel_sha: str,
) -> dict | None:
    """Load cached results for specific pages.

    Returns None if:
    - Cache doesn't exist
    - Git SHA doesn't match (code changed since cache was written)
    - Codeintel SHA doesn't match

    Returns dict with:
    - navigator_pages: cached page observations for requested page_ids
    - scorer_pages: cached scorer results for requested page_ids
    - reconciled_pages: cached reconciled results for requested page_ids
    """

def is_cache_valid(cache_dir: str, current_git_sha: str, current_codeintel_sha: str) -> bool:
    """Check if cache exists and is valid for current code state."""
```

### Cache Structure

```
changes/{id}/browser-cache/{persona}/
  cache_meta.json       ← git_sha, codeintel_sha, timestamp
  navigator_output.json ← full navigator output
  scorer_results.json   ← text + visual + network verifier results
  reconciled_pages.json ← per-page reconciled results
  screenshots/          ← cached screenshots per page
```

---

## Pipeline Changes: `pipeline.py`

### Partial Run Mode

When `--changed-pages` is provided:

```python
async def run_pipeline(
    ...,
    changed_pages: list[str] | None = None,  # NEW: page IDs to re-test
    cache_dir: str = "",                       # NEW: cache directory
) -> dict:
    if changed_pages and cache_dir:
        # Partial retry mode
        cached = load_cached_pages(cache_dir, unchanged_page_ids, git_sha, codeintel_sha)
        if cached is None:
            # Cache invalid — full run
            changed_pages = None  # fall through to full run
        else:
            # Navigator: only visit changed pages
            manifest_subset = filter_manifest(manifest, changed_pages)
            navigator_output = await run_navigator(..., manifest=manifest_subset)

            # Merge navigator outputs
            navigator_output["pages"] = navigator_output["pages"] + cached["navigator_pages"]

            # Score only changed pages
            scorer_results = await run_scorers(navigator_output, ..., page_filter=changed_pages)

            # Merge scorer results
            scorer_results = merge_scorer_results(scorer_results, cached["scorer_pages"])

            # Reconcile all pages (changed = fresh, unchanged = cached)
            ...

    # Save to cache after successful run
    if cache_dir:
        save_cache(cache_dir, navigator_output, scorer_results, reconciled_pages, git_sha, codeintel_sha)
```

### Merge Logic

```python
def merge_results(fresh_pages: list[dict], cached_pages: list[dict]) -> list[dict]:
    """Merge fresh results for changed pages with cached results for unchanged pages.

    Fresh pages take precedence if a page appears in both (shouldn't happen,
    but defensive).
    """
    result = {p["page_id"]: p for p in cached_pages}
    for p in fresh_pages:
        result[p["page_id"]] = p  # overwrite cached with fresh
    return list(result.values())
```

---

## SUDD-Side: manifest_diff

The code-analyzer-reviewer generates `manifest_diff` when invoked on retry:

```json
{
  "changed_files": ["src/RegisterPage.tsx", "src/components/FormInput.tsx"],
  "changed_pages": ["registration"],
  "unchanged_pages": ["dashboard", "settings"],
  "shared_component_impact": {
    "FormInput.tsx": ["registration", "settings"]
  },
  "reason": "RegisterPage.tsx modified + FormInput.tsx (shared component) modified → registration and settings marked changed"
}
```

Gate passes `--changed-pages registration,settings --cache-dir changes/{id}/browser-cache/{persona}/` to PB.

---

## Edge Cases

| Case | Behavior |
|------|----------|
| First run (no cache) | Full run, save cache |
| All pages changed | Full run (--changed-pages lists all pages = same as no flag) |
| Shared component changed | All pages importing it marked as changed |
| Cache file corrupted | Treat as invalid, full run |
| Codeintel changed | Cache invalid (even if git SHA same — code-analyzer found something new) |
| New page added | Not in cache → included in changed-pages automatically |
| Page removed | Not in new manifest → excluded from merge |

---

## Test Strategy (~8 tests)

- `test_save_and_load_cache` — round-trip: save → load → identical results
- `test_cache_invalid_git_sha` — different SHA → returns None
- `test_cache_invalid_codeintel_sha` — different codeintel → returns None
- `test_cache_missing` — no cache dir → returns None
- `test_pipeline_partial_retry` — changed 1 of 3 pages, verify only 1 navigated
- `test_pipeline_cache_merge` — fresh + cached pages merged correctly
- `test_pipeline_cache_invalid_falls_back` — invalid cache → full run
- `test_shared_component_marks_multiple_pages` — FormInput.tsx change → 2 pages changed

---

## Cost Savings

| Scenario | Without diff-aware | With diff-aware | Saving |
|----------|-------------------|-----------------|--------|
| 3-page app, 1 page changed | 60-90s | 20-30s | 55-67% |
| 5-page app, 1 page changed | 90-150s | 20-30s | 78-80% |
| 3-page app, all changed | 60-90s | 60-90s | 0% (full run) |
| Retry with same code (no changes) | 60-90s | ~5s (all cached) | 94-95% |

Biggest impact on overnight runs with multiple retries where each retry changes only 1-2 files.
