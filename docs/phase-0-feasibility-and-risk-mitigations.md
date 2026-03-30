# Phase 0: Feasibility Validation & Risk Mitigations

**Date**: 2026-03-30
**Updated**: 2026-03-30 — browser-use v0.12+ research findings
**Status**: COMPLETED — Phase 1 cleared to proceed
**Blocks**: All implementation phases
**Related**: `architecture-proposal-v3.md`

---

## Why This Document Exists

The v3 architecture has been through three rounds of review. Each round improved the design. But the third review identified 5 risks that cannot be solved by architecture changes — they require **empirical validation** and **operational safeguards** before any implementation begins.

Two of these risks are critical blockers: if they fail, the architecture needs fundamental redesign. Three are important operational gaps that, left unaddressed, will cause silent failures during overnight autonomous runs.

---

## Critical Discovery: browser-use v0.12+ Architecture Change

**As of v0.12.0 (current: 0.12.5), browser-use has migrated from Playwright to CDP (Chrome DevTools Protocol)** via the `cdp-use` library. Playwright is no longer a direct dependency.

This changes the feasibility landscape for both critical risks:

| What changed | Impact |
|---|---|
| `Browser` class → `BrowserSession` + `BrowserProfile` | All code examples using `Browser()` need updating |
| Playwright `page.on('request')` hooks → not directly applicable | PoC-2 Approaches A-B are outdated |
| Native HAR recording via CDP events → built into `BrowserProfile` | PoC-2 is essentially pre-solved |
| `AgentHistoryList` is a rich Pydantic model | PoC-1 risk is significantly reduced |
| Playwright can still connect via CDP to the same Chrome instance | Fallback for any Playwright-specific needs |

**Net effect: both critical risks are significantly de-risked.** The PoCs are still worth running (1-2 hours each) for empirical confirmation, but the probability of "fundamental redesign needed" has dropped from moderate to very low.

**Additional findings from PoC runs:**
- OpenRouter model ID is `google/gemini-2.5-flash` (not `gemini-2.5-flash-preview` as in config.yaml)
- `langchain_openai` may fail due to torch/c10.dll issues; `browser_use.llm.litellm.ChatLiteLLM` works as alternative

---

## Risk Summary

| # | Risk | Severity | Type | Status (post-research) |
|---|------|----------|------|------------------------|
| 1 | Navigator cannot produce structured JSON — no post-processing step defined | Critical | Feasibility | **CONFIRMED** — Outcome A validated (PoC-1, see poc/FINDINGS.md) |
| 2 | Network capture is unvalidated — 40% of v3's value depends on it | Critical | Feasibility | **CONFIRMED** — HAR recording validated (PoC-2, see poc/FINDINGS.md). Note: httpOnly cookies need supplementary CDP call. |
| 3 | Code-analyzer will produce wrong data on real codebases — no feedback loop | Important | Accuracy | Unchanged — address during Phase 5 |
| 4 | No circuit breakers for overnight autonomous runs | Important | Operational | Unchanged — address during Phase 6 |
| 5 | No meta-testing strategy — false PASSes are invisible | Important | Quality | Unchanged — address during Phase 3-4 |

---

## RISK 1: Navigator Structured Output

### The Problem

browser-use's `Agent.run()` returns an `AgentHistoryList` object. The v3 architecture specifies a detailed JSON schema for the navigator's output: `pages[]`, `network_log[]`, `manifest_coverage{}`, `auth_flow_verification{}`, `experience{}`.

The question is whether the history object contains enough structured data to build the v3 schema, or whether we need an additional LLM structuring step.

```
browser-use Agent.run()
    │
    │  returns: AgentHistoryList (Pydantic model)
    │
    ▼
    output_parser.py — deterministic transform
    │
    ▼
Pipeline expects:
    pages[0].observations.forms[0].fields_seen = ["name", "email", "password"]
    pages[0].observations.actions[3].result = "Redirected to /dashboard"
    pages[1].observations.description = "Dashboard showing 'Welcome, Jordan!'"
```

### Research Findings (2026-03-30)

**`AgentHistoryList` is a rich, fully inspectable Pydantic model.** This is NOT opaque text.

Per step, the history contains:

| Method | Returns | Useful for v3 schema |
|--------|---------|---------------------|
| `urls()` | URL at each step | `pages[].url_visited` |
| `screenshot_paths()` | File paths to saved screenshots | `pages[].screenshot` |
| `action_names()` | Name of action taken per step | `pages[].observations.actions[]` |
| `model_actions()` | Full action params per step | `pages[].observations.actions[].result` |
| `model_thoughts()` | LLM reasoning per step (`AgentBrain`) | Navigator's internal observations |
| `action_results()` | Flat list of ActionResult (success/error/extracted_content) | Action outcomes |
| `extracted_content()` | All extracted text content | Page descriptions, form data |
| `errors()` | Error messages per step | Error tracking |
| `final_result()` | Agent's final text answer | `experience{}` narrative |
| `total_duration_seconds()` | Elapsed time | `elapsed_seconds` |
| `save_to_file(path)` | JSON serialization | Debugging, caching |

**What IS available per step (via `BrowserStateHistory`):**
- URL and page title
- Open tabs
- Interacted DOM elements
- Screenshot path

**What is NOT persisted per step:**
- Full page HTML (used during execution but not saved to history)
- Full DOM/accessibility tree

**Assessment: Outcome A (best case) is very likely.** The main gap is that page-level *descriptions* (free text about what the navigator sees) come from the LLM's `model_thoughts()` and `extracted_content()`, not from a structured DOM snapshot. But action sequences, URLs, screenshots, timing, and errors are all structured.

A deterministic parser can:
- Group steps by URL to derive `pages[]`
- Map `action_names()` + `model_actions()` to `pages[].observations.actions[]`
- Map `screenshot_paths()` to `pages[].screenshot`
- Extract `final_result()` for `experience{}`
- Derive `manifest_coverage{}` by comparing visited URLs against manifest

The remaining text descriptions (what the navigator saw on each page) will need to come from the LLM's natural language output, which the parser can extract from `model_thoughts()` or `extracted_content()` per step.

> **Empirically confirmed (2026-03-30, PoC-1):** AgentHistoryList provides per-step URLs, screenshot paths (PNG files on disk), structured action dicts with full params, LLM reasoning/memory/goals via `AgentBrain`, DOM interacted elements, per-step timing, and extracted content. Page grouping by URL produces coherent per-page blocks. `final_result()` provides the experience narrative. All v3 schema fields (except `network_log`) are derivable via deterministic parser. See `poc/FINDINGS.md` for full results.

### Proof of Concept (PoC-1) — REVISED

**Goal**: Confirm the mapping from `AgentHistoryList` fields to v3 output schema. Validate that step grouping by URL produces coherent per-page data.

**Test setup**:
1. A minimal web app (or any running web app with forms + navigation)
2. Run browser-use via `Agent.run()` with a simple navigation task
3. Inspect the returned `AgentHistoryList` object

**What to measure**:
1. Iterate `history.history` (list of `AgentHistory` items) — print each step's URL, action, result, screenshot path
2. Group steps by URL — does this produce coherent per-page blocks?
3. Check `model_thoughts()` — does it contain per-page descriptions usable for `observations.description`?
4. Check `extracted_content()` — what text does the agent extract per step?
5. Test `save_to_file()` — what does the serialized JSON look like?

**Expected outcome**: Outcome A confirmed. Write `output_parser.py` as a deterministic transform.

**Fallback**: If grouping by URL is unreliable (e.g., SPAs where URL doesn't change), add a lightweight Haiku post-processor (Outcome B) to segment the history into logical pages. Cost: ~$0.005-0.02 per run.

**PoC deliverable**: A Python script that:
1. Runs browser-use against a test app with `BrowserSession` + `BrowserProfile`
2. Iterates the `AgentHistoryList` step by step
3. Prints a mapping from history fields → v3 schema fields
4. Identifies any gaps that need the parser to bridge

**Updated time estimate**: 1-2 hours (reduced — we already know the structure is rich)
**Blocks**: Phase 2 — but risk level is now LOW.

---

## RISK 2: Network Capture

### The Problem

The TASK COMPLETION rubric, network verification pipeline, auth flow verification, and 3 of 4 functional deal-breakers depend on the navigator capturing HTTP requests and responses during browsing.

### Research Findings (2026-03-30)

**browser-use v0.12+ has migrated from Playwright to CDP (Chrome DevTools Protocol).** This changes all the proposed approaches but provides a better solution.

**Key finding: HAR recording is built into `BrowserProfile` natively.**

```python
from browser_use import Agent, BrowserSession, BrowserProfile

profile = BrowserProfile(
    record_har_path='./session.har',
    record_har_content='embed',   # 'embed' | 'omit' | 'attach'
    record_har_mode='full',       # 'full' | 'minimal'
)
session = BrowserSession(browser_profile=profile)
agent = Agent(task=task, llm=llm, browser=session)
result = await agent.run()

# After session: parse the standardized HAR JSON file
```

The HAR recording is implemented as a `HarRecordingWatchdog` that registers CDP event handlers for:
- `Network.requestWillBeSent` — captures method, URL, headers, post data
- `Network.responseReceived` — captures status, headers, timing
- `Network.dataReceived` — captures response body size
- `Network.loadingFinished` / `Network.loadingFailed` — completion tracking
- `Page.lifecycleEvent` / `Page.frameNavigated` — page lifecycle

The HAR file is written automatically on browser stop. HAR is a standardized JSON format — trivial to parse for the v3 pipeline.

**Additional options available:**

1. **Playwright alongside browser-use** — Connect Playwright to the same Chrome instance via CDP for any Playwright-specific needs (official example exists: `examples/browser/playwright_integration.py`):

```python
# browser-use connects via CDP
session = BrowserSession(cdp_url='http://localhost:9222')

# Playwright ALSO connects to the same Chrome via CDP
playwright = await async_playwright().start()
pw_browser = await playwright.chromium.connect_over_cdp('http://localhost:9222')
pw_page = pw_browser.contexts[0].pages[0]

# Attach Playwright event listeners
pw_page.on('request', lambda req: log_request(req))
pw_page.on('response', lambda res: log_response(res))
```

2. **Custom CDP watchdog** — Subclass `BaseWatchdog` to write a custom network event handler that captures exactly what the v3 pipeline needs (more granular than HAR but more work).

3. **Direct CDP session access** — `session.get_or_create_cdp_session()` gives raw CDP access for `Network.enable` + custom event handlers.

### Updated Approach Assessment

| Approach | Viability | Notes |
|---|---|---|
| ~~A: Playwright page.on() hooks~~ | **Outdated** | browser-use no longer uses Playwright internally |
| ~~B: Custom Browser subclass~~ | **Outdated** | `Browser` class replaced by `BrowserSession` |
| **C: HAR recording** | **Built-in, recommended** | Native `BrowserProfile.record_har_path` — zero custom code |
| D: Playwright alongside via CDP | **Available as fallback** | Official example exists, connect to same Chrome |
| E: Redesign without network | **Unlikely needed** | HAR recording is near-certain to work |

> **Empirically confirmed (2026-03-30, PoC-2):** BrowserProfile HAR recording captures method, URL, status, timing, request bodies (POST JSON), and response bodies for all HTTP requests during a browser-use session. Known limitation: httpOnly cookies (Set-Cookie/Cookie headers) are not exposed by CDP Network events — Chrome security boundary. Workaround: supplement with `CDP Network.getAllCookies()` calls. Additional finding: HAR watchdog filters out HTTP (non-HTTPS) URLs — needs monkey-patch for localhost testing only. See `poc/FINDINGS.md` for full results.

### Proof of Concept (PoC-2) — REVISED

**Goal**: Confirm HAR recording captures the data needed for the v3 pipeline.

**Test setup**:
1. A web app with API calls (POST /api/register, GET /api/user/me)
2. Enable `record_har_path` on `BrowserProfile`
3. Run agent, parse the resulting HAR file

**What to validate**:
1. HAR captures method, URL, status code, timing for each request
2. HAR captures request headers (including cookies/auth tokens)
3. HAR captures response headers (including Set-Cookie)
4. HAR captures request body (POST data) — verify `record_har_content='embed'`
5. HAR entries can be correlated with navigator steps (by timing/URL)
6. HAR is written correctly even if the agent errors out mid-session
7. **Edge cases to test:**
   - CORS preflight requests (OPTIONS) — are they captured? Should be filtered by Network Verifier.
   - Redirect chains (302 → 302 → 200) — does HAR show all hops or just final destination?
   - Large response bodies — does `record_har_content='embed'` bloat the file? May need to cap body size.
   - Concurrent requests — multiple API calls triggered by the same page load, verify all captured.

**Expected outcome**: HAR recording works out of the box. Write a `har_parser.py` that extracts `network_log[]` entries from the HAR file in the v3 schema format.

**Fallback**: If HAR is insufficient (e.g., missing request bodies or auth headers), use the Playwright-via-CDP approach to attach real-time event listeners.

**PoC deliverable**: A Python script that:
1. Runs browser-use with HAR recording enabled against a test app
2. Parses the HAR file
3. Prints network entries in the v3 `network_log[]` format
4. Validates auth cookie capture (Set-Cookie / Cookie headers)

**Updated time estimate**: 1-2 hours (reduced — HAR recording is a known, standardized format)
**Blocks**: Phase 2 (network capture), Phase 3-4 (TASK COMPLETION scoring). Risk level is now LOW.

---

## RISK 3: Code-Analyzer Accuracy

### The Problem

LLMs reading code to extract structured data is inherently unreliable. No feedback loop exists to catch extraction errors before they propagate through the pipeline.

Specific failure scenarios on real codebases:
- Dynamic forms (react-hook-form, formik) → wrong field count
- Config-based routes (Next.js App Router) → routes not found
- Generated endpoints (Django ViewSets) → endpoints missed
- i18n error messages (locales/en.json) → strings not found
- Utility CSS (Tailwind) → design tokens empty

### Mitigation: Codeintel Validation Layer

Three mechanisms, each catching errors at a different stage.

#### 3a: Pre-gate human review (5-second glance)

code-analyzer-reviewer outputs a **human-readable summary** alongside the JSON artifacts:

```markdown
## Codeintel Summary — green_signup_01

### Frontend (from fe_codeintel.json)
- Pages found: 3 (/register, /dashboard, /settings)
- Forms found: 1 (signup form on /register with 4 fields: name, email, password, confirm)
- Frontend API calls: 2 (POST /api/auth/register, GET /api/user/me)
- Design tokens: primary=#2563eb, error=#dc2626, font=Inter
- Confidence: HIGH (standard React Router + explicit component structure)

### Backend (from be_codeintel.json)
- API endpoints: 4 (POST /auth/register, POST /auth/login, GET /user/me, POST /auth/logout)
- Auth mechanism: session cookie (httpOnly, secure)
- Protected routes: /api/user/*, /api/dashboard/*
- Data flows: 1 (register writes users table → /user/me reads users table)
- Confidence: HIGH (standard FastAPI with explicit decorators)

### Cross-Validation
- FE↔BE endpoint match: 2/2 matched ✓
- FE↔BE field names match: YES ✓
- FE↔BE status codes match: YES ✓
- Mismatches found: 0

### Verification Tasks Auto-Generated: 4
- V1: data_persistence (refresh dashboard after signup)
- V2: cross_page_consistency (check settings shows same data)
- V3: auth_persistence (refresh after auth)
- V4: auth_boundary (access dashboard before auth)
```

For interactive runs: developer reads this in 5 seconds, confirms or flags issues.
For overnight runs: automatic, no human check (covered by 3b below).

#### 3b: Codeintel confidence gate (automated)

code-analyzer-reviewer assigns an overall confidence score to codeintel extraction:

```
Confidence scoring:
  - Each extraction category gets a confidence: HIGH / MEDIUM / LOW
  - Overall confidence = minimum across all categories

  HIGH: All patterns matched expected frameworks (React Router, FastAPI decorators, etc.)
  MEDIUM: Some patterns matched, some required inference
  LOW: Significant guesswork, dynamic patterns, or missing information

Automated gate:
  IF overall confidence == HIGH:
    → proceed normally, all codeintel treated as ground truth
  IF overall confidence == MEDIUM:
    → proceed, but deal-breakers require HIGH confidence on specific criterion
    → codeintel-based criteria scored with reduced weight (0.7x)
  IF overall confidence == LOW:
    → fall back to codeintel-FREE scoring
    → scorers work from observations and rubric only
    → TASK COMPLETION criteria evaluated from text observations only
    → log: "codeintel low confidence — running without code verification"
```

This prevents bad codeintel from causing false failures during overnight runs.

#### 3c: Post-failure codeintel audit

When a gate fails on a criterion that references codeintel, the failure report includes:

```
✗ confirm_password field missing
  Code expects 4 fields (codeintel_ref: registration.elements.forms[0].fields)
  Navigator saw 3 fields

  ⚠ CODEINTEL CHECK: Verify extraction accuracy before fixing:
    Source: fe_codeintel.json → pages[0].elements.forms[0].fields
    Extracted from: RegisterPage.tsx
    If codeintel is wrong (code actually has 3 fields):
      → Report: "codeintel error: field count wrong for RegisterPage.tsx"
      → Re-run code-analyzer on next retry
    If codeintel is right (code has 4 fields but UI shows 3):
      → Fix the UI
```

For overnight runs: if the same codeintel-referenced criterion fails 3 times in a row (circuit breaker from Risk 4), the system marks it as "suspected codeintel error" and switches to codeintel-free scoring for the next retry.

---

## RISK 4: Overnight Run Circuit Breakers

### The Problem

A solo developer running SUDD overnight needs the system to fail gracefully — not burn through 8 retries at $0.50 each when the same bug can't be fixed, or loop on a codeintel extraction error.

### Where This Lives

**SUDD repo** — these are gate-level operational controls, not persona-browser-agent's concern. But persona-browser-agent's output format must support them (e.g., criterion IDs for identical-failure detection).

### Mitigation: Three Circuit Breakers

#### 4a: Cost ceiling per change

```yaml
# sudd.yaml
safety:
  max_cost_per_change: 5.00  # USD — pause and mark STUCK if exceeded
```

Gate tracks cumulative cost across retries:
- Each persona-browser-agent call reports `elapsed_seconds` and estimated token usage
- Code-analyzer calls tracked separately
- When cumulative cost exceeds threshold → mark STUCK with reason: "cost ceiling reached ($X.XX spent)"

#### 4b: Identical-failure detection

```
After each gate failure, compare the failed criteria with previous failures:

IF same criterion_id + same evidence text for 3 consecutive retries:
  → Mark STUCK early (don't burn remaining retries)
  → Reason: "Criterion '{criterion}' failed 3 times with identical evidence.
     Suspected systematic issue — either codeintel extraction error
     or a bug the coder cannot fix from the feedback provided."
  → Include: all 3 failure reports for human review

This catches:
  - Codeintel repeatedly misreading the same code
  - Navigator consistently unable to complete auth (CAPTCHA, OAuth)
  - A criterion that's impossible to satisfy (rubric bug)
```

Persona-browser-agent supports this by including stable `criterion_id` fields in its output (e.g., `form.required_marked`, `consumer.signup_has_confirm_password`). SUDD compares these across retries.

#### 4c: Partial retry (re-run from failed step)

```
When only part of the pipeline failed:

  Navigator succeeded + Scorers succeeded + Score Reconciler failed:
    → Cache navigator output + scorer output + network verification
    → Re-run ONLY the Score Reconciler with cached inputs
    → Saves: 30-90s navigator time + scorer time + cost

  Navigator succeeded + Text Scorer failed + Visual Scorer succeeded:
    → Cache navigator output + network verification
    → Re-run ONLY the Text Scorer
    → Score Reconciler runs with new text scores + cached visual scores + cached network verification

  Navigator failed:
    → Full re-run (no cache possible)

Cache location: changes/{id}/browser-cache/{persona}/
  - navigator_output.json (raw browser-use output + structured output)
  - screenshots/ (already saved)
  - text_scores.json (if text scorer completed)
  - visual_scores.json (if visual scorer completed)
  - network_verification.json (if network verifier completed — deterministic, always succeeds if HAR exists)

Cache invalidated when:
  - Code changes (git SHA differs from cached run)
  - Codeintel changes (code-analyzer re-ran)
  - Manual cache clear
```

This is particularly valuable overnight: if the Sonnet Score Reconciler call times out due to API flakiness, the next retry doesn't re-run the entire 90-second navigator session.

---

## RISK 5: Meta-Testing (Testing the Testing Tool)

### The Problem

When both scorers agree on PASS, nobody second-guesses them. False PASSes are invisible. There's no way to know if persona-browser-agent is catching 95% of bugs or 60%.

### Mitigation: Golden Test Suite

#### 5a: Test application

Create **1 small web application** with **configurable bug modes** — a single signup + dashboard app that can be launched with different flags to activate specific bug categories:

```
APP: "Golden Test App" (signup + dashboard, configurable bugs)

  Base: /register → /dashboard → /settings
  - Signup form (name, email, password, confirm_password)
  - Auth via session cookie
  - Dashboard with personalized greeting
  - Settings page shows user data

  Bug modes (activated via environment variable BUGS=mode1,mode2,...):

  MODE "clean" (no bugs):
    - Everything works correctly
    Expected verdict: PASS on all criteria

  MODE "silent-api-fail":
    - POST /api/auth/register returns 500 but frontend shows "Success!"
    - Dashboard shows generic "Welcome!" (name not persisted)
    Expected verdict: FAIL on TASK COMPLETION (Network Verifier catches 500)

  MODE "bad-ux":
    - Error messages at top of page (not near fields)
    - No required field indicators
    - Backend works perfectly
    Expected verdict: FAIL on PB rubric (forms), PASS on TASK COMPLETION

  MODE "missing-field":
    - confirm_password field has CSS display:none
    - Code still defines 4 fields (codeintel says 4, browser sees 3)
    Expected verdict: FAIL on consumer rubric (missing field)

  MODE "auth-broken":
    - Session cookie not set (auth handover fails)
    - Protected routes accessible without auth
    Expected verdict: FAIL on auth (Network Verifier catches missing cookie)

  Modes are combinable: BUGS=bad-ux,auth-broken tests multiple failures at once.
```

**Why 1 app with modes instead of 5 separate apps:**
- Faster to build and maintain (one codebase, shared components)
- Same codeintel/manifest/rubric works across all modes (only runtime behavior changes)
- Combinable modes test interaction effects (bad UX + broken auth)
- Lower effort: ~1 day instead of 2-3 days for 5 separate apps

#### 5b: Regression test runner

```bash
# Run the full pipeline against the golden test app in each bug mode
# Compare output verdicts against expected verdicts per mode
# Report any mismatches

MODES=("clean" "silent-api-fail" "bad-ux" "missing-field" "auth-broken")

for mode in "${MODES[@]}"; do
  # Start app with bug mode
  BUGS=$mode node golden-tests/app/server.js &
  APP_PID=$!
  sleep 2  # wait for startup

  persona-test \
    --persona golden-tests/persona.md \
    --url http://localhost:3333 \
    --manifest golden-tests/manifest.json \
    --rubric golden-tests/rubric.md \
    --codeintel golden-tests/codeintel.json \
    --output golden-tests/results/$mode.json

  # Compare result against expected verdict for this mode
  python golden-tests/compare.py \
    golden-tests/results/$mode.json \
    golden-tests/expected/$mode.json

  kill $APP_PID
done
```

Run this after any change to:
- Navigator prompt (`prompts.py`)
- Scorer prompts or logic
- Score Reconciler reconciliation logic
- Network Verifier matching rules
- PB rubric criteria
- Model upgrades (switching model versions, etc.)

#### 5c: Both-agree confidence check in Score Reconciler

When both scorers agree on PASS for a criterion that codeintel flagged as potentially problematic (low confidence extraction), the Score Reconciler adds an explicit note:

```json
{
  "criterion": "Form has 4 fields",
  "text_result": "PASS",
  "visual_result": "PASS",
  "reconciled": "PASS",
  "confidence": "medium",
  "note": "Both scorers agree PASS, but codeintel extraction confidence was LOW for this criterion. Manual verification recommended.",
  "codeintel_confidence": "low"
}
```

For overnight runs: this doesn't block the gate, but it appears in the gate report so the developer can spot-check in the morning.

#### 5d: Screenshot timing specification

**Clarification**: browser-use v0.12+ takes screenshots **automatically per step** via `AgentHistoryList.screenshot_paths()`. The navigator does NOT manually invoke screenshot commands — browser-use captures the page state after each action step as part of its internal loop.

This means:
- Screenshot timing is controlled by **browser-use's step lifecycle**, not by prompt instructions or custom configuration.
- Each step's screenshot shows the page state AFTER that step's action was performed and the page settled.
- Browser-use internally waits for page stability before capturing (part of its CDP-based page interaction).

**What we control**:
- The `BrowserProfile` wait strategies affect how long browser-use waits for page loads during navigation actions, which indirectly affects screenshot timing.
- If pages have loading skeletons or lazy content, the navigator's LLM can be prompted to wait ("wait until the page finishes loading before proceeding") — the screenshot for that wait step will capture the settled state.

**No additional screenshot timing configuration needed** — browser-use's built-in per-step capture is sufficient. The key is ensuring the navigator doesn't rush through steps on slow-loading pages.

---

## Implementation Order — REVISED

```
PoC-1 (Navigator output)     ──┐
                                ├──▶ CONFIRMATION (not decision — both risks are de-risked)
PoC-2 (Network capture)      ──┘
  1-2 hours each, can run in parallel

  EXPECTED (based on research):
    Both succeed → Proceed to Phase 1 as designed
    Write output_parser.py + har_parser.py

  IF PoC-1 has gaps (step grouping by URL unreliable for SPAs):
    → Add lightweight Haiku post-processor (Outcome B)
    → Cost: ~$0.005-0.02 per run, 2-3 seconds
    → Add as persona_browser/output_structurer.py

  IF PoC-2 HAR is incomplete (missing request bodies or auth headers):
    → Use Playwright-via-CDP approach as fallback
    → Connect Playwright to same Chrome instance
    → Attach page.on('request')/page.on('response') listeners

  "Both fail badly" scenario is now very unlikely given:
    → AgentHistoryList is confirmed rich/structured (Pydantic model)
    → HAR recording is confirmed built-in (CDP watchdog)

THEN (unchanged):

Risk 3 mitigations (codeintel validation)
  → Implement during Phase 5 (code-analyzer)
  → Confidence gate + human-readable summary + post-failure audit

Risk 4 mitigations (circuit breakers)
  → Implement during Phase 6 (SUDD gate integration)
  → Cost ceiling + identical-failure detection + partial retry
  → Lives in SUDD repo: sudd.yaml + gate.md

Risk 5 mitigations (golden test suite)
  → Implement during Phase 3-4 (after scorers + Network Verifier exist)
  → 1 test app with configurable bug modes + regression runner + both-agree confidence check
  → Lives in PB repo: golden-tests/
  → Screenshot timing: handled by browser-use per-step lifecycle (no custom config needed)
```

---

## Cost of Phase 0 — REVISED

```
PoC-1: Navigator output PoC
  - Use any running web app (no test app build needed for PoC)
  - Run browser-use with BrowserSession, inspect AgentHistoryList: 1 hour
  - Map fields to v3 schema, identify gaps: 30 min
  - API cost: ~$0.10 (a few LLM calls)

PoC-2: Network capture PoC
  - Enable BrowserProfile.record_har_path: 5 min
  - Run agent against app with API calls: 30 min
  - Parse HAR, validate captured data: 30 min
  - API cost: ~$0.05 (browser-use calls only)

Total: 2-3 hours of dev time, ~$0.15 in API costs
```

Reduced from original 3-6 hours because the research has already answered the primary feasibility questions. The PoCs are now **confirmation runs**, not discovery experiments.

---

## Files Created/Modified by These Mitigations

### persona-browser-agent repo (Phase 0 + ongoing)
```
persona-browser-agent/
├── docs/
│   ├── architecture-proposal-v3.md      ← UPDATE: Reviewer split, model changes, adversarial rubric
│   └── phase-0-feasibility-and-risk-mitigations.md  ← THIS FILE (updated with research)
├── fixtures/                             ← NEW: reference test fixtures for Phase 2-4 dev
│   ├── sample_codeintel.json             ← realistic codeintel for signup+dashboard app
│   ├── sample_manifest.json              ← matching manifest with auth_flow + verification_tasks
│   └── sample_rubric.md                  ← matching consumer rubric
├── poc/                                  ← NEW: proof of concept scripts
│   ├── poc1_navigator_output.py          ← PoC-1: inspect AgentHistoryList structure
│   ├── poc2_network_capture.py           ← PoC-2: validate HAR recording via BrowserProfile
│   └── test_app/                         ← minimal test app for PoCs (optional — can use any running app)
│       ├── frontend/                     ← simple signup form + dashboard
│       └── backend/                      ← simple API (register, login, user/me)
├── golden-tests/                         ← NEW: meta-testing (Risk 5, Phase 3-4)
│   ├── app/                              ← single golden test app with configurable bug modes
│   │   ├── server.js                     ← BUGS=mode1,mode2 env var activates bugs
│   │   ├── frontend/                     ← signup form + dashboard + settings
│   │   └── backend/                      ← API with bug mode switches
│   ├── persona.md                        ← shared test persona
│   ├── manifest.json                     ← shared manifest (works across all modes)
│   ├── rubric.md                         ← shared rubric
│   ├── codeintel.json                    ← shared codeintel
│   ├── expected/                         ← expected verdicts per bug mode
│   │   ├── clean.json
│   │   ├── silent-api-fail.json
│   │   ├── bad-ux.json
│   │   ├── missing-field.json
│   │   └── auth-broken.json
│   ├── results/                          ← test run outputs (gitignored)
│   ├── compare.py                        ← verdict comparison script
│   └── run_golden_tests.sh               ← regression test runner
└── persona_browser/
    ├── output_parser.py                  ← NEW: AgentHistoryList → v3 JSON (page grouping + manifest matching)
    ├── har_parser.py                     ← NEW: HAR file → network_log[] (timestamp correlation + domain filtering)
    ├── network_verifier.py               ← NEW: deterministic network_log vs codeintel verification
    ├── score_reconciler.py               ← NEW: replaces monolithic reviewer (lighter prompt)
    └── output_structurer.py              ← NEW only if PoC-1 Outcome B (lightweight Haiku post-processor)
```

### sudd2 repo (Phase 5-6)
```
sudd2/
├── sudd/
│   ├── sudd.yaml                         ← add safety.max_cost_per_change,
│   │                                        safety.identical_failure_stuck_after,
│   │                                        safety.enable_partial_retry,
│   │                                        browser_use.navigator.max_steps/timeout
│   ├── agents/
│   │   ├── code-analyzer-fe.md           ← NEW: Haiku, reads frontend
│   │   ├── code-analyzer-be.md           ← NEW: Haiku, reads backend
│   │   ├── code-analyzer-reviewer.md     ← NEW: Sonnet, cross-validates + generates
│   │   └── rubric-adversary.md           ← NEW: Haiku, adversarial rubric review
│   └── commands/micro/gate.md            ← add circuit breaker logic + code-analyzer pipeline
└── reference/
    └── persona-browser-agent-architecture.md  ← update with all v3 changes
```

---

## Appendix: browser-use v0.12+ API Reference

Quick reference for the new API used throughout this document and the v3 architecture.

### Key class changes from pre-0.12

| Old (Playwright-based) | New (CDP-based, v0.12+) |
|---|---|
| `Browser()` | `BrowserSession(browser_profile=BrowserProfile(...))` |
| `browser._context` / `browser._page` | `session.cdp_client`, `session.get_current_page()` |
| Playwright `Page` object | CDP-based `Page` actor (different API) |
| `page.on('request', ...)` | HAR recording via `BrowserProfile`, or Playwright-via-CDP fallback |
| N/A | `session.get_or_create_cdp_session()` for raw CDP access |

### BrowserProfile network-related options

```python
BrowserProfile(
    record_har_path='./session.har',     # Enable HAR recording
    record_har_content='embed',          # 'embed' | 'omit' | 'attach'
    record_har_mode='full',              # 'full' | 'minimal'
    # ... 40+ other configuration options
)
```

### AgentHistoryList key methods

```python
result = await agent.run()  # returns AgentHistoryList

result.urls()                    # list[str|None] — URL at each step
result.screenshot_paths()        # list[str|None] — screenshot file paths
result.action_names()            # list[str] — action name per step
result.model_actions()           # list[dict] — full action params per step
result.model_thoughts()          # list[AgentBrain] — LLM reasoning per step
result.action_results()          # list[ActionResult] — outcomes per step
result.extracted_content()       # list[str] — extracted text per step
result.errors()                  # list[str|None] — errors per step
result.final_result()            # str|None — agent's final answer
result.total_duration_seconds()  # float — elapsed time
result.save_to_file(path)        # JSON serialization
result.is_done()                 # bool
result.is_successful()           # bool
```
