"""
Tests for persona_browser/output_parser.py

Uses duck-typed mock classes to avoid importing browser-use
(which requires async/playwright setup at import time).
"""

import pytest
from persona_browser.output_parser import (
    parse_history,
    _group_steps_by_url,
    _match_to_manifest,
)


# ---------------------------------------------------------------------------
# Mock classes (duck-type compatible with AgentHistoryList)
# ---------------------------------------------------------------------------

class MockStep:
    def __init__(
        self,
        url="http://localhost:3333/register",
        title="Sign Up",
        screenshot_path=None,
        actions=None,
        thinking="",
        extracted="",
    ):
        self.state = type("State", (), {
            "url": url,
            "title": title,
            "screenshot_path": screenshot_path,
            "interacted_element": None,
        })()
        self.model_output = type("MO", (), {
            "action": actions or [],
            "current_state": type("CS", (), {
                "thinking": thinking,
                "memory": "",
                "next_goal": "",
            })(),
        })()
        self.result = [type("R", (), {
            "extracted_content": extracted,
            "is_done": False,
            "success": None,
            "error": None,
        })()]
        self.metadata = type("M", (), {"duration_seconds": 1.0})()


class MockHistory:
    def __init__(self, steps):
        self.history = steps

    def urls(self):
        return [s.state.url for s in self.history]

    def screenshot_paths(self):
        return [s.state.screenshot_path for s in self.history]

    def action_names(self):
        return ["navigate" for _ in self.history]

    def extracted_content(self):
        return [s.result[0].extracted_content for s in self.history]

    def final_result(self):
        return "Test completed successfully"

    def total_duration_seconds(self):
        return sum(s.metadata.duration_seconds for s in self.history)

    def is_done(self):
        return True

    def is_successful(self):
        return True

    def number_of_steps(self):
        return len(self.history)

    def model_thoughts(self):
        return [s.model_output.current_state for s in self.history]

    def errors(self):
        return [None for _ in self.history]


# ---------------------------------------------------------------------------
# Sample manifest for tests that need it
# ---------------------------------------------------------------------------

SAMPLE_MANIFEST = {
    "pages": [
        {
            "id": "registration",
            "how_to_reach": "Navigate to /register",
        },
        {
            "id": "dashboard",
            "how_to_reach": "Navigate to /dashboard",
        },
    ]
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_page_history():
    """All steps on the same URL."""
    steps = [
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_1.png", extracted="Loaded registration page"),
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_2.png", extracted="Filled name field"),
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_3.png", extracted="Clicked register"),
    ]
    return MockHistory(steps)


@pytest.fixture
def two_page_history():
    """Steps across two URLs."""
    steps = [
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_1.png", extracted="On register page"),
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_2.png", extracted="Filled form"),
        MockStep(url="http://localhost:3333/dashboard", screenshot_path="screenshots/step_3.png", extracted="On dashboard"),
    ]
    return MockHistory(steps)


@pytest.fixture
def revisit_history():
    """URL A → URL B → URL A — should produce 3 groups."""
    steps = [
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_1.png"),
        MockStep(url="http://localhost:3333/dashboard", screenshot_path="screenshots/step_2.png"),
        MockStep(url="http://localhost:3333/register", screenshot_path="screenshots/step_3.png"),
    ]
    return MockHistory(steps)


# ---------------------------------------------------------------------------
# Tests 1-3: Basic structure and status
# ---------------------------------------------------------------------------

def test_parse_history_returns_dict(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    assert isinstance(result, dict)


def test_parse_history_has_required_fields(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    for field in ("version", "status", "elapsed_seconds", "persona", "url", "manifest_coverage", "pages"):
        assert field in result, f"Missing required field: {field}"


def test_parse_history_status_done(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    assert result["status"] == "DONE"


# ---------------------------------------------------------------------------
# Tests 4-5: Page grouping
# ---------------------------------------------------------------------------

def test_parse_history_pages_grouped_by_url(two_page_history):
    result = parse_history(two_page_history, har_entries=[])
    assert len(result["pages"]) == 2


def test_parse_history_single_url_single_page(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    assert len(result["pages"]) == 1


# ---------------------------------------------------------------------------
# Test 6: Page has observations
# ---------------------------------------------------------------------------

def test_parse_history_page_has_observations(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    page = result["pages"][0]
    assert "observations" in page
    assert "description" in page["observations"]
    assert "actions" in page["observations"]


# ---------------------------------------------------------------------------
# Test 7: Screenshot from first step of group
# ---------------------------------------------------------------------------

def test_parse_history_page_has_screenshot(two_page_history):
    result = parse_history(two_page_history, har_entries=[])
    # First page group — first step screenshot
    assert result["pages"][0]["screenshot"] == "screenshots/step_1.png"
    # Second page group — first step of second group
    assert result["pages"][1]["screenshot"] == "screenshots/step_3.png"


# ---------------------------------------------------------------------------
# Test 8-9: Manifest coverage
# ---------------------------------------------------------------------------

def test_parse_history_manifest_coverage(two_page_history):
    result = parse_history(
        two_page_history,
        har_entries=[],
        manifest=SAMPLE_MANIFEST,
    )
    coverage = result["manifest_coverage"]
    assert set(coverage["expected_pages"]) == {"registration", "dashboard"}
    assert "registration" in coverage["visited"]
    assert "dashboard" in coverage["visited"]
    assert coverage["not_visited"] == []


def test_parse_history_no_manifest(two_page_history):
    result = parse_history(two_page_history, har_entries=[], manifest=None)
    coverage = result["manifest_coverage"]
    assert coverage["expected_pages"] == []
    # visited should include unique URLs (represented as IDs or slugs)
    assert len(coverage["visited"]) == 2


# ---------------------------------------------------------------------------
# Test 10-11: Experience and agent_result backward compat
# ---------------------------------------------------------------------------

def test_parse_history_experience_from_final_result(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    assert "experience" in result
    # experience section is a dict (may be empty or populated)
    assert isinstance(result["experience"], dict)


def test_parse_history_agent_result_backward_compat(single_page_history):
    result = parse_history(single_page_history, har_entries=[])
    assert "agent_result" in result
    assert isinstance(result["agent_result"], str)
    assert result["agent_result"] == "Test completed successfully"


# ---------------------------------------------------------------------------
# Test 12: Network log assignment by URL
# ---------------------------------------------------------------------------

def test_parse_history_network_log_assigned_to_pages(two_page_history):
    har_entries = [
        {
            "method": "GET",
            "url": "http://localhost:3333/register",
            "status": 200,
            "timing_ms": 50,
            "trigger": "navigation",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "HTML page",
            "set_cookie": None,
            "request_headers_note": None,
        },
        {
            "method": "GET",
            "url": "http://localhost:3333/dashboard",
            "status": 200,
            "timing_ms": 30,
            "trigger": "navigation",
            "request_content_type": None,
            "request_body": None,
            "response_summary": "HTML page",
            "set_cookie": None,
            "request_headers_note": None,
        },
    ]
    result = parse_history(two_page_history, har_entries=har_entries)
    # Each page should have exactly one network log entry assigned
    register_page = next(p for p in result["pages"] if "/register" in p["url_visited"])
    dashboard_page = next(p for p in result["pages"] if "/dashboard" in p["url_visited"])
    assert any("/register" in e["url"] for e in register_page.get("network_log", []))
    assert any("/dashboard" in e["url"] for e in dashboard_page.get("network_log", []))


# ---------------------------------------------------------------------------
# Tests 13-14: _group_steps_by_url unit tests
# ---------------------------------------------------------------------------

def test_group_steps_by_url_basic():
    """3 steps (2 URL A, 1 URL B) → 2 groups."""
    steps = [
        MockStep(url="http://localhost/a"),
        MockStep(url="http://localhost/a"),
        MockStep(url="http://localhost/b"),
    ]
    history = MockHistory(steps)
    groups = _group_steps_by_url(history)
    assert len(groups) == 2
    assert groups[0]["url"] == "http://localhost/a"
    assert groups[1]["url"] == "http://localhost/b"
    assert len(groups[0]["steps"]) == 2
    assert len(groups[1]["steps"]) == 1


def test_group_steps_by_url_revisit():
    """URL A → URL B → URL A → 3 groups."""
    steps = [
        MockStep(url="http://localhost/a"),
        MockStep(url="http://localhost/b"),
        MockStep(url="http://localhost/a"),
    ]
    history = MockHistory(steps)
    groups = _group_steps_by_url(history)
    assert len(groups) == 3
    assert groups[0]["url"] == "http://localhost/a"
    assert groups[1]["url"] == "http://localhost/b"
    assert groups[2]["url"] == "http://localhost/a"


# ---------------------------------------------------------------------------
# Tests 15-16: _match_to_manifest unit tests
# ---------------------------------------------------------------------------

def test_match_to_manifest_assigns_ids():
    """Groups matched to manifest pages by URL path substring."""
    groups = [
        {"url": "http://localhost:3333/register", "steps": []},
        {"url": "http://localhost:3333/dashboard", "steps": []},
    ]
    matched = _match_to_manifest(groups, SAMPLE_MANIFEST)
    ids = [g["page_id"] for g in matched]
    assert "registration" in ids
    assert "dashboard" in ids


def test_match_to_manifest_unmatched_gets_slug():
    """Non-manifest URL gets an 'unexpected-{slug}' id."""
    groups = [
        {"url": "http://localhost:3333/settings/profile", "steps": []},
    ]
    matched = _match_to_manifest(groups, SAMPLE_MANIFEST)
    assert matched[0]["page_id"].startswith("unexpected-")
