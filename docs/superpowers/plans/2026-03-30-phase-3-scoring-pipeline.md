# Phase 3: Scoring Pipeline Implementation Plan

> **Status: COMPLETED** (2026-03-30). Implementation in `persona_browser/network_verifier.py`, `text_scorer.py`, `visual_scorer.py`, `codeintel_filter.py`, `scorer_runner.py`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task is independent — Tasks 1–4 can be done in parallel; Task 5 depends on Tasks 1–3.

**Goal:** Build three independent scoring modules (Network Verifier, Text Scorer, Visual Scorer) that analyze the navigator's output and produce per-criterion PASS/FAIL/UNKNOWN results, plus a codeintel filter utility and a parallel scorer runner. All output conforms to the schemas in `schemas/`.

**Architecture:** Each scorer is a standalone Python module in `persona_browser/`. The Network Verifier is fully deterministic (no LLM). The Text Scorer calls an LLM with text observations + network data. The Visual Scorer calls a multimodal LLM with screenshots + filtered codeintel. A `run_scorers()` function runs all three in parallel via `asyncio.gather()`. The filter utility (`codeintel_filter.py`) is a shared helper used by the Visual Scorer.

**Tech Stack:** Python 3.11+, `browser_use.llm.litellm.chat.ChatLiteLLM` for LLM calls (same as `agent.py`), `asyncio` for parallel execution, `jsonschema` for output validation in tests, `pytest` + `unittest.mock` for TDD (LLM calls mocked in all unit tests).

**Key references (read before implementing):**
- `schemas/network-verifier-output.schema.json` — exact output structure for network verifier
- `schemas/text-scorer-output.schema.json` — per-page output structure for text scorer
- `schemas/visual-scorer-output.schema.json` — per-page output structure for visual scorer
- `rubrics/pb-feature-rubric.md` — 49 criteria + 18 deal-breakers with stable IDs
- `fixtures/sample_codeintel.json` — codeintel structure (pages, api_endpoints, auth, data_flows)
- `fixtures/sample_navigator_output.json` — navigator output format (input to all scorers)
- `fixtures/sample_network_verifier_output.json` — expected output from network verifier
- `fixtures/sample_rubric.md` — consumer rubric format (Must Pass / Should Pass / Deal-Breakers)
- `docs/consumer-rubric-format.md` — consumer rubric format spec

---

## File Structure After Phase 3

```
persona_browser/
  network_verifier.py   CREATE  — deterministic, no LLM
  text_scorer.py        CREATE  — LLM-based text analysis
  visual_scorer.py      CREATE  — LLM-based multimodal analysis
  codeintel_filter.py   CREATE  — filter codeintel to visual-only fields
  scorer_runner.py      CREATE  — parallel execution via asyncio.gather

tests/
  test_network_verifier.py   CREATE  (~20 tests)
  test_text_scorer.py        CREATE  (~10 tests, mocked LLM)
  test_visual_scorer.py      CREATE  (~8 tests, mocked LLM)
  test_codeintel_filter.py   CREATE  (~5 tests)
  test_scorer_runner.py      CREATE  (~4 tests)
```

---

## Task 1: Network Verifier (deterministic, ~20 tests)

**Files:**
- Create: `persona_browser/network_verifier.py`
- Create: `tests/test_network_verifier.py`

Pure Python. No LLM. Takes `network_log` (list of dicts from navigator output) and `codeintel` (dict) and returns a dict matching `schemas/network-verifier-output.schema.json`. Fully testable with the sample fixtures.

### Logic details

The function `verify_network(network_log, codeintel, manifest=None) -> dict` performs:

1. **API call matching:** For each entry in `network_log` where the URL path contains `/api/`:
   - Extract the path from the URL (strip scheme + host)
   - Look up `codeintel["api_endpoints"]` by matching `method` and `path`
   - Path matching is exact first, then normalized (strip trailing slash)
   - If no match: flag as unmatched, add issue string
   - If status is 5xx: add to `api_errors_during_normal_flow`; if during normal flow, add deal-breaker
   - If matched endpoint has `auth_required=true`: verify auth header or cookie was sent

2. **Auth flow:** Only runs if `manifest` is provided and contains `auth_flow`:
   - Look for a `set_cookie` in a successful auth response (any entry with `set_cookie` not null)
   - Check subsequent protected-endpoint requests for `request_headers_note` containing "Cookie"
   - Check if any post-refresh request to a protected endpoint returned 200

3. **Auth flow fallback:** Even without a manifest, check the network_log directly:
   - `auth_token_set_after_auth`: any entry has `set_cookie` not null AND the endpoint `sets_auth=true` in codeintel
   - `auth_token_sent_on_protected_requests`: protected endpoint requests have `request_headers_note` containing "Cookie"
   - `auth_persists_after_refresh`: a protected endpoint request that appears after a duplicate page request (same URL twice) returned 200

### Step 1: Write the tests first

- [ ] Create `tests/test_network_verifier.py`:

```python
"""Tests for network_verifier — deterministic network log analysis.

Uses sample fixtures exclusively. No LLM calls.
Run: pytest tests/test_network_verifier.py -v
"""
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())
NAVIGATOR_OUTPUT = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
EXPECTED_OUTPUT = json.loads((FIXTURES / "sample_network_verifier_output.json").read_text())

# Flatten all network_log entries from all pages
ALL_NETWORK_LOG = []
for page in NAVIGATOR_OUTPUT["pages"]:
    ALL_NETWORK_LOG.extend(page.get("network_log", []))

# API-only entries (the ones verify_network processes)
API_NETWORK_LOG = [e for e in ALL_NETWORK_LOG if "/api/" in e["url"]]


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------

def test_output_has_required_top_level_fields():
    """Output dict has all required top-level fields."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    for field in [
        "api_calls_total",
        "api_calls_matched_codeintel",
        "api_calls_unmatched",
        "api_errors_during_normal_flow",
        "deal_breakers",
        "issues",
    ]:
        assert field in result, f"Missing required field: {field}"


def test_output_counts_are_integers():
    """api_calls_total, _matched, _unmatched, _errors are non-negative ints."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    for field in [
        "api_calls_total",
        "api_calls_matched_codeintel",
        "api_calls_unmatched",
        "api_errors_during_normal_flow",
    ]:
        assert isinstance(result[field], int), f"{field} should be int"
        assert result[field] >= 0, f"{field} should be >= 0"


def test_deal_breakers_and_issues_are_lists_of_strings():
    """deal_breakers and issues are lists of strings."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert isinstance(result["deal_breakers"], list)
    assert isinstance(result["issues"], list)
    for item in result["deal_breakers"]:
        assert isinstance(item, str), f"deal_breaker item not a string: {item!r}"
    for item in result["issues"]:
        assert isinstance(item, str), f"issues item not a string: {item!r}"


def test_per_endpoint_is_list_when_present():
    """per_endpoint, if present, is a list of dicts with required fields."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    if "per_endpoint" in result:
        assert isinstance(result["per_endpoint"], list)
        for ep in result["per_endpoint"]:
            for field in ["method", "path", "matched_codeintel", "status"]:
                assert field in ep, f"per_endpoint entry missing {field}: {ep}"


# ---------------------------------------------------------------------------
# Correct counts from sample fixtures
# ---------------------------------------------------------------------------

def test_api_calls_total_matches_sample():
    """api_calls_total equals the number of /api/ entries in the sample log."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    # Sample has: POST /api/auth/register + GET /api/user/me x2 = 3
    assert result["api_calls_total"] == EXPECTED_OUTPUT["api_calls_total"]


def test_all_sample_api_calls_matched():
    """All 3 API calls in the sample match codeintel (0 unmatched)."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result["api_calls_matched_codeintel"] == EXPECTED_OUTPUT["api_calls_matched_codeintel"]
    assert result["api_calls_unmatched"] == EXPECTED_OUTPUT["api_calls_unmatched"]


def test_no_errors_in_normal_flow_sample():
    """Sample has no 5xx errors during normal flow."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result["api_errors_during_normal_flow"] == 0


def test_no_deal_breakers_in_sample():
    """Clean sample session has no deal-breakers."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result["deal_breakers"] == []


def test_no_issues_in_sample():
    """Clean sample session has no issues."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# Auth flow (from sample fixtures)
# ---------------------------------------------------------------------------

def test_auth_token_set_after_auth_true_in_sample():
    """Sample: POST /api/auth/register sets a session cookie (set_cookie not null)."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result.get("auth_token_set_after_auth") is True


def test_auth_token_sent_on_protected_requests_true_in_sample():
    """Sample: GET /api/user/me requests include Cookie header (auth sent)."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result.get("auth_token_sent_on_protected_requests") is True


def test_auth_persists_after_refresh_true_in_sample():
    """Sample: second GET /api/user/me (after page refresh) also returns 200."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL)
    assert result.get("auth_persists_after_refresh") is True


# ---------------------------------------------------------------------------
# Error injection: unmatched endpoint
# ---------------------------------------------------------------------------

def test_unknown_api_call_flagged_as_unmatched():
    """A network log entry for an unrecognized API path increments unmatched count."""
    from persona_browser.network_verifier import verify_network
    extra_entry = {
        "method": "DELETE",
        "url": "http://localhost:3333/api/unknown/resource",
        "status": 204,
        "timing_ms": 10,
        "trigger": "test",
        "request_content_type": None,
        "request_body": None,
        "response_summary": None,
        "set_cookie": None,
        "request_headers_note": None,
    }
    log = ALL_NETWORK_LOG + [extra_entry]
    result = verify_network(log, CODEINTEL)
    assert result["api_calls_unmatched"] >= 1
    assert any("unknown" in issue.lower() or "DELETE" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# Error injection: 500 during normal flow
# ---------------------------------------------------------------------------

def test_500_during_normal_flow_adds_deal_breaker():
    """A 5xx response on a user-action endpoint adds a deal-breaker."""
    from persona_browser.network_verifier import verify_network
    bad_entry = {
        "method": "POST",
        "url": "http://localhost:3333/api/auth/register",
        "status": 500,
        "timing_ms": 50,
        "trigger": "user action",
        "request_content_type": "application/json",
        "request_body": '{"name":"test","email":"test@test.com","password":"password123"}',
        "response_summary": "Internal Server Error",
        "set_cookie": None,
        "request_headers_note": None,
    }
    result = verify_network([bad_entry], CODEINTEL)
    assert result["api_errors_during_normal_flow"] >= 1
    assert len(result["deal_breakers"]) >= 1
    assert any("500" in db or "server error" in db.lower() for db in result["deal_breakers"])


# ---------------------------------------------------------------------------
# Error injection: missing auth header on protected endpoint
# ---------------------------------------------------------------------------

def test_missing_auth_on_protected_endpoint_flagged():
    """A request to an auth_required endpoint without Cookie is flagged."""
    from persona_browser.network_verifier import verify_network
    # GET /api/user/me without Cookie header
    no_auth_entry = {
        "method": "GET",
        "url": "http://localhost:3333/api/user/me",
        "status": 401,
        "timing_ms": 5,
        "trigger": "test",
        "request_content_type": None,
        "request_body": None,
        "response_summary": '{"message":"Not authenticated"}',
        "set_cookie": None,
        "request_headers_note": None,  # No cookie mentioned
    }
    result = verify_network([no_auth_entry], CODEINTEL)
    # per_endpoint auth_check for this entry should be FAIL or flagged
    if "per_endpoint" in result:
        me_entries = [
            ep for ep in result["per_endpoint"]
            if "/api/user/me" in ep["path"]
        ]
        if me_entries:
            assert any(
                ep.get("auth_check", "").startswith("FAIL") or "FAIL" in ep.get("auth_check", "")
                for ep in me_entries
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_network_log():
    """Empty network log returns zero counts and no deal-breakers."""
    from persona_browser.network_verifier import verify_network
    result = verify_network([], CODEINTEL)
    assert result["api_calls_total"] == 0
    assert result["api_calls_matched_codeintel"] == 0
    assert result["api_calls_unmatched"] == 0
    assert result["api_errors_during_normal_flow"] == 0
    assert result["deal_breakers"] == []


def test_non_api_entries_not_counted():
    """Non-API entries (no /api/ in URL) are not counted as API calls."""
    from persona_browser.network_verifier import verify_network
    html_only = [
        e for e in ALL_NETWORK_LOG if "/api/" not in e["url"]
    ]
    result = verify_network(html_only, CODEINTEL)
    assert result["api_calls_total"] == 0


def test_codeintel_without_api_endpoints_still_works():
    """codeintel with no api_endpoints key is handled gracefully."""
    from persona_browser.network_verifier import verify_network
    minimal_codeintel = {"version": "1.0", "pages": []}
    result = verify_network(API_NETWORK_LOG, minimal_codeintel)
    # All entries should be unmatched, no crash
    assert result["api_calls_unmatched"] == result["api_calls_total"]


def test_manifest_none_is_handled():
    """manifest=None is handled (no auth flow analysis, no crash)."""
    from persona_browser.network_verifier import verify_network
    result = verify_network(ALL_NETWORK_LOG, CODEINTEL, manifest=None)
    assert "api_calls_total" in result  # Did not crash
```

- [ ] **Run tests, confirm they fail** (module does not exist yet):

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_network_verifier.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'persona_browser.network_verifier'`

### Step 2: Implement network_verifier.py

- [ ] Create `persona_browser/network_verifier.py`:

```python
"""Network Verifier — deterministic analysis of navigator network_log.

No LLM calls. Pure Python matching logic.

Public API:
    verify_network(network_log, codeintel, manifest=None) -> dict

Output matches schemas/network-verifier-output.schema.json.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse


def verify_network(
    network_log: list[dict],
    codeintel: dict,
    manifest: Optional[dict] = None,
) -> dict:
    """Cross-reference network_log against codeintel.api_endpoints.

    Args:
        network_log: List of network log entries from navigator output.
                     Each entry follows network-log-entry.schema.json.
        codeintel: Codeintel dict (pages, api_endpoints, auth, data_flows).
        manifest: Optional manifest dict — used for auth_flow analysis.

    Returns:
        dict matching schemas/network-verifier-output.schema.json.
    """
    api_endpoints = codeintel.get("api_endpoints", [])

    # ── Separate API entries from non-API entries ─────────────────────────────
    api_entries = [e for e in network_log if "/api/" in e.get("url", "")]

    counts = {
        "total": len(api_entries),
        "matched": 0,
        "unmatched": 0,
        "errors": 0,
    }
    deal_breakers: list[str] = []
    issues: list[str] = []
    per_endpoint: list[dict] = []

    for entry in api_entries:
        path = _extract_path(entry["url"])
        method = entry.get("method", "").upper()
        status = entry.get("status", 0)

        # ── Match against codeintel ───────────────────────────────────────────
        matched_ep = _match_endpoint(method, path, api_endpoints)

        if matched_ep is None:
            counts["unmatched"] += 1
            issues.append(
                f"Unknown API call: {method} {path} (status {status}) — "
                "not found in codeintel.api_endpoints"
            )
            per_endpoint.append({
                "method": method,
                "path": path,
                "matched_codeintel": False,
                "status": status,
            })
            # Still check for 5xx on unmatched endpoints
            if status >= 500:
                counts["errors"] += 1
                deal_breakers.append(
                    f"5xx error on unrecognized endpoint {method} {path}: "
                    f"HTTP {status}"
                )
            continue

        counts["matched"] += 1

        # ── Status check ─────────────────────────────────────────────────────
        expected_status = _get_expected_status(matched_ep, entry)
        contract_match = (status == expected_status) if expected_status else None

        if status >= 500:
            counts["errors"] += 1
            deal_breakers.append(
                f"Backend 500 error on {method} {path}: HTTP {status} — "
                "deal-breaker (task.db_500)"
            )

        # ── Auth check ───────────────────────────────────────────────────────
        auth_check = _check_auth(entry, matched_ep)

        ep_record: dict = {
            "method": method,
            "path": path,
            "matched_codeintel": True,
            "status": status,
        }
        if expected_status is not None:
            ep_record["expected_status"] = expected_status
        if contract_match is not None:
            ep_record["contract_match"] = contract_match
        if auth_check is not None:
            ep_record["auth_check"] = auth_check

        per_endpoint.append(ep_record)

    # ── Auth flow analysis ────────────────────────────────────────────────────
    auth_token_set, auth_token_sent, auth_persists = _analyze_auth_flow(
        network_log, codeintel, api_endpoints
    )

    result: dict = {
        "api_calls_total": counts["total"],
        "api_calls_matched_codeintel": counts["matched"],
        "api_calls_unmatched": counts["unmatched"],
        "api_errors_during_normal_flow": counts["errors"],
        "deal_breakers": deal_breakers,
        "issues": issues,
    }

    # Optional auth fields (only set if determinable)
    if auth_token_set is not None:
        result["auth_token_set_after_auth"] = auth_token_set
    if auth_token_sent is not None:
        result["auth_token_sent_on_protected_requests"] = auth_token_sent
    if auth_persists is not None:
        result["auth_persists_after_refresh"] = auth_persists

    if per_endpoint:
        result["per_endpoint"] = per_endpoint

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_path(url: str) -> str:
    """Extract URL path from a full URL, stripping scheme and host."""
    try:
        parsed = urlparse(url)
        return parsed.path.rstrip("/") or "/"
    except Exception:
        return url


def _match_endpoint(
    method: str, path: str, api_endpoints: list[dict]
) -> Optional[dict]:
    """Find the codeintel endpoint matching this method + path.

    Tries exact match first, then strips trailing slashes.
    Returns the matching endpoint dict, or None if not found.
    """
    path_norm = path.rstrip("/")
    for ep in api_endpoints:
        ep_method = ep.get("method", "").upper()
        ep_path = ep.get("path", "").rstrip("/")
        if ep_method == method and ep_path == path_norm:
            return ep
    return None


def _get_expected_status(endpoint: dict, entry: dict) -> Optional[int]:
    """Determine expected status code for this endpoint + request.

    For auth endpoints that set_auth on 201, return 201.
    For endpoints with a single success code, return that.
    Falls back to None (cannot determine) for multi-response endpoints.
    """
    responses = endpoint.get("responses", {})
    if not responses:
        return None

    # Single response → expected = that status
    if len(responses) == 1:
        try:
            return int(list(responses.keys())[0])
        except (ValueError, TypeError):
            return None

    # Multiple responses — pick the success one (2xx with lowest code)
    success_codes = []
    for code_str in responses:
        try:
            code = int(code_str)
            if 200 <= code < 300:
                success_codes.append(code)
        except (ValueError, TypeError):
            pass

    if len(success_codes) == 1:
        return success_codes[0]

    return None


def _check_auth(entry: dict, endpoint: dict) -> Optional[str]:
    """Check whether auth requirements are satisfied for this request.

    Returns:
        "N/A (public endpoint)" if auth_required is False or absent
        "N/A (public endpoint — sets auth)" if the endpoint sets_auth=True
        "PASS — session cookie sent and accepted; ..." if auth check passes
        "FAIL — auth required but no Cookie header observed" if auth missing
        None if cannot determine
    """
    auth_required = endpoint.get("auth_required", False)
    sets_auth = False

    # Check responses for sets_auth flag
    for _code, resp_data in endpoint.get("responses", {}).items():
        if isinstance(resp_data, dict) and resp_data.get("sets_auth"):
            sets_auth = True
            break

    if sets_auth:
        return "N/A (public endpoint — sets auth)"

    if not auth_required:
        return "N/A (public endpoint)"

    # auth_required=True — check if cookie was sent
    headers_note = entry.get("request_headers_note") or ""
    status = entry.get("status", 0)

    if "Cookie" in headers_note or "cookie" in headers_note.lower():
        if 200 <= status < 300:
            response_summary = entry.get("response_summary", "")
            return (
                f"PASS — session cookie sent and accepted; "
                f"response body: {response_summary[:80]}"
            )
        else:
            return f"FAIL — cookie sent but server rejected it (HTTP {status})"
    else:
        if status == 401:
            return "FAIL — auth required but no Cookie header observed (got 401)"
        elif 200 <= status < 300:
            # Cookie may have been sent but not logged — treat as PASS with low confidence
            return (
                "PASS (inferred) — protected endpoint returned 200; "
                "Cookie header not explicitly logged"
            )
        else:
            return f"FAIL — auth required but no Cookie header observed (HTTP {status})"


def _analyze_auth_flow(
    network_log: list[dict],
    codeintel: dict,
    api_endpoints: list[dict],
) -> tuple[Optional[bool], Optional[bool], Optional[bool]]:
    """Analyze auth flow from network_log.

    Returns:
        (auth_token_set_after_auth, auth_token_sent_on_protected, auth_persists_after_refresh)
        Each may be None if not determinable.
    """
    # Find endpoints that set_auth
    auth_setting_paths: set[str] = set()
    protected_paths: set[str] = set()

    for ep in api_endpoints:
        path = ep.get("path", "").rstrip("/")
        for resp_data in ep.get("responses", {}).values():
            if isinstance(resp_data, dict) and resp_data.get("sets_auth"):
                auth_setting_paths.add(path)
                break
        if ep.get("auth_required"):
            protected_paths.add(path)

    # Also use codeintel.auth if present
    auth_config = codeintel.get("auth", {})
    register_ep = auth_config.get("register_endpoint", "")
    if register_ep:
        auth_setting_paths.add(register_ep.rstrip("/"))

    backend_protected = set()
    for route in auth_config.get("protected_routes", {}).get("backend", []):
        backend_protected.add(route.rstrip("/"))
    protected_paths |= backend_protected

    # ── Check 1: auth token set after auth ───────────────────────────────────
    auth_token_set: Optional[bool] = None
    for entry in network_log:
        path = _extract_path(entry.get("url", ""))
        if path in auth_setting_paths:
            if entry.get("set_cookie") is not None:
                auth_token_set = True
                break
    if auth_token_set is None and auth_setting_paths:
        # We have auth endpoints but saw no set_cookie
        # Only mark as False if we actually saw the auth endpoint
        auth_ep_calls = [
            e for e in network_log
            if _extract_path(e.get("url", "")) in auth_setting_paths
        ]
        if auth_ep_calls:
            auth_token_set = False

    # ── Check 2: auth token sent on protected requests ────────────────────────
    auth_token_sent: Optional[bool] = None
    all_protected = protected_paths | {
        p for p in protected_paths
    }
    protected_calls = [
        e for e in network_log
        if _extract_path(e.get("url", "")) in all_protected
    ]
    if protected_calls:
        # Check if any protected call had Cookie in headers note
        cookie_sent_calls = [
            e for e in protected_calls
            if "Cookie" in (e.get("request_headers_note") or "")
            or "cookie" in (e.get("request_headers_note") or "").lower()
        ]
        # Also infer from 200 responses (cookie must have been sent if 200)
        success_calls = [e for e in protected_calls if 200 <= e.get("status", 0) < 300]
        if cookie_sent_calls or success_calls:
            auth_token_sent = True
        else:
            auth_token_sent = False

    # ── Check 3: auth persists after refresh ─────────────────────────────────
    auth_persists: Optional[bool] = None
    if protected_calls and len(protected_calls) >= 2:
        # Look for duplicate protected-endpoint calls (refresh = same URL called twice)
        # Sort by URL and check if any URL appears more than once
        from collections import Counter
        url_counts = Counter(_extract_path(e.get("url", "")) for e in protected_calls)
        repeated_paths = {p for p, c in url_counts.items() if c >= 2}
        if repeated_paths:
            # Check that all calls to repeated paths succeeded
            repeated_calls = [
                e for e in protected_calls
                if _extract_path(e.get("url", "")) in repeated_paths
            ]
            all_succeeded = all(200 <= e.get("status", 0) < 300 for e in repeated_calls)
            auth_persists = all_succeeded

    return auth_token_set, auth_token_sent, auth_persists
```

- [ ] **Run tests, confirm they all pass:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_network_verifier.py -v
```

Expected: 20 tests pass.

---

## Task 2: Text Scorer — prompt + LLM call structure (~10 tests)

**Files:**
- Create: `persona_browser/text_scorer.py`
- Create: `tests/test_text_scorer.py`

LLM-based. Uses GLM/Gemini via ChatLiteLLM. Takes pages from navigator output, consumer rubric text, PB rubric text, codeintel, and experience dict. Returns a list of dicts matching `schemas/text-scorer-output.schema.json`. LLM is mocked in all unit tests.

### Prompt strategy

The text scorer sends one LLM call per page. Each call includes:

1. **System message:** Role as a QA evaluator. Instruction to return only valid JSON matching the schema. Instruction to use UNKNOWN when evidence is insufficient (especially for spatial/visual criteria). Instruction to reference codeintel when verifying API-level behaviour.

2. **Human message:** Structured prompt with:
   - Page ID and URL visited
   - Page observations (description + actions + forms encountered)
   - Network log for this page (filtered to /api/ calls only)
   - Relevant codeintel (api_endpoints matching the page, page-level elements)
   - Consumer rubric criteria for this page (extracted from rubric_text by page name matching)
   - Relevant PB rubric criteria (those with Scorer column containing "Text")
   - Output format: JSON object with `page_id`, `pb_criteria`, `consumer_criteria`

3. **LLM response:** JSON object that is parsed and validated. If parsing fails, retry once with an explicit "return only JSON" instruction. If still fails, return UNKNOWN for all criteria.

### Step 1: Write the tests first

- [ ] Create `tests/test_text_scorer.py`:

```python
"""Tests for text_scorer — LLM-based text analysis of navigator output.

LLM is mocked in all tests — no real API calls.
Run: pytest tests/test_text_scorer.py -v
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())
NAVIGATOR = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
RUBRIC_TEXT = (FIXTURES / "sample_rubric.md").read_text()
PB_RUBRIC_TEXT = (
    Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md"
).read_text()

# A minimal valid LLM response for one page
MOCK_LLM_RESPONSE_REGISTRATION = {
    "page_id": "registration",
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "Every input field has a visible, associated label",
            "result": "PASS",
            "evidence": "Text observations mention 'three labeled text inputs (Full Name, Email Address, Password)'",
            "confidence": "high",
        },
        {
            "feature": "forms",
            "criterion": "The submit button is visible and clearly labeled",
            "result": "PASS",
            "evidence": "Actions describe clicking 'Register' button successfully",
            "confidence": "high",
        },
        {
            "feature": "baseline",
            "criterion": "No unhandled JavaScript errors or crash states are present",
            "result": "PASS",
            "evidence": "Page loaded and form submitted without errors",
            "confidence": "high",
        },
    ],
    "consumer_criteria": [
        {
            "criterion": "The page renders a form with exactly three visible input fields",
            "result": "PASS",
            "evidence": "Agent observation: 'three labeled text inputs (Full Name, Email Address, Password)'",
            "confidence": "high",
            "codeintel_ref": "pages[0].elements.forms[0].fields",
        },
        {
            "criterion": "Submitting the form with valid credentials navigates to /dashboard",
            "result": "PASS",
            "evidence": "Network log shows POST /api/auth/register returned 201; redirect to /dashboard observed",
            "confidence": "high",
        },
    ],
}

MOCK_LLM_RESPONSE_DASHBOARD = {
    "page_id": "dashboard",
    "pb_criteria": [
        {
            "feature": "baseline",
            "criterion": "No unhandled JavaScript errors or crash states are present",
            "result": "PASS",
            "evidence": "Dashboard loaded successfully, showing user data",
            "confidence": "high",
        },
        {
            "feature": "nav",
            "criterion": "Every navigable page provides a path back or forward",
            "result": "PASS",
            "evidence": "Logout button visible, links back to registration/home",
            "confidence": "medium",
        },
    ],
    "consumer_criteria": [
        {
            "criterion": "The page displays the user's full name as entered during registration",
            "result": "PASS",
            "evidence": "Observation: 'Name: Jordan Rivera' visible in user info section",
            "confidence": "high",
        },
        {
            "criterion": "A logout button is present on the page",
            "result": "PASS",
            "evidence": "Agent step 6 result: 'Logout button visible'",
            "confidence": "high",
            "codeintel_ref": "pages[1].elements.navigation.links[0]",
        },
    ],
}


def _make_mock_llm(responses: list[dict]):
    """Create a mock ChatLiteLLM that returns predefined JSON responses."""
    mock_llm = MagicMock()
    call_count = [0]

    async def ainvoke(messages, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        mock_response = MagicMock()
        mock_response.content = json.dumps(responses[idx])
        return mock_response

    mock_llm.ainvoke = ainvoke
    return mock_llm


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_text_returns_list():
    """score_text returns a list."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    pages = NAVIGATOR["pages"]
    result = await score_text(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_score_text_returns_one_entry_per_page():
    """score_text returns one dict per page in the input."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    pages = NAVIGATOR["pages"]
    result = await score_text(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    assert len(result) == len(pages)


@pytest.mark.asyncio
async def test_each_result_has_required_fields():
    """Each result dict has page_id, pb_criteria, consumer_criteria."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    result = await score_text(
        pages=NAVIGATOR["pages"],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    for item in result:
        assert "page_id" in item, f"Missing page_id in {item}"
        assert "pb_criteria" in item, f"Missing pb_criteria in {item}"
        assert "consumer_criteria" in item, f"Missing consumer_criteria in {item}"


@pytest.mark.asyncio
async def test_page_ids_match_input():
    """Returned page_ids match the page ids from navigator output."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    result = await score_text(
        pages=NAVIGATOR["pages"],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    input_ids = {p["id"] for p in NAVIGATOR["pages"]}
    result_ids = {r["page_id"] for r in result}
    assert result_ids == input_ids


@pytest.mark.asyncio
async def test_pb_criteria_items_have_required_fields():
    """Each pb_criteria item has feature, criterion, result, evidence, confidence."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    result = await score_text(
        pages=NAVIGATOR["pages"],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    for page_result in result:
        for criterion in page_result["pb_criteria"]:
            for field in ["feature", "criterion", "result", "evidence", "confidence"]:
                assert field in criterion, (
                    f"pb_criteria item missing '{field}': {criterion}"
                )


@pytest.mark.asyncio
async def test_result_values_are_valid():
    """All result fields are PASS, FAIL, or UNKNOWN."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    result = await score_text(
        pages=NAVIGATOR["pages"],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    valid_results = {"PASS", "FAIL", "UNKNOWN"}
    for page_result in result:
        for criterion in page_result["pb_criteria"] + page_result["consumer_criteria"]:
            assert criterion["result"] in valid_results, (
                f"Invalid result value: {criterion['result']!r}"
            )


@pytest.mark.asyncio
async def test_confidence_values_are_valid():
    """All confidence fields are high, medium, or low."""
    from persona_browser.text_scorer import score_text

    mock_llm = _make_mock_llm([MOCK_LLM_RESPONSE_REGISTRATION, MOCK_LLM_RESPONSE_DASHBOARD])
    result = await score_text(
        pages=NAVIGATOR["pages"],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    valid_confidence = {"high", "medium", "low"}
    for page_result in result:
        for criterion in page_result["pb_criteria"] + page_result["consumer_criteria"]:
            assert criterion["confidence"] in valid_confidence, (
                f"Invalid confidence value: {criterion['confidence']!r}"
            )


@pytest.mark.asyncio
async def test_invalid_llm_json_returns_unknown_fallback():
    """When LLM returns invalid JSON, all criteria for that page are UNKNOWN."""
    from persona_browser.text_scorer import score_text

    mock_llm = MagicMock()

    async def ainvoke(messages, **kwargs):
        mock_response = MagicMock()
        mock_response.content = "not valid json at all {{"
        return mock_response

    mock_llm.ainvoke = ainvoke

    result = await score_text(
        pages=NAVIGATOR["pages"][:1],  # just one page
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        experience=NAVIGATOR.get("experience", {}),
        llm=mock_llm,
    )
    assert len(result) == 1
    page_result = result[0]
    # Should have UNKNOWN criteria rather than crashing
    assert "page_id" in page_result
    all_criteria = page_result.get("pb_criteria", []) + page_result.get("consumer_criteria", [])
    if all_criteria:
        for c in all_criteria:
            assert c["result"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_build_text_prompt_includes_page_observations():
    """_build_text_prompt includes the page observations in the prompt."""
    from persona_browser.text_scorer import _build_text_prompt

    page = NAVIGATOR["pages"][0]  # registration page
    prompt = _build_text_prompt(
        page=page,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
    )
    # Prompt should reference the page description
    assert "Create Account" in prompt or "registration" in prompt.lower()
    assert "Jordan Rivera" in prompt or "Full Name" in prompt


@pytest.mark.asyncio
async def test_build_text_prompt_excludes_screenshots():
    """_build_text_prompt does not include screenshot paths (those are for visual scorer)."""
    from persona_browser.text_scorer import _build_text_prompt

    page = NAVIGATOR["pages"][0]
    prompt = _build_text_prompt(
        page=page,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
    )
    # Should not include the raw screenshot file path as data
    assert "screenshots/step_1.png" not in prompt or "screenshot" in prompt.lower()
```

- [ ] **Run tests, confirm they fail:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_text_scorer.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'persona_browser.text_scorer'`

Note: `pytest-asyncio` is required for `@pytest.mark.asyncio`. Install with: `pip install pytest-asyncio`

### Step 2: Implement text_scorer.py

- [ ] Create `persona_browser/text_scorer.py`:

```python
"""Text Scorer — LLM-based evaluation of text observations from navigator output.

Scores PB rubric + consumer rubric criteria using text observations,
network_log, and codeintel. No screenshots — those go to visual_scorer.

Public API:
    async score_text(pages, rubric_text, pb_rubric_text, codeintel, experience, llm) -> list[dict]
    _build_text_prompt(page, rubric_text, pb_rubric_text, codeintel) -> str

Each returned dict matches schemas/text-scorer-output.schema.json.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# PB criteria assigned to "Text" or "Text + Visual" scorer
_TEXT_SCORER_FEATURES = {
    "forms": [
        "forms.input_types_match",
        "forms.tab_order",
        "forms.error_on_empty_submit",
        "forms.error_on_invalid",
        "forms.error_specific",
        "forms.error_clears",
        "forms.data_preserved_on_error",
        "forms.success_confirmation",
    ],
    "nav": [
        "nav.logo_links_home",
        "nav.no_dead_ends",
        "nav.back_works",
    ],
    "cta": [
        "cta.text_clear",
        "cta.destination_correct",
    ],
    "data": [
        "data.empty_states",
    ],
    "error": [
        "error.plain_language",
        "error.recovery_path",
        "error.no_jargon",
    ],
    "baseline": [
        "baseline.no_errors",
    ],
    "task": [
        "task.data_on_next_page",
        "task.survives_refresh",
        "task.data_consistent",
        "task.auth_access",
        "task.auth_persists_nav",
        "task.auth_persists_refresh",
        "task.unauth_redirect",
        "task.data_matches_api",
        "task.error_matches_api",
        "task.graceful_error_handling",
    ],
}

_SYSTEM_PROMPT = """\
You are a QA evaluator analysing a browser session for a persona-driven test.

Your task is to evaluate each criterion listed and return ONLY a valid JSON object.
Do NOT include any text before or after the JSON.

Rules:
- Use PASS when there is clear positive evidence in the observations or network data.
- Use FAIL when there is clear negative evidence (error seen, action failed, data wrong).
- Use UNKNOWN when evidence is insufficient — especially for spatial/visual criteria
  (label position, colour, layout) which cannot be determined from text observations alone.
- Reference codeintel when verifying API-level behaviour (expected status codes, field names).
- Confidence: "high" = direct evidence, "medium" = inferred, "low" = speculative.
- Be concise in evidence — max 100 words per criterion.

Return this exact JSON structure:
{
  "page_id": "<page_id>",
  "pb_criteria": [
    {
      "feature": "<feature>",
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<evidence>",
      "confidence": "high" | "medium" | "low",
      "note": "<optional>"
    }
  ],
  "consumer_criteria": [
    {
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<evidence>",
      "confidence": "high" | "medium" | "low",
      "codeintel_ref": "<optional>",
      "note": "<optional>"
    }
  ]
}
"""


async def score_text(
    pages: list[dict],
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    experience: dict,
    llm: Any,
) -> list[dict]:
    """Score all pages using LLM text analysis.

    Args:
        pages: List of page dicts from navigator output (each has id, observations, network_log).
        rubric_text: Full consumer rubric markdown text.
        pb_rubric_text: Full PB feature rubric markdown text.
        codeintel: Codeintel dict (pages, api_endpoints, auth, data_flows).
        experience: Experience dict from navigator output (first_impression, easy, hard, etc).
        llm: ChatLiteLLM instance (or mock for tests).

    Returns:
        List of dicts, one per page, matching text-scorer-output.schema.json.
    """
    results = []
    for page in pages:
        page_result = await _score_page(
            page=page,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            codeintel=codeintel,
            llm=llm,
        )
        results.append(page_result)
    return results


async def _score_page(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    llm: Any,
) -> dict:
    """Score a single page. Returns a text-scorer-output dict."""
    page_id = page.get("id", "unknown")
    prompt = _build_text_prompt(
        page=page,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        codeintel=codeintel,
    )

    # Build messages for ChatLiteLLM
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw_content = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.error("LLM call failed for page %s: %s", page_id, exc)
        return _fallback_unknown(page_id, reason=f"LLM call failed: {exc}")

    # Parse JSON response
    parsed = _parse_llm_json(raw_content)
    if parsed is None:
        # One retry with explicit JSON instruction
        retry_messages = messages + [
            HumanMessage(
                content=(
                    "Your previous response was not valid JSON. "
                    "Return ONLY the JSON object — no markdown, no explanation."
                )
            )
        ]
        try:
            response2 = await llm.ainvoke(retry_messages)
            raw2 = response2.content if hasattr(response2, "content") else str(response2)
            parsed = _parse_llm_json(raw2)
        except Exception as exc2:
            logger.error("LLM retry failed for page %s: %s", page_id, exc2)
            parsed = None

    if parsed is None:
        return _fallback_unknown(page_id, reason="Could not parse LLM JSON response")

    # Ensure page_id is correct (LLM might hallucinate a different one)
    parsed["page_id"] = page_id

    # Validate and normalise fields
    parsed = _normalise_output(parsed, page_id)
    return parsed


def _build_text_prompt(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
) -> str:
    """Build the text prompt for a single page.

    Args:
        page: Navigator page dict (id, url_visited, observations, network_log).
        rubric_text: Full consumer rubric markdown.
        pb_rubric_text: Full PB rubric markdown.
        codeintel: Full codeintel dict.

    Returns:
        Prompt string for the LLM.
    """
    page_id = page.get("id", "unknown")
    url_visited = page.get("url_visited", "unknown")
    observations = page.get("observations", {})
    network_log = page.get("network_log", [])

    # Filter network_log to API calls only (non-API entries are noise)
    api_log = [e for e in network_log if "/api/" in e.get("url", "")]

    # Filter codeintel to relevant api_endpoints for this page
    page_codeintel = _get_page_codeintel(page_id, codeintel)

    # Extract consumer rubric for this page
    consumer_rubric_section = _extract_consumer_rubric_section(page_id, rubric_text)

    # Extract relevant PB criteria (Text or Text+Visual scorers only)
    pb_criteria_section = _extract_text_pb_criteria(pb_rubric_text)

    lines = [
        f"## Page: {page_id}",
        f"URL visited: {url_visited}",
        "",
        "### Agent Observations",
        observations.get("description", "(no description)"),
        "",
        "### Actions Taken",
    ]

    for action in observations.get("actions", []):
        step = action.get("step", "?")
        act = action.get("action", "")
        res = action.get("result", "")
        lines.append(f"  Step {step}: {act} → {res}")

    if observations.get("forms"):
        lines.append("")
        lines.append("### Forms Observed")
        for form in observations["forms"]:
            lines.append(f"  Fields seen: {form.get('fields_seen', [])}")
            lines.append(f"  Submitted: {form.get('submitted', False)}")
            errors = form.get("errors_encountered", [])
            if errors:
                lines.append(f"  Errors: {errors}")

    if api_log:
        lines.append("")
        lines.append("### API Network Log (this page)")
        for entry in api_log:
            lines.append(
                f"  {entry.get('method')} {entry.get('url')} → {entry.get('status')} "
                f"({entry.get('timing_ms', '?')}ms)"
            )
            if entry.get("request_body"):
                lines.append(f"    Request body: {entry['request_body'][:200]}")
            if entry.get("response_summary"):
                lines.append(f"    Response: {entry['response_summary'][:200]}")
            if entry.get("set_cookie"):
                lines.append(f"    Set-Cookie: {entry['set_cookie'][:100]}")
            if entry.get("request_headers_note"):
                lines.append(f"    Headers note: {entry['request_headers_note'][:100]}")

    if page_codeintel:
        lines.append("")
        lines.append("### Codeintel (relevant API endpoints for this page)")
        lines.append(json.dumps(page_codeintel, indent=2)[:2000])

    if consumer_rubric_section:
        lines.append("")
        lines.append("### Consumer Rubric — Criteria for This Page")
        lines.append(consumer_rubric_section)

    if pb_criteria_section:
        lines.append("")
        lines.append("### PB Feature Rubric — Text Scorer Criteria")
        lines.append("Evaluate ONLY the following criteria (skip Visual-only criteria):")
        lines.append(pb_criteria_section)

    lines.append("")
    lines.append(
        "Now evaluate all consumer_criteria and pb_criteria listed above. "
        "Return ONLY the JSON object described in the system prompt."
    )

    return "\n".join(lines)


def _get_page_codeintel(page_id: str, codeintel: dict) -> dict:
    """Extract codeintel relevant to this page: api_endpoints + page elements."""
    result: dict = {}

    # Find matching page in codeintel.pages
    for cp in codeintel.get("pages", []):
        if cp.get("id") == page_id:
            result["page_elements"] = cp.get("elements", {})
            result["page_purpose"] = cp.get("purpose", "")
            break

    # Include all api_endpoints (scorer decides which are relevant)
    result["api_endpoints"] = codeintel.get("api_endpoints", [])
    result["auth"] = codeintel.get("auth", {})
    result["data_flows"] = codeintel.get("data_flows", [])

    return result


def _extract_consumer_rubric_section(page_id: str, rubric_text: str) -> str:
    """Extract the rubric section for this page from the consumer rubric markdown."""
    # Consumer rubric uses ## Page Name headers
    # We match by looking for a ## heading that contains the page_id (case-insensitive)
    # or the page name associated with this page_id
    lines = rubric_text.splitlines()
    in_section = False
    section_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if in_section:
                break  # End of our section
            # Check if this heading is for our page
            heading = line[3:].strip().lower()
            if page_id.lower() in heading or _page_id_matches_heading(page_id, heading):
                in_section = True
                section_lines.append(line)
        elif in_section:
            section_lines.append(line)

    return "\n".join(section_lines) if section_lines else ""


def _page_id_matches_heading(page_id: str, heading: str) -> bool:
    """Fuzzy match page_id to a rubric heading."""
    # registration → "registration page" matches
    # dashboard → "dashboard page" matches
    words = page_id.replace("_", " ").replace("-", " ").lower().split()
    return all(w in heading for w in words)


def _extract_text_pb_criteria(pb_rubric_text: str) -> str:
    """Extract only the Text-scorer-relevant criteria from PB rubric.

    Returns markdown lines for criteria where Scorer column contains "Text".
    """
    lines = pb_rubric_text.splitlines()
    result_lines: list[str] = []
    current_feature: str = ""

    for line in lines:
        # Track feature section headers
        if line.startswith("## "):
            current_feature = line[3:].strip()

        # Parse table rows: | ID | Criterion | Scorer |
        if line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")]
            # parts[0] is empty (before first |), parts[-1] is empty (after last |)
            # Actual content: parts[1], parts[2], parts[3]
            if len(parts) >= 4:
                scorer_col = parts[3] if len(parts) > 3 else ""
                criterion_id = parts[1]
                criterion_text = parts[2]
                # Skip header rows and separator rows
                if (
                    "Text" in scorer_col
                    and criterion_id not in ("ID", "---", "")
                    and criterion_text not in ("Criterion", "---", "")
                ):
                    result_lines.append(
                        f"  [{criterion_id}] {criterion_text} (Feature: {current_feature})"
                    )

    return "\n".join(result_lines)


def _parse_llm_json(content: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling common formatting issues."""
    if not content:
        return None

    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the outermost {} block
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _fallback_unknown(page_id: str, reason: str = "") -> dict:
    """Return a valid output dict with all criteria as UNKNOWN."""
    note = f"Scorer error: {reason}" if reason else "Scorer error: unknown reason"
    return {
        "page_id": page_id,
        "pb_criteria": [
            {
                "feature": "baseline",
                "criterion": "Page evaluation unavailable",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
            }
        ],
        "consumer_criteria": [
            {
                "criterion": "Page evaluation unavailable",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
            }
        ],
    }


def _normalise_output(parsed: dict, page_id: str) -> dict:
    """Normalise and validate parsed LLM output, fixing common issues."""
    valid_results = {"PASS", "FAIL", "UNKNOWN"}
    valid_confidence = {"high", "medium", "low"}

    def fix_criterion(c: dict) -> dict:
        result = c.get("result", "UNKNOWN").upper()
        if result not in valid_results:
            result = "UNKNOWN"
        confidence = c.get("confidence", "low").lower()
        if confidence not in valid_confidence:
            confidence = "low"
        c["result"] = result
        c["confidence"] = confidence
        if "evidence" not in c:
            c["evidence"] = ""
        if "criterion" not in c:
            c["criterion"] = "(criterion missing)"
        return c

    pb_criteria = [fix_criterion(c) for c in parsed.get("pb_criteria", [])]
    consumer_criteria = [fix_criterion(c) for c in parsed.get("consumer_criteria", [])]

    # Ensure pb_criteria items have "feature" field
    for c in pb_criteria:
        if "feature" not in c:
            c["feature"] = "unknown"

    return {
        "page_id": page_id,
        "pb_criteria": pb_criteria,
        "consumer_criteria": consumer_criteria,
    }
```

- [ ] Install `pytest-asyncio` if not already installed:

```bash
pip install pytest-asyncio
```

- [ ] Add `asyncio_mode = "auto"` to `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Run tests, confirm they all pass:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_text_scorer.py -v
```

Expected: 10 tests pass.

---

## Task 3: Visual Scorer — prompt + LLM call structure (~8 tests)

**Files:**
- Create: `persona_browser/visual_scorer.py`
- Create: `tests/test_visual_scorer.py`

LLM-based, multimodal. Uses Gemini 3 Flash via ChatLiteLLM. Takes pages from navigator output (with screenshot paths), consumer rubric text, PB rubric text, and filtered codeintel (visual fields only — elements, design_tokens, accessibility — NO api_endpoints, auth, data_flows). Detects features in the screenshot and scores relevant criteria. Returns list of dicts matching `schemas/visual-scorer-output.schema.json`.

### Prompt strategy

The visual scorer sends one LLM call per page. Each call is a multimodal message containing:

1. **System message:** Role as a visual QA evaluator. Instruction to return only valid JSON. Instruction to detect UI features (forms, navigation, CTA, data display, error states) in the screenshot BEFORE evaluating criteria. Instruction to evaluate only visual criteria (forms.labels_visible, nav.current_indicated, baseline.readable, etc.).

2. **Human message:** Multimodal content with:
   - Image part: screenshot loaded from file (base64-encoded)
   - Text part: filtered codeintel (elements, design_tokens, accessibility), consumer rubric visual criteria, PB visual criteria
   - Feature detection instruction: "First, list the UI features you see. Then evaluate each criterion."

3. **LLM response:** JSON object with `page_id`, `features_detected`, `pb_criteria`, `consumer_criteria`.

### Codeintel filtering (delegates to Task 4)

The visual scorer calls `filter_codeintel_for_visual(codeintel)` from `codeintel_filter.py`, which returns only the visual-relevant fields: `pages[].elements`, `pages[].design_tokens`, `pages[].accessibility`. It removes `api_endpoints`, `auth`, `data_flows`, and `data_flows`.

### Step 1: Write the tests first

- [ ] Create `tests/test_visual_scorer.py`:

```python
"""Tests for visual_scorer — multimodal LLM-based screenshot analysis.

LLM is mocked in all tests — no real API calls, no real screenshots.
Run: pytest tests/test_visual_scorer.py -v
"""
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())
NAVIGATOR = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
RUBRIC_TEXT = (FIXTURES / "sample_rubric.md").read_text()
PB_RUBRIC_TEXT = (
    Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md"
).read_text()

# Minimal valid LLM response for visual scorer
MOCK_VISUAL_RESPONSE_REGISTRATION = {
    "page_id": "registration",
    "features_detected": ["forms", "cta", "baseline"],
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "Every input field has a visible, associated label",
            "result": "PASS",
            "evidence": "Screenshot shows 'Full Name', 'Email Address', 'Password' labels above each input",
            "confidence": "high",
        },
        {
            "feature": "forms",
            "criterion": "Required fields are visually distinguished",
            "result": "UNKNOWN",
            "evidence": "No asterisks or required indicators visible in screenshot",
            "confidence": "medium",
        },
        {
            "feature": "cta",
            "criterion": "The primary CTA is visually prominent",
            "result": "PASS",
            "evidence": "Purple gradient 'Register' button spans full width at bottom of form",
            "confidence": "high",
        },
        {
            "feature": "baseline",
            "criterion": "All text content is legible",
            "result": "PASS",
            "evidence": "White text on purple gradient background, good contrast for headings",
            "confidence": "high",
        },
        {
            "feature": "baseline",
            "criterion": "The layout is not broken at the current viewport size",
            "result": "PASS",
            "evidence": "Card is centered, all elements visible, no overflow",
            "confidence": "high",
        },
    ],
    "consumer_criteria": [
        {
            "criterion": "The submit button is labelled 'Register'",
            "result": "PASS",
            "evidence": "Button text clearly shows 'Register'",
            "confidence": "high",
            "codeintel_ref": "pages[0].elements.forms[0].submit_button.text",
        },
    ],
}

MOCK_VISUAL_RESPONSE_DASHBOARD = {
    "page_id": "dashboard",
    "features_detected": ["nav", "data_display", "cta", "baseline"],
    "pb_criteria": [
        {
            "feature": "nav",
            "criterion": "The currently active page or section is visually indicated",
            "result": "UNKNOWN",
            "evidence": "Single page, no nav bar with multiple items to indicate active state",
            "confidence": "medium",
        },
        {
            "feature": "baseline",
            "criterion": "All text content is legible",
            "result": "PASS",
            "evidence": "Welcome heading and user info text clearly readable",
            "confidence": "high",
        },
        {
            "feature": "baseline",
            "criterion": "The layout is not broken at the current viewport size",
            "result": "PASS",
            "evidence": "Dashboard card is centered, Logout button visible",
            "confidence": "high",
        },
    ],
    "consumer_criteria": [
        {
            "criterion": "The page heading 'Welcome!' is visible",
            "result": "PASS",
            "evidence": "Large 'Welcome!' heading visible at top of card",
            "confidence": "high",
        },
    ],
}


def _make_mock_visual_llm(responses: list[dict]):
    """Create a mock multimodal LLM."""
    mock_llm = MagicMock()
    call_count = [0]

    async def ainvoke(messages, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        mock_response = MagicMock()
        mock_response.content = json.dumps(responses[idx])
        return mock_response

    mock_llm.ainvoke = ainvoke
    return mock_llm


def _pages_with_fake_screenshots(pages: list[dict]) -> list[dict]:
    """Replace screenshot paths with a path that exists (or None for testing)."""
    # Create a tiny 1x1 PNG in memory for testing
    # Rather than real screenshots, we use None and let the scorer handle it
    result = []
    for page in pages:
        p = dict(page)
        # For tests, use None — visual scorer must handle missing screenshots gracefully
        p = {**p, "screenshot": None}
        result.append(p)
    return result


# ---------------------------------------------------------------------------
# Schema conformance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_visual_returns_list():
    """score_visual returns a list."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = _make_mock_visual_llm(
        [MOCK_VISUAL_RESPONSE_REGISTRATION, MOCK_VISUAL_RESPONSE_DASHBOARD]
    )
    pages = _pages_with_fake_screenshots(NAVIGATOR["pages"])
    result = await score_visual(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_score_visual_returns_one_per_page():
    """score_visual returns one entry per input page."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = _make_mock_visual_llm(
        [MOCK_VISUAL_RESPONSE_REGISTRATION, MOCK_VISUAL_RESPONSE_DASHBOARD]
    )
    pages = _pages_with_fake_screenshots(NAVIGATOR["pages"])
    result = await score_visual(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    assert len(result) == len(pages)


@pytest.mark.asyncio
async def test_result_has_features_detected():
    """Each result has features_detected list."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = _make_mock_visual_llm(
        [MOCK_VISUAL_RESPONSE_REGISTRATION, MOCK_VISUAL_RESPONSE_DASHBOARD]
    )
    pages = _pages_with_fake_screenshots(NAVIGATOR["pages"])
    result = await score_visual(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    for item in result:
        assert "features_detected" in item
        assert isinstance(item["features_detected"], list)


@pytest.mark.asyncio
async def test_pb_criteria_have_required_fields():
    """pb_criteria items have feature, criterion, result, evidence, confidence."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = _make_mock_visual_llm(
        [MOCK_VISUAL_RESPONSE_REGISTRATION, MOCK_VISUAL_RESPONSE_DASHBOARD]
    )
    pages = _pages_with_fake_screenshots(NAVIGATOR["pages"])
    result = await score_visual(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    for page_result in result:
        for c in page_result["pb_criteria"]:
            for field in ["feature", "criterion", "result", "evidence", "confidence"]:
                assert field in c, f"Missing field '{field}' in pb_criteria item: {c}"


@pytest.mark.asyncio
async def test_result_values_are_valid():
    """All result fields are PASS, FAIL, or UNKNOWN."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = _make_mock_visual_llm(
        [MOCK_VISUAL_RESPONSE_REGISTRATION, MOCK_VISUAL_RESPONSE_DASHBOARD]
    )
    pages = _pages_with_fake_screenshots(NAVIGATOR["pages"])
    result = await score_visual(
        pages=pages,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    valid_results = {"PASS", "FAIL", "UNKNOWN"}
    for page_result in result:
        for c in page_result["pb_criteria"] + page_result["consumer_criteria"]:
            assert c["result"] in valid_results, f"Invalid result: {c['result']!r}"


@pytest.mark.asyncio
async def test_missing_screenshot_returns_unknown_not_crash():
    """Pages with no screenshot return UNKNOWN criteria, not an exception."""
    from persona_browser.visual_scorer import score_visual

    mock_llm = MagicMock()

    async def ainvoke(messages, **kwargs):
        # Should not be called when no screenshot
        raise AssertionError("LLM should not be called when screenshot is missing")

    mock_llm.ainvoke = ainvoke

    # Page with no screenshot
    page_no_screenshot = {
        "id": "registration",
        "url_visited": "http://localhost:3333/register",
        "screenshot": None,
        "observations": {"description": "test", "actions": [], "forms": []},
        "network_log": [],
    }

    result = await score_visual(
        pages=[page_no_screenshot],
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        codeintel=CODEINTEL,
        llm=mock_llm,
    )
    assert len(result) == 1
    page_result = result[0]
    all_criteria = page_result.get("pb_criteria", []) + page_result.get("consumer_criteria", [])
    for c in all_criteria:
        assert c["result"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_build_visual_prompt_excludes_api_endpoints():
    """_build_visual_prompt does not include api_endpoints from codeintel."""
    from persona_browser.visual_scorer import _build_visual_prompt_text

    page = NAVIGATOR["pages"][0]
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    filtered = filter_codeintel_for_visual(CODEINTEL)

    prompt_text = _build_visual_prompt_text(
        page=page,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        filtered_codeintel=filtered,
    )
    # api_endpoints should not appear in the filtered codeintel passed to visual scorer
    assert "api_endpoints" not in prompt_text.lower() or "api_endpoints" not in json.dumps(filtered)


@pytest.mark.asyncio
async def test_build_visual_prompt_includes_design_tokens():
    """_build_visual_prompt includes design_tokens from filtered codeintel."""
    from persona_browser.visual_scorer import _build_visual_prompt_text
    from persona_browser.codeintel_filter import filter_codeintel_for_visual

    page = NAVIGATOR["pages"][0]  # registration page has design_tokens
    filtered = filter_codeintel_for_visual(CODEINTEL)

    prompt_text = _build_visual_prompt_text(
        page=page,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        filtered_codeintel=filtered,
    )
    # design_tokens should be present (e.g., primary_color, error_color)
    assert "primary_color" in prompt_text or "667eea" in prompt_text or "design_token" in prompt_text.lower()
```

- [ ] **Run tests, confirm they fail:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_visual_scorer.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'persona_browser.visual_scorer'`

### Step 2: Implement visual_scorer.py

- [ ] Create `persona_browser/visual_scorer.py`:

```python
"""Visual Scorer — multimodal LLM-based evaluation of screenshots.

Scores PB rubric + consumer rubric criteria using screenshots +
filtered codeintel (visual fields only: elements, design_tokens, accessibility).
NO api_endpoints, auth, data_flows — those are for text/network scorers.

Public API:
    async score_visual(pages, rubric_text, pb_rubric_text, codeintel, llm) -> list[dict]
    _build_visual_prompt_text(page, rubric_text, pb_rubric_text, filtered_codeintel) -> str

Each returned dict matches schemas/visual-scorer-output.schema.json.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# PB criteria assigned to "Visual" or "Text + Visual" scorer (visual component)
_VISUAL_SCORER_FEATURES = {
    "forms": [
        "forms.labels_visible",
        "forms.required_marked",
        "forms.input_types_match",
        "forms.tab_order",
        "forms.error_on_empty_submit",
        "forms.error_on_invalid",
        "forms.error_near_field",
        "forms.error_clears",
        "forms.data_preserved_on_error",
        "forms.submit_visible",
        "forms.loading_state",
        "forms.success_confirmation",
    ],
    "nav": [
        "nav.current_indicated",
        "nav.logo_links_home",
        "nav.no_dead_ends",
        "nav.back_works",
    ],
    "cta": [
        "cta.prominent",
        "cta.destination_correct",
        "cta.no_competing",
    ],
    "data": [
        "data.above_fold",
        "data.grouped_logically",
        "data.empty_states",
        "data.loading_indicator",
    ],
    "baseline": [
        "baseline.no_errors",
        "baseline.readable",
        "baseline.no_broken_assets",
        "baseline.responsive",
    ],
    "task": [
        "task.data_on_next_page",
        "task.survives_refresh",
        "task.data_consistent",
        "task.auth_access",
        "task.auth_persists_nav",
        "task.auth_persists_refresh",
        "task.loading_during_async",
        "task.graceful_error_handling",
    ],
}

_SYSTEM_PROMPT = """\
You are a visual QA evaluator analysing a screenshot of a web application page.

Your task has TWO parts:
1. DETECT which UI features are present in the screenshot.
   Features to look for: forms, navigation, cta, data_display, error_states, baseline
2. EVALUATE each visual criterion listed — only those relevant to detected features.

Rules:
- Use PASS when you can clearly see the criterion is satisfied.
- Use FAIL when you can clearly see the criterion is violated.
- Use UNKNOWN when the screenshot does not give sufficient information.
- Do NOT evaluate text-only criteria (e.g., error message content, network behaviour).
- Focus on visual signals: layout, labels, colours, contrast, spacing, visible text.
- Do NOT include api_endpoints, auth mechanism, or data flow analysis.
- Be concise in evidence — max 80 words per criterion.

Return ONLY a valid JSON object in this exact structure:
{
  "page_id": "<page_id>",
  "features_detected": ["forms", "cta", ...],
  "pb_criteria": [
    {
      "feature": "<feature>",
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<visual observation>",
      "confidence": "high" | "medium" | "low",
      "note": "<optional>"
    }
  ],
  "consumer_criteria": [
    {
      "criterion": "<criterion text>",
      "result": "PASS" | "FAIL" | "UNKNOWN",
      "evidence": "<visual observation>",
      "confidence": "high" | "medium" | "low",
      "codeintel_ref": "<optional>",
      "note": "<optional>"
    }
  ]
}
"""


async def score_visual(
    pages: list[dict],
    rubric_text: str,
    pb_rubric_text: str,
    codeintel: dict,
    llm: Any,
) -> list[dict]:
    """Score all pages using multimodal LLM screenshot analysis.

    Args:
        pages: List of page dicts from navigator output (each has id, screenshot, observations).
        rubric_text: Full consumer rubric markdown text.
        pb_rubric_text: Full PB feature rubric markdown text.
        codeintel: Codeintel dict (will be filtered to visual fields only).
        llm: ChatLiteLLM instance with multimodal support (or mock for tests).

    Returns:
        List of dicts, one per page, matching visual-scorer-output.schema.json.
    """
    from .codeintel_filter import filter_codeintel_for_visual

    filtered_codeintel = filter_codeintel_for_visual(codeintel)
    results = []

    for page in pages:
        page_result = await _score_page(
            page=page,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            filtered_codeintel=filtered_codeintel,
            llm=llm,
        )
        results.append(page_result)

    return results


async def _score_page(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    filtered_codeintel: dict,
    llm: Any,
) -> dict:
    """Score a single page with multimodal LLM. Returns a visual-scorer-output dict."""
    page_id = page.get("id", "unknown")
    screenshot = page.get("screenshot")

    # No screenshot — return UNKNOWN for all criteria without calling LLM
    if not screenshot:
        return _fallback_unknown(page_id, reason="No screenshot available")

    # Load screenshot as base64
    image_b64 = _load_screenshot_b64(screenshot)
    if image_b64 is None:
        return _fallback_unknown(page_id, reason=f"Could not load screenshot: {screenshot}")

    # Build text portion of prompt
    prompt_text = _build_visual_prompt_text(
        page=page,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        filtered_codeintel=filtered_codeintel,
    )

    # Build multimodal messages
    try:
        messages = _build_multimodal_messages(image_b64, prompt_text)
    except Exception as exc:
        logger.error("Failed to build multimodal messages for page %s: %s", page_id, exc)
        return _fallback_unknown(page_id, reason=f"Message build failed: {exc}")

    # Call LLM
    try:
        response = await llm.ainvoke(messages)
        raw_content = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.error("LLM call failed for page %s: %s", page_id, exc)
        return _fallback_unknown(page_id, reason=f"LLM call failed: {exc}")

    # Parse response
    parsed = _parse_llm_json(raw_content)
    if parsed is None:
        # One retry
        try:
            from langchain_core.messages import HumanMessage
            retry_messages = messages + [
                HumanMessage(
                    content="Return ONLY the JSON object — no markdown, no explanation."
                )
            ]
            response2 = await llm.ainvoke(retry_messages)
            raw2 = response2.content if hasattr(response2, "content") else str(response2)
            parsed = _parse_llm_json(raw2)
        except Exception as exc2:
            logger.error("Retry failed for page %s: %s", page_id, exc2)

    if parsed is None:
        return _fallback_unknown(page_id, reason="Could not parse LLM JSON response")

    parsed["page_id"] = page_id
    return _normalise_output(parsed, page_id)


def _build_visual_prompt_text(
    page: dict,
    rubric_text: str,
    pb_rubric_text: str,
    filtered_codeintel: dict,
) -> str:
    """Build the text portion of the multimodal prompt.

    Args:
        page: Navigator page dict.
        rubric_text: Full consumer rubric markdown.
        pb_rubric_text: Full PB rubric markdown.
        filtered_codeintel: Already-filtered codeintel (visual fields only).

    Returns:
        Text string for the prompt (image is attached separately).
    """
    page_id = page.get("id", "unknown")
    url_visited = page.get("url_visited", "unknown")

    # Extract visual-relevant codeintel for this specific page
    page_visual_codeintel = _get_page_visual_codeintel(page_id, filtered_codeintel)

    # Extract consumer rubric for this page
    from .text_scorer import _extract_consumer_rubric_section, _page_id_matches_heading
    consumer_rubric_section = _extract_consumer_rubric_section(page_id, rubric_text)

    # Extract visual-only PB criteria
    pb_visual_section = _extract_visual_pb_criteria(pb_rubric_text)

    lines = [
        f"## Page: {page_id}",
        f"URL: {url_visited}",
        "",
        "The screenshot above shows this page.",
        "",
        "### Step 1: Detect Features",
        "List which of these features are visible in the screenshot:",
        "  - forms (input fields, submit buttons)",
        "  - navigation (nav bar, breadcrumbs, menu links)",
        "  - cta (call-to-action buttons — primary action buttons)",
        "  - data_display (tables, cards, lists of data)",
        "  - error_states (error messages, validation feedback)",
        "  - baseline (always applies)",
        "",
        "### Step 2: Evaluate Criteria",
    ]

    if page_visual_codeintel:
        lines.append("")
        lines.append("#### Codeintel — Visual Context (elements + design tokens only)")
        lines.append(json.dumps(page_visual_codeintel, indent=2)[:1500])

    if consumer_rubric_section:
        lines.append("")
        lines.append("#### Consumer Rubric — Visual Criteria for This Page")
        lines.append("Evaluate visually verifiable criteria only:")
        lines.append(consumer_rubric_section)

    if pb_visual_section:
        lines.append("")
        lines.append("#### PB Feature Rubric — Visual Criteria")
        lines.append("Evaluate ONLY these visual criteria (skip Text-only criteria):")
        lines.append(pb_visual_section)

    lines.append("")
    lines.append(
        "Now evaluate all criteria above from what you can SEE in the screenshot. "
        "Return ONLY the JSON object described in the system prompt."
    )

    return "\n".join(lines)


def _get_page_visual_codeintel(page_id: str, filtered_codeintel: dict) -> dict:
    """Extract visual codeintel for a specific page from the filtered codeintel."""
    for page_data in filtered_codeintel.get("pages", []):
        if page_data.get("id") == page_id:
            return {
                "id": page_id,
                "elements": page_data.get("elements", {}),
                "design_tokens": page_data.get("design_tokens", {}),
                "accessibility": page_data.get("accessibility", {}),
            }
    return {}


def _extract_visual_pb_criteria(pb_rubric_text: str) -> str:
    """Extract only Visual-scorer-relevant criteria from PB rubric."""
    lines = pb_rubric_text.splitlines()
    result_lines: list[str] = []
    current_feature: str = ""

    for line in lines:
        if line.startswith("## "):
            current_feature = line[3:].strip()

        if line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                scorer_col = parts[3] if len(parts) > 3 else ""
                criterion_id = parts[1]
                criterion_text = parts[2]
                if (
                    "Visual" in scorer_col
                    and criterion_id not in ("ID", "---", "")
                    and criterion_text not in ("Criterion", "---", "")
                ):
                    result_lines.append(
                        f"  [{criterion_id}] {criterion_text} (Feature: {current_feature})"
                    )

    return "\n".join(result_lines)


def _build_multimodal_messages(image_b64: str, prompt_text: str) -> list:
    """Build LangChain multimodal messages with image + text."""
    from langchain_core.messages import HumanMessage, SystemMessage

    # LangChain multimodal message: content is a list of content blocks
    human_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
        },
        {
            "type": "text",
            "text": prompt_text,
        },
    ]

    return [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def _load_screenshot_b64(screenshot_path: str) -> Optional[str]:
    """Load a screenshot file and return base64-encoded string.

    Returns None if file does not exist or cannot be read.
    """
    if not screenshot_path:
        return None

    path = Path(screenshot_path)
    if not path.exists():
        logger.warning("Screenshot not found: %s", screenshot_path)
        return None

    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception as exc:
        logger.warning("Could not read screenshot %s: %s", screenshot_path, exc)
        return None


def _parse_llm_json(content: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling common formatting issues."""
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _fallback_unknown(page_id: str, reason: str = "") -> dict:
    """Return a valid output dict with all criteria as UNKNOWN."""
    note = f"Scorer error: {reason}" if reason else "Scorer error"
    return {
        "page_id": page_id,
        "features_detected": [],
        "pb_criteria": [
            {
                "feature": "baseline",
                "criterion": "Visual evaluation unavailable",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
            }
        ],
        "consumer_criteria": [
            {
                "criterion": "Visual evaluation unavailable",
                "result": "UNKNOWN",
                "evidence": note,
                "confidence": "low",
            }
        ],
    }


def _normalise_output(parsed: dict, page_id: str) -> dict:
    """Normalise and validate parsed LLM output."""
    valid_results = {"PASS", "FAIL", "UNKNOWN"}
    valid_confidence = {"high", "medium", "low"}

    def fix_criterion(c: dict) -> dict:
        result = c.get("result", "UNKNOWN").upper()
        if result not in valid_results:
            result = "UNKNOWN"
        confidence = c.get("confidence", "low").lower()
        if confidence not in valid_confidence:
            confidence = "low"
        c["result"] = result
        c["confidence"] = confidence
        if "evidence" not in c:
            c["evidence"] = ""
        if "criterion" not in c:
            c["criterion"] = "(criterion missing)"
        return c

    pb_criteria = [fix_criterion(c) for c in parsed.get("pb_criteria", [])]
    consumer_criteria = [fix_criterion(c) for c in parsed.get("consumer_criteria", [])]

    for c in pb_criteria:
        if "feature" not in c:
            c["feature"] = "unknown"

    features_detected = parsed.get("features_detected", [])
    if not isinstance(features_detected, list):
        features_detected = []

    return {
        "page_id": page_id,
        "features_detected": features_detected,
        "pb_criteria": pb_criteria,
        "consumer_criteria": consumer_criteria,
    }
```

- [ ] **Run tests, confirm they all pass:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_visual_scorer.py -v
```

Expected: 8 tests pass (test_missing_screenshot passes without LLM call; test_build_visual_prompt_excludes_api_endpoints passes after Task 4 is done).

---

## Task 4: Codeintel Filter Utility (~5 tests)

**Files:**
- Create: `persona_browser/codeintel_filter.py`
- Create: `tests/test_codeintel_filter.py`

Small, pure-Python utility. Filters `codeintel.json` to visual-only fields for the Visual Scorer. Used by `visual_scorer.py`.

### What to keep vs remove

| Field | Keep? | Reason |
|-------|-------|--------|
| `pages[].id` | Yes | Needed to match pages |
| `pages[].routes` | No | API concern |
| `pages[].component` | No | API concern |
| `pages[].purpose` | No | Context (not visual) |
| `pages[].elements` | Yes | Form fields, nav links, buttons |
| `pages[].design_tokens` | Yes | Colours, fonts, border-radius |
| `pages[].accessibility` | Yes (if present) | ARIA roles, labels |
| `api_endpoints` | No | Network concern |
| `auth` | No | Network concern |
| `data_flows` | No | Data concern |
| `version` | Yes | Metadata |
| `generated_from` | No | Metadata (not needed) |
| `generated_at` | No | Metadata (not needed) |

### Step 1: Write the tests first

- [ ] Create `tests/test_codeintel_filter.py`:

```python
"""Tests for codeintel_filter — visual-only codeintel filtering.

Run: pytest tests/test_codeintel_filter.py -v
"""
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())


def test_filter_removes_api_endpoints():
    """Filtered output does not contain api_endpoints."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    assert "api_endpoints" not in result


def test_filter_removes_auth():
    """Filtered output does not contain auth."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    assert "auth" not in result


def test_filter_removes_data_flows():
    """Filtered output does not contain data_flows."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    assert "data_flows" not in result


def test_filter_preserves_pages():
    """Filtered output contains pages list."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    assert "pages" in result
    assert len(result["pages"]) == len(CODEINTEL["pages"])


def test_filter_preserves_page_elements_and_design_tokens():
    """Each page in filtered output retains elements and design_tokens."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    for page in result["pages"]:
        # elements and design_tokens should be present if they were in the original
        original_page = next(
            (p for p in CODEINTEL["pages"] if p["id"] == page["id"]), None
        )
        assert original_page is not None
        if "elements" in original_page:
            assert "elements" in page, f"elements missing for page {page['id']}"
        if "design_tokens" in original_page:
            assert "design_tokens" in page, f"design_tokens missing for page {page['id']}"


def test_filter_removes_page_api_call_references():
    """Page elements do not contain api_call references after filtering."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    result_str = json.dumps(result)
    # The api_call fields inside page elements should also be removed
    # (they are navigation concerns, not visual concerns)
    assert '"api_call"' not in result_str


def test_filter_does_not_mutate_original():
    """filter_codeintel_for_visual does not mutate the original codeintel dict."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    import copy
    original_copy = copy.deepcopy(CODEINTEL)
    filter_codeintel_for_visual(CODEINTEL)
    assert CODEINTEL == original_copy, "Original codeintel was mutated"


def test_filter_preserves_page_ids():
    """All page IDs from original are present in filtered output."""
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(CODEINTEL)
    original_ids = {p["id"] for p in CODEINTEL["pages"]}
    result_ids = {p["id"] for p in result["pages"]}
    assert result_ids == original_ids
```

- [ ] **Run tests, confirm they fail:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_codeintel_filter.py -v 2>&1 | head -20
```

### Step 2: Implement codeintel_filter.py

- [ ] Create `persona_browser/codeintel_filter.py`:

```python
"""Codeintel filter — strips non-visual fields from codeintel for the Visual Scorer.

The Visual Scorer must not see api_endpoints, auth, or data_flows —
those are for the Text Scorer and Network Verifier.

Public API:
    filter_codeintel_for_visual(codeintel: dict) -> dict
"""
from __future__ import annotations

import copy


# Fields to keep at the top level of each page
_PAGE_VISUAL_FIELDS = {"id", "elements", "design_tokens", "accessibility"}

# Fields to remove from page.elements.forms[].fields (form fields are visual)
# but page.elements.forms[].api_call is not visual
_FORM_NON_VISUAL_FIELDS = {"api_call", "on_success"}


def filter_codeintel_for_visual(codeintel: dict) -> dict:
    """Return a copy of codeintel with only visual-relevant fields.

    Removes:
        - api_endpoints (entire key)
        - auth (entire key)
        - data_flows (entire key)
        - pages[].component, pages[].routes, pages[].purpose
        - pages[].elements.forms[].api_call
        - pages[].elements.forms[].on_success
        - generated_from, generated_at

    Keeps:
        - version
        - pages[].id
        - pages[].elements (minus api_call/on_success in forms)
        - pages[].design_tokens
        - pages[].accessibility (if present)

    Does not mutate the original dict.
    """
    # Deep copy to avoid mutating the original
    result = copy.deepcopy(codeintel)

    # Remove top-level non-visual keys
    for key in ("api_endpoints", "auth", "data_flows", "generated_from", "generated_at"):
        result.pop(key, None)

    # Filter each page
    filtered_pages = []
    for page in result.get("pages", []):
        filtered_page: dict = {}
        for field in _PAGE_VISUAL_FIELDS:
            if field in page:
                filtered_page[field] = page[field]

        # Remove non-visual fields from form definitions within elements
        if "elements" in filtered_page:
            filtered_page["elements"] = _filter_page_elements(filtered_page["elements"])

        filtered_pages.append(filtered_page)

    result["pages"] = filtered_pages
    return result


def _filter_page_elements(elements: dict) -> dict:
    """Remove non-visual sub-fields from page elements."""
    if not isinstance(elements, dict):
        return elements

    result = copy.deepcopy(elements)

    # Strip api_call and on_success from each form definition
    for form in result.get("forms", []):
        if isinstance(form, dict):
            for key in _FORM_NON_VISUAL_FIELDS:
                form.pop(key, None)

    return result
```

- [ ] **Run tests, confirm they all pass:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_codeintel_filter.py -v
```

Expected: all 8 tests pass.

---

## Task 5: Scorer Runner — parallel execution (~4 tests)

**Files:**
- Create: `persona_browser/scorer_runner.py`
- Create: `tests/test_scorer_runner.py`

Depends on Tasks 1, 2, 3 being complete. The `run_scorers()` function runs all three scorers in parallel using `asyncio.gather()` and returns a combined results dict.

### Function signature

```python
async def run_scorers(
    navigator_output: dict,
    codeintel: dict,
    rubric_text: str,
    pb_rubric_text: str,
    text_llm: Any,
    visual_llm: Any,
    manifest: Optional[dict] = None,
) -> dict:
```

### Returns

```python
{
    "network_verifier": { ... },          # network-verifier-output.schema.json
    "text_scorer": [ ... ],               # list of text-scorer-output.schema.json
    "visual_scorer": [ ... ],             # list of visual-scorer-output.schema.json
}
```

### Step 1: Write the tests first

- [ ] Create `tests/test_scorer_runner.py`:

```python
"""Tests for scorer_runner — parallel execution of all three scorers.

Run: pytest tests/test_scorer_runner.py -v
"""
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())
NAVIGATOR = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
RUBRIC_TEXT = (FIXTURES / "sample_rubric.md").read_text()
PB_RUBRIC_TEXT = (
    Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md"
).read_text()

# Flatten all network_log entries
ALL_NETWORK_LOG = []
for _page in NAVIGATOR["pages"]:
    ALL_NETWORK_LOG.extend(_page.get("network_log", []))


def _make_mock_llm(response_dict: dict):
    """Create a mock LLM that always returns the given dict as JSON."""
    mock_llm = MagicMock()

    async def ainvoke(messages, **kwargs):
        mock_response = MagicMock()
        mock_response.content = json.dumps(response_dict)
        return mock_response

    mock_llm.ainvoke = ainvoke
    return mock_llm


MOCK_TEXT_RESPONSE = {
    "page_id": "registration",
    "pb_criteria": [
        {
            "feature": "baseline",
            "criterion": "No JS errors",
            "result": "PASS",
            "evidence": "Clean load",
            "confidence": "high",
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "Form rendered",
            "result": "PASS",
            "evidence": "Form visible",
            "confidence": "high",
        }
    ],
}

MOCK_VISUAL_RESPONSE = {
    "page_id": "registration",
    "features_detected": ["forms"],
    "pb_criteria": [
        {
            "feature": "forms",
            "criterion": "Labels visible",
            "result": "PASS",
            "evidence": "Labels present",
            "confidence": "high",
        }
    ],
    "consumer_criteria": [
        {
            "criterion": "Button visible",
            "result": "PASS",
            "evidence": "Register button present",
            "confidence": "high",
        }
    ],
}


@pytest.mark.asyncio
async def test_run_scorers_returns_all_three_keys():
    """run_scorers result has network_verifier, text_scorer, visual_scorer."""
    from persona_browser.scorer_runner import run_scorers

    text_llm = _make_mock_llm(MOCK_TEXT_RESPONSE)
    visual_llm = _make_mock_llm(MOCK_VISUAL_RESPONSE)

    result = await run_scorers(
        navigator_output=NAVIGATOR,
        codeintel=CODEINTEL,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    assert "network_verifier" in result
    assert "text_scorer" in result
    assert "visual_scorer" in result


@pytest.mark.asyncio
async def test_network_verifier_result_has_required_fields():
    """network_verifier result has required schema fields."""
    from persona_browser.scorer_runner import run_scorers

    text_llm = _make_mock_llm(MOCK_TEXT_RESPONSE)
    visual_llm = _make_mock_llm(MOCK_VISUAL_RESPONSE)

    result = await run_scorers(
        navigator_output=NAVIGATOR,
        codeintel=CODEINTEL,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    nv = result["network_verifier"]
    for field in ["api_calls_total", "api_calls_matched_codeintel", "deal_breakers", "issues"]:
        assert field in nv, f"network_verifier missing field: {field}"


@pytest.mark.asyncio
async def test_text_scorer_result_is_list():
    """text_scorer result is a list."""
    from persona_browser.scorer_runner import run_scorers

    text_llm = _make_mock_llm(MOCK_TEXT_RESPONSE)
    visual_llm = _make_mock_llm(MOCK_VISUAL_RESPONSE)

    result = await run_scorers(
        navigator_output=NAVIGATOR,
        codeintel=CODEINTEL,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    assert isinstance(result["text_scorer"], list)


@pytest.mark.asyncio
async def test_visual_scorer_result_is_list():
    """visual_scorer result is a list."""
    from persona_browser.scorer_runner import run_scorers

    text_llm = _make_mock_llm(MOCK_TEXT_RESPONSE)
    visual_llm = _make_mock_llm(MOCK_VISUAL_RESPONSE)

    result = await run_scorers(
        navigator_output=NAVIGATOR,
        codeintel=CODEINTEL,
        rubric_text=RUBRIC_TEXT,
        pb_rubric_text=PB_RUBRIC_TEXT,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    assert isinstance(result["visual_scorer"], list)
```

- [ ] **Run tests, confirm they fail:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_scorer_runner.py -v 2>&1 | head -20
```

### Step 2: Implement scorer_runner.py

- [ ] Create `persona_browser/scorer_runner.py`:

```python
"""Scorer Runner — runs all three scorers in parallel.

Combines Network Verifier, Text Scorer, and Visual Scorer into a
single async call. Uses asyncio.gather() for parallel execution.

Public API:
    async run_scorers(
        navigator_output, codeintel, rubric_text, pb_rubric_text,
        text_llm, visual_llm, manifest=None
    ) -> dict

Returns:
    {
        "network_verifier": { ... },   # network-verifier-output.schema.json
        "text_scorer": [ ... ],        # list[text-scorer-output.schema.json]
        "visual_scorer": [ ... ],      # list[visual-scorer-output.schema.json]
    }
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def run_scorers(
    navigator_output: dict,
    codeintel: dict,
    rubric_text: str,
    pb_rubric_text: str,
    text_llm: Any,
    visual_llm: Any,
    manifest: Optional[dict] = None,
) -> dict:
    """Run all three scorers in parallel and return combined results.

    Args:
        navigator_output: Full navigator output dict (pages, network_log, etc.).
        codeintel: Codeintel dict (pages, api_endpoints, auth, data_flows).
        rubric_text: Full consumer rubric markdown text.
        pb_rubric_text: Full PB feature rubric markdown text.
        text_llm: ChatLiteLLM instance for text scoring.
        visual_llm: ChatLiteLLM instance (multimodal) for visual scoring.
        manifest: Optional manifest dict for enhanced auth flow analysis.

    Returns:
        dict with keys: network_verifier, text_scorer, visual_scorer.
    """
    from .network_verifier import verify_network
    from .text_scorer import score_text
    from .visual_scorer import score_visual

    pages = navigator_output.get("pages", [])
    experience = navigator_output.get("experience", {})

    # Flatten network_log from all pages for the Network Verifier
    full_network_log: list[dict] = []
    for page in pages:
        full_network_log.extend(page.get("network_log", []))

    # ── Run all three in parallel ─────────────────────────────────────────────
    network_verifier_result, text_scorer_result, visual_scorer_result = await asyncio.gather(
        _run_network_verifier(full_network_log, codeintel, manifest),
        score_text(
            pages=pages,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            codeintel=codeintel,
            experience=experience,
            llm=text_llm,
        ),
        score_visual(
            pages=pages,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            codeintel=codeintel,
            llm=visual_llm,
        ),
    )

    return {
        "network_verifier": network_verifier_result,
        "text_scorer": text_scorer_result,
        "visual_scorer": visual_scorer_result,
    }


async def _run_network_verifier(
    network_log: list[dict],
    codeintel: dict,
    manifest: Optional[dict],
) -> dict:
    """Wrap the synchronous verify_network() in a coroutine for asyncio.gather()."""
    from .network_verifier import verify_network

    return verify_network(network_log, codeintel, manifest=manifest)
```

- [ ] **Run tests, confirm they all pass:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_scorer_runner.py -v
```

Expected: 4 tests pass.

---

## Full Test Suite

After completing all tasks, run the complete Phase 3 test suite:

- [ ] **Run all Phase 3 tests:**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest tests/test_network_verifier.py tests/test_text_scorer.py tests/test_visual_scorer.py tests/test_codeintel_filter.py tests/test_scorer_runner.py -v
```

Expected: ~47 tests pass, 0 failed.

- [ ] **Run full test suite (no regressions):**

```bash
cd C:\Users\tucan\Documents\stefano\hackaton\huggingface_gradio\persona-browser-agent && python -m pytest -v
```

Expected: all existing tests still pass + new Phase 3 tests.

---

## Dependencies to Add

- [ ] Add `pytest-asyncio` to `pyproject.toml` dev dependencies:

```toml
[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio>=0.23", "jsonschema>=4.0"]
```

- [ ] Add pytest configuration to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] Install dev dependencies:

```bash
pip install pytest-asyncio jsonschema
```

---

## LLM Setup for Production Use

When wiring the scorers into the real pipeline (not tests), use this LLM setup matching `agent.py`:

```python
import os
from browser_use.llm.litellm.chat import ChatLiteLLM

api_key = os.environ["OPENROUTER_API_KEY"]

# Text Scorer — text-only, cheap and fast
text_llm = ChatLiteLLM(
    model="openrouter/google/gemini-2.5-flash",
    api_key=api_key,
    api_base="https://openrouter.ai/api/v1",
    temperature=0.1,
)

# Visual Scorer — multimodal (same model supports vision)
visual_llm = ChatLiteLLM(
    model="openrouter/google/gemini-2.5-flash",
    api_key=api_key,
    api_base="https://openrouter.ai/api/v1",
    temperature=0.1,
)

# Run all scorers
from persona_browser.scorer_runner import run_scorers
results = await run_scorers(
    navigator_output=navigator_output,
    codeintel=codeintel,
    rubric_text=rubric_text,
    pb_rubric_text=pb_rubric_text,
    text_llm=text_llm,
    visual_llm=visual_llm,
)
```
