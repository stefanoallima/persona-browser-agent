# Persona Browser Agent v2 — Design Spec

**Date**: 2026-03-29
**Status**: SUPERSEDED by `docs/architecture-proposal-v3.md` (v3.1, 2026-03-30). Kept for historical reference only.
**Approach**: Pipeline Architecture (Approach B)

---

## 1. Purpose

Transform persona-browser-agent from a basic browser-use wrapper into a cutting-edge UX quality assessment tool. The tool runs as a CLI service called by consuming repos per the INTEGRATION.md contract. It drives browser-use with full feature utilization, evaluates websites against a multi-dimensional rubric grounded in CRO best practices, Google CrUX/Core Web Vitals, and Nielsen's heuristics, and returns structured scores with quantitative effort metrics.

---

## 2. Architecture: Pipeline

```
CLI (cli.py)
 │
 ▼
Orchestrator (agent.py)
 │
 ├─ 1. Config (config.py)
 │      Load + validate YAML, resolve API keys for 3 LLM slots
 │
 ├─ 2. LLM Factory (llm.py)
 │      Create 3 LLMs:
 │        • primary: Gemini Flash (OpenRouter) — vision + navigation
 │        • fallback: GLM-4.6 Vision (Z.AI) — vision fallback on errors
 │        • extraction: GLM-5.1 (Z.AI, free) — text extraction + rubric gen + scoring
 │
 ├─ 3. Rubric Generator (rubric.py)
 │      GLM-5.1 pre-pass:
 │        • Generate universal UX rubric (CRO/CrUX/Nielsen)
 │        • Parse persona → generate persona-specific rubric items
 │        • Generate task flow (full user journey steps from objectives)
 │      Output: Rubric + TaskFlow
 │
 ├─ 4. Prompt Builder (prompts.py)
 │      Inject persona + rubric + task flow + objectives into browser-use task
 │
 ├─ 5. Custom Tools (tools.py)
 │      browser-use @tools.action() for JS-injected measurements:
 │        • measure_web_vitals — LCP, INP, CLS, TTFB via Performance API
 │        • audit_form_ux — labels, validation, error proximity
 │        • check_cta — above-fold, contrast, touch targets, text clarity
 │        • audit_accessibility — focus states, contrast, ARIA, keyboard nav
 │        • detect_anti_patterns — modals, disabled buttons, scroll cues
 │        • track_effort — clicks, scroll, keystrokes, pages, timing
 │        • measure_cognitive_load — characters exposed, structured vs blob
 │        • check_bulk_affordances — import, paste, multi-select, batch actions
 │
 ├─ 6. Browser Runner (browser.py)
 │      Configure + run browser-use Agent with full params:
 │        • use_vision="auto", highlight_elements=True
 │        • max_failures=3, fallback_llm=GLM-4.6-Vision
 │        • page_extraction_llm=GLM-5.1
 │        • generate_gif=True, save_conversation_path
 │        • max_actions_per_step=4
 │        • custom tools registry
 │      Returns: AgentHistoryList
 │
 ├─ 7. Scoring Engine (scoring.py)
 │      GLM-5.1 evaluates:
 │        • Universal rubric items (9 dimensions, 0-3 scale)
 │        • Persona rubric items (per-item pass/fail + comment)
 │        • Task flow steps (completed? effort per step?)
 │        • Effort score (physical + cognitive + temporal)
 │        • Repetition scaling (1x/10x/100x ratio)
 │      Input: AgentHistoryList + Rubric + TaskFlow + tool measurements
 │      Output: ScoreResult
 │
 ├─ 8. Artifacts Manager (artifacts.py)
 │      Organize output: ./results/<caller>/<task-id>/run-NNN/
 │        ├── report.json
 │        ├── screenshots/
 │        ├── session.gif
 │        ├── trace.har
 │        └── conversation.json
 │
 └─ 9. Report Builder (report.py)
        Assemble final JSON: rubric_scores + effort_score + narrative + artifacts
```

---

## 3. Data Models (Pydantic)

### 3.1 Configuration

```python
class LLMSlot(BaseModel):
    provider: str              # openrouter | zai | openai | custom
    model: str
    endpoint: str
    api_key_env: str
    temperature: float = 0.1
    max_tokens: int = 4096

class LLMConfig(BaseModel):
    primary: LLMSlot           # Gemini Flash — vision + nav
    fallback: LLMSlot          # GLM-4.6 Vision — failover
    extraction: LLMSlot        # GLM-5.1 — text extraction, rubric gen, scoring

class BrowserConfig(BaseModel):
    headless: bool = True
    width: int = 1280
    height: int = 720
    timeout: int = 300
    use_vision: str = "auto"           # "auto" | "true" | "false"
    vision_detail_level: str = "auto"  # "low" | "high" | "auto"
    max_failures: int = 3
    max_actions_per_step: int = 4
    max_steps: int = 100
    highlight_elements: bool = True
    wait_between_actions: float = 0.5

class ArtifactsConfig(BaseModel):
    base_dir: str = "./results"
    screenshots: bool = True
    gif: bool = True
    har: bool = True
    conversation_log: bool = True

class RepetitionScalingConfig(BaseModel):
    enabled: bool = True
    is_blocker: bool = False
    blocker_threshold: float = 10.0
    test_levels: list[int] = [1, 10, 100]

class ScoringConfig(BaseModel):
    repetition_scaling: RepetitionScalingConfig = RepetitionScalingConfig()

class Config(BaseModel):
    llm: LLMConfig
    browser: BrowserConfig = BrowserConfig()
    artifacts: ArtifactsConfig = ArtifactsConfig()
    scoring: ScoringConfig = ScoringConfig()
```

### 3.2 Rubric

```python
class RubricItem(BaseModel):
    category: str              # "core_web_vitals", "form_ux", "cta", "nav_ia",
                               # "trust", "error_handling", "mobile", "a11y",
                               # "anti_patterns", "persona"
    criterion: str             # "LCP under 2.5s"
    weight: float              # 1.0 normal, 2.0 deal-breaker
    best_in_class: str         # what 3/3 looks like
    poor: str                  # what 0/3 looks like
    source: str                # "universal:core_web_vitals" or "persona:deal_breakers"

class Rubric(BaseModel):
    universal_items: list[RubricItem]    # CRO/CrUX/Nielsen — same every test
    persona_items: list[RubricItem]      # derived from persona file
    deal_breakers: list[str]             # instant-fail criteria
```

### 3.3 Task Flow

```python
class TaskStep(BaseModel):
    step: int
    action: str                # "search", "filter", "select_product", "add_to_cart"
    description: str           # "Filter results by color: blue"
    input: str = ""            # data to type/select if applicable
    expected_outcome: str = "" # "Results show only blue shoes"

class TaskFlow(BaseModel):
    objective: str             # "Buy a pair of blue shoes"
    steps: list[TaskStep]
```

### 3.4 Scoring

```python
class ScoredItem(BaseModel):
    criterion: str
    category: str
    passed: bool
    score: float               # 0.0 - 3.0
    weight: float
    comment: str               # what was observed
    evidence: str              # screenshot ref, JS measurement, extracted content
    best_in_class: str         # reference: what good looks like
    poor: str                  # reference: what bad looks like

class DimensionScore(BaseModel):
    dimension: str             # "core_web_vitals", "form_ux", etc.
    score: float               # weighted average of items, 0-3
    weight: float              # dimension weight (0.05 - 0.20)
    items: list[ScoredItem]

class StepScore(BaseModel):
    step: int
    action: str
    completed: bool
    score: float               # 0-3
    comment: str
    effort: dict               # per-step effort metrics

class TaskFlowScore(BaseModel):
    objective: str
    steps_total: int
    steps_completed: int
    steps_blocked: list[str]
    per_step: list[StepScore]

class EffortMetrics(BaseModel):
    pixels_scrolled: int
    clicks: int
    fields_focused: int
    characters_typed: int
    search_results_before_match: int
    pages_loaded: int
    total_loading_time_ms: int
    time_to_complete_ms: int
    back_navigations: int
    scroll_ups: int
    hover_without_click: int
    errors_encountered: int
    dead_clicks: int

class CognitiveLoad(BaseModel):
    total_characters_exposed: int
    structured_characters: int
    unstructured_characters: int
    ratio_structured: float    # 0.0 - 1.0
    per_page: list[dict]       # url, chars, structured_pct, comment

class RepetitionScaling(BaseModel):
    enabled: bool
    is_blocker: bool
    task: str
    measurements: dict         # 1x, 10x, 100x with effort and ratio
    ideal_ratio_100x: float
    actual_ratio_100x: float
    verdict: str
    bulk_affordances_found: list[str]

class EffortScore(BaseModel):
    physical: EffortMetrics
    cognitive: CognitiveLoad
    temporal: dict             # loading_time, time_to_complete
    repetition: RepetitionScaling
    per_step: list[dict]       # per task-flow step effort breakdown

class ScoreResult(BaseModel):
    universal: list[DimensionScore]   # 9 dimensions
    persona: list[ScoredItem]         # persona-specific items
    task_flow: TaskFlowScore
    effort: EffortScore
    overall_score: float              # 0-100 weighted
    deal_breakers_passed: bool
    pass_rate: str                    # "23/31 passed"
```

### 3.5 Final Report

```python
class ReportStatus(str, Enum):
    DONE = "DONE"
    ERROR = "ERROR"
    SKIP = "SKIP"

class Report(BaseModel):
    status: ReportStatus
    elapsed_seconds: float
    persona: str
    url: str
    scope: str
    task_id: str
    caller: str
    objectives: str
    rubric_scores: ScoreResult
    narrative: str                     # free-text persona experience
    artifacts: dict                    # paths to screenshots, gif, har, conversation
    metadata: dict                     # urls visited, actions taken, errors, LLMs used
```

---

## 4. Config File

```yaml
# config.yaml
llm:
  primary:
    provider: openrouter
    model: google/gemini-2.5-flash-preview
    endpoint: "https://openrouter.ai/api/v1"
    api_key_env: OPENROUTER_API_KEY
    temperature: 0.1
    max_tokens: 4096
  fallback:
    provider: zai
    model: glm-4.6-vision
    endpoint: "https://api.z.ai/api/coding/paas/v4"
    api_key_env: ZAI_API_KEY
    temperature: 0.1
    max_tokens: 4096
  extraction:
    provider: zai
    model: glm-5.1
    endpoint: "https://api.z.ai/api/coding/paas/v4"
    api_key_env: ZAI_API_KEY
    temperature: 0.0
    max_tokens: 2048

browser:
  headless: true
  width: 1280
  height: 720
  timeout: 300
  use_vision: "auto"
  vision_detail_level: "auto"
  max_failures: 3
  max_actions_per_step: 4
  max_steps: 100
  highlight_elements: true
  wait_between_actions: 0.5

artifacts:
  base_dir: "./results"
  screenshots: true
  gif: true
  har: true
  conversation_log: true

scoring:
  repetition_scaling:
    enabled: true
    is_blocker: false
    blocker_threshold: 10.0
    test_levels: [1, 10, 100]
```

**Environment variables required**: `OPENROUTER_API_KEY`, `ZAI_API_KEY`

---

## 5. CLI Interface

```bash
persona-test \
  --persona path/to/persona.md \       # REQUIRED
  --url http://localhost:3000 \         # REQUIRED
  --objectives "buy blue shoes" \      # REQUIRED
  --caller consumer-insights \          # calling repo name (default: "unknown")
  --scope task \                        # task | gate (default: task)
  --task-id T03 \                       # task identifier (default: "adhoc")
  --output-dir ./results \              # override artifacts.base_dir
  --config path/to/config.yaml \        # override config location
  --form-data path/to/data.txt \        # external form data file
  --no-gif \                            # disable GIF generation
  --no-har \                            # disable HAR recording
  --no-screenshots \                    # disable screenshots
  --headful \                           # show browser window
  --verbose                             # progress to stderr
```

**Output path**: `{output-dir}/{caller}/{task-id}/run-{NNN}/`

**stdout**: JSON report (backward compatible — consuming agents capture stdout)

**stderr**: Progress messages, browser-use logs (when --verbose)

**Exit code**: Always 0. Status field in JSON indicates outcome.

---

## 6. Rubric System — Three Layers + Effort

### Layer 1: Universal UX Rubric (every test)

9 dimensions, weighted, grounded in industry standards:

| Dimension | Weight | Source | Sub-items |
|---|---|---|---|
| Core Web Vitals | 20% | Google CrUX | LCP ≤2.5s, INP ≤200ms, CLS ≤0.1, TTFB ≤800ms |
| Form UX | 15% | CRO best practices | Visible labels, inline validation, error proximity to field, input preservation on error, submit visible without scroll, progress indicator |
| CTA Effectiveness | 10% | CRO best practices | Above-fold placement, action-oriented text, high contrast, touch target ≥44px, single primary CTA per viewport |
| Navigation & IA | 10% | Nielsen + CRO | Consistent nav, search with execute affordance, breadcrumbs, heading hierarchy (single H1, no skipped levels), content depth ≤3 clicks |
| Trust & Credibility | 10% | CRO best practices | HTTPS, security badges near payment, social proof, contact info, privacy/terms links, return policy |
| Error Handling | 10% | Nielsen + CRO | Inline errors near field, plain language, constructive suggestions, auto-focus first error, custom 404/500 pages, retry option |
| Mobile Optimization | 10% | Google + WCAG | Responsive (no horizontal scroll), touch targets ≥44px, base font ≥16px, proper input types, viewport meta tag |
| Accessibility | 10% | WCAG 2.1 AA | Visible focus states, contrast ≥4.5:1, ARIA labels, keyboard navigable, skip links |
| Anti-Patterns | 5% | UX heuristics | No modal overuse, disabled buttons explained, scroll cues when content below fold, no infinite scroll trapping footer |

Each item scored 0-3:
- 0 = Poor: violates principle, causes frustration/abandonment
- 1 = Below Average: partially implemented, significant gaps
- 2 = Good: follows best practices, minor issues
- 3 = Excellent: best-in-class implementation

### Layer 2: Persona-Derived Rubric (per test)

GLM-5.1 reads the persona text and generates:
- Rubric items from structured sections (Contract, Verification Rubric, Deal-Breakers)
- Inferred rubric items from unstructured personas (objectives, pain points, identity)
- Deal-breakers marked with weight 2.0

### Layer 3: Task Flow (per test)

GLM-5.1 imagines the complete user journey from high-level objectives:
- Generates step-by-step flow with expected interactions
- Each step becomes a scored item: reachable? completable? how much effort?
- Blocked steps reported with reason

### Layer 4: Effort Score (per test)

Quantitative measurement of total user effort:

**Physical effort** (tracked via JS injection):
- Pixels scrolled (total vertical scroll distance)
- Clicks (total)
- Fields focused (unique form fields)
- Characters typed (total keystrokes in inputs)
- Search results scanned before match
- Pages loaded (distinct navigations)
- Back navigations (frustration signal)
- Scroll-ups (looking for something missed)
- Hover without click (indecision signal)
- Dead clicks (clicks on non-interactive elements)

**Cognitive effort** (tracked via JS injection):
- Total characters exposed to user
- Structured vs unstructured content ratio
- Per-page breakdown with content classification
- Structured = bullet lists, tables, headings, short paragraphs (<150 chars)
- Unstructured = long paragraphs (>150 chars), walls of text

**Temporal effort**:
- Total loading time across all pages
- Time to complete entire task
- Per-page loading time

**Repetition scaling** (two-pass, measured not estimated):
- Pass 1: Normal 1x task execution (already part of the main test). Captures measured effort **E** (clicks, scrolls, fields, characters, etc.).
- Pass 2: Agent scans for bulk affordances (import button, paste area, multi-select, batch action bar). If found, the agent **tries the bulk path** to measure its actual effort **B**:
  - How many clicks to reach the bulk feature?
  - Does it require a file upload, a paste into a textarea, or selecting multiple checkboxes?
  - How many fields need focus? How many characters typed?
  - The real overhead B is measured, not assumed.
- Formula:
  - Bulk path found and tried: `100x = E + B` (where B is the measured effort of using the bulk feature — e.g., 3 clicks to find import, 1 field focus, 1 file upload = B is small)
  - No bulk path found: `100x = E × 100` (purely linear, user must repeat the entire individual flow 100 times)
- The ratio `(E + B) / E` tells you how efficient the bulk path is. Closer to 1.0 = excellent bulk UX. Equal to 100 = no bulk support at all.
- Only relevant for task types that naturally repeat (adding keywords, uploading products, inviting users). Skipped for inherently singular tasks like "buy shoes".
- Configurable: enabled by default, not a blocker by default, threshold adjustable

---

## 7. Custom Browser-Use Tools

Registered via `@tools.action()` decorator. The browser-use agent can call these during navigation to collect hard measurements.

### 7.1 measure_web_vitals
Injects JS using Performance API to capture LCP, INP, CLS, TTFB. Returns structured measurements with thresholds.

### 7.2 audit_form_ux
Checks all form elements for: label association (label vs placeholder-only), required field markers, input types (email, tel, number), submit button viewport visibility, autocomplete attributes.

### 7.3 check_cta
Identifies CTA buttons in viewport, measures contrast ratio (text vs button bg, button vs page bg), touch target dimensions, text content analysis (vague vs action-oriented).

### 7.4 audit_accessibility
Checks: focus state visibility (tab through elements, compare focused vs unfocused styles), text contrast ratios against WCAG AA, ARIA attributes on interactive elements, skip navigation links, keyboard operability.

### 7.5 detect_anti_patterns
Scans for: modals appearing without user interaction, disabled buttons without title/aria-describedby, 100vh hero sections with no scroll cue, infinite scroll blocking footer access.

### 7.6 track_effort
Injects persistent JS tracker that records all interactions: clicks, scroll distance, keystrokes, field focus events, page navigations, timing. Runs continuously throughout the session. The tracker exposes a `getMetrics()` function that returns cumulative counts. The browser-use agent calls this tool between task flow steps to capture per-step deltas. The scoring stage uses these deltas to attribute effort to specific steps.

### 7.7 measure_cognitive_load
Measures visible text content per page: total characters, classification of each text block (structured vs unstructured based on parent element type and paragraph length).

### 7.8 check_bulk_affordances
Scans for bulk operation support: file upload inputs, paste-accepting textareas, "Select All" checkboxes, bulk action bars, import/export buttons, keyboard shortcuts for repeat actions.

---

## 8. File Structure (new)

```
persona_browser/
├── __init__.py
├── models.py          # All Pydantic models (config, rubric, scoring, report)
├── config.py          # Config loading + validation + API key resolution
├── llm.py             # LLM factory — creates 3 LLM slots
├── rubric.py          # Rubric generator (universal + persona + task flow)
├── prompts.py         # Prompt builder — injects persona + rubric + flow into task
├── tools.py           # Custom browser-use tools (JS injection, measurements)
├── browser.py         # Browser-use Agent setup + run with full config
├── scoring.py         # Scoring engine — evaluates all rubric layers + effort
├── artifacts.py       # Output directory management
├── report.py          # Final report assembly
├── agent.py           # Orchestrator — chains the pipeline
└── cli.py             # CLI entry point
```

---

## 9. LLM Strategy

| Slot | Model | Provider | Purpose | Cost |
|---|---|---|---|---|
| Primary | Gemini Flash | OpenRouter | Vision + browser navigation | ~$0.01/test |
| Fallback | GLM-4.6 Vision | Z.AI | Failover when primary hits rate limits/errors (429, 401, 500) | Low |
| Extraction | GLM-5.1 | Z.AI | Rubric generation, page text extraction, scoring | Free |

Fallback triggers automatically via browser-use's `fallback_llm` parameter on HTTP 429, 401, 402, 500, 502, 503, 504.

---

## 10. Output Structure

### Directory
```
./results/<caller>/<task-id>/run-NNN/
├── report.json          # Full structured report
├── screenshots/         # Key moment screenshots
├── session.gif          # Animated replay of session
├── trace.har            # Network trace
└── conversation.json    # Full LLM conversation log
```

Run number auto-increments by counting existing `run-*` directories.

### Report JSON (top-level)

```json
{
  "status": "DONE",
  "elapsed_seconds": 67.3,
  "persona": "personas/ecommerce-shopper.md",
  "url": "http://localhost:3000",
  "scope": "task",
  "task_id": "T03",
  "caller": "consumer-insights",
  "objectives": "buy a pair of blue shoes",

  "rubric_scores": {
    "universal": [
      {
        "dimension": "core_web_vitals",
        "score": 2.3,
        "weight": 0.20,
        "items": [
          {
            "criterion": "LCP under 2.5s",
            "score": 3,
            "passed": true,
            "comment": "1.8s — excellent",
            "evidence": "measured: 1823ms",
            "best_in_class": "LCP under 2.0s on 4G",
            "poor": "LCP over 4s"
          }
        ]
      }
    ],
    "persona": [
      {
        "criterion": "Guest checkout option visible",
        "category": "deal_breaker",
        "score": 0,
        "passed": false,
        "weight": 2.0,
        "comment": "No guest checkout found — forced account creation",
        "evidence": "screenshot: 05-checkout-page.png"
      }
    ],
    "task_flow": {
      "objective": "buy a pair of blue shoes",
      "steps_total": 18,
      "steps_completed": 16,
      "steps_blocked": [
        "step 3: no color filter available",
        "step 8: no size chart found"
      ],
      "per_step": [
        {
          "step": 1,
          "action": "find_search",
          "completed": true,
          "score": 2,
          "comment": "Search icon in header, no label — found in 3 seconds",
          "effort": {"clicks": 1, "scroll": 0, "time_ms": 3000}
        }
      ]
    },
    "overall_score": 67.4,
    "deal_breakers_passed": false,
    "pass_rate": "23/31 passed"
  },

  "effort_score": {
    "physical": {
      "pixels_scrolled": 4820,
      "clicks": 14,
      "fields_focused": 7,
      "characters_typed": 142,
      "search_results_before_match": 12,
      "pages_loaded": 5,
      "back_navigations": 2,
      "scroll_ups": 3,
      "hover_without_click": 6,
      "errors_encountered": 1,
      "dead_clicks": 0
    },
    "cognitive": {
      "total_characters_exposed": 14200,
      "structured_characters": 4800,
      "unstructured_characters": 9400,
      "ratio_structured": 0.34,
      "per_page": [
        {"url": "/products", "chars": 3200, "structured_pct": 0.7},
        {"url": "/checkout", "chars": 8600, "structured_pct": 0.15}
      ]
    },
    "temporal": {
      "total_loading_time_ms": 8420,
      "time_to_complete_ms": 67300
    },
    "repetition": {
      "enabled": true,
      "is_blocker": false,
      "task": "add item to cart",
      "measurements": {
        "1x": {"effort": 12, "comment": "Search, select, add — straightforward"},
        "10x": {"effort": 95, "ratio": 7.9},
        "100x": {"effort": 940, "ratio": 78.3}
      },
      "ideal_ratio_100x": 1.5,
      "actual_ratio_100x": 78.3,
      "verdict": "UI designed for individual execution only",
      "bulk_affordances_found": []
    },
    "per_step": []
  },

  "narrative": "As Sarah, a busy marketing manager with 10 minutes...",

  "artifacts": {
    "report": "results/consumer-insights/T03/run-001/report.json",
    "screenshots": "results/consumer-insights/T03/run-001/screenshots/",
    "gif": "results/consumer-insights/T03/run-001/session.gif",
    "har": "results/consumer-insights/T03/run-001/trace.har",
    "conversation": "results/consumer-insights/T03/run-001/conversation.json"
  },

  "metadata": {
    "urls_visited": ["http://localhost:3000", "http://localhost:3000/products"],
    "actions_taken": 42,
    "errors": [],
    "llms_used": {
      "primary": "google/gemini-2.5-flash-preview",
      "fallback_triggered": false,
      "extraction": "glm-5.1"
    }
  }
}
```

---

## 11. Backward Compatibility

The v2 report is a superset of v1. Consuming agents that only read `status` and `agent_result` will still work — `narrative` serves the same role as `agent_result`. The INTEGRATION.md contract remains valid; new fields are additions, not replacements.

---

## 12. Dependencies

```toml
[project]
dependencies = [
    "browser-use>=0.2.0",
    "langchain-openai>=0.3.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
]
```

No new dependencies required. All custom tools use browser-use's built-in `@tools.action()` decorator and JS injection via Playwright's `page.evaluate()`.

---

## 13. Testing Strategy

- Unit tests for each pipeline stage (rubric gen, scoring, report assembly)
- Mock browser-use Agent for integration tests (avoid real browser in CI)
- One real end-to-end test against a known static HTML page (bundled in tests/)
- Custom tools tested by injecting JS against static HTML fixtures
