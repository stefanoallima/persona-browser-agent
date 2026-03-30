"""
Tests for persona_browser/har_parser.py

Uses the real poc/session.har file from PoC-2.
All tests are pure-Python — no browser-use dependency.
"""

import os
import pytest
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_HAR_PATH = os.path.join(_PROJECT, "poc", "session.har")

# Schema-allowed fields per network-log-entry.schema.json
_ALLOWED_FIELDS = {
    "method",
    "url",
    "status",
    "timing_ms",
    "trigger",
    "request_content_type",
    "request_body",
    "response_summary",
    "set_cookie",
    "request_headers_note",
}


# ---------------------------------------------------------------------------
# Lazy import so we can confirm the module-not-found failure first
# ---------------------------------------------------------------------------

from persona_browser.har_parser import (
    parse_har,
    correlate_with_steps,
    parse_har_raw_timestamps,
)


# ---------------------------------------------------------------------------
# 1. parse_har returns a non-empty list
# ---------------------------------------------------------------------------

def test_parse_har_returns_list():
    entries = parse_har(_HAR_PATH)
    assert isinstance(entries, list)
    assert len(entries) > 0


# ---------------------------------------------------------------------------
# 2. Every entry has the required fields: method, url, status
# ---------------------------------------------------------------------------

def test_parse_har_entry_has_required_fields():
    entries = parse_har(_HAR_PATH)
    for entry in entries:
        assert "method" in entry, f"Missing 'method' in {entry}"
        assert "url" in entry, f"Missing 'url' in {entry}"
        assert "status" in entry, f"Missing 'status' in {entry}"


# ---------------------------------------------------------------------------
# 3. status is always an int
# ---------------------------------------------------------------------------

def test_parse_har_status_is_int():
    entries = parse_har(_HAR_PATH)
    for entry in entries:
        assert isinstance(entry["status"], int), (
            f"status should be int, got {type(entry['status'])} in {entry}"
        )


# ---------------------------------------------------------------------------
# 4. timing_ms is a float (when present)
# ---------------------------------------------------------------------------

def test_parse_har_timing_is_number():
    entries = parse_har(_HAR_PATH)
    for entry in entries:
        if "timing_ms" in entry:
            assert isinstance(entry["timing_ms"], (int, float)), (
                f"timing_ms should be numeric, got {type(entry['timing_ms'])}"
            )
            assert entry["timing_ms"] >= 0


# ---------------------------------------------------------------------------
# 5. No extra fields beyond schema-allowed ones
# ---------------------------------------------------------------------------

def test_parse_har_no_extra_fields():
    entries = parse_har(_HAR_PATH)
    for entry in entries:
        extra = set(entry.keys()) - _ALLOWED_FIELDS
        assert not extra, f"Extra fields found: {extra} in {entry}"


# ---------------------------------------------------------------------------
# 6. POST /api/auth/register has request_body with JSON
# ---------------------------------------------------------------------------

def test_parse_har_captures_post_with_body():
    entries = parse_har(_HAR_PATH)
    post_register = [
        e for e in entries
        if e["method"] == "POST" and "/api/auth/register" in e["url"]
    ]
    assert len(post_register) > 0, "No POST /api/auth/register entries found"
    # At least one should have a request_body
    with_body = [e for e in post_register if e.get("request_body")]
    assert len(with_body) > 0, "Expected at least one POST with request_body"
    # The body should look like JSON (contains 'name' and 'email')
    for entry in with_body:
        body = entry["request_body"]
        assert isinstance(body, str)
        assert "email" in body or "name" in body


# ---------------------------------------------------------------------------
# 7. API responses have response_summary
# ---------------------------------------------------------------------------

def test_parse_har_captures_response_summary():
    entries = parse_har(_HAR_PATH)
    api_entries = [
        e for e in entries
        if "/api/" in e["url"]
    ]
    assert len(api_entries) > 0, "No API entries found"
    with_summary = [e for e in api_entries if e.get("response_summary")]
    assert len(with_summary) > 0, "Expected API entries to have response_summary"
    for entry in with_summary:
        assert len(entry["response_summary"]) <= 500


# ---------------------------------------------------------------------------
# 8. Domain filter — only localhost:3333
# ---------------------------------------------------------------------------

def test_parse_har_domain_filter():
    entries = parse_har(_HAR_PATH, app_domains=["localhost:3333"])
    assert len(entries) > 0
    for entry in entries:
        assert "localhost:3333" in entry["url"], (
            f"URL {entry['url']} should contain localhost:3333"
        )


# ---------------------------------------------------------------------------
# 9. Empty list app_domains means no filter (return all)
# ---------------------------------------------------------------------------

def test_parse_har_domain_filter_empty_list_means_all():
    all_entries = parse_har(_HAR_PATH)
    filtered_entries = parse_har(_HAR_PATH, app_domains=[])
    assert len(filtered_entries) == len(all_entries)


# ---------------------------------------------------------------------------
# 10. None app_domains means no filter (return all)
# ---------------------------------------------------------------------------

def test_parse_har_domain_filter_none_means_all():
    all_entries = parse_har(_HAR_PATH)
    filtered_entries = parse_har(_HAR_PATH, app_domains=None)
    assert len(filtered_entries) == len(all_entries)


# ---------------------------------------------------------------------------
# 11. Methods are uppercase
# ---------------------------------------------------------------------------

def test_parse_har_method_is_uppercase():
    entries = parse_har(_HAR_PATH)
    for entry in entries:
        assert entry["method"] == entry["method"].upper(), (
            f"Method should be uppercase, got: {entry['method']}"
        )


# ---------------------------------------------------------------------------
# 12. correlate_with_steps adds trigger field
# ---------------------------------------------------------------------------

def test_correlate_with_steps_adds_trigger():
    entries = parse_har(_HAR_PATH)
    # Create fake step timestamps covering the whole session range
    step_timestamps = [(0.0, 30.0), (30.0, 60.0)]
    correlated = correlate_with_steps(entries, step_timestamps)
    assert len(correlated) == len(entries)
    for entry in correlated:
        assert "trigger" in entry


# ---------------------------------------------------------------------------
# 13. Empty step_timestamps → all triggers are None
# ---------------------------------------------------------------------------

def test_correlate_with_steps_no_match_leaves_trigger_none():
    entries = parse_har(_HAR_PATH)
    correlated = correlate_with_steps(entries, step_timestamps=[])
    for entry in correlated:
        assert entry.get("trigger") is None


# ---------------------------------------------------------------------------
# 14. Missing file raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_parse_har_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_har("/nonexistent/path/to/missing.har")


# ---------------------------------------------------------------------------
# 15. set_cookie field is valid when present
# ---------------------------------------------------------------------------

def test_parse_har_set_cookie_captured():
    entries = parse_har(_HAR_PATH)
    # The session.har from PoC-2 may or may not have set-cookie headers
    # (CDP limitation). We just verify that IF it's present it's a non-empty string.
    cookie_entries = [e for e in entries if e.get("set_cookie")]
    for entry in cookie_entries:
        assert isinstance(entry["set_cookie"], str)
        assert len(entry["set_cookie"]) > 0
    # Test passes even if no set-cookie entries — confirms field is omitted
    # rather than set to None when missing (schema says omit None fields)
    none_cookie_entries = [e for e in entries if "set_cookie" in e and e["set_cookie"] is None]
    assert len(none_cookie_entries) == 0, (
        "set_cookie should be omitted (not None) when not present"
    )
