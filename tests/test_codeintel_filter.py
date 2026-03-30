"""Tests for codeintel_filter — strip non-visual fields for Visual Scorer."""
import json
from pathlib import Path

CODEINTEL_PATH = str(Path(__file__).parent.parent / "fixtures" / "sample_codeintel.json")

def _load_codeintel():
    with open(CODEINTEL_PATH) as f:
        return json.load(f)

def test_filter_removes_api_endpoints():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    assert "api_endpoints" not in result

def test_filter_removes_auth():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    assert "auth" not in result

def test_filter_removes_data_flows():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    assert "data_flows" not in result

def test_filter_keeps_pages():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    assert "pages" in result
    assert len(result["pages"]) > 0

def test_filter_keeps_design_tokens():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    page = result["pages"][0]
    assert "design_tokens" in page

def test_filter_keeps_elements():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    page = result["pages"][0]
    assert "elements" in page

def test_filter_removes_api_call_from_forms():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    result = filter_codeintel_for_visual(_load_codeintel())
    for page in result["pages"]:
        for form in page.get("elements", {}).get("forms", []):
            assert "api_call" not in form, "api_call should be stripped from forms"
            assert "on_success" not in form, "on_success should be stripped from forms"

def test_filter_does_not_modify_original():
    from persona_browser.codeintel_filter import filter_codeintel_for_visual
    original = _load_codeintel()
    filter_codeintel_for_visual(original)
    assert "api_endpoints" in original, "Original should not be modified"
