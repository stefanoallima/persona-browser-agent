"""
persona_browser/network_verifier.py

Deterministic Network Verifier — no LLM.

Cross-references navigator network_log entries against codeintel.api_endpoints
to verify API contracts, auth flow integrity, and catch wiring errors.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


# Patterns that are safe to ignore when unmatched against codeintel.
# These are common browser/framework requests, not app API calls.
_SAFE_UNMATCHED_PATTERNS = [
    r"/favicon\.ico$",
    r"/manifest\.json$",
    r"/robots\.txt$",
    r"/sitemap\.xml$",
    r"/\.well-known/",
    r"/__webpack",
    r"/_next/",
    r"/hot-update",
    r"/sockjs-node",
    r"/ws$",
]
_SAFE_UNMATCHED_RE = re.compile("|".join(_SAFE_UNMATCHED_PATTERNS))


def verify_network(
    network_log: list[dict],
    codeintel: dict,
    manifest: dict | None = None,
) -> dict:
    """
    Verify network log entries against codeintel API contract definitions.

    Parameters
    ----------
    network_log:
        Flat list of network log entry dicts (already flattened from all pages).
    codeintel:
        Parsed codeintel dict containing ``api_endpoints`` and ``auth`` sections.
    manifest:
        Optional manifest dict (unused currently, reserved for future use).

    Returns
    -------
    dict matching the network-verifier-output.schema.json shape.
    """
    api_endpoints: list[dict] = codeintel.get("api_endpoints", [])
    auth_info: dict = codeintel.get("auth", {})

    # Build a lookup: (METHOD, normalized_path) -> endpoint definition
    endpoint_lookup: dict[tuple[str, str], dict] = {}
    for ep in api_endpoints:
        key = (ep["method"].upper(), _normalize_path(ep["path"]))
        endpoint_lookup[key] = ep

    # Filter to only /api/ entries
    api_entries = [e for e in network_log if "/api/" in e.get("url", "")]

    api_calls_total = len(api_entries)
    api_calls_matched = 0
    api_calls_unmatched = 0
    api_errors_during_normal_flow = 0
    deal_breakers: list[str] = []
    issues: list[str] = []
    per_endpoint: list[dict] = []

    for entry in api_entries:
        method = entry.get("method", "").upper()
        url = entry.get("url", "")
        path = _normalize_path(urlparse(url).path)
        status = entry.get("status", 0)
        request_headers_note = entry.get("request_headers_note") or ""

        key = (method, path)
        matched_ep = endpoint_lookup.get(key)

        matched_codeintel = matched_ep is not None

        if matched_codeintel:
            api_calls_matched += 1
            expected_statuses = [int(s) for s in matched_ep.get("responses", {}).keys()]
            # Accept ANY of the documented status codes as a valid contract match
            contract_match = status in expected_statuses if expected_statuses else False
            # Report expected_status as the closest match, or first if no exact match
            expected_status = status if contract_match else (expected_statuses[0] if expected_statuses else None)
            auth_required = matched_ep.get("auth_required", False)
            sets_auth = any(
                r.get("sets_auth") for r in matched_ep.get("responses", {}).values()
                if isinstance(r, dict)
            )
        else:
            api_calls_unmatched += 1
            expected_status = None
            contract_match = False
            auth_required = False
            sets_auth = False
            # Only report unmatched endpoints that aren't known safe patterns
            # (favicon, webpack HMR, etc.)
            if not _SAFE_UNMATCHED_RE.search(path):
                issues.append(f"Unmatched endpoint: {method} {path}")

        # Check for 500 errors — always a deal-breaker
        if status >= 500:
            deal_breakers.append(
                f"API returns 500 during normal user flow: {method} {path}"
            )

        # Check for 4xx errors on non-auth endpoints (unexpected failures)
        elif 400 <= status < 500:
            if auth_required and status == 401:
                # 401 on a protected endpoint when auth should be working
                issues.append(
                    f"auth handover failed: {method} {path} returned 401"
                )
            elif not sets_auth:
                # 4xx that isn't part of a deliberate auth/validation flow
                api_errors_during_normal_flow += 1

        # Determine auth_check for per_endpoint
        if not matched_codeintel:
            auth_check = "N/A (unknown endpoint)"
        elif not auth_required:
            auth_check = "N/A (public endpoint)"
        else:
            # Protected endpoint — check for Cookie or Authorization header
            has_auth_header = (
                "Cookie" in request_headers_note
                or "Authorization" in request_headers_note
            )
            if has_auth_header:
                auth_check = "PASS"
            else:
                auth_check = "FAIL"

        ep_entry: dict = {
            "method": method,
            "path": path,
            "matched_codeintel": matched_codeintel,
            "status": status,
        }
        if expected_status is not None:
            ep_entry["expected_status"] = expected_status
        if matched_codeintel:
            ep_entry["contract_match"] = contract_match
        ep_entry["auth_check"] = auth_check

        per_endpoint.append(ep_entry)

    # -----------------------------------------------------------------------
    # Auth flow checks
    # -----------------------------------------------------------------------

    # auth_token_set_after_auth:
    # Look for an entry whose matched endpoint has sets_auth=true in its 201 response
    # OR where set_cookie is present.
    auth_token_set_after_auth = _check_auth_token_set(api_entries, endpoint_lookup)

    # auth_token_sent_on_protected_requests:
    # Protected endpoints should have Cookie or Authorization in request_headers_note.
    auth_token_sent_on_protected = _check_auth_sent_on_protected(
        api_entries, endpoint_lookup
    )

    # auth_persists_after_refresh:
    # A protected endpoint called more than once where the later call returned 200.
    auth_persists_after_refresh = _check_auth_persists(api_entries, endpoint_lookup)

    return {
        "api_calls_total": api_calls_total,
        "api_calls_matched_codeintel": api_calls_matched,
        "api_calls_unmatched": api_calls_unmatched,
        "api_errors_during_normal_flow": api_errors_during_normal_flow,
        "auth_token_set_after_auth": auth_token_set_after_auth,
        "auth_token_sent_on_protected_requests": auth_token_sent_on_protected,
        "auth_persists_after_refresh": auth_persists_after_refresh,
        "deal_breakers": deal_breakers,
        "issues": issues,
        "per_endpoint": per_endpoint,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    """Normalize a URL path for comparison.

    Strips query parameters, fragments, and trailing slashes (but keeps root '/').
    This ensures /api/users?page=1 matches /api/users in codeintel.
    """
    # Strip query params and fragments
    parsed = urlparse(path)
    clean = parsed.path if parsed.scheme or parsed.netloc else path.split("?")[0].split("#")[0]
    # Strip trailing slash (but keep root)
    if clean and clean != "/" and clean.endswith("/"):
        clean = clean.rstrip("/")
    return clean


def _check_auth_token_set(
    api_entries: list[dict],
    endpoint_lookup: dict[tuple[str, str], dict],
) -> bool:
    """
    Return True if any network entry indicates an auth token was set.

    Detection heuristics (in priority order):
    1. Entry has a non-null ``set_cookie`` field.
    2. The matched endpoint has ``sets_auth: true`` in any of its response
       definitions AND the observed status matches that response's key.
    """
    for entry in api_entries:
        # Heuristic 1: explicit set_cookie capture
        if entry.get("set_cookie"):
            return True

        # Heuristic 2: matched endpoint with sets_auth
        method = entry.get("method", "").upper()
        path = _normalize_path(urlparse(entry.get("url", "")).path)
        ep = endpoint_lookup.get((method, path))
        if ep:
            status = entry.get("status", 0)
            for status_str, resp in ep.get("responses", {}).items():
                if isinstance(resp, dict) and resp.get("sets_auth"):
                    if status == int(status_str):
                        return True

    return False


def _check_auth_sent_on_protected(
    api_entries: list[dict],
    endpoint_lookup: dict[tuple[str, str], dict],
) -> bool:
    """
    Return True if ALL requests to auth-required endpoints carry an auth header.

    If there are no auth-required endpoints visited, returns True (vacuously).
    If at least one protected request is missing auth headers, return False.
    """
    protected_entries = []
    for entry in api_entries:
        method = entry.get("method", "").upper()
        path = _normalize_path(urlparse(entry.get("url", "")).path)
        ep = endpoint_lookup.get((method, path))
        if ep and ep.get("auth_required"):
            protected_entries.append(entry)

    if not protected_entries:
        return True

    for entry in protected_entries:
        note = entry.get("request_headers_note") or ""
        if "Cookie" not in note and "Authorization" not in note:
            return False

    return True


def _check_auth_persists(
    api_entries: list[dict],
    endpoint_lookup: dict[tuple[str, str], dict],
) -> bool:
    """
    Return True if any protected endpoint is called more than once and the
    later call(s) still returned 200 (session persisted across refresh).

    If no protected endpoint is called more than once, return True (vacuously).
    """
    # Group API entries by (method, path) for protected endpoints
    path_groups: dict[tuple[str, str], list[int]] = {}

    for entry in api_entries:
        method = entry.get("method", "").upper()
        path = _normalize_path(urlparse(entry.get("url", "")).path)
        ep = endpoint_lookup.get((method, path))
        if ep and ep.get("auth_required"):
            key = (method, path)
            path_groups.setdefault(key, []).append(entry.get("status", 0))

    # Find any protected endpoint called more than once
    for key, statuses in path_groups.items():
        if len(statuses) > 1:
            # All later calls should be 200
            later_calls = statuses[1:]
            if all(s == 200 for s in later_calls):
                return True
            else:
                return False

    # No protected endpoint was called more than once — vacuously true
    return True
