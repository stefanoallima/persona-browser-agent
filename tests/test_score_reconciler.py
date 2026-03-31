"""Tests for score_reconciler -- deterministic helpers + mocked LLM reconciliation.

Uses sample fixtures. LLM calls mocked in reconciliation tests.
Run: pytest tests/test_score_reconciler.py -v
"""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
NAVIGATOR_OUTPUT = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
MANIFEST = json.loads((FIXTURES / "sample_manifest.json").read_text())
NETWORK_VERIFICATION = json.loads((FIXTURES / "sample_network_verifier_output.json").read_text())


class TestManifestCoverage:
    def test_all_visited(self):
        from persona_browser.score_reconciler import _check_manifest_coverage

        result = _check_manifest_coverage(NAVIGATOR_OUTPUT, MANIFEST)
        assert result["expected_pages"] == ["registration", "dashboard"]
        assert result["visited"] == ["registration", "dashboard"]
        assert result["not_visited"] == []
        assert result["unexpected_pages"] == []

    def test_missing_pages(self):
        from persona_browser.score_reconciler import _check_manifest_coverage

        nav = {
            "manifest_coverage": {
                "expected_pages": ["registration", "dashboard"],
                "visited": ["registration"],
                "not_visited": ["dashboard"],
                "unexpected_pages": [],
            }
        }
        result = _check_manifest_coverage(nav, MANIFEST)
        assert "dashboard" in result["not_visited"]
        assert "registration" in result["visited"]

    def test_unexpected_pages(self):
        from persona_browser.score_reconciler import _check_manifest_coverage

        nav = {
            "manifest_coverage": {
                "expected_pages": ["registration", "dashboard"],
                "visited": ["registration", "dashboard"],
                "not_visited": [],
                "unexpected_pages": ["/about"],
            }
        }
        result = _check_manifest_coverage(nav, MANIFEST)
        assert "/about" in result["unexpected_pages"]

    def test_no_manifest(self):
        from persona_browser.score_reconciler import _check_manifest_coverage

        result = _check_manifest_coverage(NAVIGATOR_OUTPUT, None)
        assert "expected_pages" in result
        assert "visited" in result

class TestVerificationTasks:
    def test_all_pass(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, MANIFEST)
        assert len(result) >= 2
        for task in result:
            assert task["result"] in ("PASS", "FAIL")
            assert "id" in task
            assert "type" in task
            assert "evidence" in task

    def test_persistence_maps_correctly(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, MANIFEST)
        v1 = next((t for t in result if t["id"] == "V1"), None)
        assert v1 is not None
        assert v1["type"] == "data_persistence"
        assert v1["result"] == "PASS"
        assert len(v1["evidence"]) > 0

    def test_auth_persistence_maps_correctly(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, MANIFEST)
        v3 = next((t for t in result if t["id"] == "V3"), None)
        assert v3 is not None
        assert v3["type"] == "auth_persistence"
        assert v3["result"] == "PASS"

    def test_not_performed(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        nav = {"pages": [], "manifest_coverage": {"expected_pages": [], "visited": []}}
        manifest_with_tasks = {
            "pages": [],
            "verification_tasks": [
                {"id": "V1", "type": "data_persistence", "description": "test", "check": "test"}
            ],
        }
        result = _evaluate_verification_tasks(nav, manifest_with_tasks)
        v1 = next((t for t in result if t["id"] == "V1"), None)
        assert v1 is not None
        assert v1["result"] == "FAIL"
        assert "not performed" in v1["evidence"].lower()

    def test_no_manifest(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, None)
        assert isinstance(result, list)


class TestClassifyScorerAvailability:
    def test_both_available(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            [{"page_id": "reg", "pb_criteria": [], "consumer_criteria": []}],
            [{"page_id": "reg", "features_detected": [], "pb_criteria": [], "consumer_criteria": []}],
        )
        assert result == "both"

    def test_text_only(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            [{"page_id": "reg", "pb_criteria": [], "consumer_criteria": []}],
            {"error": "No visual LLM provided"},
        )
        assert result == "text_only"

    def test_visual_only(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            {"error": "Text scorer failed"},
            [{"page_id": "reg", "features_detected": [], "pb_criteria": [], "consumer_criteria": []}],
        )
        assert result == "visual_only"

    def test_neither(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            {"error": "Text failed"},
            {"error": "Visual failed"},
        )
        assert result == "neither"

class TestComputeSummary:
    def test_correct_counts(self):
        from persona_browser.score_reconciler import _compute_summary

        # Manually build reconciled pages matching the sample final report
        reconciled_pages = [
            {
                "id": "registration",
                "pb_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "FAIL", "discrepancy": None},
                    {"reconciled": "UNKNOWN", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": "Text scorer lacked spatial information."},
                    {"reconciled": "PASS", "discrepancy": "Only evaluated by visual scorer"},
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": "Only evaluated by visual scorer"},
                ],
                "consumer_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": "Visual scorer lacked redirect information."},
                ],
                "deal_breakers": [],
            },
            {
                "id": "dashboard",
                "pb_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": "Text scorer lacked spatial information."},
                    {"reconciled": "PASS", "discrepancy": "Only evaluated by visual scorer"},
                ],
                "consumer_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": None},
                    {"reconciled": "PASS", "discrepancy": None},
                ],
                "deal_breakers": [],
            },
        ]
        verification_tasks = [
            {"id": "V1", "type": "data_persistence", "result": "PASS", "evidence": "..."},
            {"id": "V3", "type": "auth_persistence", "result": "PASS", "evidence": "..."},
            {"id": "V4", "type": "auth_boundary", "result": "PASS", "evidence": "..."},
        ]

        result = _compute_summary(reconciled_pages, NETWORK_VERIFICATION, verification_tasks)

        assert result["pb_criteria_total"] == 10
        assert result["pb_criteria_passed"] == 8
        assert result["pb_criteria_failed"] == 1
        assert result["pb_criteria_unknown"] == 1
        assert result["consumer_criteria_total"] == 5
        assert result["consumer_criteria_passed"] == 5
        assert result["consumer_criteria_failed"] == 0
        assert result["verification_tasks_total"] == 3
        assert result["verification_tasks_passed"] == 3
        assert result["verification_tasks_failed"] == 0
        assert result["network_issues"] == 0
        assert result["deal_breakers_triggered"] == []
        assert "registration" in result["pages_with_failures"]
        assert "dashboard" in result["pages_clean"]
