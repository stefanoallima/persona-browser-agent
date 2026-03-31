"""Tests for pipeline.py -- full pipeline orchestrator.

All components (navigator, scorers, reconciler) are mocked.
Run: pytest tests/test_pipeline.py -v
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
NAVIGATOR_OUTPUT = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
SCORER_RESULTS = json.loads((FIXTURES / "sample_scorer_results.json").read_text())
NETWORK_VERIFICATION = json.loads((FIXTURES / "sample_network_verifier_output.json").read_text())
CODEINTEL = json.loads((FIXTURES / "sample_codeintel.json").read_text())
FINAL_REPORT = json.loads((FIXTURES / "sample_final_report.json").read_text())
RUBRIC_TEXT = (FIXTURES / "sample_rubric.md").read_text()


def _nav_report(status="DONE", nav_output=None):
    """Create a navigator report dict."""
    report = {
        "status": status,
        "elapsed_seconds": 24.6,
        "persona": "micro-persona-signup-form",
        "url": "http://localhost:3333",
    }
    if nav_output:
        report.update(nav_output)
    return report

class TestPipelineFullSuccess:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        from persona_browser.pipeline import run_pipeline
        from persona_browser.config import Config

        config = Config()

        with patch("persona_browser.pipeline.run_navigator") as mock_nav, \
             patch("persona_browser.pipeline.run_scorers") as mock_scorers, \
             patch("persona_browser.pipeline.reconcile_scores") as mock_reconcile, \
             patch("persona_browser.pipeline._create_scoring_llms") as mock_llms, \
             patch("persona_browser.pipeline._load_json_file") as mock_json, \
             patch("persona_browser.pipeline._load_text_file") as mock_text:

            mock_json.return_value = CODEINTEL
            mock_text.return_value = RUBRIC_TEXT
            mock_nav.return_value = _nav_report("DONE", NAVIGATOR_OUTPUT)
            mock_scorers.return_value = SCORER_RESULTS
            mock_reconcile.return_value = FINAL_REPORT
            mock_llms.return_value = (MagicMock(), MagicMock(), MagicMock())

            result = await run_pipeline(
                persona_path="persona.md",
                url="http://localhost:3333",
                objectives="signup",
                config=config,
                codeintel_path="codeintel.json",
                rubric_path="rubric.md",
            )

            assert result["status"] == "DONE"
            mock_nav.assert_called_once()
            mock_scorers.assert_called_once()
            mock_reconcile.assert_called_once()

class TestPipelineNavigatorError:
    @pytest.mark.asyncio
    async def test_navigator_error_returns_immediately(self):
        from persona_browser.pipeline import run_pipeline
        from persona_browser.config import Config

        config = Config()

        with patch("persona_browser.pipeline.run_navigator") as mock_nav, \
             patch("persona_browser.pipeline.run_scorers") as mock_scorers, \
             patch("persona_browser.pipeline._create_scoring_llms") as mock_llms, \
             patch("persona_browser.pipeline._load_json_file") as mock_json, \
             patch("persona_browser.pipeline._load_text_file") as mock_text:

            mock_json.return_value = CODEINTEL
            mock_text.return_value = RUBRIC_TEXT
            mock_nav.return_value = {"status": "ERROR", "error": "Browser crashed", "elapsed_seconds": 0}
            mock_llms.return_value = (MagicMock(), MagicMock(), MagicMock())

            result = await run_pipeline(
                persona_path="persona.md",
                url="http://localhost:3333",
                objectives="signup",
                config=config,
                codeintel_path="codeintel.json",
                rubric_path="rubric.md",
            )

            assert result["status"] == "ERROR"
            mock_scorers.assert_not_called()

class TestPipelineBothScorersFail:
    @pytest.mark.asyncio
    async def test_both_scorers_fail(self):
        from persona_browser.pipeline import run_pipeline
        from persona_browser.config import Config

        config = Config()

        with patch("persona_browser.pipeline.run_navigator") as mock_nav, \
             patch("persona_browser.pipeline.run_scorers") as mock_scorers, \
             patch("persona_browser.pipeline.reconcile_scores") as mock_reconcile, \
             patch("persona_browser.pipeline._create_scoring_llms") as mock_llms, \
             patch("persona_browser.pipeline._load_json_file") as mock_json, \
             patch("persona_browser.pipeline._load_text_file") as mock_text:

            mock_json.return_value = CODEINTEL
            mock_text.return_value = RUBRIC_TEXT
            mock_nav.return_value = _nav_report("DONE", NAVIGATOR_OUTPUT)
            mock_scorers.return_value = {
                "network_verification": NETWORK_VERIFICATION,
                "text_scores": {"error": "Text LLM failed"},
                "visual_scores": {"error": "Visual LLM failed"},
            }
            mock_llms.return_value = (MagicMock(), MagicMock(), MagicMock())

            # reconcile_scores handles 'neither' mode internally
            mock_reconcile.return_value = {
                "version": "1.1",
                "status": "PARTIAL",
                "elapsed_seconds": 1.0,
                "persona": "",
                "url": "",
                "manifest_coverage": {},
                "pages": [],
                "summary": {
                    "pb_criteria_total": 0, "pb_criteria_passed": 0,
                    "pb_criteria_failed": 0, "pb_criteria_unknown": 0,
                    "consumer_criteria_total": 0, "consumer_criteria_passed": 0,
                    "consumer_criteria_failed": 0,
                    "verification_tasks_total": 0, "verification_tasks_passed": 0,
                    "verification_tasks_failed": 0,
                    "network_issues": 0, "total_discrepancies": 0,
                    "deal_breakers_triggered": [], "pages_with_failures": [],
                    "pages_clean": [],
                },
            }

            result = await run_pipeline(
                persona_path="persona.md",
                url="http://localhost:3333",
                objectives="signup",
                config=config,
                codeintel_path="codeintel.json",
                rubric_path="rubric.md",
            )

            mock_reconcile.assert_called_once()

class TestPipelineReconcilerFailure:
    @pytest.mark.asyncio
    async def test_reconciler_fails_returns_partial(self):
        from persona_browser.pipeline import run_pipeline
        from persona_browser.config import Config

        config = Config()

        with patch("persona_browser.pipeline.run_navigator") as mock_nav, \
             patch("persona_browser.pipeline.run_scorers") as mock_scorers, \
             patch("persona_browser.pipeline.reconcile_scores") as mock_reconcile, \
             patch("persona_browser.pipeline._create_scoring_llms") as mock_llms, \
             patch("persona_browser.pipeline._load_json_file") as mock_json, \
             patch("persona_browser.pipeline._load_text_file") as mock_text:

            mock_json.return_value = CODEINTEL
            mock_text.return_value = RUBRIC_TEXT
            mock_nav.return_value = _nav_report("DONE", NAVIGATOR_OUTPUT)
            mock_scorers.return_value = SCORER_RESULTS
            mock_reconcile.side_effect = Exception("Reconciler LLM error")
            mock_llms.return_value = (MagicMock(), MagicMock(), MagicMock())

            result = await run_pipeline(
                persona_path="persona.md",
                url="http://localhost:3333",
                objectives="signup",
                config=config,
                codeintel_path="codeintel.json",
                rubric_path="rubric.md",
            )

            assert result["status"] == "PARTIAL"

class TestPipelineMissingInputs:
    @pytest.mark.asyncio
    async def test_missing_codeintel(self):
        from persona_browser.pipeline import run_pipeline
        from persona_browser.config import Config

        config = Config()

        result = await run_pipeline(
            persona_path="persona.md",
            url="http://localhost:3333",
            objectives="signup",
            config=config,
            codeintel_path="nonexistent.json",
            rubric_path="rubric.md",
        )

        assert result["status"] in ("ERROR", "SKIP")
