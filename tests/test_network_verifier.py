"""
Tests for persona_browser/network_verifier.py

TDD: all tests written first. Load fixtures from fixtures/ directory.
Network log is flattened from pages[].network_log arrays.
"""

import copy
import json
import os
import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_FIXTURES = os.path.join(_PROJECT, "fixtures")


# ---------------------------------------------------------------------------
# Fixture loading helpers
# ---------------------------------------------------------------------------

def _load_codeintel():
    with open(os.path.join(_FIXTURES, "sample_codeintel.json")) as f:
        return json.load(f)


def _load_navigator_output():
    with open(os.path.join(_FIXTURES, "sample_navigator_output.json")) as f:
        return json.load(f)


def _flatten_network_log(navigator_output):
    """Flatten network_log entries from all pages into a single list."""
    log = []
    for page in navigator_output.get("pages", []):
        log.extend(page.get("network_log", []))
    return log


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

from persona_browser.network_verifier import verify_network


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def codeintel():
    return _load_codeintel()


@pytest.fixture
def navigator_output():
    return _load_navigator_output()


@pytest.fixture
def network_log(navigator_output):
    return _flatten_network_log(navigator_output)


# ---------------------------------------------------------------------------
# 1. Returns a dict
# ---------------------------------------------------------------------------

def test_verify_returns_dict(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 2. Has required schema fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "api_calls_total",
    "api_calls_matched_codeintel",
    "api_calls_unmatched",
    "api_errors_during_normal_flow",
    "deal_breakers",
    "issues",
]


def test_verify_has_required_fields(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    for field in REQUIRED_FIELDS:
        assert field in result, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# 3. api_calls_total counts /api/ entries
# ---------------------------------------------------------------------------

def test_verify_api_calls_counted(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    api_entries = [e for e in network_log if "/api/" in e["url"]]
    assert result["api_calls_total"] == len(api_entries)


# ---------------------------------------------------------------------------
# 4. With sample fixtures, all API calls match codeintel
# ---------------------------------------------------------------------------

def test_verify_all_matched(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert result["api_calls_matched_codeintel"] == result["api_calls_total"]
    assert result["api_calls_unmatched"] == 0


# ---------------------------------------------------------------------------
# 5. With clean sample data, api_errors = 0
# ---------------------------------------------------------------------------

def test_verify_no_errors(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert result["api_errors_during_normal_flow"] == 0


# ---------------------------------------------------------------------------
# 6. With clean sample data, deal_breakers is empty
# ---------------------------------------------------------------------------

def test_verify_no_deal_breakers(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert result["deal_breakers"] == []


# ---------------------------------------------------------------------------
# 7. per_endpoint has entries for each API call
# ---------------------------------------------------------------------------

def test_verify_per_endpoint_populated(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    api_entries = [e for e in network_log if "/api/" in e["url"]]
    assert "per_endpoint" in result
    assert len(result["per_endpoint"]) == len(api_entries)


# ---------------------------------------------------------------------------
# 8. Each per_endpoint entry has required fields
# ---------------------------------------------------------------------------

PER_ENDPOINT_REQUIRED = ["method", "path", "matched_codeintel", "status"]


def test_verify_per_endpoint_fields(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    for entry in result.get("per_endpoint", []):
        for field in PER_ENDPOINT_REQUIRED:
            assert field in entry, f"Missing field '{field}' in per_endpoint entry: {entry}"


# ---------------------------------------------------------------------------
# 9. auth_token_set_after_auth = true with sample data
# ---------------------------------------------------------------------------

def test_verify_auth_set(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert result["auth_token_set_after_auth"] is True


# ---------------------------------------------------------------------------
# 10. auth_token_sent_on_protected_requests = true with sample data
# ---------------------------------------------------------------------------

def test_verify_auth_sent(network_log, codeintel):
    result = verify_network(network_log, codeintel)
    assert result["auth_token_sent_on_protected_requests"] is True


# ---------------------------------------------------------------------------
# 11. auth_persists_after_refresh = true (duplicate /api/user/me calls)
# ---------------------------------------------------------------------------

def test_verify_auth_persists(network_log, codeintel):
    # The sample navigator output has two GET /api/user/me calls (load + refresh)
    result = verify_network(network_log, codeintel)
    assert result["auth_persists_after_refresh"] is True


# ---------------------------------------------------------------------------
# 12. Inject unknown endpoint → unmatched count increases
# ---------------------------------------------------------------------------

def test_verify_unknown_endpoint(network_log, codeintel):
    log_with_unknown = network_log + [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/unknown/endpoint",
            "status": 200,
            "timing_ms": 5,
            "trigger": "injected",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "{}",
            "set_cookie": None,
            "request_headers_note": None,
        }
    ]
    result = verify_network(log_with_unknown, codeintel)
    assert result["api_calls_unmatched"] >= 1
    # Total should be one more than original
    original = verify_network(network_log, codeintel)
    assert result["api_calls_total"] == original["api_calls_total"] + 1


# ---------------------------------------------------------------------------
# 13. Inject 500 status → deal_breakers populated
# ---------------------------------------------------------------------------

def test_verify_500_is_deal_breaker(network_log, codeintel):
    log_with_500 = network_log + [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/user/me",
            "status": 500,
            "timing_ms": 2,
            "trigger": "injected 500",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "Internal Server Error",
            "set_cookie": None,
            "request_headers_note": "Cookie: session=abc",
        }
    ]
    result = verify_network(log_with_500, codeintel)
    assert len(result["deal_breakers"]) > 0
    # Should mention method and path
    combined = " ".join(result["deal_breakers"])
    assert "500" in combined or "GET" in combined or "/api/user/me" in combined


# ---------------------------------------------------------------------------
# 14. Inject 401 on protected endpoint → issue flagged
# ---------------------------------------------------------------------------

def test_verify_401_on_protected(network_log, codeintel):
    log_with_401 = network_log + [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/user/me",
            "status": 401,
            "timing_ms": 2,
            "trigger": "injected 401",
            "request_content_type": None,
            "request_body": None,
            "response_summary": '{"message": "Not authenticated"}',
            "set_cookie": None,
            "request_headers_note": "Cookie: session=abc",
        }
    ]
    result = verify_network(log_with_401, codeintel)
    # Should have at least one issue about auth failure
    issues_text = " ".join(result["issues"]).lower()
    assert "auth" in issues_text or "handover" in issues_text or "401" in issues_text


# ---------------------------------------------------------------------------
# 15. Empty network_log → all counts 0, no errors
# ---------------------------------------------------------------------------

def test_verify_empty_log(codeintel):
    result = verify_network([], codeintel)
    assert result["api_calls_total"] == 0
    assert result["api_calls_matched_codeintel"] == 0
    assert result["api_calls_unmatched"] == 0
    assert result["api_errors_during_normal_flow"] == 0
    assert result["deal_breakers"] == []
    assert result["issues"] == []
    assert result.get("per_endpoint", []) == []


# ---------------------------------------------------------------------------
# 16. codeintel with empty api_endpoints → all unmatched
# ---------------------------------------------------------------------------

def test_verify_no_codeintel_endpoints(network_log):
    empty_codeintel = {"api_endpoints": [], "auth": {}}
    result = verify_network(network_log, empty_codeintel)
    api_entries = [e for e in network_log if "/api/" in e["url"]]
    assert result["api_calls_unmatched"] == len(api_entries)
    assert result["api_calls_matched_codeintel"] == 0


# ---------------------------------------------------------------------------
# 17. URL with trailing slash matches endpoint without
# ---------------------------------------------------------------------------

def test_verify_path_normalization(codeintel):
    log_with_trailing_slash = [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/user/me/",
            "status": 200,
            "timing_ms": 4,
            "trigger": "test trailing slash",
            "request_content_type": None,
            "request_body": None,
            "response_summary": '{"name": "Jordan", "email": "jordan@example.com"}',
            "set_cookie": None,
            "request_headers_note": "Cookie: session=abc",
        }
    ]
    result = verify_network(log_with_trailing_slash, codeintel)
    # With trailing slash normalization, should still match
    assert result["api_calls_matched_codeintel"] == 1
    assert result["api_calls_unmatched"] == 0


# ---------------------------------------------------------------------------
# 18. contract_match: correct status → true, wrong status → false
# ---------------------------------------------------------------------------

def test_verify_contract_match_status(codeintel):
    # Correct status for GET /api/user/me is 200
    log_correct = [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/user/me",
            "status": 200,
            "timing_ms": 4,
            "trigger": "test",
            "request_content_type": None,
            "request_body": None,
            "response_summary": '{"name": "Jordan", "email": "jordan@example.com"}',
            "set_cookie": None,
            "request_headers_note": "Cookie: session=abc",
        }
    ]
    result_correct = verify_network(log_correct, codeintel)
    assert len(result_correct["per_endpoint"]) == 1
    assert result_correct["per_endpoint"][0]["contract_match"] is True

    # Wrong (unexpected) status for GET /api/user/me — use 404 which is not in responses
    log_wrong = [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/user/me",
            "status": 404,
            "timing_ms": 4,
            "trigger": "test",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "Not Found",
            "set_cookie": None,
            "request_headers_note": "Cookie: session=abc",
        }
    ]
    result_wrong = verify_network(log_wrong, codeintel)
    assert len(result_wrong["per_endpoint"]) == 1
    assert result_wrong["per_endpoint"][0]["contract_match"] is False


# ---------------------------------------------------------------------------
# 19. issues list contains strings
# ---------------------------------------------------------------------------

def test_verify_issues_are_strings(network_log, codeintel):
    # Inject an unknown endpoint to generate an issue
    log_with_unknown = network_log + [
        {
            "method": "GET",
            "url": "http://localhost:3333/api/no/such/path",
            "status": 200,
            "timing_ms": 3,
            "trigger": "injected",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "{}",
            "set_cookie": None,
            "request_headers_note": None,
        }
    ]
    result = verify_network(log_with_unknown, codeintel)
    for issue in result["issues"]:
        assert isinstance(issue, str), f"Expected string issue, got: {type(issue)}"


# ---------------------------------------------------------------------------
# 20. deal_breakers list contains strings
# ---------------------------------------------------------------------------

def test_verify_deal_breakers_are_strings(network_log, codeintel):
    log_with_500 = network_log + [
        {
            "method": "POST",
            "url": "http://localhost:3333/api/auth/register",
            "status": 500,
            "timing_ms": 10,
            "trigger": "injected 500",
            "request_content_type": "application/json",
            "request_body": '{"name":"x","email":"x@x.com","password":"password1"}',
            "response_summary": "Internal Server Error",
            "set_cookie": None,
            "request_headers_note": None,
        }
    ]
    result = verify_network(log_with_500, codeintel)
    for db in result["deal_breakers"]:
        assert isinstance(db, str), f"Expected string deal_breaker, got: {type(db)}"
