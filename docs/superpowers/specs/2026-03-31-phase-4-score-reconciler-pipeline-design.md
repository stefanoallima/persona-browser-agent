# Phase 4: Score Reconciler + Full Pipeline — Design Spec

**Date**: 2026-03-31
**Status**: IMPLEMENTED (2026-03-31)
**Depends on**: Phase 1 (schemas/fixtures), Phase 2 (navigator), Phase 3 (scoring pipeline) — all complete
**Architecture ref**: `docs/architecture-proposal-v3.md` lines 2139-2148, Agent 4 (lines 653-857)

---

## Goal

Build the Score Reconciler (LLM-based, Sonnet) and wire the full pipeline: navigator → parallel scorers → score reconciler → final JSON report matching `schemas/final-report.schema.json`. Implement graceful degradation for every failure mode.

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Re-visit capability | Deferred — flag `re_visit_recommended: true` only | High complexity (second browser session), arch doc flags as open question |
| Pipeline location | New `pipeline.py` module | Clean separation: `agent.py` stays navigator-only |
| LLM config | Caller passes LLM instances; config has `scoring` section with 3 sub-configs | Consistent with scorer pattern, testable via mocking |
| PB rubric CLI flag | No flag — loaded internally from `rubrics/pb-feature-rubric.md` | PB rubric is fixed; only consumer rubric varies per project |
| Reconciler scope | LLM does score reconciliation only; coverage + verification + summary are deterministic | Reduces token cost, increases reliability |
| Reconciliation granularity | Page-by-page LLM calls (parallelized) | Smaller JSON per call, partial failure recovery |
| Mismatched criteria | Explicit case: one-scorer-only → trust with medium confidence | Text and visual scorers detect different features independently |

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `persona_browser/score_reconciler.py` | LLM-based per-page score reconciliation |
| `persona_browser/pipeline.py` | Full pipeline orchestrator |
| `tests/test_score_reconciler.py` | TDD tests for reconciler (mocked LLM) |
| `tests/test_pipeline.py` | Pipeline integration tests (all components mocked) |
| `fixtures/sample_scorer_results.json` | Combined scorer output for reconciler tests |
| `fixtures/sample_final_report.json` | Expected final report output for pipeline tests |

### Modified Files

| File | Change |
|------|--------|
| `persona_browser/config.py` | Add `ScoringConfig` with 3 LLM sub-configs |
| `persona_browser/cli.py` | Activate `--codeintel` and `--rubric`, wire to `pipeline.py` |

---

## Module: `score_reconciler.py`

### Public API

```python
async def reconcile_scores(
    text_scores: list[dict] | dict,      # Per-page text scorer output, or {"error": "..."}
    visual_scores: list[dict] | dict,     # Per-page visual scorer output, or {"error": "..."}
    network_verification: dict,           # Network verifier output (pre-computed)
    navigator_output: dict,               # Full navigator output (experience, coverage, auth, pages)
    manifest: dict | None,                # Manifest for coverage check
    rubric_text: str,                     # Consumer rubric markdown
    pb_rubric_text: str,                  # PB feature rubric markdown
    llm=None,                            # LangChain-compatible LLM (Sonnet)
) -> dict:
    """Reconcile scorer outputs into a final report.

    Returns a dict matching schemas/final-report.schema.json.
    """
```

### Internal Structure

Three phases, only one uses the LLM:

#### Phase 1: Deterministic Pre-Processing

```python
def _check_manifest_coverage(navigator_output: dict, manifest: dict | None) -> dict:
    """Compare navigator's visited pages against manifest expectations.

    Returns:
        {
            "expected_pages": [...],
            "visited": [...],
            "not_visited": [...],
            "unexpected_pages": [...]
        }
    """

def _evaluate_verification_tasks(navigator_output: dict, manifest: dict | None) -> list[dict]:
    """Extract and normalize verification task results from navigator output.

    The navigator reports auth verification as narrative strings in
    auth_flow_verification:
        - persistence_after_refresh → maps to V1 (data_persistence) and V3 (auth_persistence)
        - post_auth_access → maps to V4 (auth_boundary, inverted)
        - logout_test → maps to logout verification (if present)

    Cross-page consistency (V2) is inferred from page observations:
    if the same data appears on multiple pages, it passes.

    Manifest verification_tasks (if present) provide the definitive list
    of expected verifications. Each is matched against navigator evidence.

    Returns list of dicts:
        [{"id": "V1", "type": "data_persistence", "result": "PASS", "evidence": "..."}]

    Rules:
        - If auth_flow_verification field is a non-empty string → PASS with that string as evidence
        - If field is null or missing → result depends on manifest:
            - If manifest lists this verification → FAIL ("Not performed")
            - If manifest does not list it → omit from results
    """

def _classify_scorer_availability(text_scores, visual_scores) -> str:
    """Determine which scorers produced valid results.

    Returns one of: "both", "text_only", "visual_only", "neither"
    """
```

#### Phase 2: LLM-Based Score Reconciliation (page-by-page, parallel)

```python
async def _reconcile_page(
    page_id: str,
    text_page: dict | None,        # Text scorer output for this page, or None
    visual_page: dict | None,       # Visual scorer output for this page, or None
    network_verification: dict,     # For context (deal-breakers, issues)
    rubric_text: str,
    pb_rubric_text: str,
    availability: str,              # "both", "text_only", "visual_only"
    llm=None,
) -> dict:
    """Reconcile scores for a single page via LLM.

    Returns per-page reconciled result:
        {
            "page_id": "registration",
            "pb_criteria": [...reconciled criteria...],
            "consumer_criteria": [...reconciled criteria...],
            "deal_breakers": [...]
        }
    """
```

**Prompt strategy**: The LLM receives both scorers' per-criterion results for one page and applies these rules:

| Text Result | Visual Result | Reconciled | Confidence |
|-------------|---------------|------------|------------|
| PASS | PASS | PASS | high |
| FAIL | FAIL | FAIL | high |
| PASS | FAIL | LLM decides (spatial → trust visual, behavioral → trust text) | medium |
| FAIL | PASS | LLM decides (spatial → trust visual, behavioral → trust text) | medium |
| PASS/FAIL | UNKNOWN | Trust the scored one | medium |
| UNKNOWN | PASS/FAIL | Trust the scored one | medium |
| UNKNOWN | UNKNOWN | UNKNOWN | low |
| (only one scorer evaluated) | — | Trust that scorer | medium |
| Disagree on deal-breaker | — | FAIL + `re_visit_recommended: true` | low |

**LLM output format** (per page):

```json
{
  "page_id": "registration",
  "pb_criteria": [
    {
      "feature": "forms",
      "criterion": "Every field has a visible label",
      "text_result": "PASS",
      "visual_result": "PASS",
      "reconciled": "PASS",
      "confidence": "high",
      "evidence": "Both scorers confirm: 3 fields with visible labels",
      "discrepancy": null
    }
  ],
  "consumer_criteria": [...],
  "deal_breakers": []
}
```

**Prompt adaptation per availability mode**:
- `"both"`: Full reconciliation prompt with comparison rules
- `"text_only"`: "Only text scores available. Assign each criterion the text scorer's result with confidence: low. Note: 'Visual scorer unavailable — result based on text evidence only.'"
- `"visual_only"`: Same pattern, visual evidence only
- `"neither"`: No LLM call — return all criteria as UNKNOWN with confidence: low

#### Phase 3: Deterministic Post-Processing

```python
def _assemble_final_report(
    navigator_output: dict,
    reconciled_pages: list[dict],
    network_verification: dict,
    manifest_coverage: dict,
    verification_tasks: list[dict],
    elapsed_seconds: float,
) -> dict:
    """Assemble the final report from all pipeline components.

    Merges navigator metadata (persona, url, scope, experience, screenshots,
    video, agent_result) with reconciled scoring results, network verification,
    and computed summary statistics.

    Returns dict matching schemas/final-report.schema.json.
    """

def _compute_summary(
    reconciled_pages: list[dict],
    network_verification: dict,
    verification_tasks: list[dict],
) -> dict:
    """Compute aggregate summary stats deterministically.

    Counts:
        pb_criteria_total/passed/failed/unknown
        consumer_criteria_total/passed/failed
        verification_tasks_total/passed/failed
        network_issues (len of network_verification.issues)
        total_discrepancies (count of non-null discrepancy fields)
        deal_breakers_triggered (collected from all pages + network)
        pages_with_failures (page IDs with at least one FAIL or deal-breaker)
        pages_clean (page IDs with zero FAILs and zero deal-breakers)
    """
```

### JSON Extraction

Reuse the same `_extract_json()` pattern from `text_scorer.py` / `visual_scorer.py`:
1. Try direct `json.loads()`
2. Extract from markdown code block
3. Return None on failure → flag page as reconciliation error

---

## Module: `pipeline.py`

### Public API

```python
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
```

### Pipeline Flow

```
run_pipeline()
  │
  ├── Load inputs: codeintel.json, consumer rubric, PB rubric (from rubrics/pb-feature-rubric.md)
  ├── Create 3 LLM instances from config.scoring (text, visual, reconciler)
  │
  ├── Step 1: run_navigator() → navigator_output
  │     └── If ERROR/SKIP → return error report immediately
  │
  ├── Step 2: run_scorers(navigator_output, codeintel, rubrics, ...) → {
  │     │       network_verification, text_scores, visual_scores
  │     │     }
  │     └── Each scorer's failure is isolated (returns {"error": "..."})
  │
  ├── Step 3: reconcile_scores(text_scores, visual_scores, network_verification,
  │     │       navigator_output, manifest, rubrics, reconciler_llm)
  │     └── If reconciler fails → fallback (see graceful degradation)
  │
  └── Return final report dict
```

### LLM Instance Creation

```python
def _create_scoring_llms(config: Config) -> tuple:
    """Create LLM instances for text scorer, visual scorer, and reconciler.

    Uses config.scoring.text_scorer, config.scoring.visual_scorer,
    config.scoring.reconciler respectively.

    Returns (text_llm, visual_llm, reconciler_llm).
    Each can be None if the API key is missing (graceful degradation).
    """
```

Uses the same `ChatLiteLLM` import pattern as `agent.py`, with `ChatOpenAI` fallback.

### Graceful Degradation

| Failure | Behavior |
|---------|----------|
| Navigator returns ERROR or SKIP | Return error report immediately, no scoring |
| Navigator returns PARTIAL | Proceed with scoring on whatever pages were collected |
| Network verifier fails | Pass `{"error": "..."}` through; reconciler proceeds without network context |
| Text scorer fails | Reconciler uses visual scores only (confidence: low for all) |
| Visual scorer fails | Reconciler uses text scores only (confidence: low for all) |
| Both scorers fail | Skip reconciliation; return navigator output + network verification + all criteria UNKNOWN |
| Reconciler fails | Return raw scorer outputs + network verification without reconciliation; set `status: PARTIAL` |
| codeintel file missing/invalid | Return error report — codeintel is required for scoring |
| rubric file missing/invalid | Return error report — consumer rubric is required for scoring |
| PB rubric file missing | Return error report — internal file missing (installation issue) |

### Backward Compatibility

`pipeline.py` is only called when `--codeintel` and `--rubric` are both provided. Without them, `cli.py` calls `run_navigator()` directly — identical to current behavior.

The final report includes `agent_result` (backward-compat narrative) and `version: "1.1"` per the architecture spec.

---

## Config Changes: `config.py`

### New `ScoringConfig` Model

```python
class ScoringLLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = ""              # Must be set per scorer
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

class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)           # Navigator
    scoring: ScoringConfig = Field(default_factory=ScoringConfig) # NEW
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
```

The `ScoringLLMConfig` reuses `LLMConfig`'s field structure but with different defaults per scorer. All three share `api_key_env` by default (OpenRouter), but each can be overridden independently (e.g., if visual scorer needs a Google API key).

---

## CLI Changes: `cli.py`

### Activated Flags

- `--codeintel PATH` — path to codeintel.json (required for full pipeline)
- `--rubric PATH` — path to consumer rubric.md (required for full pipeline)

### Removed

- `--pb-rubric` — PB rubric loaded internally
- "Phase 3" stderr notes for `--codeintel` and `--rubric`

### Routing Logic

```python
if args.codeintel and args.rubric:
    # Full pipeline: navigator → scorers → reconciler
    report = run_pipeline_sync(
        persona_path=args.persona,
        url=args.url,
        objectives=args.objectives,
        config=config,
        codeintel_path=args.codeintel,
        rubric_path=args.rubric,
        scope=args.scope,
        ...
    )
else:
    # Navigator only (backward compat)
    report = run_sync(
        persona_path=args.persona,
        url=args.url,
        objectives=args.objectives,
        config=config,
        ...
    )
```

A new `run_pipeline_sync()` wrapper in `pipeline.py` mirrors the existing `run_sync()` pattern: `asyncio.run(run_pipeline(...))`.

---

## Test Fixtures

### `fixtures/sample_scorer_results.json`

Combined output matching what `run_scorers()` returns:

```json
{
  "network_verification": { ... },
  "text_scores": [
    {
      "page_id": "registration",
      "pb_criteria": [
        {"feature": "forms", "criterion": "Every field has a visible label",
         "result": "PASS", "evidence": "...", "confidence": "high"}
      ],
      "consumer_criteria": [...]
    }
  ],
  "visual_scores": [
    {
      "page_id": "registration",
      "features_detected": ["forms", "cta"],
      "pb_criteria": [
        {"feature": "forms", "criterion": "Every field has a visible label",
         "result": "PASS", "evidence": "...", "confidence": "high"},
        {"feature": "forms", "criterion": "Error message appears near the triggering field",
         "result": "FAIL", "evidence": "Error at page top, 300px from fields", "confidence": "high"}
      ],
      "consumer_criteria": [...]
    }
  ]
}
```

Includes cases for: both agree, both disagree, one UNKNOWN, one-scorer-only criteria, and deal-breaker disagreements.

### `fixtures/sample_final_report.json`

Expected output of the full pipeline matching `schemas/final-report.schema.json`. Used by `test_pipeline.py` for structural validation.

---

## Test Strategy

### `test_score_reconciler.py` (~15 tests, all mocked LLM)

**Deterministic function tests (no LLM):**
- `test_manifest_coverage_all_visited` — all pages visited
- `test_manifest_coverage_missing_pages` — some pages not visited
- `test_manifest_coverage_unexpected_pages` — extra pages visited
- `test_manifest_coverage_no_manifest` — manifest is None
- `test_verification_tasks_all_pass` — all V1-V4 pass
- `test_verification_tasks_some_fail` — some fail
- `test_verification_tasks_not_performed` — navigator didn't run them
- `test_classify_both_available` — both scorers returned valid results
- `test_classify_text_only` — visual has error
- `test_classify_visual_only` — text has error
- `test_classify_neither` — both have errors
- `test_compute_summary` — correct aggregation of counts

**LLM reconciliation tests (mocked):**
- `test_reconcile_page_both_agree` — mock LLM returns expected reconciliation
- `test_reconcile_page_disagreement` — mock LLM investigates discrepancy
- `test_reconcile_page_text_only_mode` — only text scores available

**Assembly test:**
- `test_assemble_final_report_matches_schema` — validate against final-report.schema.json

### `test_pipeline.py` (~8 tests, all components mocked)

- `test_pipeline_full_success` — all components succeed, report matches schema
- `test_pipeline_navigator_error` — navigator fails, returns error immediately
- `test_pipeline_navigator_partial` — partial results still scored
- `test_pipeline_text_scorer_fails` — proceeds with visual only
- `test_pipeline_visual_scorer_fails` — proceeds with text only
- `test_pipeline_both_scorers_fail` — returns UNKNOWN for all criteria
- `test_pipeline_reconciler_fails` — returns raw scores + PARTIAL status
- `test_pipeline_backward_compat` — without codeintel/rubric, same as navigator-only

---

## Out of Scope

- **Re-visit capability**: Flagged with `re_visit_recommended: true` but no second browser session (deferred)
- **Phase 5 code-analyzer pipeline**: Separate phase, separate repo (sudd2)
- **SUDD gate integration**: Phase 6
- **Multiple persona support**: Phase 4 handles one persona per run; orchestrating multiple personas is SUDD's responsibility
- **Score formula / threshold config**: SUDD owns the formula for converting per-criterion PASS/FAIL into numerical scores — persona-browser-agent only reports the evidence
