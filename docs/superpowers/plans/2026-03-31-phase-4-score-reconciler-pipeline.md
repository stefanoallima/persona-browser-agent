# Phase 4: Score Reconciler + Full Pipeline Implementation Plan

> **Status: COMPLETED** (2026-03-31). Implementation in `persona_browser/score_reconciler.py`, `pipeline.py`. Config + CLI updated. 137 tests passing.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task is independent unless noted — Tasks 1–4 can be done in parallel; Tasks 5–6 depend on Tasks 1–4; Task 7 depends on Tasks 5–6.

**Goal:** Build the Score Reconciler (LLM-based, Sonnet) and wire the full pipeline: navigator → parallel scorers → score reconciler → final JSON report. Implement graceful degradation for every failure mode.

**Architecture:** Three-phase reconciler (deterministic pre-processing → per-page LLM reconciliation → deterministic post-processing). New `pipeline.py` orchestrates the full flow. Config gets a `scoring` section with 3 LLM sub-configs. CLI routes to full pipeline when `--codeintel` and `--rubric` are provided.

**Tech Stack:** Python 3.11+, `browser_use.llm.litellm.chat.ChatLiteLLM` for LLM calls (same as `agent.py`), `asyncio` for parallel execution, `jsonschema` for schema validation in tests, `pytest` + `unittest.mock` for TDD (LLM calls mocked in all unit tests).

**Key references (read before implementing):**
- `docs/superpowers/specs/2026-03-31-phase-4-score-reconciler-pipeline-design.md` — full design spec
- `schemas/final-report.schema.json` — exact output structure for the final report
- `schemas/text-scorer-output.schema.json` — per-page text scorer output structure
- `schemas/visual-scorer-output.schema.json` — per-page visual scorer output structure
- `schemas/network-verifier-output.schema.json` — network verifier output structure
- `fixtures/sample_navigator_output.json` — navigator output format (input to scorers)
- `fixtures/sample_network_verifier_output.json` — network verifier output
- `fixtures/sample_codeintel.json` — codeintel structure
- `fixtures/sample_manifest.json` — manifest with verification_tasks
- `fixtures/sample_rubric.md` — consumer rubric format
- `rubrics/pb-feature-rubric.md` — PB feature rubric (built-in)
- `persona_browser/text_scorer.py` — reference for LLM call pattern, prompt structure, JSON parsing
- `persona_browser/scorer_runner.py` — parallel scorer execution (feeds into reconciler)
- `persona_browser/config.py` — current config models
- `persona_browser/cli.py` — current CLI routing

---

## File Structure After Phase 4

```
persona_browser/
  score_reconciler.py   CREATE  — LLM-based per-page reconciliation + deterministic helpers
  pipeline.py           CREATE  — full pipeline orchestrator
  config.py             MODIFY  — add ScoringConfig with 3 LLM sub-configs
  cli.py                MODIFY  — activate --codeintel/--rubric, wire to pipeline.py

tests/
  test_score_reconciler.py  CREATE  (~15 tests, mocked LLM)
  test_pipeline.py          CREATE  (~8 tests, all components mocked)

fixtures/
  sample_scorer_results.json   CREATE  — combined scorer output for reconciler tests
  sample_final_report.json     CREATE  — expected final report for pipeline tests
```

---

## Task 1: Config Changes (ScoringConfig)

**Files:**
- Modify: `persona_browser/config.py`
- Test: `tests/test_config.py` (existing)

### Step 1: Write the failing test

- [ ] Add test to `tests/test_config.py`:

```python
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


def test_config_without_scoring_uses_defaults():
    """Config without scoring section should use defaults (backward compat)."""
    from persona_browser.config import Config

    config = Config(**{"llm": {"model": "some/navigator-model"}})
    assert config.scoring.text_scorer.model != ""
    assert config.scoring.visual_scorer.model != ""
    assert config.scoring.reconciler.model != ""
```

### Step 2: Run tests to verify they fail

- [ ] Run: `pytest tests/test_config.py -v -k "scoring"`

Expected: FAIL — `ScoringConfig` and `ScoringLLMConfig` do not exist yet.

### Step 3: Implement ScoringConfig

- [ ] Edit `persona_browser/config.py` — add after the existing `LLMConfig` class:

```python
class ScoringLLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = ""
    endpoint: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 20000


class ScoringConfig(BaseModel):
    text_scorer: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="zhipuai/glm-5-turbo",
        )
    )
    visual_scorer: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="google/gemini-3-flash",
        )
    )
    reconciler: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="anthropic/claude-sonnet-4-6",
        )
    )
```

Then modify the existing `Config` class to add the new field:

```python
class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)  # NEW
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
```

### Step 4: Run tests to verify they pass

- [ ] Run: `pytest tests/test_config.py -v`

Expected: ALL PASS (existing tests should still pass too).

### Step 5: Commit

- [ ] ```bash
git add persona_browser/config.py tests/test_config.py
git commit -m "feat: add ScoringConfig with text_scorer, visual_scorer, reconciler LLM configs"
```

---

## Task 2: Test Fixtures (sample_scorer_results.json + sample_final_report.json)

**Files:**
- Create: `fixtures/sample_scorer_results.json`
- Create: `fixtures/sample_final_report.json`

### Step 1: Create sample_scorer_results.json

- [ ] Create `fixtures/sample_scorer_results.json` — this represents what `run_scorers()` returns for the sample navigator output. Must cover: both-agree, disagreement, one-UNKNOWN, one-scorer-only, and deal-breaker cases.

```json
{
  "network_verification": {
    "api_calls_total": 3,
    "api_calls_matched_codeintel": 3,
    "api_calls_unmatched": 0,
    "api_errors_during_normal_flow": 0,
    "auth_token_set_after_auth": true,
    "auth_token_sent_on_protected_requests": true,
    "auth_persists_after_refresh": true,
    "deal_breakers": [],
    "issues": [],
    "per_endpoint": [
      {
        "method": "POST",
        "path": "/api/auth/register",
        "matched_codeintel": true,
        "status": 201,
        "expected_status": 201,
        "contract_match": true,
        "auth_check": "N/A (public endpoint — sets auth)"
      },
      {
        "method": "GET",
        "path": "/api/user/me",
        "matched_codeintel": true,
        "status": 200,
        "expected_status": 200,
        "contract_match": true,
        "auth_check": "PASS — session cookie sent and accepted"
      },
      {
        "method": "GET",
        "path": "/api/user/me",
        "matched_codeintel": true,
        "status": 200,
        "expected_status": 200,
        "contract_match": true,
        "auth_check": "PASS — session cookie still valid after page refresh"
      }
    ]
  },
  "text_scores": [
    {
      "page_id": "registration",
      "pb_criteria": [
        {
          "feature": "forms",
          "criterion": "Every field has a visible label",
          "result": "PASS",
          "evidence": "Navigator described 3 labeled fields: Full Name, Email Address, Password",
          "confidence": "high"
        },
        {
          "feature": "forms",
          "criterion": "Required fields are marked",
          "result": "FAIL",
          "evidence": "No asterisks or 'required' indicators described by navigator",
          "confidence": "high"
        },
        {
          "feature": "forms",
          "criterion": "Error message appears near the triggering field",
          "result": "UNKNOWN",
          "evidence": "Cannot determine spatial position from text observations",
          "confidence": "low"
        },
        {
          "feature": "forms",
          "criterion": "Submit button is visible without scrolling",
          "result": "UNKNOWN",
          "evidence": "Cannot determine scrolling position from text observations",
          "confidence": "low"
        },
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "result": "PASS",
          "evidence": "Navigator reported clean page load, no errors",
          "confidence": "high"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Registration form has Full Name, Email Address, and Password fields",
          "result": "PASS",
          "evidence": "Navigator described all three fields present",
          "confidence": "high",
          "codeintel_ref": "pages[0].elements.forms[0].fields"
        },
        {
          "criterion": "Submitting valid data redirects to /dashboard",
          "result": "PASS",
          "evidence": "Navigator reported redirect to /dashboard after form submission",
          "confidence": "high",
          "codeintel_ref": "pages[0].elements.forms[0].on_success.redirect"
        }
      ]
    },
    {
      "page_id": "dashboard",
      "pb_criteria": [
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "result": "PASS",
          "evidence": "Dashboard loaded with user data displayed",
          "confidence": "high"
        },
        {
          "feature": "data_display",
          "criterion": "Most important data is above the fold",
          "result": "UNKNOWN",
          "evidence": "Cannot determine fold position from text observations",
          "confidence": "low"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Dashboard displays user's full name",
          "result": "PASS",
          "evidence": "Navigator saw 'Name: Jordan Rivera'",
          "confidence": "high"
        },
        {
          "criterion": "Dashboard displays user's email address",
          "result": "PASS",
          "evidence": "Navigator saw 'Email: jordan@example.com'",
          "confidence": "high"
        },
        {
          "criterion": "Logout button is present",
          "result": "PASS",
          "evidence": "Navigator described 'Logout button visible'",
          "confidence": "high"
        }
      ]
    }
  ],
  "visual_scores": [
    {
      "page_id": "registration",
      "features_detected": ["forms", "cta", "baseline"],
      "pb_criteria": [
        {
          "feature": "forms",
          "criterion": "Every field has a visible label",
          "result": "PASS",
          "evidence": "Screenshot shows 3 fields with labels: Full Name, Email Address, Password",
          "confidence": "high"
        },
        {
          "feature": "forms",
          "criterion": "Required fields are marked",
          "result": "FAIL",
          "evidence": "No asterisks or required indicators visible in screenshot",
          "confidence": "high"
        },
        {
          "feature": "forms",
          "criterion": "Error message appears near the triggering field",
          "result": "UNKNOWN",
          "evidence": "No error state visible in the screenshot taken (form was submitted successfully)",
          "confidence": "low"
        },
        {
          "feature": "forms",
          "criterion": "Submit button is visible without scrolling",
          "result": "PASS",
          "evidence": "Register button visible in screenshot viewport without scrolling",
          "confidence": "high"
        },
        {
          "feature": "cta",
          "criterion": "Primary CTA is the most visually prominent element",
          "result": "PASS",
          "evidence": "Register button has purple gradient, full-width, stands out",
          "confidence": "high"
        },
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "result": "PASS",
          "evidence": "Clean page render, no error messages or broken elements",
          "confidence": "high"
        },
        {
          "feature": "baseline",
          "criterion": "Text is readable (sufficient contrast, reasonable size)",
          "result": "PASS",
          "evidence": "Dark text on white card, good contrast ratio",
          "confidence": "high"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Registration form has Full Name, Email Address, and Password fields",
          "result": "PASS",
          "evidence": "All three fields visible in screenshot with correct labels",
          "confidence": "high",
          "codeintel_ref": "pages[0].elements.forms[0].fields"
        },
        {
          "criterion": "Submitting valid data redirects to /dashboard",
          "result": "UNKNOWN",
          "evidence": "Cannot verify redirect from a static screenshot",
          "confidence": "low"
        }
      ]
    },
    {
      "page_id": "dashboard",
      "features_detected": ["data_display", "navigation", "baseline"],
      "pb_criteria": [
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "result": "PASS",
          "evidence": "Dashboard rendered cleanly with user data card",
          "confidence": "high"
        },
        {
          "feature": "data_display",
          "criterion": "Most important data is above the fold",
          "result": "PASS",
          "evidence": "User name and email visible in top half of viewport",
          "confidence": "high"
        },
        {
          "feature": "navigation",
          "criterion": "No dead-end pages (always a path forward or back)",
          "result": "PASS",
          "evidence": "Logout button provides exit path from dashboard",
          "confidence": "high"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Dashboard displays user's full name",
          "result": "PASS",
          "evidence": "Screenshot shows 'Name: Jordan Rivera' in user info card",
          "confidence": "high"
        },
        {
          "criterion": "Dashboard displays user's email address",
          "result": "PASS",
          "evidence": "Screenshot shows 'Email: jordan@example.com' in user info card",
          "confidence": "high"
        },
        {
          "criterion": "Logout button is present",
          "result": "PASS",
          "evidence": "Logout button visible at bottom of card",
          "confidence": "high"
        }
      ]
    }
  ]
}
```

### Step 2: Create sample_final_report.json

- [ ] Create `fixtures/sample_final_report.json` — expected pipeline output matching `schemas/final-report.schema.json`:

```json
{
  "version": "1.1",
  "status": "DONE",
  "elapsed_seconds": 52.3,
  "persona": "micro-persona-signup-form",
  "url": "http://localhost:3333",
  "scope": "gate",
  "agent_result": "Successfully completed the signup flow on the test app...",
  "manifest_coverage": {
    "expected_pages": ["registration", "dashboard"],
    "visited": ["registration", "dashboard"],
    "not_visited": [],
    "unexpected_pages": []
  },
  "pages": [
    {
      "id": "registration",
      "url_visited": "http://localhost:3333/register",
      "screenshot": "screenshots/step_1.png",
      "features_detected": ["forms", "cta", "baseline"],
      "observations": {
        "description": "The registration page renders a centered card on a purple gradient background..."
      },
      "pb_criteria": [
        {
          "feature": "forms",
          "criterion": "Every field has a visible label",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm: 3 fields with visible labels (Full Name, Email Address, Password)",
          "discrepancy": null
        },
        {
          "feature": "forms",
          "criterion": "Required fields are marked",
          "text_result": "FAIL",
          "visual_result": "FAIL",
          "reconciled": "FAIL",
          "confidence": "high",
          "evidence": "Both scorers confirm: no required field indicators found",
          "discrepancy": null
        },
        {
          "feature": "forms",
          "criterion": "Error message appears near the triggering field",
          "text_result": "UNKNOWN",
          "visual_result": "UNKNOWN",
          "reconciled": "UNKNOWN",
          "confidence": "low",
          "evidence": "Neither scorer could evaluate — no error state captured",
          "discrepancy": null
        },
        {
          "feature": "forms",
          "criterion": "Submit button is visible without scrolling",
          "text_result": "UNKNOWN",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Visual scorer confirms button visible in viewport. Text scorer could not assess spatial position.",
          "discrepancy": "Text scorer lacked spatial information. Visual scorer's assessment is definitive."
        },
        {
          "feature": "cta",
          "criterion": "Primary CTA is the most visually prominent element",
          "text_result": "UNKNOWN",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Visual scorer confirms Register button has purple gradient, full-width, most prominent. Only visual scorer evaluated this criterion.",
          "discrepancy": "Only evaluated by visual scorer"
        },
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm clean page load",
          "discrepancy": null
        },
        {
          "feature": "baseline",
          "criterion": "Text is readable (sufficient contrast, reasonable size)",
          "text_result": "UNKNOWN",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Visual scorer confirms dark text on white card with good contrast. Only visual scorer evaluated this criterion.",
          "discrepancy": "Only evaluated by visual scorer"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Registration form has Full Name, Email Address, and Password fields",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm all three fields present with correct labels",
          "codeintel_ref": "pages[0].elements.forms[0].fields",
          "discrepancy": null
        },
        {
          "criterion": "Submitting valid data redirects to /dashboard",
          "text_result": "PASS",
          "visual_result": "UNKNOWN",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Text scorer confirms redirect occurred. Visual scorer cannot verify redirect from screenshot.",
          "discrepancy": "Visual scorer lacked redirect information. Text scorer's assessment is definitive for behavioral criterion."
        }
      ],
      "deal_breakers": []
    },
    {
      "id": "dashboard",
      "url_visited": "http://localhost:3333/dashboard",
      "screenshot": "screenshots/step_5.png",
      "features_detected": ["data_display", "navigation", "baseline"],
      "observations": {
        "description": "The dashboard page renders a centered card on the same purple gradient background..."
      },
      "pb_criteria": [
        {
          "feature": "baseline",
          "criterion": "Page loads without visible errors",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm dashboard loaded cleanly",
          "discrepancy": null
        },
        {
          "feature": "data_display",
          "criterion": "Most important data is above the fold",
          "text_result": "UNKNOWN",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Visual scorer confirms user data visible in top half of viewport",
          "discrepancy": "Text scorer lacked spatial information. Visual scorer's assessment is definitive."
        },
        {
          "feature": "navigation",
          "criterion": "No dead-end pages (always a path forward or back)",
          "text_result": "UNKNOWN",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "medium",
          "evidence": "Visual scorer confirms Logout button provides exit path. Only visual scorer evaluated.",
          "discrepancy": "Only evaluated by visual scorer"
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Dashboard displays user's full name",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm 'Name: Jordan Rivera' displayed",
          "discrepancy": null
        },
        {
          "criterion": "Dashboard displays user's email address",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm 'Email: jordan@example.com' displayed",
          "discrepancy": null
        },
        {
          "criterion": "Logout button is present",
          "text_result": "PASS",
          "visual_result": "PASS",
          "reconciled": "PASS",
          "confidence": "high",
          "evidence": "Both scorers confirm Logout button visible",
          "discrepancy": null
        }
      ],
      "deal_breakers": []
    }
  ],
  "experience": {
    "first_impression": "Clean, minimal signup form. Purple gradient background gives it a modern look.",
    "easy": [
      "Form fields are clearly labeled",
      "Single-action flow: fill form, click Register, done",
      "Immediate feedback via redirect to dashboard on success"
    ],
    "hard": [],
    "hesitation_points": [
      "No password strength indicator"
    ],
    "would_return": true,
    "would_recommend": "Yes — the signup flow is frictionless",
    "satisfaction": 8,
    "satisfaction_reason": "Registration completed in one attempt with no errors."
  },
  "network_verification": {
    "_source": "Network Verifier (deterministic module — not LLM)",
    "api_calls_total": 3,
    "api_calls_matched_codeintel": 3,
    "api_calls_unmatched": 0,
    "api_errors_during_normal_flow": 0,
    "auth_token_set_after_auth": true,
    "auth_token_sent_on_protected_requests": true,
    "auth_persists_after_refresh": true,
    "deal_breakers": [],
    "issues": [],
    "per_endpoint": [
      {
        "method": "POST",
        "path": "/api/auth/register",
        "matched_codeintel": true,
        "status": 201,
        "expected_status": 201,
        "contract_match": true,
        "auth_check": "N/A (public endpoint — sets auth)"
      },
      {
        "method": "GET",
        "path": "/api/user/me",
        "matched_codeintel": true,
        "status": 200,
        "expected_status": 200,
        "contract_match": true,
        "auth_check": "PASS — session cookie sent and accepted"
      },
      {
        "method": "GET",
        "path": "/api/user/me",
        "matched_codeintel": true,
        "status": 200,
        "expected_status": 200,
        "contract_match": true,
        "auth_check": "PASS — session cookie still valid after page refresh"
      }
    ]
  },
  "verification_tasks": [
    {
      "id": "V1",
      "type": "data_persistence",
      "result": "PASS",
      "evidence": "Dashboard re-rendered after F5 page refresh without redirect to /register; GET /api/user/me returned 200 again, confirming the httpOnly session cookie persists across full page reloads"
    },
    {
      "id": "V3",
      "type": "auth_persistence",
      "result": "PASS",
      "evidence": "Dashboard re-rendered after F5 page refresh without redirect to /register; GET /api/user/me returned 200 again, confirming the httpOnly session cookie persists across full page reloads"
    },
    {
      "id": "V4",
      "type": "auth_boundary",
      "result": "PASS",
      "evidence": "After POST /api/auth/register 201, browser redirected to /dashboard which rendered correctly; GET /api/user/me returned 200 with user data, confirming the session cookie was accepted by the server"
    }
  ],
  "summary": {
    "pb_criteria_total": 10,
    "pb_criteria_passed": 8,
    "pb_criteria_failed": 1,
    "pb_criteria_unknown": 1,
    "consumer_criteria_total": 5,
    "consumer_criteria_passed": 5,
    "consumer_criteria_failed": 0,
    "verification_tasks_total": 3,
    "verification_tasks_passed": 3,
    "verification_tasks_failed": 0,
    "network_issues": 0,
    "total_discrepancies": 5,
    "deal_breakers_triggered": [],
    "pages_with_failures": ["registration"],
    "pages_clean": ["dashboard"]
  },
  "screenshots": [
    "screenshots/step_1.png",
    "screenshots/step_5.png"
  ],
  "video": null
}
```

### Step 3: Validate fixtures against schemas

- [ ] Run:

```bash
python -c "
import json, jsonschema
schema = json.load(open('schemas/final-report.schema.json'))
report = json.load(open('fixtures/sample_final_report.json'))
jsonschema.validate(report, schema)
print('sample_final_report.json validates OK')
"
```

Expected: validates without error (or reveals schema mismatches to fix).

### Step 4: Commit

- [ ] ```bash
git add fixtures/sample_scorer_results.json fixtures/sample_final_report.json
git commit -m "feat: add Phase 4 test fixtures for scorer results and final report"
```

---

## Task 3: Score Reconciler — Deterministic Helpers (~12 tests)

**Files:**
- Create: `persona_browser/score_reconciler.py` (partial — deterministic functions only)
- Create: `tests/test_score_reconciler.py` (partial — deterministic tests only)

### Step 1: Write test file with deterministic tests

- [ ] Create `tests/test_score_reconciler.py`:

```python
"""Tests for score_reconciler — deterministic helpers + mocked LLM reconciliation.

Uses sample fixtures. LLM calls mocked in reconciliation tests.
Run: pytest tests/test_score_reconciler.py -v
"""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"
NAVIGATOR_OUTPUT = json.loads((FIXTURES / "sample_navigator_output.json").read_text())
SCORER_RESULTS = json.loads((FIXTURES / "sample_scorer_results.json").read_text())
MANIFEST = json.loads((FIXTURES / "sample_manifest.json").read_text())
NETWORK_VERIFICATION = json.loads((FIXTURES / "sample_network_verifier_output.json").read_text())


# =========================================================================
# _check_manifest_coverage tests
# =========================================================================

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

        # Navigator only visited registration, not dashboard
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
        # Without manifest, use navigator's own coverage report
        assert "expected_pages" in result
        assert "visited" in result


# =========================================================================
# _evaluate_verification_tasks tests
# =========================================================================

class TestVerificationTasks:
    def test_all_pass(self):
        from persona_browser.score_reconciler import _evaluate_verification_tasks

        result = _evaluate_verification_tasks(NAVIGATOR_OUTPUT, MANIFEST)
        assert len(result) >= 2  # At least V1 and V3 from our manifest
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

        # Navigator has no auth_flow_verification at all
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
        # Without manifest, derive from auth_flow_verification if present
        # Should still produce some results from auth_flow_verification
        assert isinstance(result, list)


# =========================================================================
# _classify_scorer_availability tests
# =========================================================================

class TestClassifyScorerAvailability:
    def test_both_available(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            SCORER_RESULTS["text_scores"],
            SCORER_RESULTS["visual_scores"],
        )
        assert result == "both"

    def test_text_only(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            SCORER_RESULTS["text_scores"],
            {"error": "No visual LLM provided"},
        )
        assert result == "text_only"

    def test_visual_only(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            {"error": "Text scorer failed"},
            SCORER_RESULTS["visual_scores"],
        )
        assert result == "visual_only"

    def test_neither(self):
        from persona_browser.score_reconciler import _classify_scorer_availability

        result = _classify_scorer_availability(
            {"error": "Text failed"},
            {"error": "Visual failed"},
        )
        assert result == "neither"


# =========================================================================
# _compute_summary tests
# =========================================================================

class TestComputeSummary:
    def test_correct_counts(self):
        from persona_browser.score_reconciler import _compute_summary

        # Use the sample final report's pages as reconciled_pages
        FINAL_REPORT = json.loads((FIXTURES / "sample_final_report.json").read_text())
        reconciled_pages = FINAL_REPORT["pages"]
        verification_tasks = FINAL_REPORT["verification_tasks"]

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
```

### Step 2: Run tests to verify they fail

- [ ] Run: `pytest tests/test_score_reconciler.py -v`

Expected: FAIL — `score_reconciler` module does not exist.

### Step 3: Implement deterministic helpers

- [ ] Create `persona_browser/score_reconciler.py`:

```python
"""
persona_browser/score_reconciler.py

Score Reconciler — reconciles text scorer, visual scorer, and network verifier
outputs into a final report.

Three phases:
1. Deterministic pre-processing (manifest coverage, verification tasks, scorer availability)
2. LLM-based per-page score reconciliation (parallel)
3. Deterministic post-processing (assemble report, compute summary)
"""

from __future__ import annotations

import asyncio
import json
import re


# ---------------------------------------------------------------------------
# Phase 1: Deterministic Pre-Processing
# ---------------------------------------------------------------------------


def _check_manifest_coverage(navigator_output: dict, manifest: dict | None) -> dict:
    """Compare navigator's visited pages against manifest expectations.

    Uses the navigator's own manifest_coverage if present, otherwise
    derives from manifest pages list vs navigator page IDs.
    """
    nav_coverage = navigator_output.get("manifest_coverage", {})

    if nav_coverage:
        return {
            "expected_pages": nav_coverage.get("expected_pages", []),
            "visited": nav_coverage.get("visited", []),
            "not_visited": nav_coverage.get("not_visited", []),
            "unexpected_pages": nav_coverage.get("unexpected_pages", []),
        }

    # Derive from manifest + navigator pages
    nav_page_ids = [p.get("id", "") for p in navigator_output.get("pages", [])]

    if manifest is None:
        return {
            "expected_pages": [],
            "visited": nav_page_ids,
            "not_visited": [],
            "unexpected_pages": [],
        }

    manifest_page_ids = [p.get("id", "") for p in manifest.get("pages", [])]
    visited = [pid for pid in manifest_page_ids if pid in nav_page_ids]
    not_visited = [pid for pid in manifest_page_ids if pid not in nav_page_ids]
    unexpected = [pid for pid in nav_page_ids if pid not in manifest_page_ids]

    return {
        "expected_pages": manifest_page_ids,
        "visited": visited,
        "not_visited": not_visited,
        "unexpected_pages": unexpected,
    }


def _evaluate_verification_tasks(
    navigator_output: dict, manifest: dict | None
) -> list[dict]:
    """Extract and normalize verification task results from navigator output.

    Maps auth_flow_verification fields to structured V1-V4 format.
    Uses manifest verification_tasks as the definitive list when present.
    """
    auth_flow = navigator_output.get("auth_flow_verification", {})
    results: list[dict] = []

    # Mapping from manifest verification_task types to auth_flow_verification fields
    type_to_auth_field = {
        "data_persistence": "persistence_after_refresh",
        "auth_persistence": "persistence_after_refresh",
        "auth_boundary": "post_auth_access",
    }

    if manifest and "verification_tasks" in manifest:
        # Use manifest as definitive list
        for vtask in manifest["verification_tasks"]:
            vid = vtask["id"]
            vtype = vtask["type"]
            auth_field = type_to_auth_field.get(vtype)
            evidence_value = auth_flow.get(auth_field) if auth_field and auth_flow else None

            if evidence_value and isinstance(evidence_value, str) and evidence_value.strip():
                results.append({
                    "id": vid,
                    "type": vtype,
                    "result": "PASS",
                    "evidence": evidence_value,
                })
            else:
                results.append({
                    "id": vid,
                    "type": vtype,
                    "result": "FAIL",
                    "evidence": "Verification task not performed by navigator",
                })
    elif auth_flow:
        # No manifest — derive from auth_flow_verification
        if auth_flow.get("persistence_after_refresh"):
            results.append({
                "id": "V1",
                "type": "data_persistence",
                "result": "PASS",
                "evidence": auth_flow["persistence_after_refresh"],
            })
            results.append({
                "id": "V3",
                "type": "auth_persistence",
                "result": "PASS",
                "evidence": auth_flow["persistence_after_refresh"],
            })
        if auth_flow.get("post_auth_access"):
            results.append({
                "id": "V4",
                "type": "auth_boundary",
                "result": "PASS",
                "evidence": auth_flow["post_auth_access"],
            })

    return results


def _classify_scorer_availability(text_scores, visual_scores) -> str:
    """Determine which scorers produced valid results.

    Returns one of: "both", "text_only", "visual_only", "neither".
    A scorer result is invalid if it's a dict with an "error" key.
    """
    text_ok = isinstance(text_scores, list) and len(text_scores) > 0
    visual_ok = isinstance(visual_scores, list) and len(visual_scores) > 0

    if text_ok and visual_ok:
        return "both"
    elif text_ok:
        return "text_only"
    elif visual_ok:
        return "visual_only"
    else:
        return "neither"


# ---------------------------------------------------------------------------
# Phase 3: Deterministic Post-Processing
# ---------------------------------------------------------------------------


def _compute_summary(
    reconciled_pages: list[dict],
    network_verification: dict,
    verification_tasks: list[dict],
) -> dict:
    """Compute aggregate summary stats deterministically."""
    pb_total = pb_passed = pb_failed = pb_unknown = 0
    con_total = con_passed = con_failed = 0
    total_discrepancies = 0
    all_deal_breakers: list[str] = []
    pages_with_failures: list[str] = []
    pages_clean: list[str] = []

    for page in reconciled_pages:
        page_id = page.get("id", "unknown")
        page_has_failure = False

        for c in page.get("pb_criteria", []):
            pb_total += 1
            r = c.get("reconciled", "UNKNOWN")
            if r == "PASS":
                pb_passed += 1
            elif r == "FAIL":
                pb_failed += 1
                page_has_failure = True
            else:
                pb_unknown += 1
            if c.get("discrepancy"):
                total_discrepancies += 1

        for c in page.get("consumer_criteria", []):
            con_total += 1
            r = c.get("reconciled", "UNKNOWN")
            if r == "PASS":
                con_passed += 1
            elif r == "FAIL":
                con_failed += 1
                page_has_failure = True
            if c.get("discrepancy"):
                total_discrepancies += 1

        deal_breakers = page.get("deal_breakers", [])
        if deal_breakers:
            page_has_failure = True
            all_deal_breakers.extend(deal_breakers)

        if page_has_failure:
            pages_with_failures.append(page_id)
        else:
            pages_clean.append(page_id)

    # Network deal-breakers
    net_deal_breakers = network_verification.get("deal_breakers", [])
    all_deal_breakers.extend(net_deal_breakers)
    network_issues = len(network_verification.get("issues", []))

    vt_total = len(verification_tasks)
    vt_passed = sum(1 for v in verification_tasks if v.get("result") == "PASS")
    vt_failed = vt_total - vt_passed

    return {
        "pb_criteria_total": pb_total,
        "pb_criteria_passed": pb_passed,
        "pb_criteria_failed": pb_failed,
        "pb_criteria_unknown": pb_unknown,
        "consumer_criteria_total": con_total,
        "consumer_criteria_passed": con_passed,
        "consumer_criteria_failed": con_failed,
        "verification_tasks_total": vt_total,
        "verification_tasks_passed": vt_passed,
        "verification_tasks_failed": vt_failed,
        "network_issues": network_issues,
        "total_discrepancies": total_discrepancies,
        "deal_breakers_triggered": all_deal_breakers,
        "pages_with_failures": pages_with_failures,
        "pages_clean": pages_clean,
    }


def _assemble_final_report(
    navigator_output: dict,
    reconciled_pages: list[dict],
    network_verification: dict,
    manifest_coverage: dict,
    verification_tasks: list[dict],
    elapsed_seconds: float,
) -> dict:
    """Assemble the final report from all pipeline components.

    Merges navigator metadata with reconciled scoring results.
    Returns dict matching schemas/final-report.schema.json.
    """
    summary = _compute_summary(reconciled_pages, network_verification, verification_tasks)

    report: dict = {
        "version": "1.1",
        "status": navigator_output.get("status", "DONE"),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "persona": navigator_output.get("persona", ""),
        "url": navigator_output.get("url", ""),
        "manifest_coverage": manifest_coverage,
        "pages": reconciled_pages,
        "summary": summary,
    }

    # Optional fields
    if navigator_output.get("scope"):
        report["scope"] = navigator_output["scope"]
    if navigator_output.get("agent_result"):
        report["agent_result"] = navigator_output["agent_result"]
    if navigator_output.get("experience"):
        report["experience"] = navigator_output["experience"]

    # Network verification with source tag
    net_with_source = {"_source": "Network Verifier (deterministic module — not LLM)"}
    net_with_source.update(network_verification)
    report["network_verification"] = net_with_source

    if verification_tasks:
        report["verification_tasks"] = verification_tasks
    if navigator_output.get("screenshots"):
        report["screenshots"] = navigator_output["screenshots"]
    if navigator_output.get("video"):
        report["video"] = navigator_output["video"]

    return report
```

### Step 4: Run tests to verify they pass

- [ ] Run: `pytest tests/test_score_reconciler.py -v`

Expected: ALL PASS.

### Step 5: Commit

- [ ] ```bash
git add persona_browser/score_reconciler.py tests/test_score_reconciler.py
git commit -m "feat: add score_reconciler deterministic helpers with tests"
```

---

## Task 4: Score Reconciler — LLM Reconciliation (~3 tests, mocked)

**Files:**
- Modify: `persona_browser/score_reconciler.py` (add LLM functions)
- Modify: `tests/test_score_reconciler.py` (add LLM tests)

### Step 1: Add LLM reconciliation tests

- [ ] Append to `tests/test_score_reconciler.py`:

```python
from unittest.mock import AsyncMock, MagicMock


# =========================================================================
# _reconcile_page tests (mocked LLM)
# =========================================================================

class TestReconcilePage:
    @pytest.mark.asyncio
    async def test_both_agree(self):
        from persona_browser.score_reconciler import _reconcile_page

        text_page = SCORER_RESULTS["text_scores"][1]   # dashboard — mostly PASS
        visual_page = SCORER_RESULTS["visual_scores"][1]  # dashboard — mostly PASS

        # Mock LLM to return expected reconciliation
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "pb_criteria": [
                {
                    "feature": "baseline",
                    "criterion": "Page loads without visible errors",
                    "text_result": "PASS",
                    "visual_result": "PASS",
                    "reconciled": "PASS",
                    "confidence": "high",
                    "evidence": "Both scorers confirm dashboard loaded cleanly",
                    "discrepancy": None,
                }
            ],
            "consumer_criteria": [
                {
                    "criterion": "Dashboard displays user's full name",
                    "text_result": "PASS",
                    "visual_result": "PASS",
                    "reconciled": "PASS",
                    "confidence": "high",
                    "evidence": "Both scorers confirm name displayed",
                    "discrepancy": None,
                }
            ],
            "deal_breakers": [],
        })
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        result = await _reconcile_page(
            page_id="dashboard",
            text_page=text_page,
            visual_page=visual_page,
            network_verification=NETWORK_VERIFICATION,
            rubric_text="",
            pb_rubric_text="",
            availability="both",
            llm=mock_llm,
        )

        assert result["page_id"] == "dashboard"
        assert len(result["pb_criteria"]) > 0
        assert result["pb_criteria"][0]["reconciled"] == "PASS"
        assert result["pb_criteria"][0]["confidence"] == "high"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_only_mode(self):
        from persona_browser.score_reconciler import _reconcile_page

        text_page = SCORER_RESULTS["text_scores"][0]  # registration

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "pb_criteria": [
                {
                    "feature": "forms",
                    "criterion": "Every field has a visible label",
                    "text_result": "PASS",
                    "visual_result": "UNKNOWN",
                    "reconciled": "PASS",
                    "confidence": "low",
                    "evidence": "Text scorer: 3 labeled fields. Visual scorer unavailable.",
                    "discrepancy": "Visual scorer unavailable — result based on text evidence only",
                }
            ],
            "consumer_criteria": [],
            "deal_breakers": [],
        })
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        result = await _reconcile_page(
            page_id="registration",
            text_page=text_page,
            visual_page=None,
            network_verification=NETWORK_VERIFICATION,
            rubric_text="",
            pb_rubric_text="",
            availability="text_only",
            llm=mock_llm,
        )

        assert result["page_id"] == "registration"
        assert result["pb_criteria"][0]["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_llm_parse_failure_returns_unknown(self):
        from persona_browser.score_reconciler import _reconcile_page

        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON at all"
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        result = await _reconcile_page(
            page_id="registration",
            text_page=SCORER_RESULTS["text_scores"][0],
            visual_page=SCORER_RESULTS["visual_scores"][0],
            network_verification=NETWORK_VERIFICATION,
            rubric_text="",
            pb_rubric_text="",
            availability="both",
            llm=mock_llm,
        )

        assert result["page_id"] == "registration"
        # On parse failure, should return fallback with UNKNOWN
        for c in result.get("pb_criteria", []):
            assert c["reconciled"] == "UNKNOWN"


# =========================================================================
# reconcile_scores (full public API) test
# =========================================================================

class TestReconcileScores:
    @pytest.mark.asyncio
    async def test_full_reconciliation(self):
        from persona_browser.score_reconciler import reconcile_scores

        # Mock LLM — returns a simple reconciled page per call
        call_count = 0

        async def mock_ainvoke(prompt):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.content = json.dumps({
                "pb_criteria": [
                    {
                        "feature": "baseline",
                        "criterion": "Page loads without visible errors",
                        "text_result": "PASS",
                        "visual_result": "PASS",
                        "reconciled": "PASS",
                        "confidence": "high",
                        "evidence": "Both confirm",
                        "discrepancy": None,
                    }
                ],
                "consumer_criteria": [],
                "deal_breakers": [],
            })
            return resp

        mock_llm = AsyncMock()
        mock_llm.ainvoke = mock_ainvoke

        result = await reconcile_scores(
            text_scores=SCORER_RESULTS["text_scores"],
            visual_scores=SCORER_RESULTS["visual_scores"],
            network_verification=NETWORK_VERIFICATION,
            navigator_output=NAVIGATOR_OUTPUT,
            manifest=MANIFEST,
            rubric_text="## Test rubric",
            pb_rubric_text="## PB rubric",
            llm=mock_llm,
        )

        # Should produce a final report dict
        assert result["version"] == "1.1"
        assert "pages" in result
        assert "summary" in result
        assert "manifest_coverage" in result
        assert "network_verification" in result
        # LLM should have been called once per page (2 pages)
        assert call_count == 2
```

### Step 2: Run new tests to verify they fail

- [ ] Run: `pytest tests/test_score_reconciler.py -v -k "Reconcile"`

Expected: FAIL — `_reconcile_page` and `reconcile_scores` do not exist.

### Step 3: Implement LLM reconciliation

- [ ] Add to `persona_browser/score_reconciler.py` — insert between Phase 1 and Phase 3 sections:

```python
# ---------------------------------------------------------------------------
# Phase 2: LLM-Based Score Reconciliation (page-by-page, parallel)
# ---------------------------------------------------------------------------


async def _reconcile_page(
    page_id: str,
    text_page: dict | None,
    visual_page: dict | None,
    network_verification: dict,
    rubric_text: str,
    pb_rubric_text: str,
    availability: str,
    llm=None,
) -> dict:
    """Reconcile scores for a single page via LLM.

    Returns per-page reconciled result with page_id, pb_criteria,
    consumer_criteria, and deal_breakers.
    """
    if availability == "neither" or llm is None:
        return _fallback_page(page_id, text_page, visual_page)

    prompt = _build_reconciliation_prompt(
        page_id, text_page, visual_page, network_verification,
        rubric_text, pb_rubric_text, availability,
    )

    response = await llm.ainvoke(prompt)
    raw_text: str = response.content if hasattr(response, "content") else str(response)

    parsed = _parse_reconciliation_response(raw_text)
    if parsed is None:
        return _fallback_page(page_id, text_page, visual_page)

    parsed["page_id"] = page_id
    if "deal_breakers" not in parsed:
        parsed["deal_breakers"] = []
    return parsed


def _build_reconciliation_prompt(
    page_id: str,
    text_page: dict | None,
    visual_page: dict | None,
    network_verification: dict,
    rubric_text: str,
    pb_rubric_text: str,
    availability: str,
) -> str:
    """Build the reconciliation prompt for a single page."""
    text_section = json.dumps(text_page, indent=2) if text_page else "N/A (text scorer unavailable)"
    visual_section = json.dumps(visual_page, indent=2) if visual_page else "N/A (visual scorer unavailable)"

    # Summarise network issues relevant to this page
    net_issues = network_verification.get("issues", [])
    net_deal_breakers = network_verification.get("deal_breakers", [])
    net_section = ""
    if net_issues:
        net_section += "Network issues: " + "; ".join(net_issues) + "\n"
    if net_deal_breakers:
        net_section += "Network DEAL-BREAKERS: " + "; ".join(net_deal_breakers) + "\n"
    if not net_section:
        net_section = "No network issues detected."

    if availability == "both":
        mode_instructions = """You have BOTH text and visual scorer results.
Reconcile each criterion using these rules:
- Both PASS → reconciled: PASS, confidence: high
- Both FAIL → reconciled: FAIL, confidence: high
- One PASS, one FAIL → Investigate: is this a spatial criterion (trust visual) or behavioral (trust text)? Pick the winner, confidence: medium. Explain the discrepancy.
- One scored, one UNKNOWN → Trust the scored one, confidence: medium. Note which scorer couldn't assess it.
- Both UNKNOWN → reconciled: UNKNOWN, confidence: low
- If a criterion was evaluated by only one scorer, trust that scorer, confidence: medium. Set discrepancy to "Only evaluated by {text|visual} scorer".
- If scorers disagree on a deal-breaker criterion → reconciled: FAIL, confidence: low. Flag for re-investigation."""
    elif availability == "text_only":
        mode_instructions = """Only TEXT scorer results are available (visual scorer failed).
For each criterion, use the text scorer's result. Set confidence: low for all.
Set discrepancy to "Visual scorer unavailable — result based on text evidence only"."""
    else:  # visual_only
        mode_instructions = """Only VISUAL scorer results are available (text scorer failed).
For each criterion, use the visual scorer's result. Set confidence: low for all.
Set discrepancy to "Text scorer unavailable — result based on visual evidence only"."""

    prompt = f"""You are a QA score reconciler. Reconcile the text and visual scorer results for page "{page_id}".

{mode_instructions}

## Text Scorer Results
{text_section}

## Visual Scorer Results
{visual_section}

## Network Verification Context
{net_section}

## Consumer Rubric
{rubric_text}

## PB Feature Rubric
{pb_rubric_text}

## Output Format

Return a JSON object with exactly three keys:
- "pb_criteria": array of reconciled PB criteria, each with: feature, criterion, text_result, visual_result, reconciled, confidence, evidence, discrepancy (string or null)
- "consumer_criteria": array of reconciled consumer criteria, each with: criterion, text_result, visual_result, reconciled, confidence, evidence, discrepancy (string or null)
- "deal_breakers": array of deal-breaker description strings (empty array if none)

For criteria only evaluated by one scorer, set the other scorer's result to "UNKNOWN".

Output ONLY the JSON object. No preamble, no explanation outside the JSON.
"""
    return prompt


def _parse_reconciliation_response(raw_text: str) -> dict | None:
    """Parse the LLM's reconciliation response.

    Returns parsed dict or None on failure.
    """
    stripped = raw_text.strip()

    # Attempt 1: direct JSON parse
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 2: extract from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _fallback_page(page_id: str, text_page: dict | None, visual_page: dict | None) -> dict:
    """Build a fallback page result when LLM is unavailable or parse fails.

    All criteria set to UNKNOWN with confidence: low.
    """
    pb_criteria: list[dict] = []
    consumer_criteria: list[dict] = []

    # Collect criteria from whichever scorer is available
    sources = []
    if text_page and isinstance(text_page, dict):
        sources.append(("text", text_page))
    if visual_page and isinstance(visual_page, dict):
        sources.append(("visual", visual_page))

    seen_pb: set[str] = set()
    seen_con: set[str] = set()

    for source_name, page_data in sources:
        for c in page_data.get("pb_criteria", []):
            key = f"{c.get('feature', '')}:{c.get('criterion', '')}"
            if key not in seen_pb:
                seen_pb.add(key)
                pb_criteria.append({
                    "feature": c.get("feature", "unknown"),
                    "criterion": c.get("criterion", ""),
                    "text_result": "UNKNOWN",
                    "visual_result": "UNKNOWN",
                    "reconciled": "UNKNOWN",
                    "confidence": "low",
                    "evidence": "Reconciliation failed — using fallback",
                    "discrepancy": "LLM reconciliation unavailable",
                })
        for c in page_data.get("consumer_criteria", []):
            key = c.get("criterion", "")
            if key not in seen_con:
                seen_con.add(key)
                consumer_criteria.append({
                    "criterion": c.get("criterion", ""),
                    "text_result": "UNKNOWN",
                    "visual_result": "UNKNOWN",
                    "reconciled": "UNKNOWN",
                    "confidence": "low",
                    "evidence": "Reconciliation failed — using fallback",
                    "discrepancy": "LLM reconciliation unavailable",
                })

    return {
        "page_id": page_id,
        "pb_criteria": pb_criteria,
        "consumer_criteria": consumer_criteria,
        "deal_breakers": [],
    }
```

Then add the public `reconcile_scores` function at the top of the file (after imports):

```python
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def reconcile_scores(
    text_scores: list[dict] | dict,
    visual_scores: list[dict] | dict,
    network_verification: dict,
    navigator_output: dict,
    manifest: dict | None,
    rubric_text: str,
    pb_rubric_text: str,
    llm=None,
) -> dict:
    """Reconcile scorer outputs into a final report.

    Returns a dict matching schemas/final-report.schema.json.
    """
    import time
    start = time.time()

    # Phase 1: deterministic pre-processing
    manifest_coverage = _check_manifest_coverage(navigator_output, manifest)
    verification_tasks = _evaluate_verification_tasks(navigator_output, manifest)
    availability = _classify_scorer_availability(text_scores, visual_scores)

    # Build page lookup for scorers
    text_by_page: dict[str, dict] = {}
    if isinstance(text_scores, list):
        for ts in text_scores:
            text_by_page[ts.get("page_id", "")] = ts

    visual_by_page: dict[str, dict] = {}
    if isinstance(visual_scores, list):
        for vs in visual_scores:
            visual_by_page[vs.get("page_id", "")] = vs

    # Collect all page IDs from both scorers + navigator
    all_page_ids: list[str] = []
    for page in navigator_output.get("pages", []):
        pid = page.get("id", "")
        if pid and pid not in all_page_ids:
            all_page_ids.append(pid)

    # Phase 2: LLM reconciliation (page-by-page, parallel)
    reconcile_tasks = []
    for pid in all_page_ids:
        reconcile_tasks.append(
            _reconcile_page(
                page_id=pid,
                text_page=text_by_page.get(pid),
                visual_page=visual_by_page.get(pid),
                network_verification=network_verification,
                rubric_text=rubric_text,
                pb_rubric_text=pb_rubric_text,
                availability=availability,
                llm=llm,
            )
        )

    reconciled_pages = await asyncio.gather(*reconcile_tasks)
    reconciled_pages = list(reconciled_pages)

    # Merge navigator observations + features_detected into reconciled pages
    nav_pages = {p.get("id"): p for p in navigator_output.get("pages", [])}
    for rp in reconciled_pages:
        pid = rp.get("page_id", "")
        nav_page = nav_pages.get(pid, {})

        # Rename page_id to id for final report schema
        rp["id"] = rp.pop("page_id", pid)

        # Copy navigator fields
        if nav_page.get("url_visited"):
            rp["url_visited"] = nav_page["url_visited"]
        else:
            rp["url_visited"] = ""
        if nav_page.get("screenshot"):
            rp["screenshot"] = nav_page["screenshot"]
        if nav_page.get("observations"):
            rp["observations"] = nav_page["observations"]
        else:
            rp["observations"] = {"description": ""}

        # features_detected from visual scorer
        vs = visual_by_page.get(pid)
        if vs and isinstance(vs, dict):
            rp["features_detected"] = vs.get("features_detected", [])

    elapsed = time.time() - start

    # Phase 3: deterministic post-processing
    return _assemble_final_report(
        navigator_output=navigator_output,
        reconciled_pages=reconciled_pages,
        network_verification=network_verification,
        manifest_coverage=manifest_coverage,
        verification_tasks=verification_tasks,
        elapsed_seconds=elapsed,
    )
```

### Step 4: Run all reconciler tests

- [ ] Run: `pytest tests/test_score_reconciler.py -v`

Expected: ALL PASS.

### Step 5: Commit

- [ ] ```bash
git add persona_browser/score_reconciler.py tests/test_score_reconciler.py
git commit -m "feat: add LLM-based per-page score reconciliation with mocked tests"
```

---

## Task 5: Pipeline Orchestrator (~8 tests)

**Depends on:** Tasks 1-4 (config, fixtures, reconciler)

**Files:**
- Create: `persona_browser/pipeline.py`
- Create: `tests/test_pipeline.py`

### Step 1: Write test file

- [ ] Create `tests/test_pipeline.py`:

```python
"""Tests for pipeline.py — full pipeline orchestrator.

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
MANIFEST = json.loads((FIXTURES / "sample_manifest.json").read_text())
FINAL_REPORT = json.loads((FIXTURES / "sample_final_report.json").read_text())
RUBRIC_TEXT = (FIXTURES / "sample_rubric.md").read_text()
PB_RUBRIC = (Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md").read_text()


def _make_navigator_report(status="DONE", nav_output=None):
    """Create a navigator report dict similar to what agent.py returns."""
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

            # Mock file loading
            mock_json.return_value = CODEINTEL
            mock_text.return_value = RUBRIC_TEXT

            mock_nav.return_value = _make_navigator_report("DONE", NAVIGATOR_OUTPUT)
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


class TestPipelineScorerFailures:
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
            mock_nav.return_value = _make_navigator_report("DONE", NAVIGATOR_OUTPUT)
            mock_scorers.return_value = {
                "network_verification": NETWORK_VERIFICATION,
                "text_scores": {"error": "Text LLM failed"},
                "visual_scores": {"error": "Visual LLM failed"},
            }
            mock_llms.return_value = (MagicMock(), MagicMock(), MagicMock())

            # reconcile_scores should still be called — it handles "neither" mode
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

            # Reconciler should still be called even with both scorers failing
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
            mock_nav.return_value = _make_navigator_report("DONE", NAVIGATOR_OUTPUT)
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
            # Should still contain network_verification
            assert "network_verification" in result


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
```

### Step 2: Run tests to verify they fail

- [ ] Run: `pytest tests/test_pipeline.py -v`

Expected: FAIL — `pipeline` module does not exist.

### Step 3: Implement pipeline.py

- [ ] Create `persona_browser/pipeline.py`:

```python
"""
persona_browser/pipeline.py

Full pipeline orchestrator: navigator → parallel scorers → score reconciler → final report.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from .config import Config, ScoringLLMConfig, get_api_key, load_config
from .agent import run_navigator
from .scorer_runner import run_scorers
from .score_reconciler import reconcile_scores

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_pipeline(
    persona_path: str,
    url: str,
    objectives: str,
    config: Config,
    codeintel_path: str,
    rubric_path: str,
    scope: str = "task",
    task_id: str = "",
    form_data: str = "",
    manifest_path: str = "",
    screenshots_dir: str = "",
    record_video_dir: str = "",
    app_domains: list | None = None,
) -> dict:
    """Run the full persona browser testing pipeline.

    Steps:
        1. Run navigator → navigator_output
        2. Run scorers in parallel (network verifier + text scorer + visual scorer)
        3. Reconcile scores → final report

    Returns dict matching schemas/final-report.schema.json.
    """
    pipeline_start = time.time()

    # ── Load inputs ──────────────────────────────────────────────────────────
    codeintel = _load_json_file(codeintel_path)
    if codeintel is None:
        return _error_report(
            f"codeintel file not found or invalid: {codeintel_path}",
            persona_path, url,
        )

    rubric_text = _load_text_file(rubric_path)
    if rubric_text is None:
        return _error_report(
            f"Rubric file not found: {rubric_path}",
            persona_path, url,
        )

    pb_rubric_path = Path(__file__).parent.parent / "rubrics" / "pb-feature-rubric.md"
    pb_rubric_text = _load_text_file(str(pb_rubric_path))
    if pb_rubric_text is None:
        return _error_report(
            f"PB feature rubric not found: {pb_rubric_path}",
            persona_path, url,
        )

    manifest: dict | None = None
    if manifest_path:
        manifest = _load_json_file(manifest_path)

    # ── Create scoring LLMs ─────────────────────────────────────────────────
    text_llm, visual_llm, reconciler_llm = _create_scoring_llms(config)

    # ── Step 1: Navigator ────────────────────────────────────────────────────
    nav_report = await run_navigator(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        config=config,
        scope=scope,
        task_id=task_id,
        form_data=form_data,
        manifest_path=manifest_path,
        screenshots_dir=screenshots_dir,
        record_video_dir=record_video_dir,
        app_domains=app_domains,
    )

    nav_status = nav_report.get("status", "")
    if nav_status in ("ERROR", "SKIP"):
        return nav_report

    # Extract navigator output (the structured v3 data)
    navigator_output = _extract_navigator_output(nav_report)

    # ── Step 2: Scorers (parallel) ───────────────────────────────────────────
    scorer_results = await run_scorers(
        navigator_output=navigator_output,
        codeintel=codeintel,
        rubric_text=rubric_text,
        pb_rubric_text=pb_rubric_text,
        manifest=manifest,
        text_llm=text_llm,
        visual_llm=visual_llm,
    )

    # ── Step 3: Reconciler ───────────────────────────────────────────────────
    try:
        final_report = await reconcile_scores(
            text_scores=scorer_results.get("text_scores", {"error": "no text scores"}),
            visual_scores=scorer_results.get("visual_scores", {"error": "no visual scores"}),
            network_verification=scorer_results.get("network_verification", {}),
            navigator_output=navigator_output,
            manifest=manifest,
            rubric_text=rubric_text,
            pb_rubric_text=pb_rubric_text,
            llm=reconciler_llm,
        )

        # Update elapsed with full pipeline time
        final_report["elapsed_seconds"] = round(time.time() - pipeline_start, 1)
        return final_report

    except Exception as e:
        logger.error("Reconciler failed: %s", e)
        # Graceful degradation: return partial report with raw scorer outputs
        return _partial_report(
            navigator_output=navigator_output,
            scorer_results=scorer_results,
            elapsed=time.time() - pipeline_start,
            error=str(e),
        )


def run_pipeline_sync(
    persona_path: str,
    url: str,
    objectives: str,
    **kwargs,
) -> dict:
    """Synchronous wrapper for run_pipeline."""
    return asyncio.run(run_pipeline(
        persona_path=persona_path,
        url=url,
        objectives=objectives,
        **kwargs,
    ))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_json_file(path: str) -> dict | None:
    """Load and parse a JSON file. Returns None on failure."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load JSON %s: %s", path, e)
        return None


def _load_text_file(path: str) -> str | None:
    """Load a text file. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to load text file %s: %s", path, e)
        return None


def _create_scoring_llms(config: Config) -> tuple:
    """Create LLM instances for text scorer, visual scorer, and reconciler.

    Returns (text_llm, visual_llm, reconciler_llm).
    Each can be None if the API key is missing.
    """
    def _make_llm(scoring_config: ScoringLLMConfig):
        try:
            api_key = os.environ.get(scoring_config.api_key_env, "")
            if not api_key:
                logger.warning(
                    "Missing API key %s for model %s — scorer will be skipped",
                    scoring_config.api_key_env, scoring_config.model,
                )
                return None

            try:
                from browser_use.llm.litellm.chat import ChatLiteLLM
                return ChatLiteLLM(
                    model=f"openrouter/{scoring_config.model}",
                    api_key=api_key,
                    api_base=scoring_config.endpoint,
                    temperature=scoring_config.temperature,
                )
            except ImportError:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=scoring_config.model,
                    api_key=api_key,
                    base_url=scoring_config.endpoint,
                    temperature=scoring_config.temperature,
                )
        except Exception as e:
            logger.warning("Failed to create LLM for %s: %s", scoring_config.model, e)
            return None

    return (
        _make_llm(config.scoring.text_scorer),
        _make_llm(config.scoring.visual_scorer),
        _make_llm(config.scoring.reconciler),
    )


def _extract_navigator_output(nav_report: dict) -> dict:
    """Extract the structured v3 navigator output from the report.

    The navigator report has top-level metadata + merged navigator fields.
    We need the full dict as the navigator_output for downstream use.
    """
    return nav_report


def _error_report(error: str, persona: str, url: str) -> dict:
    """Create a minimal error report."""
    return {
        "status": "ERROR",
        "error": error,
        "elapsed_seconds": 0,
        "persona": persona,
        "url": url,
    }


def _partial_report(
    navigator_output: dict,
    scorer_results: dict,
    elapsed: float,
    error: str,
) -> dict:
    """Create a partial report when reconciler fails.

    Includes raw scorer outputs and network verification.
    """
    report = {
        "version": "1.1",
        "status": "PARTIAL",
        "elapsed_seconds": round(elapsed, 1),
        "persona": navigator_output.get("persona", ""),
        "url": navigator_output.get("url", ""),
        "error": f"Reconciler failed: {error}",
        "manifest_coverage": navigator_output.get("manifest_coverage", {}),
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

    # Include network verification if available
    nv = scorer_results.get("network_verification", {})
    if not isinstance(nv, dict) or "error" not in nv:
        report["network_verification"] = {
            "_source": "Network Verifier (deterministic module — not LLM)",
            **nv,
        }

    # Include experience from navigator
    if navigator_output.get("experience"):
        report["experience"] = navigator_output["experience"]
    if navigator_output.get("agent_result"):
        report["agent_result"] = navigator_output["agent_result"]

    return report
```

### Step 4: Run tests to verify they pass

- [ ] Run: `pytest tests/test_pipeline.py -v`

Expected: ALL PASS.

### Step 5: Commit

- [ ] ```bash
git add persona_browser/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with graceful degradation"
```

---

## Task 6: CLI Wiring

**Depends on:** Task 5 (pipeline.py)

**Files:**
- Modify: `persona_browser/cli.py`

### Step 1: Update CLI to activate flags and wire pipeline

- [ ] Edit `persona_browser/cli.py` — replace the Phase 3 notes and routing logic:

1. Update the `--codeintel` help text (remove "stored for Phase 3" note):

```python
    parser.add_argument(
        "--codeintel",
        default="",
        help="Path to codeintel.json for scoring pipeline (enables full pipeline mode)",
    )
    parser.add_argument(
        "--rubric",
        default="",
        help="Path to consumer rubric.md for scoring pipeline (enables full pipeline mode)",
    )
```

2. Remove the Phase 3 stderr notes block:

```python
    # DELETE this block:
    # Note for Phase 3 flags (stored but not yet active)
    if args.codeintel:
        print(
            "Note: --codeintel stored for Phase 3 (not used by navigator)",
            file=sys.stderr,
        )
    if args.rubric:
        print(
            "Note: --rubric stored for Phase 3 (not used by navigator)",
            file=sys.stderr,
        )
```

3. Replace the `report = run_sync(...)` call with routing logic:

```python
    # Run test — full pipeline or navigator-only
    if args.codeintel and args.rubric:
        # Full pipeline: navigator → scorers → reconciler
        from .pipeline import run_pipeline_sync

        report = run_pipeline_sync(
            persona_path=args.persona,
            url=args.url,
            objectives=args.objectives,
            config=config,
            codeintel_path=args.codeintel,
            rubric_path=args.rubric,
            scope=args.scope,
            task_id=args.task_id,
            form_data=form_data,
            manifest_path=args.manifest,
            screenshots_dir=args.screenshots_dir,
            record_video_dir=args.record_video,
            app_domains=domains,
        )
    else:
        # Navigator only (backward compat)
        report = run_sync(
            persona_path=args.persona,
            url=args.url,
            objectives=args.objectives,
            config=config,
            scope=args.scope,
            task_id=args.task_id,
            form_data=form_data,
            screenshots_dir=args.screenshots_dir,
            record_video_dir=args.record_video,
            manifest_path=args.manifest,
            app_domains=domains,
        )
```

### Step 2: Verify existing CLI tests still pass

- [ ] Run: `pytest tests/ -v`

Expected: ALL PASS (no regressions).

### Step 3: Commit

- [ ] ```bash
git add persona_browser/cli.py
git commit -m "feat: wire CLI to full pipeline when --codeintel and --rubric provided"
```

---

## Task 7: Final Validation

**Depends on:** All previous tasks

### Step 1: Run full test suite

- [ ] Run: `pytest tests/ -v`

Expected: ALL PASS across all test files.

### Step 2: Validate fixtures against schemas

- [ ] Run:

```bash
python -c "
import json, jsonschema

# Validate final report fixture
schema = json.load(open('schemas/final-report.schema.json'))
report = json.load(open('fixtures/sample_final_report.json'))
jsonschema.validate(report, schema)
print('sample_final_report.json validates OK')

# Validate scorer results against individual schemas
ts_schema = json.load(open('schemas/text-scorer-output.schema.json'))
vs_schema = json.load(open('schemas/visual-scorer-output.schema.json'))
nv_schema = json.load(open('schemas/network-verifier-output.schema.json'))
sr = json.load(open('fixtures/sample_scorer_results.json'))

for ts in sr['text_scores']:
    jsonschema.validate(ts, ts_schema)
for vs in sr['visual_scores']:
    jsonschema.validate(vs, vs_schema)
jsonschema.validate(sr['network_verification'], nv_schema)
print('sample_scorer_results.json validates OK')
"
```

Expected: Both validate without errors.

### Step 3: Quick smoke test of CLI help

- [ ] Run: `python -m persona_browser.cli --help`

Expected: Should show `--codeintel` and `--rubric` flags with updated help text (no "Phase 3" notes).

### Step 4: Final commit

- [ ] ```bash
git add -A
git commit -m "feat: Phase 4 complete — score reconciler + full pipeline"
```
