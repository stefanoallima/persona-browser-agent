"""
Tests for new BrowserConfig fields and ReportStatus.PARTIAL — Phase 2 Task 4.

Run:  pytest tests/test_config.py -v
"""

import os
import tempfile
import pytest
import yaml

from persona_browser.config import BrowserConfig, Config, load_config
from persona_browser.report import ReportStatus, create_report, _classify_error


# ---------------------------------------------------------------------------
# 1. BrowserConfig defaults include new fields
# ---------------------------------------------------------------------------

def test_browser_config_defaults():
    cfg = BrowserConfig()
    assert cfg.max_steps == 50
    assert cfg.timeout_seconds == 120
    assert cfg.app_domains == []
    assert cfg.capture_network is True


# ---------------------------------------------------------------------------
# 2. All new fields can be overridden
# ---------------------------------------------------------------------------

def test_browser_config_custom():
    cfg = BrowserConfig(
        max_steps=100,
        timeout_seconds=300,
        app_domains=["example.com", "api.example.com"],
        capture_network=False,
    )
    assert cfg.max_steps == 100
    assert cfg.timeout_seconds == 300
    assert cfg.app_domains == ["example.com", "api.example.com"]
    assert cfg.capture_network is False


# ---------------------------------------------------------------------------
# 3. app_domains accepts a list of strings
# ---------------------------------------------------------------------------

def test_browser_config_app_domains_list():
    domains = ["localhost:3000", "localhost:3333", "api.myapp.io"]
    cfg = BrowserConfig(app_domains=domains)
    assert isinstance(cfg.app_domains, list)
    assert len(cfg.app_domains) == 3
    for d in domains:
        assert d in cfg.app_domains


# ---------------------------------------------------------------------------
# 4. load_config picks up new fields from YAML
# ---------------------------------------------------------------------------

def test_config_loads_from_yaml():
    data = {
        "browser": {
            "max_steps": 75,
            "timeout_seconds": 200,
            "app_domains": ["staging.example.com"],
            "capture_network": False,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(data, f)
        tmp_path = f.name

    try:
        cfg = load_config(tmp_path)
        assert cfg.browser.max_steps == 75
        assert cfg.browser.timeout_seconds == 200
        assert cfg.browser.app_domains == ["staging.example.com"]
        assert cfg.browser.capture_network is False
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# 5. PARTIAL is a valid ReportStatus value
# ---------------------------------------------------------------------------

def test_report_status_partial():
    assert ReportStatus.PARTIAL == "PARTIAL"
    # Confirm it round-trips correctly
    assert ReportStatus("PARTIAL") is ReportStatus.PARTIAL
    # Confirm original values still present
    assert ReportStatus.DONE == "DONE"
    assert ReportStatus.ERROR == "ERROR"
    assert ReportStatus.SKIP == "SKIP"


# ---------------------------------------------------------------------------
# 6. create_report works with PARTIAL status
# ---------------------------------------------------------------------------

def test_report_create_partial():
    report = create_report(
        status=ReportStatus.PARTIAL,
        elapsed=45.3,
        persona="alice",
        url="http://localhost:3000",
    )
    assert report["status"] == "PARTIAL"
    assert report["elapsed_seconds"] == 45.3
    assert report["persona"] == "alice"
    assert report["url"] == "http://localhost:3000"


# ---------------------------------------------------------------------------
# 7. create_report merges navigator_output dict into report
# ---------------------------------------------------------------------------

def test_report_create_with_navigator_output():
    nav_output = {
        "steps_taken": 50,
        "observations": ["login form found", "submitted successfully"],
        "final_state": "max_steps_reached",
    }
    report = create_report(
        status=ReportStatus.PARTIAL,
        elapsed=60.0,
        persona="bob",
        url="http://example.com",
        navigator_output=nav_output,
    )
    assert report["status"] == "PARTIAL"
    # navigator_output fields should be merged into the report
    assert report["steps_taken"] == 50
    assert report["observations"] == ["login form found", "submitted successfully"]
    assert report["final_state"] == "max_steps_reached"


# ---------------------------------------------------------------------------
# 8. _classify_error detects max_steps
# ---------------------------------------------------------------------------

def test_classify_error_max_steps():
    assert _classify_error("max_steps limit reached") == "max_steps_reached"
    assert _classify_error("Navigator stopped: MAX_STEPS exceeded") == "max_steps_reached"
    assert _classify_error("reached max steps after 50 iterations") == "max_steps_reached"


# ---------------------------------------------------------------------------
# 9. _classify_error timeout — doesn't conflict with existing timeout logic
# ---------------------------------------------------------------------------

def test_classify_error_timeout():
    # The existing "timeout"/"timed out" classification should return "timeout_reached"
    # (or "timeout" — whichever the implementation uses; we test max_steps is NOT returned)
    result_timeout = _classify_error("operation timed out after 120 seconds")
    assert result_timeout in ("timeout_reached", "timeout")
    assert result_timeout != "max_steps_reached"

    result_timed_out = _classify_error("timed out waiting for element")
    assert result_timed_out in ("timeout_reached", "timeout")

    # Pure timeout error should NOT be classified as max_steps_reached
    result = _classify_error("session timeout")
    assert result != "max_steps_reached"


# ---------------------------------------------------------------------------
# 10. Config has scoring section with text_scorer, visual_scorer, reconciler
# ---------------------------------------------------------------------------

def test_config_has_scoring_section():
    """Config should have a scoring section with text_scorer, visual_scorer, reconciler."""
    from persona_browser.config import Config, ScoringConfig, ScoringLLMConfig

    config = Config()
    assert hasattr(config, "scoring")
    assert isinstance(config.scoring, ScoringConfig)
    assert isinstance(config.scoring.text_scorer, ScoringLLMConfig)
    assert isinstance(config.scoring.visual_scorer, ScoringLLMConfig)
    assert isinstance(config.scoring.reconciler, ScoringLLMConfig)

    # Check defaults
    assert "glm" in config.scoring.text_scorer.model.lower() or "glm-5" in config.scoring.text_scorer.model
    assert "gemini" in config.scoring.visual_scorer.model.lower()
    assert "sonnet" in config.scoring.reconciler.model.lower() or "claude" in config.scoring.reconciler.model.lower()


# ---------------------------------------------------------------------------
# 11. ScoringConfig loadable from a YAML dict
# ---------------------------------------------------------------------------

def test_scoring_config_from_yaml():
    """ScoringConfig should be loadable from a YAML dict."""
    from persona_browser.config import Config

    data = {
        "scoring": {
            "text_scorer": {"model": "custom/text-model", "api_key_env": "CUSTOM_KEY"},
            "visual_scorer": {"model": "custom/visual-model"},
            "reconciler": {"model": "custom/reconciler-model", "temperature": 0.3},
        }
    }
    config = Config(**data)
    assert config.scoring.text_scorer.model == "custom/text-model"
    assert config.scoring.text_scorer.api_key_env == "CUSTOM_KEY"
    assert config.scoring.visual_scorer.model == "custom/visual-model"
    assert config.scoring.reconciler.model == "custom/reconciler-model"
    assert config.scoring.reconciler.temperature == 0.3


# ---------------------------------------------------------------------------
# 12. Config without scoring section uses defaults (backward compat)
# ---------------------------------------------------------------------------

def test_config_without_scoring_uses_defaults():
    """Config without scoring section should use defaults (backward compat)."""
    from persona_browser.config import Config

    config = Config(**{"llm": {"model": "some/navigator-model"}})
    assert config.scoring.text_scorer.model != ""
    assert config.scoring.visual_scorer.model != ""
    assert config.scoring.reconciler.model != ""
