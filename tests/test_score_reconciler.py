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
NETWORK_VERIFICATION = json.loads(
    (FIXTURES / "sample_network_verifier_output.json").read_text()
)


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
                {
                    "id": "V1",
                    "type": "data_persistence",
                    "description": "test",
                    "check": "test",
                }
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
            [
                {
                    "page_id": "reg",
                    "features_detected": [],
                    "pb_criteria": [],
                    "consumer_criteria": [],
                }
            ],
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
            [
                {
                    "page_id": "reg",
                    "features_detected": [],
                    "pb_criteria": [],
                    "consumer_criteria": [],
                }
            ],
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
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Text scorer lacked spatial information.",
                    },
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Only evaluated by visual scorer",
                    },
                    {"reconciled": "PASS", "discrepancy": None},
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Only evaluated by visual scorer",
                    },
                ],
                "consumer_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Visual scorer lacked redirect information.",
                    },
                ],
                "deal_breakers": [],
            },
            {
                "id": "dashboard",
                "pb_criteria": [
                    {"reconciled": "PASS", "discrepancy": None},
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Text scorer lacked spatial information.",
                    },
                    {
                        "reconciled": "PASS",
                        "discrepancy": "Only evaluated by visual scorer",
                    },
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
            {
                "id": "V1",
                "type": "data_persistence",
                "result": "PASS",
                "evidence": "...",
            },
            {
                "id": "V3",
                "type": "auth_persistence",
                "result": "PASS",
                "evidence": "...",
            },
            {"id": "V4", "type": "auth_boundary", "result": "PASS", "evidence": "..."},
        ]

        result = _compute_summary(
            reconciled_pages, NETWORK_VERIFICATION, verification_tasks
        )

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


class TestAssembleFinalReport:
    def test_version_is_set(self):
        from persona_browser.score_reconciler import _assemble_final_report

        result = _assemble_final_report(
            navigator_output={
                "status": "DONE",
                "persona": "test",
                "url": "http://test",
            },
            reconciled_pages=[],
            network_verification={"deal_breakers": [], "issues": []},
            manifest_coverage={
                "expected_pages": [],
                "visited": [],
                "not_visited": [],
                "unexpected_pages": [],
            },
            verification_tasks=[],
            elapsed_seconds=10.5,
        )
        assert result["version"] == "1.1"
        assert result["elapsed_seconds"] == 10.5

    def test_source_tag_added_to_network_verification(self):
        from persona_browser.score_reconciler import _assemble_final_report

        result = _assemble_final_report(
            navigator_output={
                "status": "DONE",
                "persona": "test",
                "url": "http://test",
            },
            reconciled_pages=[],
            network_verification={
                "deal_breakers": [],
                "issues": [],
                "api_calls_total": 3,
            },
            manifest_coverage={
                "expected_pages": [],
                "visited": [],
                "not_visited": [],
                "unexpected_pages": [],
            },
            verification_tasks=[],
            elapsed_seconds=5.0,
        )
        assert "_source" in result["network_verification"]
        assert "Network Verifier" in result["network_verification"]["_source"]
        assert result["network_verification"]["api_calls_total"] == 3

    def test_optional_fields_conditional(self):
        from persona_browser.score_reconciler import _assemble_final_report

        result_without = _assemble_final_report(
            navigator_output={
                "status": "DONE",
                "persona": "test",
                "url": "http://test",
            },
            reconciled_pages=[],
            network_verification={"deal_breakers": [], "issues": []},
            manifest_coverage={
                "expected_pages": [],
                "visited": [],
                "not_visited": [],
                "unexpected_pages": [],
            },
            verification_tasks=[],
            elapsed_seconds=5.0,
        )
        assert "scope" not in result_without
        assert "agent_result" not in result_without
        assert "experience" not in result_without
        assert "screenshots" not in result_without
        result_with = _assemble_final_report(
            navigator_output={
                "status": "DONE",
                "persona": "test",
                "url": "http://test",
                "scope": "gate",
                "agent_result": "Test narrative",
                "experience": {"satisfaction": 8},
                "screenshots": ["ss1.png"],
            },
            reconciled_pages=[],
            network_verification={"deal_breakers": [], "issues": []},
            manifest_coverage={
                "expected_pages": [],
                "visited": [],
                "not_visited": [],
                "unexpected_pages": [],
            },
            verification_tasks=[],
            elapsed_seconds=5.0,
        )
        assert result_with["scope"] == "gate"
        assert result_with["agent_result"] == "Test narrative"
        assert result_with["experience"] == {"satisfaction": 8}
        assert result_with["screenshots"] == ["ss1.png"]


SCORER_RESULTS = json.loads((FIXTURES / "sample_scorer_results.json").read_text())


from unittest.mock import AsyncMock, MagicMock


class TestReconcilePage:
    @pytest.mark.asyncio
    async def test_both_agree(self):
        """Mock LLM returns reconciled page. Verify page_id and criteria structure."""
        from persona_browser.score_reconciler import _reconcile_page

        text_page = SCORER_RESULTS["text_scores"][0]
        visual_page = SCORER_RESULTS["visual_scores"][0]

        # Mock LLM response
        llm_response_json = '{"pb_criteria": [{"feature": "forms", "criterion": "Every field has a visible label", "reconciled": "PASS", "confidence": "high", "evidence": "Both scorers agree", "discrepancy": null}], "consumer_criteria": [{"criterion": "Registration form has Full Name, Email Address, and Password fields", "reconciled": "PASS", "confidence": "high", "evidence": "Both scorers agree", "discrepancy": null}], "deal_breakers": []}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content=llm_response_json)

        result = await _reconcile_page(
            page_id="registration",
            text_page=text_page,
            visual_page=visual_page,
            network_verification=NETWORK_VERIFICATION,
            rubric_text="test rubric",
            pb_rubric_text="test pb rubric",
            availability="both",
            llm=mock_llm,
        )

        assert result["page_id"] == "registration"
        assert len(result["pb_criteria"]) >= 1
        assert result["pb_criteria"][0]["reconciled"] == "PASS"
        assert result["pb_criteria"][0]["confidence"] == "high"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_only_mode(self):
        """When visual_page is None, LLM gets text_only prompt. Confidence should be low."""
        from persona_browser.score_reconciler import _reconcile_page

        text_page = SCORER_RESULTS["text_scores"][0]

        llm_response_json = '{"pb_criteria": [{"feature": "forms", "criterion": "Every field has a visible label", "reconciled": "PASS", "confidence": "low", "evidence": "Text scorer only", "discrepancy": null}], "consumer_criteria": [], "deal_breakers": []}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content=llm_response_json)

        result = await _reconcile_page(
            page_id="registration",
            text_page=text_page,
            visual_page=None,
            network_verification=NETWORK_VERIFICATION,
            rubric_text="test rubric",
            pb_rubric_text="test pb rubric",
            availability="text_only",
            llm=mock_llm,
        )

        assert result["page_id"] == "registration"
        assert result["pb_criteria"][0]["confidence"] == "low"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_parse_failure_returns_unknown(self):
        """When LLM returns invalid JSON, fallback to UNKNOWN for all criteria."""
        from persona_browser.score_reconciler import _reconcile_page

        text_page = SCORER_RESULTS["text_scores"][0]
        visual_page = SCORER_RESULTS["visual_scores"][0]

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="This is not valid JSON")

        result = await _reconcile_page(
            page_id="registration",
            text_page=text_page,
            visual_page=visual_page,
            network_verification=NETWORK_VERIFICATION,
            rubric_text="test rubric",
            pb_rubric_text="test pb rubric",
            availability="both",
            llm=mock_llm,
        )

        assert result["page_id"] == "registration"
        # All criteria should be UNKNOWN (fallback)
        for c in result["pb_criteria"]:
            assert c["reconciled"] == "UNKNOWN"
            assert c["confidence"] == "low"
            assert c["text_result"] == "UNKNOWN"
            assert c["visual_result"] == "UNKNOWN"
        for c in result["consumer_criteria"]:
            assert c["reconciled"] == "UNKNOWN"
            assert c["confidence"] == "low"
            assert c["text_result"] == "UNKNOWN"
            assert c["visual_result"] == "UNKNOWN"


class TestReconcileScores:
    @pytest.mark.asyncio
    async def test_full_reconciliation(self):
        """Full reconcile_scores call with mocked LLM. Verify it calls LLM once per page."""
        from persona_browser.score_reconciler import reconcile_scores

        text_scores = SCORER_RESULTS["text_scores"]
        visual_scores = SCORER_RESULTS["visual_scores"]

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content='{"pb_criteria": [{"feature": "forms", "criterion": "test", "reconciled": "PASS", "confidence": "high", "evidence": "test", "discrepancy": null}], "consumer_criteria": [{"criterion": "test", "reconciled": "PASS", "confidence": "high", "evidence": "test", "discrepancy": null}], "deal_breakers": []}')

        result = await reconcile_scores(
            text_scores=text_scores,
            visual_scores=visual_scores,
            network_verification=NETWORK_VERIFICATION,
            navigator_output=NAVIGATOR_OUTPUT,
            manifest=MANIFEST,
            rubric_text="test rubric",
            pb_rubric_text="test pb rubric",
            llm=mock_llm,
        )

        assert result["version"] == "1.1"
        assert "pages" in result
        assert "summary" in result
        assert "manifest_coverage" in result
        # LLM should be called once per page (2 pages in fixture)
        assert mock_llm.ainvoke.call_count == 2
