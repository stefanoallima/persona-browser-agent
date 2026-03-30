# Persona Browser Agent — Architecture Proposal v2

**Date**: 2026-03-30
**Status**: rejected -> new V3 exists
**Responds to**: `feedback_browser_use.md`
**Supersedes**: v1 (2026-03-29)

---

## Problem Statement

The current persona-browser-agent does everything in a single browser-use agent call: navigates pages, fills forms, judges usability, scores UX, and renders a verdict. This creates three problems:

1. **Conflicting authority** — Both the browser agent AND SUDD can score, producing contradictory verdicts
2. **Overloaded prompt** — One mega-prompt tries to navigate AND summarize AND score
3. **Tight coupling** — Scoring logic is baked into persona-browser-agent, making it unusable outside SUDD
4. **No visual verification** — Text-only scoring misses layout breaks, color issues, spatial relationships
5. **Monolithic rubric** — One "overall UX score" gives no actionable feedback on specific pages

---

## Architecture: Triangulated Scoring with Dual Rubrics

Three agents inside persona-browser-agent, then SUDD makes the final call based on detailed per-page rubric results.

```
  persona-browser-agent
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  NAVIGATOR-SCORER (Gemini Flash, vision)           │  │
│  │                                                    │  │
│  │  For EACH page visited:                            │  │
│  │    1. Navigate to page                             │  │
│  │    2. Look at it (vision)                          │  │
│  │    3. Interact (click, fill, etc.)                 │  │
│  │    4. Score THIS PAGE against PB page-type rubric  │  │
│  │    5. Score THIS PAGE against consumer rubric      │  │
│  │    6. Save screenshot                              │  │
│  │    7. Move to next page                            │  │
│  │                                                    │  │
│  │  Output: per-page observations + per-page scores   │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│                         ▼                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  TEXT SCORER (text-only model, cheaper)            │  │
│  │                                                    │  │
│  │  Receives: text observations only (NO images)      │  │
│  │  Scores: same rubrics, same per-page structure     │  │
│  │  Independent judgment from text evidence alone     │  │
│  │  Does NOT see the navigator-scorer's scores        │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│                         ▼                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  REVIEWER (reasoning model)                        │  │
│  │                                                    │  │
│  │  Compares visual vs text per-page, per-criterion   │  │
│  │  If scores agree: confirms                         │  │
│  │  If scores diverge (delta > 15 on any criterion):  │  │
│  │    - investigates WHY                              │  │
│  │    - decides which scorer is right                 │  │
│  │    - explains the discrepancy                      │  │
│  │  Produces: reconciled per-page scores              │  │
│  │          + discrepancy analysis                    │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          │
                          ▼  full report JSON

                    ┌───────────┐
                    │   SUDD    │
                    │           │
                    │  Reads per-page rubric details
                    │  Reads discrepancy explanations
                    │  Reads specific criteria pass/fail
                    │  NOT just top-line scores
                    │           │
                    │  PASS only if:
                    │    PB rubric ≥ threshold  AND
                    │    Consumer rubric ≥ threshold
                    │           │
                    │  Can override based on
                    │  specific criterion failures
                    │  even if top-line passes
                    └───────────┘
```

---

## Why This Architecture

### Navigator-scorer merged (not separate)

The navigator already has visual context — it's looking at each page as it interacts. Asking it to also score while the page is in front of it is natural, not extra cognitive load. Splitting them would mean passing screenshots to a separate model that re-processes what the navigator already saw — wasteful.

Context window is not a bottleneck. Gemini Flash has 1M tokens. Navigation uses ~20-30k tokens. Adding per-page scoring rubrics adds ~2-5k. Nowhere near the limit.

### Text scorer as independent check

The text scorer works from observations only — no images. This catches a specific class of problems: when the visual scorer gives a PASS because it "saw" the right element, but the textual evidence reveals the interaction failed. It also catches the reverse: when the visual scorer flags a layout issue that doesn't actually affect the described user journey.

The key value is **disagreement**. When visual and text agree, you have high confidence. When they disagree, the reviewer investigates — and that investigation IS the valuable finding.

### Reviewer as reconciler

Not a rubber stamp. The reviewer:
- Skips criteria where both scorers agree (most of them)
- Investigates only discrepancies (typically 1-3 per page)
- Decides which scorer is right based on the nature of the criterion (spatial criteria → trust visual; behavioral criteria → trust text)
- Explains its reasoning so SUDD (and humans) can audit

### SUDD reads details, not just scores

SUDD doesn't just check "score ≥ 98." It reads per-page, per-criterion results. This means SUDD can:
- "Score is 96 but the /register page failed error-placement — that's a deal-breaker for this change. FAIL."
- "Score is 94 but the failures are all on /about which this change didn't touch. PASS."
- Route specific failures back to the coder as targeted action items

---

## Dual Rubric System

Two rubrics are applied to every page. Both must pass.

### PB Rubric (Universal — built into persona-browser-agent)

This is persona-browser-agent's **intellectual property** — its opinionated view of what good UX looks like. Every consumer gets it automatically. It's what makes persona-browser-agent a product, not a commodity browser-use wrapper.

The PB rubric is applied **per page type**. The navigator-scorer classifies each page it visits, then applies the matching rubric.

#### Page Type: FORM

```
Labels & Inputs
  □ Every field has a visible label (not just placeholder)
  □ Required fields are marked (asterisk, "required" text, or equivalent)
  □ Input types match content (email → email field, password → password field)
  □ Tab order is logical (top-to-bottom or left-to-right)

Validation & Errors
  □ Required-field error on empty submit
  □ Format error on invalid input (email, phone, etc.)
  □ Error message appears NEAR the field, not just at page top
  □ Error is specific ("Email must contain @" not "Invalid input")
  □ Valid input clears previous errors
  □ User doesn't lose entered data on error

Submission
  □ Submit button is visible without scrolling
  □ Button shows loading state during submission
  □ Success confirmation is clear
  □ No double-submit on rapid clicks

Deal-breakers (instant FAIL)
  ✗ Form submits with invalid/empty required data
  ✗ Submitted data is silently lost
  ✗ No way to correct errors without re-entering everything
```

#### Page Type: LANDING / MARKETING

```
Clarity
  □ Purpose of the page is clear within 3 seconds
  □ Primary CTA is the most prominent element
  □ No more than 2 competing CTAs

Navigation
  □ Main nav is visible and functional
  □ Logo links to home
  □ Current page is indicated in nav

Performance
  □ Largest contentful paint < 3 seconds
  □ No layout shift after load
  □ Images are not broken

Deal-breakers (instant FAIL)
  ✗ Page is blank or shows error on load
  ✗ Primary CTA leads to 404 or error
```

#### Page Type: DASHBOARD / DATA DISPLAY

```
Information Hierarchy
  □ Most important data is above the fold
  □ Data is grouped logically
  □ Empty states have helpful messaging (not just blank)

Interaction
  □ Clickable elements look clickable (cursor, color, underline)
  □ Hover/active states provide feedback
  □ Destructive actions have confirmation

Deal-breakers (instant FAIL)
  ✗ Data is visibly wrong or contradictory
  ✗ Key actions are hidden or unreachable
```

#### Page Type: ERROR / 404

```
Recovery
  □ Error message explains what happened in plain language
  □ Clear path back (link to home, back button works)
  □ No technical jargon (no stack traces, no raw error codes)

Deal-breakers (instant FAIL)
  ✗ White/blank page with no guidance
  ✗ Back button doesn't work (trapped)
```

#### Page Type: OTHER

```
Baseline
  □ Page loads without errors
  □ Primary content is visible above the fold
  □ Navigation works (can get to other pages)
  □ No console errors visible to user

Deal-breakers (instant FAIL)
  ✗ Page is non-functional
  ✗ Navigation is broken (dead end)
```

### Consumer Rubric (Project-specific — injected by consumer)

Passed via `--rubric rubric.md` CLI flag. The consumer (SUDD or any other system) writes this rubric from their own requirements. persona-browser-agent doesn't need to understand SUDD to apply it — it's just "another rubric to score."

Example consumer rubric:

```markdown
## Scoring Rubric: Signup Flow

### /register page
- Signup form has name, email, password fields
- Password strength indicator appears on focus
- Email format validation happens inline (not on submit)

### /dashboard page (after signup)
- Shows "Welcome, {name}" with the submitted name
- Dashboard is not empty — shows onboarding content

### Deal-breakers
- Form submits without email validation
- Signup succeeds but dashboard shows wrong name or no name
```

### Why Both Rubrics

| Scenario | PB Rubric | Consumer Rubric | What Happened |
|----------|-----------|-----------------|---------------|
| Beautiful form, wrong fields | PASS | FAIL | Looks great, doesn't meet spec |
| Right fields, invisible errors | FAIL | PASS | Meets spec, bad UX |
| Both good | PASS | PASS | Ship it |
| Both bad | FAIL | FAIL | Back to drawing board |

Neither rubric alone catches everything. The AND gate is what gives real quality.

---

## Agent Details

### Agent 1: Navigator-Scorer

**Lives in**: persona-browser-agent
**Model**: Gemini Flash (multimodal, vision required)
**Role**: Navigate as the persona AND score each page visually

#### Prompt Structure (two-phase per page)

```
"You are {persona}. Navigate to {url} and attempt {objectives}.

AT EACH PAGE YOU VISIT:

1. OBSERVE: What do you see? Describe the page factually.

2. CLASSIFY: What type of page is this?
   (form | landing | dashboard | error | other)

3. SCORE PB RUBRIC: Apply the rubric for this page type.
   Check each criterion:
   - PASS / FAIL
   - Brief evidence (what you see that proves it)

4. SCORE CONSUMER RUBRIC: Apply these project-specific criteria
   for this page (if any apply):
   {injected consumer rubric criteria}

5. Take a screenshot.

6. Continue navigating to the next objective."
```

The model scores **while looking at the page** — not after the journey. This means visual evidence (element positions, colors, layout) is assessed in real time.

#### Inputs

| Input | Source | Required |
|-------|--------|----------|
| `--url` | CLI arg | Yes |
| `--persona` | Persona .md file path | Yes |
| `--objectives` | CLI arg (comma-separated) | Yes |
| `--rubric` | Consumer rubric .md file path | No |
| `--scope` | CLI arg (`task` or `gate`) | No (default: `task`) |
| `--form-data` | File path or embedded in persona | No |
| `--screenshots-dir` | CLI arg | No |
| `--record-video` | CLI arg (directory path) | No |
| `--config` | CLI arg (path to config.yaml) | No |

#### Output

Per-page observations and scores (structured JSON). See full output format in Output section below.

### Agent 2: Text Scorer

**Lives in**: persona-browser-agent
**Model**: Haiku or Flash (text-only, cheap)
**Role**: Score the same rubrics from text observations only — no images

#### Receives

- Text observations from navigator-scorer (descriptions, actions, error messages, timing)
- PB rubric (same page-type rubrics)
- Consumer rubric (same injected rubric)
- Does NOT see: screenshots, navigator-scorer's scores

#### Key Property: Independence

The text scorer must not see the navigator-scorer's scores. It works from text descriptions of what happened, not from the visual evidence. This independence is what makes disagreement meaningful.

#### What It Catches That Visual Misses

- Behavioral sequences ("clicked X, then Y happened, but Z was expected")
- Timing issues ("took 3.2 seconds" — text scorer can compare to threshold)
- Data correctness ("submitted 'Jordan', dashboard shows 'Welcome, User'" — visual scorer might not notice the name mismatch if layout looks fine)

### Agent 3: Reviewer

**Lives in**: persona-browser-agent
**Model**: Sonnet (needs reasoning quality for discrepancy analysis)
**Role**: Compare visual vs text scores, investigate discrepancies, produce reconciled verdict

#### Receives

- Navigator-scorer's per-page scores (with visual evidence notes)
- Text scorer's per-page scores (with text evidence notes)
- Both rubrics (to understand what each criterion is asking)

#### Logic

```
For each page:
  For each criterion:
    if visual_score == text_score:
      reconciled = agreed score (high confidence)
    elif abs(visual_score - text_score) <= 15:
      reconciled = average (minor variance, normal LLM noise)
    else:
      INVESTIGATE:
        - What did visual scorer see that text scorer didn't?
        - What did text scorer infer that visual scorer missed?
        - Is this criterion spatial (trust visual) or behavioral (trust text)?
        - Produce explanation
        reconciled = reviewer's judgment
```

#### Discrepancy Example

```
Page: /register
Criterion: "Error message appears near the triggering field"

Visual scorer: FAIL
  "Error banner appears at page top, 400px away from email field"

Text scorer: PASS
  "Navigator reported: 'got error: Invalid email format'"

Reviewer analysis:
  "Text scorer evaluated WHETHER an error appeared — it did.
   Visual scorer evaluated WHERE it appeared — far from the field.
   The criterion specifies 'near the field' — position matters.
   Visual scorer is correct."

Reconciled: FAIL
Explanation: "Error exists but is positioned at page top, not
  adjacent to the triggering field. Text observation missed
  the spatial relationship."
```

---

## Output Format

persona-browser-agent returns a single JSON object on stdout. The structure is per-page, per-rubric, per-criterion.

```json
{
  "status": "DONE",
  "elapsed_seconds": 45.2,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "scope": "task",
  "task_id": "T03",
  "objectives": "fill signup form, submit, verify confirmation",

  "pages": [
    {
      "url": "/register",
      "page_type": "form",
      "screenshot": "screenshots/03-register.png",

      "observations": {
        "description": "Registration page with centered form. Three input fields: name, email, password. Submit button below.",
        "actions": [
          {
            "step": 1,
            "action": "Filled name field with 'Jordan Rivera'",
            "result": "Field accepted input"
          },
          {
            "step": 2,
            "action": "Submitted empty email",
            "result": "Error banner at page top: 'Please fill in all fields'"
          },
          {
            "step": 3,
            "action": "Filled all fields with valid data, submitted",
            "result": "Redirected to /dashboard"
          }
        ]
      },

      "pb_rubric": {
        "page_type": "form",
        "visual_score": 78,
        "text_score": 88,
        "reconciled_score": 78,
        "criteria": [
          {
            "id": "form.labels_visible",
            "name": "Every field has a visible label",
            "visual": "PASS",
            "text": "PASS",
            "reconciled": "PASS",
            "discrepancy": null
          },
          {
            "id": "form.required_marked",
            "name": "Required fields are marked",
            "visual": "FAIL",
            "text": "FAIL",
            "reconciled": "FAIL",
            "evidence": "No asterisk or 'required' text on any field"
          },
          {
            "id": "form.error_near_field",
            "name": "Error message appears near the triggering field",
            "visual": "FAIL",
            "text": "PASS",
            "reconciled": "FAIL",
            "discrepancy": "Text scorer only evaluated message existence, not position. Visual scorer detected error banner 400px from email field. Criterion requires proximity — visual is correct."
          },
          {
            "id": "form.submit_visible",
            "name": "Submit button visible without scrolling",
            "visual": "PASS",
            "text": "PASS",
            "reconciled": "PASS",
            "discrepancy": null
          }
        ],
        "deal_breakers_triggered": []
      },

      "consumer_rubric": {
        "visual_score": 95,
        "text_score": 99,
        "reconciled_score": 97,
        "criteria": [
          {
            "id": "signup_has_name_email_password",
            "name": "Signup form has name, email, password fields",
            "visual": "PASS",
            "text": "PASS",
            "reconciled": "PASS"
          },
          {
            "id": "success_redirects_to_dashboard",
            "name": "Successful signup redirects to dashboard",
            "visual": "PASS",
            "text": "PASS",
            "reconciled": "PASS"
          }
        ],
        "deal_breakers_triggered": []
      }
    },
    {
      "url": "/dashboard",
      "page_type": "dashboard",
      "screenshot": "screenshots/04-dashboard.png",
      "observations": { "..." : "..." },
      "pb_rubric": { "..." : "..." },
      "consumer_rubric": { "..." : "..." }
    }
  ],

  "summary": {
    "pages_visited": 2,
    "pb_rubric_score": 85,
    "consumer_rubric_score": 97,
    "total_discrepancies": 1,
    "discrepancy_details": [
      "Page /register, criterion form.error_near_field: visual FAIL vs text PASS — visual correct, error positioned away from field"
    ],
    "deal_breakers_triggered": []
  },

  "screenshots": [
    "screenshots/01-initial-load.png",
    "screenshots/02-form-empty-submit.png",
    "screenshots/03-register.png",
    "screenshots/04-dashboard.png"
  ],

  "video": "recordings/session.webm"
}
```

---

## Integration Contract: SUDD ↔ persona-browser-agent

This section defines the complete interaction between SUDD and persona-browser-agent: who calls what, when, with what data, and how results flow back.

### Principle: Evidence vs Judgment

persona-browser-agent provides **EVIDENCE** (scores, criteria, discrepancies, screenshots).
SUDD makes the **DECISION** (pass/fail, what to fix, whether to retry, threshold policy).

- persona-browser-agent can report "PB score: 85" and that's valid output
- SUDD can decide "85 is below our 98 threshold, FAIL" — that's SUDD's policy
- Another consumer could decide "85 is fine for our MVP" — their policy
- The evidence is the same; the judgment varies by consumer

### Principle: Call Once, Share Results

**Current problem**: SUDD calls persona-browser-agent up to 3 times per persona at gate (persona-validator calls it, ux-tester calls it independently, sometimes twice for different persona files). This is redundant — 3 browser sessions testing the same app.

**New pattern**: persona-browser-agent is called **ONCE per persona** at gate time. The JSON report is saved to disk. All downstream agents (persona-validator, ux-tester) READ the report — they do not launch their own browser sessions.

```
CURRENT (redundant):

  gate.md dispatches:
    ├── persona-validator → calls persona-browser-agent (session 1)
    ├── persona-validator → calls persona-browser-agent (session 2)
    └── ux-tester ────────→ calls persona-browser-agent (session 3)

  3 browser sessions, 3 API calls to Gemini, same app, same persona


NEW (single call, shared report):

  gate.md:
    │
    │ STEP 2a: Call persona-browser-agent ONCE per persona
    │          Save report to changes/{id}/browser-reports/{persona}.json
    │
    ├── persona-validator READS the saved report
    │   (no browser session, no API call to Gemini)
    │
    └── ux-tester READS the saved report
        (no browser session, may still run Playwright for technical checks)
```

---

### 1. Consumer Rubric Lifecycle

The consumer rubric is the project-specific scoring criteria that SUDD passes to persona-browser-agent. It defines what THIS change must deliver, not universal UX quality.

#### Who Writes It

The **architect agent** during `/sudd:plan`, derived from:
- `specs.md` acceptance criteria
- `design.md` route expectations and UI behavior
- Persona deal-breakers from `personas/*.md`

#### When It's Written

```
/sudd:plan (design phase)
    │
    │ architect reads specs.md + design.md + personas
    │ extracts testable criteria per URL/page
    │ writes rubric.md
    │
    ▼
changes/{id}/rubric.md  ← created here, used at gate time
```

#### Where It Lives

```
sudd/changes/active/{id}/
├── proposal.md
├── specs.md
├── design.md
├── tasks.md
├── rubric.md              ← NEW: consumer rubric for persona-browser-agent
├── personas/
│   ├── end-user.md
│   └── admin-user.md
├── browser-reports/        ← NEW: persona-browser-agent output
│   ├── end-user.json
│   └── admin-user.json
├── screenshots/
│   └── gate/
│       ├── end-user/
│       │   ├── 01-initial-load.png
│       │   ├── 02-form-filled.png
│       │   └── 03-submit-success.png
│       └── admin-user/
│           └── ...
├── recordings/             ← NEW: session videos
│   ├── end-user.webm
│   └── admin-user.webm
└── log.md
```

#### Rubric Format

Markdown with per-page criteria. The navigator-scorer LLM interprets this — no strict schema required, but this structure works best:

```markdown
# Consumer Rubric: {change-id}

Generated from: specs.md, design.md
Persona context: {persona name and role}

## /register

### Must Pass
- Signup form has name, email, password fields
- Password strength indicator appears when password field is focused
- Email format validation happens inline (before submit)
- Successful submission redirects to /dashboard within 2 seconds

### Should Pass
- Form remembers entered data on validation error (no re-entry)
- Password requirements shown proactively (not only on error)

### Deal-Breakers
- Form submits with empty required fields
- Signup succeeds but user data is lost (dashboard shows generic greeting)

## /dashboard

### Must Pass
- Shows "Welcome, {name}" with the name submitted during signup
- Dashboard has at least one onboarding element (not completely empty)
- Navigation menu is visible and includes links to settings

### Deal-Breakers
- Dashboard is blank/empty after signup
- Name displayed doesn't match what was submitted
```

**"Must Pass"** criteria map to the consumer rubric score. All must pass for 100.
**"Should Pass"** criteria are weighted lower — failure reduces score but doesn't trigger deal-breaker.
**"Deal-Breakers"** trigger instant FAIL regardless of score.

---

### 2. Gate Workflow (Revised Step-by-Step)

This replaces the current gate.md Step 2 for UI changes.

#### Prerequisites

- Dev server is running (started by gate orchestrator)
- `persona-browser-agent` is installed (`pip install -e ../persona-browser-agent`)
- API key is set (`OPENROUTER_API_KEY`)
- `changes/{id}/rubric.md` exists (written during /sudd:plan)

#### Step 2a: Browser Testing (ONE call per persona)

```
FOR EACH persona file in changes/{id}/personas/:

  persona-test \
    --persona "sudd/changes/active/{id}/personas/{persona-name}.md" \
    --url {dev_server_url} \
    --objectives "{ALL objectives from persona ## Objectives, comma-separated}" \
    --rubric "sudd/changes/active/{id}/rubric.md" \
    --scope gate \
    --screenshots-dir "sudd/changes/active/{id}/screenshots/gate/{persona-name}/" \
    --record-video "sudd/changes/active/{id}/recordings/" \
    --output "sudd/changes/active/{id}/browser-reports/{persona-name}.json" \
    --config persona-browser-agent/config.yaml

  Parse stdout JSON.

  IF status == "DONE":
    → Report saved. Continue to Step 2b.
  IF status == "SKIP":
    → Log warning: "Browser testing skipped: {reason}"
    → Fall back to Playwright-only validation
    → Score capped at 90 (no visual/persona simulation evidence)
  IF status == "ERROR":
    → Log error: "Browser testing failed: {error}"
    → Apply -5 score penalty
    → Fall back to Playwright-only validation
```

**Personas can be tested IN PARALLEL** — each gets its own browser session, its own report file, its own screenshot directory.

#### Step 2b: Persona Validator (reads report, no browser)

```
DISPATCH(agent=persona-validator):

  Input:
    - Persona research: changes/{id}/personas/{persona-name}.md
    - Browser report: changes/{id}/browser-reports/{persona-name}.json  ← READS, doesn't re-run
    - Change context: specs.md, design.md, tasks.md
    - Micro-persona results (from build phase)
    - Macro-wiring report (from Step 0)

  What persona-validator does with the report:
    1. Reads consumer_rubric scores per page
    2. Reads per-criterion pass/fail with evidence
    3. Reads deal_breakers_triggered
    4. Reads discrepancy analysis (visual vs text disagreements)
    5. Maps objectives from persona to objective results in report
    6. Checks handoff contract compliance
    7. Applies deal-breaker logic (any triggered = instant FAIL)

  What persona-validator does NOT do:
    - Launch a browser session
    - Call persona-browser-agent
    - Navigate the app via Playwright
    - Take its own screenshots

  Output:
    {score, level, objectives_met, critical_assessment,
     intuitiveness_verdict, confidence}

  The persona-validator's score is based on:
    - Consumer rubric results from the report (primary evidence)
    - Objective completion from the report
    - Deal-breaker status
    - Its own assessment of the handoff contract and change context
```

#### Step 2c: UX Tester (reads report, optional Playwright technical checks)

```
DISPATCH(agent=ux-tester):

  Input:
    - Browser report: changes/{id}/browser-reports/{persona-name}.json  ← READS, doesn't re-run
    - Persona research: changes/{id}/personas/{persona-name}.md
    - Design system: design-system/MASTER.md (if exists)

  What ux-tester does with the report:
    1. Reads pb_rubric scores per page
    2. Reads per-page observations (layout, interactions, errors)
    3. Reads discrepancy analysis
    4. Checks intuitiveness signals (discoverability, friction points)

  What ux-tester MAY still do independently:
    - Run Playwright for TECHNICAL checks only:
      - Console errors (JavaScript exceptions)
      - Accessibility audit (axe-core or similar)
      - Design system compliance (CSS property checks vs MASTER.md)
      - Network request failures (4xx/5xx)
    - These are things browser-use can't check
    - These use Playwright MCP tools, NOT persona-browser-agent

  What ux-tester does NOT do:
    - Call persona-browser-agent
    - Navigate the app as a persona (browser-use already did this)
    - Score intuitiveness from scratch (uses report findings)

  Output:
    {verdict, score, scenarios_tested, issues, confidence}

  The ux-tester's score is based on:
    - PB rubric results from the report (40%)
    - Intuitiveness assessment from report (30%)
    - Its own Playwright technical checks (30%)
```

#### Step 2d: Wait and Aggregate

```
WAIT for all dispatches (persona-validator + ux-tester per persona)

FOR EACH persona:

  browser_report = read changes/{id}/browser-reports/{persona-name}.json

  CHECKS (all must pass for this persona to PASS):

  1. PB rubric:
     - browser_report.summary.pb_rubric_score >= 98?
     - Any deal_breakers_triggered in any page? → instant FAIL
     - Any page with reconciled_score < 90? → FAIL
       (one bad page can fail the gate even if overall is above 98)

  2. Consumer rubric:
     - browser_report.summary.consumer_rubric_score >= 98?
     - Any deal_breakers_triggered in any page? → instant FAIL
     - Any "Must Pass" criterion with reconciled = "FAIL"? → FAIL

  3. Persona validator:
     - Level == EXEMPLARY? (existing logic, unchanged)
     - Score >= 98?

  4. UX tester:
     - Score >= 98?
     - Any CRITICAL issues found in technical checks?

  IF all 4 checks pass → this persona PASSES
  IF any check fails → this persona FAILS


ALL personas pass → GATE PASS
ANY persona fails → GATE FAIL
```

---

### 3. Failure Routing

When the gate fails, SUDD must give the coder **targeted, actionable feedback** — not just "score was 85." The browser report provides per-page, per-criterion detail that makes this possible.

#### Failure Report Format

```markdown
## Gate: FAILED

### Persona: End User (Sarah Chen)

**PB Rubric: 78/100 — FAIL**

  Page /register (FORM):
    ✓ form.labels_visible — PASS
    ✗ form.required_marked — FAIL
      Evidence: No asterisk or 'required' text on any field
      Action: Add required field indicators (asterisk + aria-required)
    ✗ form.error_near_field — FAIL
      Evidence: Error banner at page top, not near triggering field
      Discrepancy: Text scorer missed this (only checked error existence).
                   Visual scorer caught the spatial issue.
      Action: Move validation errors to inline position below each field

  Page /dashboard (DASHBOARD):
    ✓ All criteria passed

**Consumer Rubric: 97/100 — PASS**

  All "Must Pass" criteria met.
  "Should Pass" gap: password requirements not shown proactively (-3)

**Discrepancies Resolved: 1**
  - form.error_near_field: text PASS vs visual FAIL → visual correct
    (text scorer evaluated message content, visual evaluated position)

### Action Items for Coder (priority order):
1. /register: Move validation error messages to inline (below each field)
   - Currently: error banner at page top
   - Required: error text appears directly below the field that caused it
2. /register: Add required field indicators
   - Add asterisk (*) next to label text for required fields
   - Add aria-required="true" to input elements

### Do NOT Touch:
- /dashboard — all criteria passed
- /settings — not part of this change

### Screenshots for Reference:
- screenshots/gate/end-user/02-form-empty-submit.png — shows error at top
- screenshots/gate/end-user/03-form-filled.png — shows missing required markers
```

#### How This Feeds Back to /sudd:apply

When the gate fails and retries, the coder receives:
1. The failure report above (appended to `log.md` under `## Accumulated Feedback`)
2. Specific file paths and line numbers where changes are needed (if identifiable from the page URL + component mapping)
3. Screenshot paths for visual reference
4. The "Do NOT Touch" list — prevents unnecessary rework on passing pages

The coder does NOT receive:
- The raw browser report JSON (too verbose)
- PB rubric definitions (not the coder's concern)
- Discrepancy analysis details (already resolved by reviewer)

---

### 4. Agent Role Changes

#### persona-validator.md — Changes

**Before (current)**:
- Launches browser via Playwright MCP tools
- Calls persona-browser-agent via Bash
- Navigates app independently
- Takes its own screenshots
- Scores based on its own navigation experience

**After (new)**:
- READS `changes/{id}/browser-reports/{persona-name}.json`
- Does NOT launch any browser
- Does NOT call persona-browser-agent
- Focuses on: consumer rubric interpretation, objective mapping, deal-breaker logic, handoff contract compliance, critical assessment
- Still writes first-person narrative ("As Sarah Chen, I reviewed the report and...")
- Still applies EXEMPLARY/STRONG/ACCEPTABLE scoring from standards.md
- Uses browser report scores as PRIMARY evidence, not as the only input — can disagree with the report if it finds issues in the change context that the browser test couldn't catch (e.g., API contract violations, missing documentation)

**New input contract**:
```
Input:
  - browser_report_path: changes/{id}/browser-reports/{persona-name}.json
  - persona_file: changes/{id}/personas/{persona-name}.md
  - specs: changes/{id}/specs.md
  - design: changes/{id}/design.md
  - tasks: changes/{id}/tasks.md
  - micro_persona_results: [{task, score, consumer, verdict}, ...]
  - wiring_report: from macro-wiring-checker
```

#### ux-tester.md — Changes

**Before (current)**:
- Calls persona-browser-agent via Bash
- Navigates app via Playwright MCP tools
- Runs full persona simulation
- Scores intuitiveness from its own experience

**After (new)**:
- READS `changes/{id}/browser-reports/{persona-name}.json`
- Does NOT call persona-browser-agent
- Does NOT navigate as the persona (browser-use already did this)
- MAY still use Playwright MCP tools for TECHNICAL checks only:
  - Console error detection
  - Accessibility audits (axe-core)
  - Design system CSS compliance
  - Network request validation
- Uses PB rubric scores from report as primary intuitiveness evidence
- Its own Playwright technical checks complement (not replace) the report

**New input contract**:
```
Input:
  - browser_report_path: changes/{id}/browser-reports/{persona-name}.json
  - persona_file: changes/{id}/personas/{persona-name}.md
  - design_system: design-system/MASTER.md (optional)
  - dev_server_url: {url} (only if running Playwright technical checks)
```

#### gate.md — Changes

**Before (current)**:
- Step 2 dispatches persona-validator and ux-tester in parallel
- Each agent independently calls persona-browser-agent
- Gate aggregates their scores

**After (new)**:
- Step 2a: gate calls persona-browser-agent ONCE per persona (before dispatching agents)
- Step 2b: dispatches persona-validator with browser report path
- Step 2c: dispatches ux-tester with browser report path
- Step 2d: aggregates — checks BOTH rubric scores from report AND agent scores
- Failure routing: generates targeted action items from per-criterion failures

---

### 5. Task-Level Testing (During /sudd:apply)

Browser testing also happens per-task during the build phase, not just at gate. The interaction is simpler:

```
/sudd:apply (per task, if task has UI):

  persona-test \
    --persona "sudd/changes/active/{id}/tasks/{task-id}/micro-persona.md" \
    --url {dev_server_url} \
    --objectives "{objectives from micro-persona}" \
    --rubric "sudd/changes/active/{id}/rubric.md" \
    --scope task \
    --task-id {task-id} \
    --screenshots-dir "sudd/changes/active/{id}/screenshots/{task-id}/" \
    --output "sudd/changes/active/{id}/tasks/{task-id}/browser-report.json"

  Parse result.
  Use as evidence for micro-persona validation.
  No separate persona-validator dispatch — micro-persona-validator
  reads the task-level browser report directly.
```

Task-level tests are:
- Scoped to the pages/routes modified by that task only (`--scope task`)
- Faster (fewer pages to visit)
- Use the same rubric.md but only criteria relevant to the task's pages apply
- Feed into micro-persona validation as evidence

---

### 6. Configuration

#### sudd.yaml additions

```yaml
browser_use:
  enabled: true
  run_on:
    task: true           # run per-task during /sudd:apply
    gate: true           # run at gate during /sudd:gate
  config_path: "persona-browser-agent/config.yaml"
  rubric_threshold:
    pb_rubric: 98        # minimum PB rubric reconciled score
    consumer_rubric: 98  # minimum consumer rubric reconciled score
    per_page_floor: 90   # minimum score for any single page
  deal_breaker_policy: "instant_fail"  # any deal-breaker = gate FAIL
```

#### persona-browser-agent config.yaml (unchanged, owned by PB)

```yaml
llm:
  provider: openrouter
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY

browser:
  headless: true
  timeout: 300

reporting:
  screenshots: true
  format: json
```

SUDD does NOT modify persona-browser-agent's config. It only passes `--config` to point to the file. LLM model choice, browser settings, and internal pipeline configuration are persona-browser-agent's domain.

---

### 7. Error Handling Across the Boundary

| Scenario | Who Detects | What Happens | SUDD's Response |
|----------|-------------|--------------|-----------------|
| persona-browser-agent not installed | gate.md (pip check) | Pre-flight check before Step 2a | Log warning, fall back to Playwright-only, cap score at 90 |
| API key missing | persona-browser-agent | Returns `status: SKIP, reason: missing_api_key` | Log warning, fall back to Playwright-only, cap score at 90 |
| Dev server not running | persona-browser-agent | Returns `status: ERROR, reason: connection_failed` | SUDD starts dev server, retries once |
| Browser timeout | persona-browser-agent | Returns `status: ERROR, reason: timeout` | Log error, -5 penalty, use partial results if any |
| Navigator-scorer fails | persona-browser-agent | Returns `status: ERROR` | Fall back to Playwright-only for this persona |
| Text scorer fails | persona-browser-agent (internal) | Returns report with `text_score: null` per criterion | SUDD uses visual scores only, notes reduced confidence |
| Reviewer fails | persona-browser-agent (internal) | Returns report with `reconciled = null`, raw scores present | SUDD uses visual scores as reconciled, notes reduced confidence |
| Report JSON is malformed | gate.md (JSON parse) | Parse error caught | Log error, fall back to Playwright-only for this persona |
| Rubric file missing | gate.md (pre-flight) | File not found | FAIL gate — rubric is required. "Run /sudd:plan to generate rubric.md" |
| Persona file missing | gate.md (pre-flight) | File not found | FAIL gate — persona is required. "Run /sudd:plan to generate personas" |

#### Pre-flight Checklist (gate.md Step 2a, before calling persona-browser-agent)

```
Before calling persona-browser-agent, verify:

  1. [ ] persona-browser-agent installed? (pip show persona-browser-agent)
  2. [ ] API key set? ($OPENROUTER_API_KEY not empty)
  3. [ ] Dev server running? (curl -s {url} returns 200)
  4. [ ] Rubric file exists? (changes/{id}/rubric.md)
  5. [ ] At least one persona file exists? (changes/{id}/personas/*.md)
  6. [ ] Screenshots directory writable? (mkdir -p test)

  If any fail:
    1-2: fall back to Playwright-only, cap score at 90
    3:   start dev server, wait, retry
    4:   FAIL gate — "Missing rubric. Run /sudd:plan."
    5:   FAIL gate — "Missing personas. Run /sudd:plan."
    6:   continue without screenshots (non-blocking)
```

---

## Pipeline Execution

### Happy Path (all 3 agents work)

```
Navigator-Scorer (30-60s, browser interaction)
       │
       ├──▶ Text Scorer (3-5s, text-only, runs after navigator finishes)
       │
       └──▶ [screenshots saved to disk]

       Both scores ready
              │
              ▼
       Reviewer (5-10s, compares and reconciles)
              │
              ▼
       JSON output to stdout
```

**Total: ~40-75 seconds per persona**

### Degraded: Text Scorer Fails

```
Navigator-Scorer ──▶ Reviewer (skips comparison, passes through visual scores)
                     flags: "text scoring unavailable, visual-only assessment"
```

### Degraded: Reviewer Fails

```
Navigator-Scorer ──┐
                   ├──▶ Output both score sets without reconciliation
Text Scorer ───────┘    flags: "reconciliation unavailable, showing raw scores"
```

### Degraded: Navigator-Scorer Fails

```
ERROR status, no scores possible.
Consumer decides: retry, skip browser testing, or manual review.
```

---

## Cost Estimate

| Agent | Model | Cost per call | Notes |
|-------|-------|---------------|-------|
| Navigator-Scorer | Gemini Flash | ~$0.01-0.05 | Vision + interaction, most tokens |
| Text Scorer | Haiku / Flash | ~$0.01-0.03 | Text-only, small prompt |
| Reviewer | Sonnet | ~$0.02-0.05 | Reasoning, focused prompt |
| **Total per persona** | | **~$0.04-0.13** | |

| Gate scenario | Personas | Cost | Time |
|---------------|----------|------|------|
| Task-level (1 persona) | 1 | ~$0.04-0.13 | ~40-75s |
| Gate with 3 personas | 3 | ~$0.12-0.39 | ~2-4 min |
| Gate with 5 personas | 5 | ~$0.20-0.65 | ~3-6 min |

Acceptable for quality software. For rapid iteration, task-level tests (1 persona) are cheap and fast.

---

## CLI Interface

```
persona-test \
  --persona persona.md \
  --url http://localhost:3000 \
  --objectives "fill signup, submit, verify confirmation" \
  --rubric rubric.md \          # NEW: consumer rubric (optional)
  --scope task \
  --task-id T03 \
  --screenshots-dir ./screenshots \
  --record-video ./recordings \
  --config config.yaml \
  --output report.json
```

New flags vs current:
- `--rubric` — consumer rubric file (optional, if omitted only PB rubric is applied)
- All other flags remain the same

---

## What This Solves (Mapped to Feedback)

| # | Feedback Issue | How This Proposal Addresses It |
|---|---------------|-------------------------------|
| 1 | Backward compatibility broken | New output format. `agent_result` string kept alongside structured output during transition period. Deprecated in v2. |
| 2 | Universal rubric should NOT be LLM-generated at runtime | PB rubric is static, defined per page type, built into persona-browser-agent. Consumer rubric is static, injected by consumer. Neither is generated at runtime. |
| 3 | Evaluation inside vs outside the tool | **Resolved**: Scoring happens in persona-browser-agent (with visual context). SUDD makes the pass/fail DECISION based on the detailed report. Clear boundary: evidence vs judgment. |
| 4 | Missing error handling between pipeline stages | Graceful degradation: text scorer failure → visual-only. Reviewer failure → raw scores. Navigator failure → ERROR status. |
| 5 | Repetition scaling over-engineered | Backlog. Not part of this proposal. |
| 6 | Custom tools assume stable JS injection | Navigator uses browser-use's native capabilities only. No custom JS injection. |
| 7 | Some measurements unreliable in automated contexts | Navigator reports factual observations. Text scorer + visual scorer triangulate. Reviewer resolves conflicts. |
| 8 | Scoring engine prompt size | **Resolved**: Three focused prompts. Navigator-scorer prompt includes only current page's rubric criteria. Text scorer gets text observations only. Reviewer gets score comparisons only. |
| 9 | HAR recording isn't native to browser-use | Backlog. Not part of this proposal. |
| 10 | How does browser-use agent know to call custom tools? | Navigator doesn't use custom tools. Standard browser-use actions only. |
| 11 | Max tokens | Navigator prompt is smaller per-page. Each agent gets a focused context. 10k-20k tokens per agent is comfortable. |

---

## Implementation Phases

### Phase 1: PB Rubrics + Consumer Rubric Format

**Repo**: persona-browser-agent
- Define the 5 page-type PB rubrics (form, landing, dashboard, error, other) as markdown files
- These are the product's IP — design carefully
- Define the consumer rubric format specification (the "Must Pass / Should Pass / Deal-Breakers" structure)
- **Effort**: Medium — rubric design is the hard part
- **No code changes** — just rubric content and format documentation

### Phase 2: Navigator-Scorer + Screenshot Saving

**Repo**: persona-browser-agent
- Modify `prompts.py` to include per-page scoring instructions (classify page type, apply PB rubric, apply consumer rubric)
- Add `--rubric` CLI flag for consumer rubric injection
- Restructure output from flat `agent_result` string to per-page JSON (new output format)
- Fix screenshot saving (directory is created but no files are written — implement actual capture)
- Enable video recording pass-through
- **Effort**: Medium — prompt rework + output restructuring + screenshot fix

### Phase 3: Text Scorer + Reviewer

**Repo**: persona-browser-agent
- New module: `persona_browser/text_scorer.py` — independent text-only scoring
- New module: `persona_browser/reviewer.py` — compare visual vs text, investigate discrepancies
- Wire into pipeline: navigator-scorer → text scorer → reviewer → final JSON output
- Implement graceful degradation (text scorer fails → visual-only, reviewer fails → raw scores)
- **Effort**: Medium-Large — two new modules + pipeline orchestration

### Phase 4: SUDD Rubric Generation

**Repo**: sudd2
- Update architect agent to generate `changes/{id}/rubric.md` during `/sudd:plan`
- Rubric is derived from specs.md + design.md + persona deal-breakers
- Per-page structure matching the consumer rubric format from Phase 1
- **Effort**: Small-Medium — architect agent prompt update + new file in change structure

### Phase 5: SUDD Gate Integration

**Repo**: sudd2
- Update `gate.md` Step 2:
  - Add Step 2a: pre-flight checks + call persona-browser-agent once per persona
  - Add Step 2b/2c: dispatch persona-validator and ux-tester with browser report paths
  - Add Step 2d: dual-rubric aggregation logic (PB ≥ 98 AND consumer ≥ 98)
- Update `persona-validator.md`:
  - Remove browser launching and persona-browser-agent calling
  - Add browser report reading logic
  - Focus on consumer rubric interpretation + objective mapping
- Update `ux-tester.md`:
  - Remove persona-browser-agent calling
  - Add browser report reading logic
  - Keep Playwright technical checks (console errors, accessibility, design system)
  - Focus on PB rubric interpretation + intuitiveness assessment
- Add failure routing: per-criterion failures → targeted coder action items
- Update `sudd.yaml` schema with `rubric_threshold` config
- **Effort**: Medium-Large — 3 agent files + gate workflow + sudd.yaml changes

### Phase 6: Task-Level Integration

**Repo**: sudd2
- Wire persona-browser-agent into `/sudd:apply` per-task flow
- Micro-persona-validator reads task-level browser report
- `--scope task` limits to pages modified by the task
- **Effort**: Small — same pattern as gate, narrower scope

---

## Separation of Concerns

```
persona-browser-agent's job:          SUDD's job:
────────────────────────               ──────────
Know HOW to measure UX                Define WHAT to measure (consumer rubric)
Own the universal UX rubric (PB)      Write project-specific rubrics
Navigate as personas                  Define personas
Apply rubrics with visual context     Set the quality threshold (98/100)
Triangulate (visual + text + review)  Make PASS/FAIL decisions
Report evidence + scores              Route failures to developers
Be a reusable, sellable service       Be the orchestrator
```

---

## Open Questions

### Resolved

1. ~~**Consumer rubric format**~~: Markdown with "Must Pass / Should Pass / Deal-Breakers" per page. LLM interprets it. No YAML weights needed. **Resolved in Integration Contract §1.**

2. ~~**Who calls persona-browser-agent**~~: Gate calls it ONCE per persona. persona-validator and ux-tester read the saved report. No duplicate browser sessions. **Resolved in Integration Contract §2.**

3. ~~**Where consumer rubric lives**~~: `changes/{id}/rubric.md`, written by architect during `/sudd:plan`. **Resolved in Integration Contract §1.**

### Still Open

4. **PB rubric versioning**: As the universal rubric evolves, how do we handle version changes? Proposal: version the rubric set (v1.0, v1.1) and include version in output JSON so consumers can track.

5. **Page type classification accuracy**: The navigator must classify pages correctly to apply the right rubric. If it misclassifies a form page as "other," the form-specific criteria won't be checked. Mitigation: include classification confidence in output; allow consumer rubric to override page type per URL pattern.

6. **Discrepancy threshold**: Proposed 15-point delta to trigger reviewer investigation. This needs empirical tuning — too low means the reviewer wastes time on LLM noise, too high means it misses real disagreements.

7. **Video vs screenshots**: Video (WebM) captures the full session but is large and harder to reference. Screenshots at key moments are smaller and directly linkable from rubric criteria. Recommendation: screenshots as primary evidence, video as optional deep-dive artifact.

8. **Persona-validator scoring overlap**: persona-validator currently produces its own score (EXEMPLARY/STRONG/etc) AND now reads consumer rubric scores from the browser report. How do these interact? Proposal: persona-validator's score INCORPORATES browser report scores as evidence but can adjust up/down based on factors the browser test can't check (API contracts, documentation quality, code patterns). The gate checks BOTH the browser report scores AND the persona-validator score — both must pass.

9. **Playwright technical checks scope**: ux-tester may still run Playwright for console errors, accessibility, and design system compliance. Should these technical checks also be per-page and feed into the same per-page scoring structure? Or are they a separate "technical quality" dimension?

10. **Parallel persona testing**: Multiple personas can be tested in parallel (separate browser sessions). But each session takes 30-60 seconds and uses a browser instance. Should there be a max concurrency limit? On CI, resource constraints may apply.

---

## Decision Needed

Approve this architecture so we can begin implementation, starting with Phase 1 (PB rubric design + consumer rubric format).
