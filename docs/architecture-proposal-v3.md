# Persona Browser Agent — Architecture Proposal v3

**Date**: 2026-03-30
**Updated**: 2026-03-30 — browser-use v0.12+ API changes (CDP migration)
**Status**: APPROVED — Phases 0-4 implemented (2026-03-31)
**Responds to**: `feedback_browser_use.md`, critical review of v2
**Supersedes**: v2 (2026-03-30), v1 (2026-03-29)

> **NOTE (2026-03-30):** browser-use v0.12+ has migrated from Playwright to CDP (Chrome DevTools Protocol) via `cdp-use`. The `Browser` class is replaced by `BrowserSession` + `BrowserProfile`. Playwright is no longer a direct dependency but can connect to the same Chrome instance via CDP. HAR recording is built-in via `BrowserProfile`. `AgentHistoryList` is a rich Pydantic model with per-step structured data. See `phase-0-feasibility-and-risk-mitigations.md` appendix for the full API reference. Code examples in this document have been updated to reflect the new API where relevant; some conceptual examples retain the old style for clarity with inline notes.

---

## Problem Statement

The current persona-browser-agent does everything in a single browser-use agent call: navigates pages, fills forms, judges usability, scores UX, and renders a verdict. This creates five problems:

1. **Conflicting authority** — Both the browser agent AND SUDD can score, producing contradictory verdicts
2. **Overloaded prompt** — One mega-prompt tries to navigate AND summarize AND score, degrading quality
3. **Tight coupling** — Scoring logic baked into persona-browser-agent, making it unusable outside SUDD
4. **No visual verification** — Text-only scoring misses layout breaks, color issues, spatial relationships
5. **Monolithic rubric** — One "overall UX score" gives no actionable feedback on specific pages

### Issues identified in v2 critical review

6. **browser-use cannot produce structured per-page JSON** — `Agent.run()` returns free-form text, not structured output. Per-page scoring during navigation is not feasible without a post-processing step.
7. **Text scorer independence was illusory** — In v2, the text scorer read the navigator's own narrative. "Independent analysis of dependent data" is not real triangulation.
8. **Page-type classification creates silent false passes** — Misclassifying a form page as "landing" means the wrong rubric is applied, producing a false PASS.
9. **Consumer rubric URL matching is fragile** — SPAs and dynamic pages don't map cleanly to URL-based rubric sections.
10. **Score aggregation formula undefined** — Binary criteria (PASS/FAIL) to numerical scores was left to LLM interpretation.

---

## Architecture: Genuine Triangulation with Code Intelligence

4 LLM agents + 1 deterministic module inside persona-browser-agent, with genuinely independent information sources. SUDD provides code-derived ground truth via a dedicated code-analyzer pipeline (3 agents + adversarial rubric review).

```
  SUDD                               persona-browser-agent
  ════                               ═════════════════════

  code-analyzer pipeline (3 agents + adversarial review):

  code-analyzer-fe ──┐  (Haiku, reads frontend)
                     ├──▶ code-analyzer-reviewer (Sonnet)
  code-analyzer-be ──┘  (Haiku, reads backend)
       │
       │ generates draft:
       │   codeintel.json, manifest.json, rubric.md (draft)
       │
       ├──▶ rubric-adversary (Haiku) critiques draft rubric
       │      vs specs + design + objectives
       ├──▶ code-analyzer-reviewer revises rubric (v2)
       ├──▶ rubric-adversary critiques v2
       ├──▶ code-analyzer-reviewer finalizes rubric
       │
       │ final outputs:
       │   manifest.json  (pages + tasks + auth flow + verification tasks)
       │   rubric.md      (consumer criteria — adversarially hardened)
       │   codeintel.json (merged FE+BE ground truth, cross-validated)
       │
       ▼
                          ┌──────────────────────────────────┐
  persona.md ────────────▶│                                  │
  manifest.json ─────────▶│  AGENT 1: NAVIGATOR              │
  url ───────────────────▶│  (browser-use, Gemini Flash)     │
  objectives ────────────▶│                                  │
                          │  Navigates as persona             │
  Does NOT receive:       │  Takes screenshots per page       │
    rubric, codeintel     │  Reports text observations        │
    (stays "blind")       │  Network captured via HAR recording  │
                          │  Gives first-person experience    │
                          │  Does NOT score anything          │
                          │  max_steps + timeout configured   │
                          └──────────────┬───────────────────┘
                                         │
                          observations + screenshots + network_log + experience
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
             ┌──────────────┐  ┌───────────────────┐  ┌─────────────────┐
rubric ─────▶│ AGENT 2:     │  │ AGENT 3:          │  │ NETWORK         │
codeintel ──▶│ TEXT SCORER  │  │ VISUAL SCORER     │  │ VERIFIER        │
observations▶│              │  │                   │  │ (deterministic  │
network_log▶│ Reads: text  │  │ Sees: screenshots │  │  Python module) │
experience ─▶│ + network    │  │ only              │  │                 │
             │              │  │                   │  │ Inputs:         │
             │ Verifies     │  │ Verifies visual   │  │  network_log    │
             │ behavior +   │  │ elements against  │  │  codeintel      │
             │ API calls    │  │ code ground truth │  │  manifest       │
             │ against code │  │                   │  │                 │
             │ ground truth │  │ Receives filtered │  │ Rule-based:     │
             │              │  │ codeintel (visual │  │  API matching   │
             │ Model:       │  │ fields only)      │  │  Auth flow      │
             │ GLM 5-turbo  │  │                   │  │  Status codes   │
             │              │  │ Model: Gemini 3   │  │  Contract check │
             │              │  │ Flash (multimodal)│  │                 │
             └──────┬───────┘  └──────┬────────────┘  └──────┬──────────┘
                    │   ALL THREE RUN IN PARALLEL            │
                    └──────────────┬──────────────────────────┘
                                   │
                                   ▼
                   ┌──────────────────────────────────────┐
  rubric.md ──────▶│ AGENT 4: SCORE RECONCILER             │
  manifest.json ──▶│ (Sonnet, reasoning)                   │
                   │                                       │
                   │ Inputs:                               │
                   │  text_scores + visual_scores           │
                   │  network_verification (pre-computed)   │
                   │  experience narrative                  │
                   │  manifest (for coverage check)         │
                   │                                       │
                   │ Compares text vs visual scores         │
                   │ All agree → confirm (high confidence)  │
                   │ Disagree → investigate + explain       │
                   │ Big gap on critical criterion →        │
                   │   can request browser-use re-visit     │
                   │ Checks manifest coverage               │
                   │   (all pages visited?)                 │
                   │ Integrates network_verification report │
                   │   (already computed — no LLM needed)   │
                   │                                       │
                   │ Produces: reconciled per-page scores   │
                   │         + discrepancy analysis         │
                   │         + manifest coverage report     │
                   │         + confidence levels            │
                   └──────────────────┬────────────────────┘
                                     │
                                     ▼ JSON report
                               ┌───────────┐
                               │   SUDD    │
                               │           │
                               │ Reads detailed report
                               │ Applies own scoring formula
                               │ PASS / FAIL + action items
                               └───────────┘
```

---

## Why This Architecture

### Genuine triangulation (v2 fix)

In v2, the text scorer read the navigator's narrative — fake independence. In v3, each scorer has a **different information source**:

| Scorer | Information Source | What It Catches |
|--------|-------------------|-----------------|
| Text Scorer | Navigator's text observations + codeintel | Behavioral issues, missing elements, wrong error messages, sequence failures. Compares described behavior against code ground truth. |
| Visual Scorer | Screenshots + codeintel | Layout breaks, color mismatches, spatial issues (error at top vs near field), missing elements visible in screenshot but not mentioned by navigator. Compares visual state against code ground truth. |

When they disagree, the disagreement is meaningful — one saw something the other literally could not access.

### Navigator stays blind (tests real UX)

The navigator does NOT receive the rubric or code intelligence. It knows who it is (persona), where to go (manifest pages), and what to try (objectives). It discovers the UI naturally, like a real user. If you tell the navigator "there are 4 form fields," you're no longer testing discoverability.

### Code intelligence makes scoring precise (v2 fix)

Instead of generic criteria like "form has validation," the scorers verify against code-derived ground truth: "email field has validation regex `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, error message should be 'Please enter a valid email address', field should have `aria-label='Email address'`."

### Feature-based rubrics, not page-type classification (v2 fix)

No page-type classification step. No misclassification risk. The scorers detect what features are present on each page (forms, navigation, CTAs, data displays) and apply the relevant criteria. A signup page with a nav bar gets both FORM and NAVIGATION criteria.

### Score aggregation owned by SUDD (v2 fix)

persona-browser-agent reports per-criterion PASS/FAIL with evidence. SUDD owns the formula for converting those into numerical scores and the threshold for PASS/FAIL. Different consumers can apply different formulas to the same evidence.

### Network capture catches invisible failures (v3 addition)

A beautiful form that shows "Success!" means nothing if the API call failed silently, the auth token wasn't set, or the data wasn't persisted. The Navigator captures all HTTP requests/responses during its session via **browser-use's built-in HAR recording** (`BrowserProfile.record_har_path`). The HAR file is a standardized JSON format that captures method, URL, status, headers (including Set-Cookie and auth tokens), timing, and optionally request/response bodies. A `har_parser.py` module transforms HAR entries into the v3 `network_log[]` format. The Text Scorer cross-references this network log against codeintel's API contracts and auth configuration. This catches the exact class of bugs that UX-focused testing misses: wiring errors, auth handover failures, and backend-frontend contract violations.

### End-to-end verification proves the feature works (v3 addition)

The code-analyzer traces data flows through the codebase (which endpoints write data, which endpoints read it) and auto-generates verification tasks: "after signup, refresh the page — is the data still there?" The Navigator executes these verification tasks and reports the results. The Score Reconciler evaluates whether data round-trips actually work. This is the difference between "the form submits" and "the feature works."

### Auth flows are first-class citizens (v3 addition)

Authentication is the #1 source of wiring failures between frontend and backend. The manifest includes an explicit auth_flow section that tells the Navigator HOW to structure its session: pre-auth pages → auth action → post-auth pages → verify persistence → verify logout. The codeintel includes auth configuration (mechanism, protected routes, token/cookie details) so the Text Scorer can verify that auth tokens are actually being set and sent correctly in the network log.

---

## Agent Details

### Agent 1: Navigator

**Lives in**: persona-browser-agent
**Model**: Gemini Flash (multimodal, vision required)
**Role**: Navigate as the persona, observe, screenshot. No scoring.
**Browser runtime**: browser-use v0.12+ via `BrowserSession` + `BrowserProfile` (CDP-based). Network capture via built-in HAR recording. Screenshots saved per step in `AgentHistoryList`.
**Safety limits**: `max_steps: 50` (prevents infinite loops), `timeout_seconds: 120` (prevents stuck sessions). Both configurable via CLI or config.yaml. If either limit is hit, navigator saves partial results and returns `status: PARTIAL`.

#### Receives

| Input | Source | Purpose |
|-------|--------|---------|
| `--persona` | Persona .md file | Who to be |
| `--url` | CLI arg | Where to start |
| `--objectives` | CLI arg | What to try |
| `--manifest` | manifest.json from SUDD | Which pages to visit, what tasks to accomplish |
| `--form-data` | File or embedded in persona | Data to use when filling forms |
| `--scope` | CLI arg (`task` or `gate`) | Narrow or broad exploration |

#### Does NOT Receive

- `--rubric` — does not see scoring criteria
- `--codeintel` — does not see code-derived expectations
- Any information about what the UI "should" look like

#### Prompt (simplified, focused)

```
"You are {persona}. Navigate to {url} and attempt these objectives:
{objectives}

Visit these pages (from manifest):
{manifest pages with purpose and how_to_reach}

AT EACH PAGE:
1. Describe what you see — layout, elements, content
2. Interact naturally — click, fill forms, explore
3. Take a screenshot
4. Report what happened factually
5. [Network requests are captured automatically via HAR recording — no navigator action needed]
6. Move to the next page

IF manifest includes auth_flow:
  Follow the auth_flow sequence:
  1. Visit pre-auth pages first
  2. Complete the auth action (login/signup)
  3. Visit post-auth pages
  4. If verify_auth_persistence: refresh the page after auth, report if still authenticated
  5. If verify_logout: logout, then try accessing a post-auth page, report what happens

IF manifest includes VERIFY tasks:
  After completing the main flow, run each verification:
  - Refresh the page — is the data still there?
  - Navigate to a different page that should show the same data — is it consistent?
  - Report exactly what you see vs what you submitted

AFTER ALL PAGES:
Give your honest first-person experience:
- What was easy? What was hard?
- Where did you hesitate or feel confused?
- Would you come back? Would you recommend this?
- Rate your overall satisfaction 1-10 with explanation

Do NOT score against criteria. Do NOT judge quality.
Just navigate, observe, and report your experience."
```

#### Output

> **Implementation note (v0.12+):** This JSON is NOT produced directly by browser-use. It is assembled by `output_parser.py` (deterministic transform from `AgentHistoryList`) + `har_parser.py` (HAR file → `network_log[]`). The `AgentHistoryList` provides URLs, screenshot paths, actions, results, and timing per step. The HAR file provides all network data. Page-level text descriptions come from the LLM's `model_thoughts()` and `extracted_content()` per step.
>
> **Page grouping algorithm** (handles SPAs and multi-visit scenarios):
> 1. Primary key: URL changes in `history.urls()`. Each URL transition starts a new page segment.
> 2. Manifest matching: each segment is matched to a `manifest.pages[].id` by comparing the segment URL against manifest `how_to_reach` hints and expected routes from codeintel.
> 3. Multi-visit handling: if the navigator visits the same URL twice (e.g., /register → /dashboard → /register for error testing), each visit becomes a separate page entry with a visit suffix: `registration-visit-1`, `registration-visit-2`.
> 4. SPA fallback: if the URL doesn't change for >3 consecutive steps but the navigator's `model_thoughts()` indicate a new page context (e.g., "I now see a different form" or "modal appeared"), split into a new segment. Match to manifest by content description.
> 5. Unmatched segments: pages not in the manifest get `"id": "unexpected-{url_slug}"` and are flagged in `manifest_coverage.unexpected_pages`.
>
> **HAR-step correlation algorithm** (maps network requests to navigator actions):
> 1. For each navigator step, record the timestamp window: `[step_start, step_end]` from `AgentHistoryList` timing.
> 2. For each HAR entry, check if `startedDateTime` falls within a step's timestamp window.
> 3. Filter noise: exclude requests to known non-app domains (analytics, fonts, CDN static assets) via a configurable allowlist of app domains.
> 4. Assign each HAR entry a `trigger` field: `"step {N} — {action_name}"` if it falls within a step window, or `"background"` if it doesn't correlate to any step (prefetch, polling, websocket).
> 5. Ambiguous timing (request spans step boundary): assign to the step that initiated it (earliest overlap).

```json
{
  "status": "DONE",
  "elapsed_seconds": 45.2,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "scope": "gate",
  "cdp_port": 9222,

  "manifest_coverage": {
    "expected_pages": ["registration", "dashboard"],
    "visited": ["registration", "dashboard"],
    "not_visited": [],
    "unexpected_pages": ["/about"]
  },

  "pages": [
    {
      "id": "registration",
      "url_visited": "http://localhost:3000/register",
      "screenshot": "screenshots/01-registration.png",
      "observations": {
        "description": "Page with centered form. Three visible input fields: name, email, password. Submit button below. 'Already have an account? Log in' link at bottom.",
        "actions": [
          {"step": 1, "action": "Looked for signup form", "result": "Form is the main content, immediately visible"},
          {"step": 2, "action": "Filled name field with 'Jordan Rivera'", "result": "Field accepted input"},
          {"step": 3, "action": "Submitted with empty email", "result": "Error appeared at top of page: 'Please fill in all fields'"},
          {"step": 4, "action": "Filled all fields, submitted", "result": "Redirected to /dashboard"}
        ],
        "forms": [
          {
            "fields_seen": ["name", "email", "password"],
            "submitted": true,
            "errors_encountered": [
              {"trigger": "empty email submit", "message": "Please fill in all fields", "location": "top of page"}
            ]
          }
        ]
      },
      "network_log": [
        {"method": "GET", "url": "/register", "status": 200, "timing_ms": 120, "trigger": "page load"},
        {"method": "POST", "url": "/api/auth/register", "status": 400, "timing_ms": 85,
         "trigger": "step 3 — empty email submit",
         "request_content_type": "application/json",
         "response_summary": "{\"error\": \"Please fill in all fields\"}"},
        {"method": "POST", "url": "/api/auth/register", "status": 201, "timing_ms": 340,
         "trigger": "step 4 — full submit",
         "request_content_type": "application/json",
         "response_summary": "{\"user_id\": 42}",
         "set_cookie": "session=abc123; HttpOnly; Path=/"}
      ]
    },
    {
      "id": "dashboard",
      "url_visited": "http://localhost:3000/dashboard",
      "screenshot": "screenshots/02-dashboard.png",
      "observations": {
        "description": "Dashboard page showing 'Welcome, Jordan!' at top. Three cards below with placeholder content. Left sidebar navigation.",
        "actions": [
          {"step": 5, "action": "Looked for personalized greeting", "result": "Found 'Welcome, Jordan!' at top"},
          {"step": 6, "action": "Refreshed the page (verification)", "result": "Still showing 'Welcome, Jordan!' — data persisted"}
        ]
      },
      "network_log": [
        {"method": "GET", "url": "/dashboard", "status": 200, "timing_ms": 95, "trigger": "redirect after signup"},
        {"method": "GET", "url": "/api/user/me", "status": 200, "timing_ms": 45,
         "trigger": "dashboard data load",
         "request_headers_note": "session cookie sent automatically",
         "response_summary": "{\"name\": \"Jordan Rivera\", \"email\": \"jordan@example.com\"}"},
        {"method": "GET", "url": "/api/user/me", "status": 200, "timing_ms": 42,
         "trigger": "step 6 — page refresh verification",
         "response_summary": "{\"name\": \"Jordan Rivera\"}"}
      ]
    }
  ],

  "auth_flow_verification": {
    "auth_completed": true,
    "auth_mechanism_observed": "session cookie set after POST /api/auth/register",
    "post_auth_access": "PASS — dashboard loaded with personalized data",
    "persistence_after_refresh": "PASS — data survived page refresh",
    "logout_test": null
  },

  "experience": {
    "first_impression": "Clean, simple registration page. Knew immediately what to do.",
    "easy": ["Finding the form", "Filling in fields", "Submitting"],
    "hard": ["Error message appeared at top, not near the field I missed"],
    "hesitation_points": ["After error, wasn't sure which field caused it"],
    "would_return": true,
    "would_recommend": "yes, with minor caveat about error messages",
    "satisfaction": 7,
    "satisfaction_reason": "Works fine but error handling could be more helpful"
  },

  "screenshots": [
    "screenshots/01-registration.png",
    "screenshots/02-registration-error.png",
    "screenshots/03-dashboard.png"
  ],

  "video": "recordings/session.webm"
}
```

**Key: `agent_result` backward compatibility.** During transition (v1.x), the output ALSO includes an `agent_result` string field containing a text narrative of the experience (derived from `AgentHistoryList.final_result()` — same format as current `str(result)` output). This allows existing consumers to keep working while migrating to the structured format. A `version` field indicates which format is active:

```json
{
  "version": "1.1",
  "status": "DONE",
  "agent_result": "## Persona Test Report\n\nFirst impression: Clean registration...",
  "pages": [ ... ],
  "experience": { ... }
}
```

`version: "1.x"` = both fields present. `version: "2.0"` = `agent_result` removed.

---

### Agent 2: Text Scorer

**Lives in**: persona-browser-agent
**Model**: GLM 5-turbo (text-only, cost-effective)
**Role**: Score rubric criteria from text observations + code intelligence. No images.

#### Receives

| Input | What It Is |
|-------|------------|
| Navigator's text observations | Per-page descriptions, actions, results, error messages |
| Navigator's network log | Per-page HTTP requests/responses captured during navigation |
| Navigator's experience | First-person narrative (hesitation, satisfaction) |
| Rubric (consumer) | Criteria to score against |
| PB rubric (built-in) | Universal UX feature criteria |
| Code intelligence | Ground truth: expected elements, validation rules, error messages, routes, API contracts, auth config |

#### Does NOT Receive

- Screenshots (cannot see the page visually)
- Navigator's satisfaction score (scorer forms own judgment)

#### What It Catches (that visual scorer can't)

- **Behavioral sequences**: "Navigator clicked submit, then got error, then had to re-enter data" — text reveals the flow, screenshots show frozen moments
- **Timing**: "Took 3.2 seconds to load" — not visible in a screenshot
- **Error message text accuracy**: Navigator quoted "Please fill in all fields." Code says it should be "Email is required." Text scorer catches the mismatch.
- **Missing interactions**: Navigator only saw 3 fields. Code intelligence says 4 exist (confirm_password missing). Text scorer flags it.
- **API contract violations**: Network log shows `POST /api/auth/register → 201` but codeintel says success should set a session cookie — network log confirms cookie was/wasn't set. Catches silent backend failures invisible to the user.
- **Auth handover failures**: Network log shows `GET /api/user/me → 401` after signup — auth token wasn't propagated. The user sees a dashboard but the next request will fail.
- **Wrong API endpoints**: Network log shows frontend called `POST /api/register` but codeintel says the backend route is `POST /api/auth/register` — wiring mismatch.
- **Backend validation gaps**: Frontend shows success but network log shows `500 Internal Server Error` — the UI caught the error silently or showed a generic fallback.

#### Output (per page, per criterion)

```json
{
  "page_id": "registration",
  "pb_criteria": [
    {
      "feature": "forms",
      "criterion": "Every field has a visible label",
      "result": "PASS",
      "evidence": "Navigator described 3 labeled fields: name, email, password",
      "confidence": "high"
    },
    {
      "feature": "forms",
      "criterion": "Error message appears near the triggering field",
      "result": "UNKNOWN",
      "evidence": "Navigator reported error message appeared but did not specify spatial position relative to field",
      "confidence": "low",
      "note": "Cannot determine spatial position from text. Deferring to visual scorer."
    }
  ],
  "consumer_criteria": [
    {
      "criterion": "Signup form has name, email, password, confirm_password fields",
      "result": "FAIL",
      "evidence": "Navigator saw 3 fields (name, email, password). Code intelligence says 4 fields expected (confirm_password missing or not visible).",
      "confidence": "high",
      "codeintel_ref": "registration.elements.forms[0].fields"
    },
    {
      "criterion": "Error message matches code-defined text",
      "result": "FAIL",
      "evidence": "Navigator reported: 'Please fill in all fields'. Code defines email_empty error as: 'Email is required'. Messages don't match.",
      "confidence": "medium",
      "note": "Navigator may have paraphrased. Or the generic error fires before field-specific errors.",
      "codeintel_ref": "registration.elements.forms[0].error_messages.email_empty"
    },
    {
      "criterion": "Signup API returns 201 and sets session cookie",
      "result": "PASS",
      "evidence": "Network log: POST /api/auth/register → 201 (340ms). Response set cookie: session=abc123. Matches codeintel API contract.",
      "confidence": "high",
      "codeintel_ref": "api_endpoints[0].success"
    },
    {
      "criterion": "Dashboard loads user data via authenticated API call",
      "result": "PASS",
      "evidence": "Network log: GET /api/user/me → 200 with session cookie sent. Response contains name='Jordan Rivera' matching signup input. Data persists after page refresh (second GET /api/user/me → 200).",
      "confidence": "high",
      "codeintel_ref": "api_endpoints[1]"
    }
  ]
}
```

---

### Agent 3: Visual Scorer

**Lives in**: persona-browser-agent
**Model**: Gemini 3 Flash (multimodal, vision required)
**Role**: Score rubric criteria from screenshots + code intelligence. No text observations.

#### Receives

| Input | What It Is |
|-------|------------|
| Screenshots | Per-page images from navigator |
| Rubric (consumer) | Criteria to score against |
| PB rubric (built-in) | Universal UX feature criteria |
| Code intelligence (filtered) | Visual-relevant fields only: `elements` (component structure, expected fields), `design_tokens` (colors, fonts, spacing), `accessibility` (aria attributes, roles). Does NOT receive `api_endpoints`, `auth`, `data_flows` — those are irrelevant to visual assessment and would waste tokens / contaminate judgment. |

#### Does NOT Receive

- Navigator's text observations (cannot read what the navigator described)
- Navigator's experience narrative (doesn't know what was easy/hard)
- What the navigator did (only sees the resulting page state)
- Network log (network activity is invisible to users)
- Non-visual codeintel (API contracts, auth config, data flows)

#### What It Catches (that text scorer can't)

- **Spatial relationships**: Error message at page top vs near the field — visible in screenshot, not in text
- **Visual design**: Button color is green but design token says blue (#2563eb) — text scorer can't see colors
- **Layout breaks**: Element overflows container, text truncated, overlapping elements — text scorer can't detect layout
- **Missing elements**: confirm_password field not visible in screenshot — confirms text scorer's finding with visual evidence
- **Visual hierarchy**: CTA button is smaller than secondary links — design issue only visible in screenshot

#### Feature Detection (replaces page-type classification)

The visual scorer does NOT classify the page type. Instead, it detects which features are present in the screenshot and applies the relevant PB criteria:

```
Screenshot analysis:
  "I see: a form with input fields → apply FORMS criteria
   I see: a navigation bar at top → apply NAVIGATION criteria
   I see: a large button labeled 'Sign Up' → apply CTA criteria
   I do not see: data tables, charts → skip DATA DISPLAY criteria
   I do not see: error messages currently → skip ERROR STATES criteria
                                            (but FORMS criteria still check
                                             for error handling capability)"
```

#### Output (per page, per criterion)

```json
{
  "page_id": "registration",
  "features_detected": ["forms", "navigation", "cta"],
  "pb_criteria": [
    {
      "feature": "forms",
      "criterion": "Every field has a visible label",
      "result": "PASS",
      "evidence": "Screenshot shows 3 fields with labels above each: 'Full Name', 'Email Address', 'Password'",
      "confidence": "high"
    },
    {
      "feature": "forms",
      "criterion": "Error message appears near the triggering field",
      "result": "FAIL",
      "evidence": "Screenshot shows error banner at page top, approximately 300px above the form fields. Error text is not adjacent to any specific field.",
      "confidence": "high"
    },
    {
      "feature": "forms",
      "criterion": "Required fields are marked",
      "result": "FAIL",
      "evidence": "No asterisks, 'required' text, or other indicators visible on any field label",
      "confidence": "high"
    }
  ],
  "consumer_criteria": [
    {
      "criterion": "Signup form has name, email, password, confirm_password fields",
      "result": "FAIL",
      "evidence": "Screenshot shows 3 input fields. No confirm_password field visible. Checked below fold — not found.",
      "confidence": "high"
    },
    {
      "criterion": "Button color matches design system",
      "result": "FAIL",
      "evidence": "Button appears green (~#22c55e). Code intelligence specifies primary_color: #2563eb (blue).",
      "confidence": "medium",
      "note": "Color detection from screenshots is approximate",
      "codeintel_ref": "registration.design_tokens.primary_color"
    }
  ]
}
```

---

### Network Verifier (Deterministic Module)

**Lives in**: persona-browser-agent (`persona_browser/network_verifier.py`)
**Model**: None — deterministic Python code, no LLM
**Role**: Cross-reference network_log (from HAR) against codeintel API contracts. Runs in parallel with scorers. Produces a structured verification report that the Score Reconciler integrates.

**Why deterministic, not LLM**: Network verification is rule-based matching (method + path → expected status, check auth headers, match response fields). An LLM adds latency, cost, and non-determinism for what is fundamentally a comparison algorithm. Deterministic code is also easier to debug when codeintel is wrong.

#### Receives

| Input | What It Is |
|-------|------------|
| Navigator's network_log | Per-page HTTP requests/responses from HAR |
| codeintel.json | API endpoint definitions, auth config, data flows |
| manifest.json | Auth flow definition, verification tasks |
| Navigator's auth_flow_verification | Auth flow observations from navigator |

#### Verification Logic

```
For each page:
  For each API call in network_log:

    1. Match to codeintel.api_endpoints by method + path
       → NOT FOUND in codeintel: FLAG "unknown API call — may be wiring error"

    2. Check status code against codeintel.responses
       → 2xx expected, got 4xx/5xx: FAIL with "API error during normal flow"
       → 500 on any user action: DEAL-BREAKER (instant FAIL)

    3. Check auth requirements:
       → codeintel says auth_required=true
       → network_log shows no auth cookie/token sent: FLAG "missing auth"
       → network_log shows 401: FLAG "auth handover failed"

    4. Check response matches codeintel contract:
       → Expected fields missing from response: FLAG "API contract violation"
       → Response data doesn't match what UI displays: FLAG "frontend-backend mismatch"

For auth_flow (if manifest includes auth_flow):
  1. Check auth token/cookie was SET after auth action
     → network_log should show Set-Cookie or auth token in response
  2. Check auth token/cookie was SENT on subsequent requests
     → all post-auth API calls should include the token/cookie
  3. Check persistence: after page refresh, auth still works
     → network_log for refresh should still return 200 on protected endpoints
  4. Check logout (if verify_logout):
     → after logout, protected endpoint should return 401
```

#### Output

```json
{
  "api_calls_total": 5,
  "api_calls_matched_codeintel": 5,
  "api_calls_unmatched": 0,
  "api_errors_during_normal_flow": 0,
  "auth_token_set_after_auth": true,
  "auth_token_sent_on_protected_requests": true,
  "auth_persists_after_refresh": true,
  "deal_breakers": [],
  "issues": [],
  "per_endpoint": [
    {
      "method": "POST", "path": "/api/auth/register",
      "matched_codeintel": true, "status": 201, "expected_status": 201,
      "contract_match": true, "auth_check": "N/A (public endpoint)"
    }
  ]
}
```

---

### Agent 4: Score Reconciler

**Lives in**: persona-browser-agent
**Model**: Sonnet (needs reasoning quality for discrepancy analysis)
**Role**: Compare text vs visual scores, investigate discrepancies, check manifest coverage, integrate pre-computed network verification, produce reconciled verdict. Does NOT perform network verification itself — that's already done deterministically.

#### Receives

| Input | What It Is |
|-------|------------|
| Text scorer results | Per page, per criterion |
| Visual scorer results | Per page, per criterion |
| Network verification report | Pre-computed by Network Verifier (structured JSON, not raw network_log) |
| Navigator's experience narrative | First-person UX assessment |
| Manifest | Expected pages, auth_flow, verification_tasks |
| Navigator's manifest coverage | Which pages were visited |
| Navigator's auth_flow_verification | Auth flow observations |
| Rubric (consumer + PB) | Criteria definitions |

#### Does NOT Receive

- Raw network_log (already processed by Network Verifier)
- Full codeintel.json (Network Verifier already extracted what's needed)
- This reduces input tokens by ~30-40% vs the previous monolithic Reviewer

#### Reconciliation Logic

```
For each page:
  For each criterion:

    BOTH PASS → reconciled: PASS (high confidence)
    BOTH FAIL → reconciled: FAIL (high confidence)

    One PASS, one FAIL → INVESTIGATE:
      1. Read both evidence statements
      2. Determine: is this criterion spatial (trust visual)
         or behavioral (trust text)?
      3. Decide which scorer is correct
      4. Explain the discrepancy
      reconciled: winner's result (medium confidence)

    One scored, one UNKNOWN → trust the one that scored
      (scorer marked UNKNOWN because it couldn't assess
       from its information source — that's honest, not a failure)

    Big disagreement on CRITICAL criterion (deal-breaker) →
      Flag for optional browser-use re-visit of that specific page
      (reconciler can request navigator to go back and look again)
```

#### Manifest Coverage Check

```
For each page in manifest:
  IF page was visited:
    → check that all consumer criteria for this page were evaluated
    → flag any criteria not evaluated (scorer couldn't assess)
  IF page was NOT visited:
    → FLAG as MISSING
    → all criteria for this page: NOT_EVALUATED
    → reason: navigator could not reach the page (explain why if possible)
    → this alone may warrant FAIL depending on consumer policy

For each verification_task in manifest:
  IF verification was performed:
    → check result against expected behavior
    → V1 (data_persistence): data survived refresh? PASS/FAIL
    → V2 (cross_page_consistency): same data on both pages? PASS/FAIL
    → V3 (auth_persistence): still authenticated after refresh? PASS/FAIL
    → V4 (auth_boundary): blocked when unauthenticated? PASS/FAIL
  IF verification was NOT performed:
    → FLAG as SKIPPED with reason
```

#### Output (final report — assembled from all pipeline components)

The final JSON report merges outputs from Navigator, Text Scorer, Visual Scorer, Network Verifier, and Score Reconciler.

```json
{
  "version": "1.1",
  "status": "DONE",
  "elapsed_seconds": 52.3,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "scope": "gate",
  "cdp_port": 9222,

  "agent_result": "## Persona Test Report\n\n...(backward compat narrative)...",

  "manifest_coverage": {
    "expected": ["registration", "dashboard"],
    "visited": ["registration", "dashboard"],
    "missing": [],
    "coverage_pct": 100
  },

  "pages": [
    {
      "id": "registration",
      "url_visited": "http://localhost:3000/register",
      "screenshot": "screenshots/01-registration.png",
      "features_detected": ["forms", "navigation", "cta"],
      "observations": {
        "description": "...",
        "actions": [...]
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
          "criterion": "Error message appears near the triggering field",
          "text_result": "UNKNOWN",
          "visual_result": "FAIL",
          "reconciled": "FAIL",
          "confidence": "high",
          "evidence": "Visual scorer detected error banner at page top, ~300px from fields. Text scorer could not determine spatial position from narrative.",
          "discrepancy": "Text scorer lacked spatial information. Visual scorer's assessment is definitive for this criterion."
        },
        {
          "feature": "forms",
          "criterion": "Required fields are marked",
          "text_result": "FAIL",
          "visual_result": "FAIL",
          "reconciled": "FAIL",
          "confidence": "high",
          "evidence": "No required field indicators found by either scorer",
          "discrepancy": null
        }
      ],
      "consumer_criteria": [
        {
          "criterion": "Signup form has name, email, password, confirm_password fields",
          "text_result": "FAIL",
          "visual_result": "FAIL",
          "reconciled": "FAIL",
          "confidence": "high",
          "evidence": "Both scorers found only 3 fields. Code intelligence confirms 4 expected (confirm_password missing).",
          "codeintel_ref": "registration.elements.forms[0].fields"
        }
      ],
      "deal_breakers": []
    }
  ],

  "experience": {
    "satisfaction": 7,
    "hesitation_points": ["After error, wasn't sure which field caused it"],
    "would_recommend": "yes, with caveats"
  },

  "network_verification": {
    "_source": "Network Verifier (deterministic module — not LLM)",
    "api_calls_total": 5,
    "api_calls_matched_codeintel": 5,
    "api_calls_unmatched": 0,
    "api_errors_during_normal_flow": 0,
    "auth_token_set_after_auth": true,
    "auth_token_sent_on_protected_requests": true,
    "auth_persists_after_refresh": true,
    "deal_breakers": [],
    "issues": []
  },

  "verification_tasks": [
    {"id": "V1", "type": "data_persistence", "result": "PASS",
     "evidence": "After page refresh, GET /api/user/me returned name='Jordan Rivera' — matches signup input"},
    {"id": "V2", "type": "cross_page_consistency", "result": "PASS",
     "evidence": "Settings page shows name='Jordan Rivera', email='jordan@example.com' — consistent with signup"},
    {"id": "V3", "type": "auth_persistence", "result": "PASS",
     "evidence": "After refresh, dashboard loaded normally — session cookie survived"},
    {"id": "V4", "type": "auth_boundary", "result": "PASS",
     "evidence": "Before signup, navigating to /dashboard redirected to /login as expected"}
  ],

  "summary": {
    "pb_criteria_total": 18,
    "pb_criteria_passed": 14,
    "pb_criteria_failed": 3,
    "pb_criteria_unknown": 1,
    "consumer_criteria_total": 8,
    "consumer_criteria_passed": 6,
    "consumer_criteria_failed": 2,
    "verification_tasks_total": 4,
    "verification_tasks_passed": 4,
    "verification_tasks_failed": 0,
    "network_issues": 0,
    "total_discrepancies": 1,
    "deal_breakers_triggered": [],
    "pages_with_failures": ["/register"],
    "pages_clean": ["/dashboard", "/settings"]
  },

  "screenshots": ["screenshots/01-registration.png", "screenshots/02-dashboard.png"],
  "video": "recordings/session.webm"
}
```

---

## PB Rubric: Feature-Based (Not Page-Type)

No page-type classification. No misclassification risk. The visual scorer detects which features are present on each page and activates the relevant criteria.

### FORMS (apply when form fields are visible on the page)

```
Labels & Inputs
  □ Every field has a visible label (not just placeholder text)
  □ Required fields are marked (asterisk, "required" text, or equivalent)
  □ Input types match content (email → email keyboard, password → masked)
  □ Tab order is logical

Validation & Errors
  □ Required-field error appears on empty submit
  □ Format error appears on invalid input
  □ Error message appears NEAR the triggering field (not only at page top)
  □ Error message is specific (not generic "Invalid input")
  □ Valid input clears previous errors
  □ User doesn't lose entered data on error

Submission
  □ Submit button is visible without scrolling
  □ Button shows loading state during async submission
  □ Success confirmation is clear and immediate

Deal-breakers (instant FAIL)
  ✗ Form submits with empty required fields and no error
  ✗ Submitted data is silently lost
  ✗ No way to correct errors without re-entering everything
```

### NAVIGATION (apply when nav elements are visible)

```
  □ Current page/section is indicated in nav
  □ Logo or brand links to home
  □ No dead-end pages (always a path forward or back)
  □ Back button / breadcrumb works as expected

Deal-breakers
  ✗ Navigation leads to 404 or blank page
  ✗ User gets trapped (no way back)
```

### CTA (apply when call-to-action buttons are visible)

```
  □ Primary CTA is the most visually prominent element
  □ CTA text is action-oriented and clear
  □ CTA leads to expected destination (not 404)
  □ No more than 2 competing CTAs on the same page

Deal-breakers
  ✗ Primary CTA is non-functional
```

### DATA DISPLAY (apply when tables, cards, lists, or data are visible)

```
  □ Most important data is above the fold
  □ Data is grouped logically
  □ Empty states have helpful messaging (not blank)
  □ Dynamic content loads with visible loading indicator

Deal-breakers
  ✗ Data is visibly wrong or contradictory
  ✗ Key data is unreachable
```

### ERROR STATES (apply when error messages or error pages are visible)

```
  □ Error message explains what happened in plain language
  □ Clear recovery path exists (link, button, or instruction)
  □ No technical jargon (no stack traces, raw error codes)

Deal-breakers
  ✗ Blank page with no guidance
  ✗ Error page with no way to recover
```

### BASELINE (apply to EVERY page, always)

```
  □ Page loads without visible errors
  □ Text is readable (sufficient contrast, reasonable size)
  □ No broken images or missing assets
  □ Page is responsive to viewport (no horizontal scroll on standard widths)

Deal-breakers
  ✗ Page is blank or non-functional
  ✗ Console errors that affect user experience
```

### TASK COMPLETION (conditional — activates when network activity and/or codeintel is present)

**Activation**: These criteria activate when the navigator's network_log contains API calls AND codeintel includes api_endpoints. If neither is present (e.g., a static marketing site with no backend), these criteria are skipped entirely — no false passes, no irrelevant results.

This category catches the failures that are invisible in screenshots and often missed by UX-focused testing: broken wiring, failed API calls, auth handover issues, and data that doesn't persist. An end user doesn't care how pretty the form is if their data disappears after submit.

```
End-to-End Flow
  □ Primary user action produces the expected backend outcome (not just visual feedback)
  □ Data submitted via forms appears correctly on subsequent pages
  □ API calls triggered by user actions return expected status codes (no silent 4xx/5xx)
  □ No network errors or failed requests during normal user flow

Data Persistence
  □ Page state survives a browser refresh (data persists, not just in-memory/session state)
  □ Data entered by user is consistent across all pages that display it
  □ Empty/loading states resolve to real data within reasonable time

Authentication & Authorization
  □ Auth-protected pages are accessible after successful login/signup flow
  □ Auth state persists across page navigations (session/token not lost)
  □ Auth state survives page refresh (user doesn't get logged out)
  □ Unauthenticated users are redirected to login (not shown a blank/broken page)

Backend-Frontend Handover
  □ Frontend displays data that matches what the backend API returns
  □ Error messages shown to user match the error the backend actually sent
  □ Loading states appear during async operations and resolve correctly
  □ Frontend gracefully handles backend errors (no raw JSON, stack traces, or blank screens)

Deal-breakers (instant FAIL — requires HIGH confidence evidence)
  ✗ Primary action silently fails (success message shown but no backend effect)
  ✗ Data entered by user is lost or corrupted between pages
  ✗ Authenticated user gets 401/403 on a page they should have access to
  ✗ User completes a flow but cannot verify or access their result
  ✗ API returns 500 during normal user flow (not edge case)
  ✗ Frontend shows success but network log reveals failure

  IMPORTANT: These deal-breakers only trigger at confidence "high."
  If the evidence confidence is "medium" (e.g., codeintel might have
  the wrong API contract, or navigator may have paraphrased), the
  criterion is scored as a PENALTY (-20) not an instant FAIL.
  This prevents false positives from codeintel extraction errors.
```

**How this is scored:**
- Text Scorer evaluates these criteria using navigator observations + network_log + codeintel
- Visual Scorer evaluates data consistency (does the name shown match what was submitted?)
- Network Verifier (deterministic) cross-references network_log with codeintel API contracts — produces structured pass/fail per endpoint
- Score Reconciler integrates network_verification results with scorer assessments for the final verdict

---

## Code Intelligence: What SUDD Extracts from the Codebase

SUDD has access to the full source code. A dedicated **code-analyzer agent** reads the codebase and extracts structured ground truth that the scorers use to verify observations.

### Code-Analyzer Pipeline (SUDD-side) — 3 Agents

The code-analyzer is split into three focused agents that run sequentially. Each has a narrow scope, making them reliable on cheap models and easy to debug when codeintel is wrong.

```
  code-analyzer-fe (Haiku, reads frontend)
       │
       │ fe_codeintel.json (routes, components, validation, design tokens)
       ▼
  code-analyzer-be (Haiku, reads backend)
       │
       │ be_codeintel.json (API endpoints, auth config, middleware, data flows)
       ▼
  code-analyzer-reviewer (Sonnet, merges + validates + generates)
       │
       │ codeintel.json (merged, cross-validated)
       │ manifest.json (pages + auth_flow + verification_tasks)
       │ rubric.md (DRAFT — consumer criteria from both FE + BE)
       ▼
  rubric-adversary (Haiku, critiques draft rubric)
       │ critique: gaps, vague criteria, untestable items, priority mismatches
       ▼
  code-analyzer-reviewer (Sonnet, revises rubric based on critique)
       │ rubric.md v2
       ▼
  rubric-adversary (Haiku, critiques v2)
       │ critique: remaining issues, over-corrections, new gaps
       ▼
  code-analyzer-reviewer (Sonnet, finalizes)
       │
       │ rubric.md (FINAL — adversarially hardened)
       ▼
  All artifacts written to changes/{id}/
```

**Why 3 code-analyzer agents + adversarial rubric review:**
- **FE and BE are different skills** — parsing React components vs FastAPI decorators requires different pattern recognition. Dedicated agents are more accurate.
- **Each agent has a small, focused prompt** — reads one part of the codebase, extracts one type of information. No overloaded prompts.
- **Haiku is cheap** — the full pipeline (2× Haiku FE/BE + 3× Sonnet reviewer + 2× Haiku adversary) costs ~$0.09-0.29. Worth it for accuracy.
- **Debugging** — if codeintel has a wrong API contract, you know whether it was the FE analyzer (wrong endpoint URL), BE analyzer (wrong response schema), or reviewer (bad merge). Each agent's output is inspectable.
- **Adversarial rubric review** — auto-generated rubrics are a single point of failure. The rubric-adversary ensures criteria are specific, complete, testable, and correctly prioritized before they're used to score. Two iterations catch both obvious gaps and subtler issues introduced by revisions.
- **Night runs without supervision** — a solo developer running this overnight needs each step to be reliable and debuggable from logs. Focused agents with clear outputs + hardened rubrics = fewer false passes and false failures.

#### code-analyzer-fe (Frontend)

**Model**: Haiku (text-only, cheap)
**Input**: Frontend source code, specs.md, design.md
**Scope**: Everything the browser will render

Extracts:
- Route definitions (React Router, Vue Router, Next.js pages, etc.)
- Component structure per page (form fields, buttons, navigation elements)
- Frontend validation rules (regex, min/max length, required flags)
- Error message strings (from code, not from backend responses)
- CSS / design tokens (colors, fonts, spacing — from CSS vars, Tailwind config, theme files)
- Accessibility attributes (aria-labels, roles, focus management)
- Frontend API call sites (which endpoints does the frontend call, with what method)

Output: `fe_codeintel.json`

#### code-analyzer-be (Backend)

**Model**: Haiku (text-only, cheap)
**Input**: Backend source code, specs.md
**Scope**: Everything behind the API

Extracts:
- API endpoint definitions (method, path, handler, middleware chain)
- Request body schemas (field names, types, required flags, constraints)
- Response schemas (status codes, body structure, headers set)
- Auth configuration (mechanism, token/cookie details, expiry, session store)
- Auth middleware — which endpoints are protected
- Backend validation rules (DB constraints, server-side validation that may differ from frontend)
- Error responses (exact error message strings for each error condition)
- Data writes (which endpoints write to which tables/collections, what fields)
- Data reads (which endpoints read from which tables/collections, what fields)

Output: `be_codeintel.json`

#### code-analyzer-reviewer

**Model**: Sonnet (needs reasoning for cross-validation)
**Input**: fe_codeintel.json, be_codeintel.json, specs.md, design.md, personas/*.md

Does:
1. **Merges** FE and BE codeintel into a single `codeintel.json`

2. **Cross-validates** — checks that frontend API call sites match backend endpoint definitions:
   - FE calls `POST /api/register` but BE defines `POST /api/auth/register` → flags mismatch
   - FE sends `{name, email, password}` but BE expects `{username, email, password}` → flags field name mismatch
   - FE expects `200` on success but BE returns `201` → flags status code mismatch
3. **Traces data flows** — follows data from write endpoint → DB → read endpoint:
   - `POST /api/auth/register` writes `{name, email, password_hash}` to `users` table
   - `GET /api/user/me` reads `{name, email}` from `users` table
   - Data flow: name entered in signup form → stored in DB → displayed on dashboard
4. **Generates verification tasks** from data flows:
   - Each data flow becomes a verification task: "After signup, refresh dashboard — is name still there?"
   - Each auth-protected route becomes an auth boundary test: "Before login, try accessing /dashboard — should redirect"
5. **Generates manifest** with pages, auth_flow, and verification_tasks
6. **Generates draft consumer rubric** from specs + codeintel, with per-page Must Pass / Should Pass / Deal-Breakers. This draft is then adversarially reviewed (see rubric-adversary below).
7. **Flags codeintel uncertainties** — if the analyzer wasn't confident about an extraction (e.g., couldn't find the auth middleware, or route definition was dynamically generated), it marks those entries with `"confidence": "low"`. The scorers and Score Reconciler treat low-confidence codeintel as advisory, not authoritative.

Output: `codeintel.json`, `manifest.json`, `rubric.md` (draft → hardened after adversarial review)

#### rubric-adversary

**Model**: Haiku (text-only, critique-focused)
**Input**: draft rubric.md, specs.md, design.md, task objectives, codeintel.json
**Role**: Adversarially review the auto-generated consumer rubric. Runs twice (2 iterations).

Checks:
1. **Specificity** — Are criteria specific enough to catch real bugs? ("form should work well" → too vague, "signup form has name, email, password, confirm_password fields" → good)
2. **Completeness** — Do criteria cover all features described in the objectives and specs? Any gaps?
3. **Testability** — Can every criterion be verified from browser observation (text + screenshots + network)? Flag any that require DB access, server logs, or other non-observable state.
4. **Priority correctness** — Are Must Pass / Should Pass / Deal-Breaker classifications aligned with the feature's actual importance? (missing auth → Deal-Breaker, not Should Pass)
5. **Contradiction check** — Do any criteria contradict each other or the codeintel?
6. **Over-specification** — Are any criteria so specific they'd false-fail on valid implementations? (e.g., "button must be exactly 48px tall" when design says "touch-friendly")

Output: structured critique with specific issues and suggested fixes.

**Runs**: Just before calling persona-browser-agent, at gate time (Step 2a)
If code changes on retry, the full pipeline re-runs and produces updated artifacts.

### What Gets Extracted

```
FROM FRONTEND CODE:                     USEFUL FOR:

Route definitions                       MANIFEST
  /register → RegisterPage.tsx          Navigator knows WHERE to go
  /dashboard → Dashboard.tsx            Score Reconciler checks page coverage

Component structure                     CODEINTEL → Visual Scorer
  RegisterPage has:                     "I should see 4 input fields
    <Input name="name" required />       and a submit button"
    <Input name="email" type="email" />
    <Input name="password" type="password" />
    <Input name="confirm" type="password" />
    <Button>Sign Up</Button>

Frontend validation rules               CODEINTEL → Text Scorer
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/  "Navigator reported error X —
  password: minLength(8)                 code expects minLength(8)"

Error messages (exact strings)          CODEINTEL → Text Scorer
  "Email is required"                   Verify exact error text
  "Password must be at least 8 chars"   matches what code defines

CSS / Design tokens                     CODEINTEL → Visual Scorer
  --primary: #2563eb                    "Button should be blue,
  font-family: Inter                     not green"
  border-radius: 8px

Accessibility attributes                CODEINTEL → flags for technical checks
  aria-label="Email address"            (can't verify from screenshots
  aria-required="true"                   or text — needs CDP/Playwright check)
  role="alert" on error messages

Frontend API calls                      CODEINTEL → Text Scorer (network verification)
  fetch('/api/auth/register', {POST})   Verify navigator's network_log hits
  fetch('/api/user/me', {GET})           the right endpoints

FROM BACKEND CODE:                      USEFUL FOR:

API endpoint definitions                CODEINTEL → Text Scorer (network verification)
  POST /api/auth/register               Verify network_log status codes,
    handler: AuthController.register     response format, side effects
    middleware: [rateLimit]              match what backend actually defines
    success: 201 → {user_id}
    error: 400 → {error: "..."}
    error: 409 → {error: "Email already registered"}

  GET /api/user/me                      Verify dashboard data comes from
    handler: UserController.getProfile    the right endpoint with right auth
    middleware: [authMiddleware]
    success: 200 → {name, email}
    error: 401 → {error: "Unauthorized"}

Auth configuration                      CODEINTEL + MANIFEST (auth_flow)
  mechanism: JWT / session cookie       Text Scorer verifies token/cookie
  token_location: httpOnly cookie        is set in network_log after login
  token_expiry: 24h                     Navigator follows auth_flow sequence
  refresh_mechanism: /api/auth/refresh  Score Reconciler checks auth persistence

Protected routes                        MANIFEST + CODEINTEL
  [authMiddleware] on:                  Navigator tests that protected pages
    /api/user/*                          work after auth and fail before auth
    /api/dashboard/*                    Text Scorer verifies 401 on
    /dashboard (frontend redirect)       unauthenticated access

Backend validation rules                CODEINTEL → Text Scorer
  email: unique constraint in DB        Catches cases where frontend
  password: bcrypt, min 8 chars          validation passes but backend
  name: max 255 chars, not empty         rejects (different rules)

Data flow (what gets persisted)         MANIFEST (verification tasks)
  POST /register writes:               Code-analyzer auto-generates
    → users table (name, email, hash)    VERIFY tasks: "after signup,
  GET /user/me reads:                    refresh dashboard — is name
    → users table (by session user_id)   still there?"
```

### codeintel.json Format

```json
{
  "version": "1.0",
  "generated_from": "git:abc1234",
  "generated_at": "2026-03-30T12:00:00Z",

  "pages": [
    {
      "id": "registration",
      "routes": ["/register", "/signup"],
      "component": "RegisterPage.tsx",
      "purpose": "User creates a new account",
      "elements": {
        "forms": [
          {
            "id": "signup-form",
            "fields": [
              {"name": "name", "type": "text", "required": true, "label": "Full Name"},
              {"name": "email", "type": "email", "required": true, "label": "Email Address",
               "validation": "regex: /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/"},
              {"name": "password", "type": "password", "required": true, "label": "Password",
               "validation": "minLength: 8"},
              {"name": "confirm", "type": "password", "required": true, "label": "Confirm Password",
               "validation": "must match password field"}
            ],
            "submit_button": {"text": "Sign Up", "type": "submit"},
            "error_messages": {
              "name_empty": "Name is required",
              "email_empty": "Email is required",
              "email_invalid": "Please enter a valid email address",
              "password_short": "Password must be at least 8 characters",
              "confirm_mismatch": "Passwords do not match"
            },
            "on_success": {"redirect": "/dashboard", "status": 201},
            "api_call": {"method": "POST", "endpoint": "/api/auth/register"}
          }
        ],
        "navigation": {
          "links": [{"text": "Already have an account? Log in", "href": "/login"}]
        }
      },
      "design_tokens": {
        "primary_color": "#2563eb",
        "error_color": "#dc2626",
        "font_family": "Inter",
        "border_radius": "8px"
      },
      "accessibility": {
        "form_labels": true,
        "aria_required": true,
        "error_role": "alert",
        "focus_management": "first invalid field on error"
      }
    }
  ],

  "api_endpoints": [
    {
      "method": "POST",
      "path": "/api/auth/register",
      "source_file": "backend/routes/auth.py:45",
      "auth_required": false,
      "middleware": ["rateLimit"],
      "request_body": {
        "name": {"type": "string", "required": true, "max_length": 255},
        "email": {"type": "string", "required": true, "format": "email", "unique": true},
        "password": {"type": "string", "required": true, "min_length": 8}
      },
      "responses": {
        "201": {
          "body": {"user_id": "number"},
          "side_effects": ["creates row in users table", "sets session cookie"],
          "sets_auth": {"type": "cookie", "name": "session", "httpOnly": true}
        },
        "400": {"body": {"error": "string"}, "when": "validation fails"},
        "409": {"body": {"error": "Email already registered"}, "when": "email exists in DB"}
      }
    },
    {
      "method": "GET",
      "path": "/api/user/me",
      "source_file": "backend/routes/user.py:12",
      "auth_required": true,
      "middleware": ["authMiddleware"],
      "responses": {
        "200": {
          "body": {"name": "string", "email": "string", "created_at": "datetime"},
          "data_source": "users table, looked up by session user_id"
        },
        "401": {"body": {"error": "Unauthorized"}, "when": "no valid session"}
      }
    }
  ],

  "auth": {
    "mechanism": "session cookie",
    "cookie_name": "session",
    "cookie_attributes": {"httpOnly": true, "secure": true, "sameSite": "lax", "path": "/"},
    "session_store": "server-side (Redis/DB)",
    "login_endpoint": "POST /api/auth/login",
    "register_endpoint": "POST /api/auth/register",
    "logout_endpoint": "POST /api/auth/logout",
    "refresh_mechanism": "none — session-based, no token refresh needed",
    "protected_routes": {
      "frontend": ["/dashboard", "/settings", "/profile"],
      "backend": ["/api/user/*", "/api/dashboard/*"]
    },
    "redirect_on_unauth": "/login"
  },

  "data_flows": [
    {
      "trigger": "POST /api/auth/register",
      "writes_to": "users table (name, email, password_hash)",
      "then_readable_from": ["GET /api/user/me (name, email)"],
      "verification": "After signup, GET /api/user/me should return the name and email that were submitted"
    }
  ]
}
```

**Key additions over pure-frontend codeintel:**
- `api_endpoints` — backend route definitions with auth requirements, middleware, request/response schemas, and side effects. Lets the Text Scorer verify network_log against what the backend actually expects.
- `auth` — authentication mechanism, token/cookie configuration, protected routes. Lets the Network Verifier check auth flow integrity and the Score Reconciler verify auth persistence.
- `data_flows` — how data moves from write endpoints to read endpoints. Lets the code-analyzer auto-generate VERIFY tasks in the manifest.
- `api_call` on form elements — links frontend forms to the backend endpoint they call. Lets the Text Scorer verify the right API was called.

### manifest.json Format

```json
{
  "pages": [
    {
      "id": "registration",
      "purpose": "User creates an account",
      "how_to_reach": "Click 'Sign Up' from homepage, or navigate to /register",
      "expected_features": ["forms", "navigation", "cta"],
      "auth_required": false
    },
    {
      "id": "dashboard",
      "purpose": "User sees their account after signup",
      "how_to_reach": "Successful registration submission redirects here",
      "auth_required": true,
      "expected_data": ["personalized greeting with submitted name", "user-specific content"]
    },
    {
      "id": "settings",
      "purpose": "User manages their account settings",
      "how_to_reach": "Click 'Settings' in sidebar navigation",
      "auth_required": true,
      "expected_data": ["name and email matching what was submitted during signup"]
    }
  ],

  "auth_flow": {
    "pre_auth_pages": ["registration"],
    "auth_action": "Submit the registration form with valid data",
    "post_auth_pages": ["dashboard", "settings"],
    "verify_auth_persistence": true,
    "verify_logout": true,
    "unauthenticated_behavior": {
      "expected": "redirect to /login",
      "test": "Before completing signup, navigate directly to /dashboard — should redirect"
    }
  },

  "tasks": [
    "Complete full signup flow from homepage to dashboard",
    "Test form validation with invalid data",
    "Test error recovery (wrong input, then correct)"
  ],

  "verification_tasks": [
    {
      "id": "V1",
      "type": "data_persistence",
      "description": "After signup, refresh the dashboard page",
      "check": "Is the personalized greeting still showing the submitted name?",
      "derived_from": "data_flows[0] — POST /register writes name, GET /user/me reads it"
    },
    {
      "id": "V2",
      "type": "cross_page_consistency",
      "description": "Navigate from dashboard to settings page",
      "check": "Does the name and email on settings match what was entered during signup?",
      "derived_from": "data_flows[0] — same data should appear on all pages reading from users table"
    },
    {
      "id": "V3",
      "type": "auth_persistence",
      "description": "After signup, refresh the page",
      "check": "Is the user still authenticated? Or are they redirected to login?",
      "derived_from": "auth.mechanism — session cookie should survive page refresh"
    },
    {
      "id": "V4",
      "type": "auth_boundary",
      "description": "Before completing signup, navigate directly to /dashboard",
      "check": "Is the user blocked or redirected to login? (should be)",
      "derived_from": "auth.protected_routes.frontend — /dashboard requires auth"
    }
  ]
}
```

**Key additions:**
- `auth_flow` — tells the Navigator HOW to structure its navigation: pre-auth pages first, then auth action, then post-auth pages. Also instructs verification of auth persistence and logout. Does not tell the Navigator WHAT to expect (stays blind to scoring criteria).
- `verification_tasks` — auto-generated by the code-analyzer from `data_flows` in codeintel.json. Each task tests a specific data round-trip or auth boundary. The Navigator runs these after the main flow and reports observations factually.
- `auth_required` per page — the Navigator uses this to understand page ordering, NOT to judge pass/fail. The scorers use it with codeintel to verify auth enforcement.
- `expected_data` per page — hints for verification tasks (what data should appear on this page after the flow completes).

### Who Sees What

```
                      persona  manifest  rubric  codeintel       screenshots  text obs  network_log  net_verif
                      ───────  ────────  ──────  ─────────       ───────────  ────────  ───────────  ─────────
Navigator              ✓        ✓        ✗       ✗              produces     produces  produces     ✗
Text Scorer            ✗        ✗        ✓       ✓ (full)       ✗            ✓         ✓            ✗
Visual Scorer          ✗        ✗        ✓       ✓ (filtered*)  ✓ (sees)     ✗         ✗            ✗
Network Verifier       ✗        ✓        ✗       ✓ (full)       ✗            ✗         ✓            produces
Score Reconciler       ✗        ✓        ✓       ✗              ✗            ✗         ✗            ✓ (reads)

* Visual Scorer receives filtered codeintel: design_tokens, elements, accessibility only.
  Does NOT receive api_endpoints, auth, data_flows.
```

**Why this distribution:**
- **Visual Scorer** gets filtered codeintel — API contracts and auth config are irrelevant to visual assessment and would waste tokens / contaminate judgment.
- **Network Verifier** is deterministic Python — it doesn't need rubrics or screenshots, just the raw data to match against contracts.
- **Score Reconciler** does NOT receive raw network_log or full codeintel — it reads the pre-computed `network_verification` report from the Network Verifier. This reduces its input by ~30-40% vs a monolithic Reviewer, keeping it focused on score reconciliation and discrepancy investigation.

---

## Integration Contract: SUDD ↔ persona-browser-agent

### Principle: Evidence vs Judgment

persona-browser-agent provides **EVIDENCE** (per-criterion PASS/FAIL with evidence, screenshots, discrepancies, confidence levels).
SUDD makes the **DECISION** (score aggregation formula, threshold, PASS/FAIL, what to fix).

### Principle: Call Once, Share Results

persona-browser-agent is called **ONCE per persona** at gate time. The JSON report is saved to disk. All downstream SUDD agents (persona-validator, ux-tester) READ the report — they do not launch browsers.

---

### 1. SUDD Gate Workflow (Revised)

#### Step 0: Macro-wiring check (existing, unchanged)

#### Step 1: Identify consumers (existing, unchanged)

#### Step 2a: Code Intelligence Extraction (NEW — 3-agent pipeline + adversarial rubric review)

```
Sequential dispatch (each agent feeds the next):

1. Dispatch(agent=code-analyzer-fe):
     Model: Haiku (cheap, focused)
     Input: frontend source code, specs.md, design.md
     Output: changes/{id}/fe_codeintel.json
       (routes, components, validation, design tokens, accessibility, FE API calls)

2. Dispatch(agent=code-analyzer-be):
     Model: Haiku (cheap, focused)
     Input: backend source code, specs.md
     Output: changes/{id}/be_codeintel.json
       (API endpoints, auth config, middleware, request/response schemas, data flows)

   Steps 1 and 2 CAN run IN PARALLEL (independent codebases).

3. Dispatch(agent=code-analyzer-reviewer):
     Model: Sonnet (needs reasoning for cross-validation)
     Input: fe_codeintel.json, be_codeintel.json, specs.md, design.md, personas/*.md
     Output (written to changes/{id}/):
       - codeintel.json  — merged + cross-validated FE+BE ground truth
       - manifest.json   — pages + auth_flow + verification_tasks (auto-generated from data flows)
       - rubric.md       — DRAFT consumer criteria from specs + code

   Cross-validation catches FE↔BE mismatches BEFORE browser testing:
     - FE calls wrong endpoint → flagged in codeintel as known mismatch
     - FE sends wrong field names → flagged
     - FE expects wrong status code → flagged
   These pre-caught mismatches appear in the browser report with
   "codeintel_pre_flagged: true" — higher confidence, since the code
   itself confirms the wiring error.

4. Adversarial rubric review (2 iterations):

   4a. Dispatch(agent=rubric-adversary):
         Model: Haiku
         Input: draft rubric.md, specs.md, design.md, task objectives
         Output: critique (gaps, vague criteria, untestable items, priority mismatches)

   4b. Dispatch(agent=code-analyzer-reviewer):
         Model: Sonnet
         Input: draft rubric.md + adversary critique
         Output: revised rubric.md (v2)

   4c. Dispatch(agent=rubric-adversary):
         Model: Haiku
         Input: rubric v2, specs.md, design.md, task objectives
         Output: critique (remaining issues, over-corrections)

   4d. Dispatch(agent=code-analyzer-reviewer):
         Model: Sonnet
         Input: rubric v2 + adversary critique
         Output: FINAL rubric.md (adversarially hardened)

Re-runs on retry if code has changed since last run (git SHA check).
Cost: ~$0.09-0.29 total (2x Haiku FE/BE + 3x Sonnet reviewer + 2x Haiku adversary).
Runs once per gate, shared across all personas.
```

#### Step 2b: Browser Testing (ONE call per persona)

```
FOR EACH persona in changes/{id}/personas/:

  persona-test \
    --persona "changes/{id}/personas/{name}.md" \
    --url {dev_server_url} \
    --objectives "{from persona ## Objectives}" \
    --manifest "changes/{id}/manifest.json" \
    --rubric "changes/{id}/rubric.md" \
    --codeintel "changes/{id}/codeintel.json" \
    --scope gate \
    --screenshots-dir "changes/{id}/screenshots/gate/{name}/" \
    --record-video "changes/{id}/recordings/" \
    --output "changes/{id}/browser-reports/{name}.json"

  IF status == "DONE" → continue
  IF status == "SKIP" → log, technical-checks-only (Playwright-via-CDP or direct CDP), cap score at 90
  IF status == "ERROR" → log, -5 penalty, continue

  Personas CAN be tested IN PARALLEL (independent browser sessions).
```

#### Step 2c: Persona Validator (reads report)

```
Dispatch(agent=persona-validator):
  Input:
    - browser_report: changes/{id}/browser-reports/{name}.json
    - persona research: changes/{id}/personas/{name}.md
    - change context: specs.md, design.md, tasks.md

  Reads from report:
    - consumer_criteria results (per page, per criterion)
    - manifest coverage (all pages visited?)
    - experience narrative
    - deal_breakers triggered

  Does NOT:
    - Launch a browser
    - Call persona-browser-agent
    - Take screenshots

  Still provides:
    - First-person narrative ("As Sarah Chen, I reviewed...")
    - EXEMPLARY/STRONG/ACCEPTABLE scoring (from standards.md)
    - Critical assessment
    - Handoff contract check

  Output: {score, level, objectives_met, critical_assessment, confidence}
```

#### Step 2d: UX Tester (reads report + optional technical checks via CDP/Playwright)

```
Dispatch(agent=ux-tester):
  Input:
    - browser_report: changes/{id}/browser-reports/{name}.json
    - design system: design-system/MASTER.md (if exists)
    - dev_server_url (for technical checks only — via CDP or Playwright-over-CDP)

  Reads from report:
    - pb_criteria results (per page, per feature, per criterion)
    - features_detected per page
    - discrepancy analysis

  MAY still run technical checks (via CDP session or Playwright connected over CDP):
    - Console error detection (JavaScript exceptions)
    - Accessibility audit (axe-core or similar)
    - Design system CSS compliance checks
    - Network request validation (4xx/5xx)
    - Checks flagged by reviewer as "needs technical verification"
      (e.g., aria attributes can't be verified from screenshots — use CDP or Playwright-over-CDP)

  Does NOT:
    - Call persona-browser-agent
    - Navigate as a persona

  Output: {verdict, score, scenarios_tested, issues, confidence}
```

#### Step 2e: Aggregate and Decide

```
FOR EACH persona:

  Read: changes/{id}/browser-reports/{name}.json
  Read: persona-validator output
  Read: ux-tester output

  SUDD applies its own scoring formula:

    pb_pass_rate = pb_criteria_passed / pb_criteria_total
    consumer_pass_rate = consumer_criteria_passed / consumer_criteria_total
    verification_pass_rate = verification_tasks_passed / verification_tasks_total

    pb_score = pb_pass_rate * 100
      - apply weighting if defined in sudd.yaml
      - deal-breaker triggered → instant 0
      - TASK COMPLETION deal-breaker (silent API fail, data loss, auth break) → instant 0

    consumer_score = consumer_pass_rate * 100
      - "Must Pass" failures → weighted at 100%
      - "Should Pass" failures → weighted at 50%
      - deal-breaker triggered → instant 0

    verification_score = verification_pass_rate * 100
      - ALL verification tasks must pass (threshold: 100%)
      - ANY failure → -20 per failed verification task

    network_penalty:
      - API 500 during normal flow → DEAL-BREAKER (instant 0)
      - API 4xx during normal flow (not validation) → -15 per occurrence
      - Auth token not set after auth action → DEAL-BREAKER (instant 0)
      - API contract mismatch (wrong fields, wrong status) → -10 per occurrence

    manifest_penalty:
      - missing pages → -10 per missing page
      - 0% coverage → automatic FAIL

    experience_factor (INFORMATIONAL — included in report for human review, does NOT affect score):
      - navigator satisfaction and "would recommend" are LLM-fabricated subjective ratings
      - using them to penalize scores creates circular LLM-judging-LLM dependency
      - included in gate report for morning review, not in PASS/FAIL calculation

  CHECK ALL (must ALL pass):
    □ pb_score >= rubric_threshold.pb (default 98)
    □ consumer_score >= rubric_threshold.consumer (default 98)
    □ verification_score == 100 (ALL verification tasks must pass)
    □ No deal-breakers triggered at HIGH confidence (UX, functional, or network)
      (medium-confidence deal-breaker evidence → -20 penalty, not instant fail)
    □ No API 500 errors during normal user flow
    □ Auth flow integrity verified (token set, persists, sent on protected requests)
    □ manifest coverage = 100% (all pages visited)
    □ persona-validator level == EXEMPLARY
    □ ux-tester score >= 98

  ALL pass → GATE PASS for this persona
  ANY fail → GATE FAIL with specific reasons + categorized action items ([WIRING], [FRONTEND], [BACKEND], [AUTH])

ALL personas pass → GATE PASS
ANY persona fails → GATE FAIL + targeted feedback
```

---

### 2. Failure Routing

When the gate fails, SUDD generates **targeted, actionable feedback** from the per-criterion report.

#### Failure Report Format (appended to log.md)

```markdown
## Gate: FAILED

### Persona: End User (Sarah Chen)

**PB Criteria: 8/12 passed (67%) — FAIL (threshold: 98%)**

  Page /register:
    ✓ forms.labels_visible — PASS (both scorers agree)
    ✗ forms.required_marked — FAIL (both scorers agree)
      Evidence: No asterisks or required indicators on any field
      Action: Add required field indicators (asterisk + aria-required)
    ✗ forms.error_near_field — FAIL (text: UNKNOWN, visual: FAIL)
      Evidence: Error banner at page top, ~300px from fields
      Discrepancy: Text scorer couldn't determine position. Visual is definitive.
      Action: Move validation errors to inline position below each field
    ✓ forms.submit_visible — PASS

  Page /dashboard:
    ✓ All criteria passed

**Consumer Criteria: 4/6 passed (67%) — FAIL (threshold: 98%)**

    ✗ confirm_password field missing
      Code expects 4 fields, only 3 visible
      Action: Add confirm_password field to registration form
    ✗ Error message text mismatch
      Expected (from code): "Email is required"
      Actual (from navigation): "Please fill in all fields"
      Action: Ensure field-specific errors fire, not just generic form error

**Manifest Coverage: 100%** — all pages visited

**Network Verification: 1 issue found**

    ⚠️ GET /api/user/me → 200 after signup, but response missing `created_at` field
      Expected (from codeintel): {name, email, created_at}
      Actual (from network_log): {name, email}
      Action: Backend UserController.getProfile should include created_at in response

**Verification Tasks: 3/4 passed — FAIL (threshold: 100%)**

    ✓ V1 (data_persistence): Name survived page refresh
    ✓ V3 (auth_persistence): Session survived page refresh
    ✓ V4 (auth_boundary): /dashboard blocked when unauthenticated
    ✗ V2 (cross_page_consistency): Settings page shows email but NOT name
      Evidence: After signup with name='Jordan Rivera', /settings shows email='jordan@example.com' but name field is empty
      Action: Fix GET /api/user/settings endpoint to include name field, or fix frontend to read from correct endpoint

**Navigator Experience: 7/10** — "error handling could be more helpful"

### Action Items for Coder (priority order):
1. [WIRING] Fix settings page — name not displayed (API response missing name field, or frontend not reading it)
2. [FRONTEND] Add confirm_password field to RegisterPage.tsx
3. [BACKEND] Add created_at to GET /api/user/me response
4. [FRONTEND] Fix validation to show field-specific errors (not generic message)
5. [FRONTEND] Move error messages to inline (below triggering field)
6. [FRONTEND] Add required field indicators (asterisk on labels)

### Do NOT Touch:
- /dashboard — all criteria passed
- POST /api/auth/register — working correctly (201, sets session cookie)

### Codeintel Accuracy Check:
If any failure references a codeintel_ref, the developer should verify
the codeintel extraction is correct before implementing the fix:
  - codeintel says: registration.elements.forms[0].fields has 4 fields
  - If the code actually has 3 fields (codeintel was wrong): re-run code-analyzer
  - If the code actually has 4 fields (codeintel was right): fix the UI
Report codeintel errors to improve the code-analyzer for next run.
```

---

### 3. Consumer Rubric Format

Written by SUDD's code-analyzer agent, informed by specs.md + design.md + actual code.

```markdown
# Consumer Rubric: green_signup_01

Generated from: specs.md, design.md, codebase analysis
Change scope: Registration flow + post-signup dashboard

## Registration Page
Identified by: page with signup/registration form

### Must Pass
- Signup form has name, email, password, confirm_password fields
- Password strength indicator appears when password field is focused
- Email format validation happens inline (not only on submit)
- Error messages match code-defined text (see codeintel.json)
- Successful submission redirects to /dashboard within 2 seconds

### Should Pass
- Form remembers entered data on validation error
- Password requirements shown proactively (not only on error)
- Tab order follows visual layout top-to-bottom

### Deal-Breakers
- Form submits with empty required fields and no error
- Signup succeeds but user data is lost

## Dashboard (after signup)
Identified by: page shown after successful login/signup

### Must Pass
- Shows "Welcome, {name}" with the name submitted during signup
- Dashboard has onboarding content (not completely empty)
- Navigation menu visible with links to settings

### Deal-Breakers
- Dashboard is blank after signup
- Displayed name doesn't match submitted name
```

---

### 4. File Structure

```
sudd/changes/active/{id}/
├── proposal.md
├── specs.md
├── design.md
├── tasks.md
├── fe_codeintel.json          ← NEW: frontend code analysis (intermediate)
├── be_codeintel.json          ← NEW: backend code analysis (intermediate)
├── codeintel.json             ← NEW: merged + cross-validated ground truth
├── manifest.json              ← NEW: pages + auth_flow + verification tasks
├── rubric.md                  ← NEW: consumer criteria (adversarially hardened)
├── rubric-drafts/             ← NEW: rubric revision history (debug)
│   ├── rubric-draft-v1.md
│   ├── adversary-critique-v1.md
│   ├── rubric-draft-v2.md
│   └── adversary-critique-v2.md
├── personas/
│   ├── end-user.md
│   └── admin-user.md
├── browser-reports/            ← NEW: persona-browser-agent output
│   ├── end-user.json
│   └── admin-user.json
├── screenshots/
│   └── gate/
│       ├── end-user/
│       │   ├── 01-registration.png
│       │   ├── 02-registration-error.png
│       │   └── 03-dashboard.png
│       └── admin-user/
│           └── ...
├── recordings/                 ← NEW: session videos
│   ├── end-user.webm
│   └── admin-user.webm
└── log.md
```

---

### 5. Task-Level Testing (during /sudd:apply)

Same pattern as gate, narrower scope:

```
persona-test \
  --persona "changes/{id}/tasks/{task-id}/micro-persona.md" \
  --url {dev_server_url} \
  --objectives "{from micro-persona}" \
  --manifest "changes/{id}/manifest.json" \
  --rubric "changes/{id}/rubric.md" \
  --codeintel "changes/{id}/codeintel.json" \
  --scope task \
  --task-id {task-id} \
  --screenshots-dir "changes/{id}/screenshots/{task-id}/" \
  --output "changes/{id}/tasks/{task-id}/browser-report.json"
```

Task-level tests:
- Use `--scope task` (navigator focuses on pages relevant to this task only)
- Same rubric/codeintel but only criteria for the task's pages apply
- Faster (fewer pages, fewer screenshots)
- Feed into micro-persona validation as evidence

---

### 6. Configuration

#### sudd.yaml additions

```yaml
browser_use:
  enabled: true
  run_on:
    task: true
    gate: true
  config_path: "persona-browser-agent/config.yaml"
  capture_network: true       # Navigator captures HTTP requests/responses via HAR
  navigator:
    max_steps: 50             # prevent infinite loops (browser-use max_steps param)
    timeout_seconds: 120      # hard timeout per persona session
    app_domains: []           # allowlist for HAR filtering (empty = auto-detect from url)
  rubric_threshold:
    pb: 98                    # minimum PB criteria pass rate (%)
    consumer: 98              # minimum consumer criteria pass rate (%)
    verification: 100         # ALL verification tasks must pass (data persistence, auth)
  scoring:
    must_pass_weight: 1.0     # "Must Pass" failure = full weight
    should_pass_weight: 0.5   # "Should Pass" failure = half weight
    manifest_missing_penalty: 10  # -10 per missing page
    # experience_factor: INFORMATIONAL ONLY (not a penalty — LLM-fabricated, for human review)
    network_error_penalty: 15     # -15 per API error during normal flow
    verification_fail_penalty: 20 # -20 per failed verification task
  deal_breaker_policy: "instant_fail"
  # Deal-breakers include: silent API failures, auth handover failures,
  # data loss between pages, 500 errors during normal user flow
```

---

### 7. Error Handling

| Scenario | Who Detects | Response |
|----------|-------------|----------|
| persona-browser-agent not installed | gate pre-flight | Technical-checks-only (CDP/Playwright-over-CDP), cap score at 90 |
| API key missing | persona-browser-agent | `status: SKIP`, technical-checks-only, cap at 90 |
| Dev server not running | persona-browser-agent | `status: ERROR`, SUDD starts server, retry |
| Browser timeout | persona-browser-agent | `status: ERROR`, -5 penalty, use partial results |
| Text scorer fails | persona-browser-agent (internal) | Visual-only + network verification, reduced confidence flag |
| Visual scorer fails | persona-browser-agent (internal) | Text-only + network verification, reduced confidence flag |
| Network Verifier fails | persona-browser-agent (internal) | Scorers still produce results, TASK COMPLETION from text only |
| Score Reconciler fails | persona-browser-agent (internal) | Pass through raw scores + network verification without reconciliation |
| Report JSON malformed | gate (JSON parse) | Technical-checks-only fallback |
| Manifest missing | gate pre-flight | FAIL — "Run code-analyzer or /sudd:plan" |
| Rubric missing | gate pre-flight | FAIL — "Run code-analyzer or /sudd:plan" |
| Codeintel missing | gate pre-flight | FAIL for UI changes — "Run code-analyzer". Codeintel is required for scoring pipeline. Non-UI changes skip codeintel entirely. |
| Navigator misses a manifest page | Score Reconciler | Flags as MISSING, criteria NOT_EVALUATED |
| Code changed since codeintel was generated | gate (git check) | Re-run code-analyzer before browser testing |
| HAR recording fails | persona-browser-agent (Navigator) | Network Verifier skipped, TASK COMPLETION from text only. Fallback: Playwright-over-CDP listeners |
| API returns 500 during normal flow | Network Verifier (deterministic) | DEAL-BREAKER — instant FAIL regardless of visual/UX quality |
| Auth token not set after login/signup | Network Verifier (deterministic) | FAIL on all auth-related criteria, flag as auth handover failure |
| Verification task fails (data not persisted) | Score Reconciler (verification tasks) | FAIL with specific evidence of what data was lost |
| Backend not running (all API calls fail) | Network Verifier (deterministic) | FAIL — "Backend unreachable, all API calls returned errors" |

#### Pre-flight Checklist (gate Step 2b, before calling persona-browser-agent)

```
1. [ ] persona-browser-agent installed?
2. [ ] API key set? ($OPENROUTER_API_KEY)
3. [ ] Dev server running?
4. [ ] manifest.json exists?
5. [ ] rubric.md exists?
6. [ ] codeintel.json exists?
7. [ ] codeintel generated from current commit? (compare git SHA)
8. [ ] At least one persona file exists?
9. [ ] Screenshots directory writable?

If 1-2 fail: technical-checks-only (CDP/Playwright-over-CDP), cap at 90
If 3 fails: start dev server, wait, retry
If 4-5 fail: FAIL — "Run code-analyzer"
If 6 fails: proceed without codeintel (degraded accuracy)
If 7 fails: re-run code-analyzer
If 8 fails: FAIL — "No personas"
If 9 fails: continue without screenshots (non-blocking)
```

---

## Pipeline Execution

### Happy Path

```
code-analyzer pipeline (5-20s, reads frontend + backend + adversarial rubric review)
       │
       │ manifest + rubric (hardened) + codeintel
       ▼
Navigator (30-90s, browser interaction + auth flow + verification tasks)
       │
       │ observations + screenshots + network_log + auth_flow_verification + experience
       │
       ├──────────────────────┬──────────────────────┐
       ▼                      ▼                      ▼
Text Scorer          Visual Scorer          Network Verifier
(GLM 5-turbo,        (Gemini 3 Flash,       (deterministic Python,
 3-8s, verifies       5-8s, images)          <1s, rule-based
 text + network)                             API/auth matching)
       │                      │                      │
       └──────────┬───────────┴──────────────────────┘
                  ▼              ALL THREE RUN IN PARALLEL
       Score Reconciler (Sonnet, 5-10s)
       Lighter than old Reviewer — network verification is pre-computed
              │
              ▼
       JSON report → SUDD
```

**Total: ~43-120 seconds per persona** (including code-analyzer, which runs once for all personas). Navigator takes the bulk of time due to browser interaction + auth flow + verification tasks. Score Reconciler is faster than the old monolithic Reviewer because network verification is pre-computed deterministically.

### Degraded Modes

```
Text scorer fails → visual-only + network verification + reduced confidence flag
                    (TASK COMPLETION criteria partially evaluated via network verifier)
Visual scorer fails → text-only + network verification + reduced confidence flag
Both scorers fail → network verification + navigator experience only
                    + "manual review recommended"
Network Verifier fails → scorers still produce results, TASK COMPLETION from text only
Score Reconciler fails → raw scores + network verification without reconciliation
Navigator fails → ERROR status, no scores
Network capture fails → Network Verifier skipped,
                        TASK COMPLETION criteria evaluated from text only (reduced confidence)
Backend not running → all API calls fail,
                      Network Verifier flags as DEAL-BREAKER
```

---

## Cost Estimate

| Agent | Model | Cost per call |
|-------|-------|---------------|
| Code Analyzer FE (SUDD) | Haiku | ~$0.005-0.02 (reads frontend code) |
| Code Analyzer BE (SUDD) | Haiku | ~$0.005-0.02 (reads backend code) |
| Code Analyzer Reviewer (SUDD) | Sonnet | ~$0.03-0.10 (merges, cross-validates, generates) |
| Rubric Adversary × 2 (SUDD) | Haiku | ~$0.01-0.03 (2 critique iterations) |
| Code Analyzer Reviewer revisions × 2 | Sonnet | ~$0.04-0.12 (2 rubric revisions) |
| Navigator | Gemini Flash | ~$0.02-0.08 (longer sessions with auth flow + verification) |
| Text Scorer | GLM 5-turbo | ~$0.005-0.02 (text + network verification) |
| Visual Scorer | Gemini 3 Flash | ~$0.02-0.08 (multimodal, screenshots) |
| Network Verifier | None (Python) | $0.00 (deterministic, no LLM) |
| Score Reconciler | Sonnet | ~$0.04-0.12 (lighter — no raw network_log, no full codeintel) |
| **Total per persona** | | **~$0.09-0.30** |
| **+ code-analyzer pipeline (once)** | | **~$0.09-0.29** |

| Scenario | Personas | Cost | Time |
|----------|----------|------|------|
| Task-level (1 persona) | 1 | ~$0.18-0.59 | ~43-120s |
| Gate with 3 personas (parallel) | 3 | ~$0.36-1.19 | ~43-120s (parallel) |
| Gate with 5 personas (parallel) | 5 | ~$0.54-1.79 | ~43-120s (parallel) |
| Gate retry (4 retries avg, 3 personas) | 12 | ~$1.2-4.2 | ~3-7 min total |

**Note**: GLM 5-turbo and Gemini 3 Flash are significantly cheaper than Haiku/Sonnet. The Network Verifier being deterministic saves one LLM call per persona. The adversarial rubric review adds ~$0.05-0.15 to the code-analyzer pipeline but runs only once per gate (amortized across all personas).

### Model Capability Requirements

If specific model IDs become unavailable at implementation time, substitute any model meeting these requirements:

| Agent | Current Model | Required Capabilities | Budget |
|-------|--------------|----------------------|--------|
| Navigator | Gemini Flash | Multimodal (vision), browser-use compatible, function calling | <$0.08/call |
| Text Scorer | GLM 5-turbo | Text-only, structured JSON output, >8K context | <$0.02/call |
| Visual Scorer | Gemini 3 Flash | Multimodal (image input), structured JSON output, >8K context | <$0.08/call |
| Network Verifier | None (Python) | N/A — deterministic, no LLM | $0.00 |
| Score Reconciler | Sonnet | Strong reasoning, structured JSON output, >32K context | <$0.15/call |
| Code Analyzer FE/BE | Haiku | Text-only, code comprehension, structured JSON output | <$0.02/call |
| Code Analyzer Reviewer | Sonnet | Reasoning for cross-validation, structured JSON, >32K context | <$0.10/call |
| Rubric Adversary | Haiku | Text-only, critique/analysis, structured output | <$0.02/call |

---

## CLI Interface

```
persona-test \
  --persona persona.md \
  --url http://localhost:3000 \
  --objectives "complete signup flow" \
  --manifest manifest.json \           # NEW: pages + tasks
  --rubric rubric.md \                 # consumer criteria
  --codeintel codeintel.json \         # NEW: code-derived ground truth
  --scope gate \
  --task-id T03 \
  --screenshots-dir ./screenshots \
  --record-video ./recordings \
  --config config.yaml \
  --output report.json
```

New flags vs current:
- `--manifest` — pages to visit, tasks to accomplish, auth flow, verification tasks (optional, if omitted navigator explores freely)
- `--rubric` — consumer criteria (optional, if omitted only PB rubric applied)
- `--codeintel` — code-derived ground truth for scorers including API contracts and auth config (optional, if omitted scorers work without verification)
- `--capture-network` — enable network request/response capture during navigation (default: true if codeintel provided)
- `--max-steps` — navigator step limit to prevent infinite loops (default: 50)
- `--timeout` — hard timeout in seconds per session (default: 120)
- `--app-domains` — allowlist for HAR filtering, comma-separated (default: auto-detect from --url)
- All existing flags unchanged

---

## Separation of Concerns

```
persona-browser-agent's job:          SUDD's job:
────────────────────────               ──────────
Navigate as personas                  Define personas
Capture network activity (HAR)        Write consumer rubric (adversarially hardened)
Verify network vs codeintel           Extract code intelligence (FE + BE + cross-validate)
  (deterministic Network Verifier)    Generate manifest (pages + auth flow + verifications)
Apply PB rubric (universal UX+func)   Generate codeintel (API contracts, auth, data flows)
Apply consumer rubric (injected)      Adversarial rubric review (2 iterations)
Execute verification tasks            Apply scoring formula
Triangulate (text + visual + net)     Set thresholds (98/100)
Reconcile scores (Score Reconciler)   Make PASS/FAIL decisions
Report per-criterion evidence         Route failures to developers
Provide confidence levels             Run technical checks (CDP/Playwright-over-CDP)
Save screenshots + video              Be the orchestrator
Be a reusable, sellable service
```

---

## Implementation Phases

### Phase 1: PB Feature Rubrics + Formats + Test Fixtures -- COMPLETED (2026-03-30)

**Repo**: persona-browser-agent
- Define feature-based PB rubric criteria (forms, navigation, CTA, data display, error states, baseline, **task completion**)
- Define consumer rubric format spec (Must Pass / Should Pass / Deal-Breakers per page)
- Define codeintel.json schema (**including api_endpoints, auth, data_flows sections**)
- Define manifest.json schema (**including auth_flow, verification_tasks sections**)
- Define network_log schema (per-page HTTP request/response capture format)
- **Create hand-written reference test fixtures** for Phase 2-4 development:
  - `fixtures/sample_codeintel.json` — realistic codeintel for a signup+dashboard app
  - `fixtures/sample_manifest.json` — matching manifest with auth_flow + verification_tasks
  - `fixtures/sample_rubric.md` — matching consumer rubric
  - These decouple Phases 2-4 (PB pipeline) from Phase 5 (code-analyzer) — PB development doesn't block on SUDD code-analyzer being ready
- **No code changes** — rubric content, format documentation, and test fixtures only
- **Effort**: Medium

### Phase 2: Navigator (observation-only, no scoring, with network capture) -- COMPLETED (2026-03-30)

**Repo**: persona-browser-agent
- **Migrate from `Browser` to `BrowserSession` + `BrowserProfile`** (browser-use v0.12+ CDP-based API)
- Rewrite `prompts.py` — navigator observes only, no scoring language
- Add `--manifest` CLI flag — navigator uses manifest for page navigation
- **Enable HAR recording** via `BrowserProfile(record_har_path=..., record_har_content='embed')` — captures all network requests/responses automatically during navigation. No custom interception code needed.
- **Add `har_parser.py`** — transforms HAR file into v3 `network_log[]` format (method, URL, status, timing, headers, auth cookies). Includes HAR-step correlation algorithm (timestamp-window matching + app-domain filtering).
- **Add `output_parser.py`** — deterministic transform from `AgentHistoryList` → v3 structured JSON. Implements page grouping algorithm: URL-based primary grouping, manifest matching by `how_to_reach` hints, multi-visit suffixes, SPA fallback (content-change detection from `model_thoughts()`).
- **Add auth_flow handling** — navigator follows manifest.auth_flow sequence (pre-auth → auth action → post-auth → verify persistence → verify logout)
- **Add verification task execution** — navigator runs manifest.verification_tasks after main flow (refresh pages, check data consistency)
- Restructure output from `agent_result` string to structured `pages[]` + `network_log` + `auth_flow_verification` + `experience`
- Add `version` field and backward-compat `agent_result` string (from `AgentHistoryList.final_result()`) during transition
- Add `--capture-network`, `--max-steps`, `--timeout`, `--app-domains` CLI flags
- **Configure safety limits**: `max_steps=50`, `timeout_seconds=120` (defaults, overridable). Navigator returns `status: PARTIAL` if limits hit.
- Fix screenshot saving (leverage `AgentHistoryList.screenshot_paths()` — browser-use controls screenshot timing per step lifecycle, no manual timing needed)
- Enable video recording pass-through via `BrowserProfile`
- **Effort**: Medium (reduced from Medium-Large — HAR recording and structured history eliminate custom interception work)

### Phase 3: Text Scorer + Visual Scorer + Network Verifier -- COMPLETED (2026-03-30)

**Repo**: persona-browser-agent
- New module: `persona_browser/text_scorer.py` — **GLM 5-turbo**, text-only scoring with codeintel verification
  - **Receives network_log** in addition to text observations
  - **Verifies API calls against codeintel.api_endpoints** (correct endpoint, expected status, auth headers present)
  - **Scores TASK COMPLETION criteria** using network_log + codeintel cross-referencing
- New module: `persona_browser/visual_scorer.py` — **Gemini 3 Flash** (multimodal), scoring with filtered codeintel
  - Receives **filtered codeintel** (design_tokens, elements, accessibility only — no API/auth/data_flow fields)
  - Does NOT receive network_log (visual-only assessment)
  - Can verify data consistency visually (does displayed name match submitted name?)
- New module: `persona_browser/network_verifier.py` — **deterministic Python** (no LLM)
  - Cross-references HAR-derived network_log against codeintel.api_endpoints
  - Checks auth flow integrity (token set, sent, persists)
  - Produces structured pass/fail per endpoint
  - Runs in parallel with scorers (~<1s execution)
- Add `--rubric` and `--codeintel` CLI flags
- Feature detection logic in visual scorer (detect forms, nav, CTA, etc. from screenshot)
- All three (Text Scorer, Visual Scorer, Network Verifier) run in parallel after navigator completes
- **Effort**: Large

### Phase 4: Score Reconciler + Final Pipeline -- COMPLETED (2026-03-31)

**Repo**: persona-browser-agent
- New module: `persona_browser/score_reconciler.py` — **Sonnet**, reconciliation + discrepancy analysis + manifest coverage
  - Receives text scores, visual scores, and **pre-computed** network_verification report
  - Does NOT receive raw network_log or full codeintel (lighter prompt, focused on reconciliation)
- **Add verification task evaluation** — check each manifest.verification_task result
- Wire full pipeline: navigator → (text scorer + visual scorer + network verifier) parallel → score reconciler → JSON output
- Implement graceful degradation for each failure mode (including network capture failure, scorer failure, verifier failure)
- **Effort**: Medium (reduced from Medium-Large — network verification is now deterministic Python in Phase 3)

### Phase 5: Code-Analyzer Pipeline (SUDD) — 3 Agents

**Repo**: sudd2

**5a: code-analyzer-fe**
- New agent: `sudd/agents/code-analyzer-fe.md`
- Model: Haiku (cheap, focused)
- Reads frontend code only: routes, components, validation, errors, design tokens, accessibility, frontend API call sites
- Output: `fe_codeintel.json`
- **Effort**: Medium

**5b: code-analyzer-be**
- New agent: `sudd/agents/code-analyzer-be.md`
- Model: Haiku (cheap, focused)
- Reads backend code only: API endpoints, middleware chains, auth config, request/response schemas, backend validation, data writes/reads
- Output: `be_codeintel.json`
- **Effort**: Medium
- **5a and 5b can be built and tested independently** — FE reads React/Vue/Svelte, BE reads Express/FastAPI/Django. Different skills, different test cases.

**5c: code-analyzer-reviewer**
- New agent: `sudd/agents/code-analyzer-reviewer.md`
- Model: Sonnet (reasoning for cross-validation)
- Merges fe_codeintel + be_codeintel, cross-validates FE↔BE wiring (endpoint URLs, field names, status codes, auth requirements)
- Traces data flows from write endpoints → DB → read endpoints
- Auto-generates verification tasks from data flows
- Generates manifest (pages + auth_flow + verification_tasks), **draft rubric** (consumer criteria), codeintel (merged + validated)
- Flags uncertainties with `"confidence": "low"` — scorers treat low-confidence entries as advisory
- **Effort**: Medium-Large (cross-validation and data flow tracing are the complex parts)

**5d: rubric-adversary (adversarial review — 2 iterations)**
- New agent: `sudd/agents/rubric-adversary.md`
- Model: Haiku (cheap, critique-focused)
- Purpose: Strengthen the auto-generated consumer rubric by adversarially reviewing it against the project's vision, task/feature objectives, and deployed behavior
- **Iteration flow**:
  1. code-analyzer-reviewer generates **draft rubric.md**
  2. rubric-adversary critiques the draft against specs.md, design.md, and task objectives:
     - Are criteria specific enough to catch real bugs? (not vague "should work well")
     - Do criteria cover all features in the objectives? (completeness)
     - Are any criteria impossible to verify from browser observation? (testability)
     - Do Must Pass / Should Pass / Deal-Breaker classifications match the feature's importance?
     - Are there contradictions between criteria?
  3. code-analyzer-reviewer revises rubric based on critique → **rubric v2**
  4. rubric-adversary critiques v2 (focus: did the revision address all issues? any new gaps?)
  5. code-analyzer-reviewer finalizes → **rubric.md** (final, hardened)
- **Why 2 iterations**: First pass catches obvious gaps (missing criteria, vague wording, wrong priorities). Second pass catches subtler issues revealed by the revisions (over-correction, new contradictions, testability concerns). Diminishing returns after 2.
- **Effort**: Small (Haiku critiques are fast and cheap)
- **Cost**: ~$0.05-0.15 (2× Haiku critique + 2× Sonnet revision)

Total cost per pipeline run: ~$0.09-0.29 (2× Haiku FE/BE + 3× Sonnet reviewer + 2× Haiku adversary). Runs once per gate.

### Phase 6: SUDD Gate Integration

**Repo**: sudd2
- Update `gate.md`: add Step 2a (code-analyzer + adversarial rubric review), rewrite Step 2b-2e
- Update `persona-validator.md`: remove browser launching, add report reading (including network_verification and verification_tasks results)
- Update `ux-tester.md`: remove PB calling, keep technical checks (CDP/Playwright-over-CDP), add report reading
- Add scoring formula to gate aggregation (binary → numerical, weighting, penalties, **network error penalties, verification task penalties**)
- Add failure routing format (per-criterion action items, **including API/auth/wiring fix instructions**)
- Update `sudd.yaml` schema with scoring/threshold config (**including verification threshold, network_error_penalty, verification_fail_penalty**)
- Implement lightweight circuit breakers early: cost ceiling (`max_cost_per_change`) and identical-failure detection (3 same → STUCK) — don't wait for full Risk 4 mitigation
- **Effort**: Medium-Large

### Phase 7: Task-Level Integration

**Repo**: sudd2
- Wire persona-browser-agent into `/sudd:apply` per-task flow
- Code-analyzer runs once, shared across tasks
- `--scope task` limits navigator to task-relevant pages (but still runs auth flow if task touches auth-protected pages)
- **Effort**: Small

---

## Open Questions

### Resolved (from v2)

1. ~~Consumer rubric format~~ → Markdown: Must Pass / Should Pass / Deal-Breakers per page
2. ~~Who calls persona-browser-agent~~ → Gate calls once per persona, agents read report
3. ~~Where consumer rubric lives~~ → `changes/{id}/rubric.md`
4. ~~Text scorer independence~~ → Genuine independence via separate information sources (text vs screenshots)
5. ~~Page-type classification risk~~ → Feature-based detection, no classification step
6. ~~Score aggregation~~ → SUDD owns the formula, defined in sudd.yaml
7. ~~Backward compatibility~~ → `version` field + `agent_result` string during v1.x transition
8. ~~Missing pages~~ → Manifest coverage check, MISSING flag for unvisited pages
9. ~~URL matching for SPAs~~ → Pages identified by purpose/content, not URL

### Resolved (from v3 review)

10. ~~**Code-analyzer depth**~~ → Split into 3 agents: code-analyzer-fe (Haiku, frontend patterns), code-analyzer-be (Haiku, backend patterns), code-analyzer-reviewer (Sonnet, cross-validation + merge). Each agent has a focused scope. Start with React/Vue + Express/FastAPI/Django pattern matching, extend as needed.

11. ~~**Code-analyzer as single agent**~~ → Split into FE + BE + Reviewer pipeline. FE and BE run in parallel on Haiku. Reviewer merges on Sonnet. Total cost ~$0.05-0.12.

12. ~~**Deal-breaker false positives**~~ → Deal-breakers only trigger at confidence "high." Medium-confidence evidence produces -20 penalty, not instant fail. Prevents false positives from codeintel extraction errors.

13. ~~**TASK COMPLETION on static sites**~~ → Conditional activation: criteria only apply when network_log contains API calls AND codeintel includes api_endpoints. Static sites skip these criteria entirely.

14. ~~**Data flow verification**~~ → API-level verification via verification tasks auto-generated from data flows. No direct DB verification — API round-trips test what the user actually sees. code-analyzer-reviewer traces write→DB→read chains and generates VERIFY tasks.

### Still Open

15. **Discrepancy threshold**: For aggregate page scores, what delta triggers Score Reconciler investigation? 15 points proposed. Needs empirical tuning.

16. **Video utility**: Video recordings are large. Are they worth storing? Proposal: screenshots as primary evidence, video as optional opt-in for debugging failed gates.

17. **Parallel persona concurrency**: How many simultaneous browser sessions should be allowed? Resource constraints may apply on CI. Default: 3 parallel.

18. **Score Reconciler re-visit capability**: The Score Reconciler can request the navigator to re-visit a specific page on big discrepancies. How is this implemented? Separate browser-use call for just that page? Or is this a v2 enhancement?

19. **codeintel freshness**: If the coder changes code between gate runs (during retries), the code-analyzer must re-run. Should it diff against the previous codeintel to show what changed? The code-analyzer-reviewer could output a `codeintel_diff.md` showing what FE↔BE mismatches were resolved since last run.

20. **~~Network capture mechanism~~** — **RESOLVED (2026-03-30)**: browser-use v0.12+ uses CDP internally and provides built-in HAR recording via `BrowserProfile(record_har_path=...)`. HAR captures all network data (method, URL, status, headers, timing, bodies). No proxy or custom hooks needed. Additionally, Playwright can connect to the same Chrome instance via CDP as a fallback for any Playwright-specific needs. See `phase-0-feasibility-and-risk-mitigations.md` for full details.

21. **Auth mechanism diversity**: The auth section of codeintel assumes session cookies or JWT. How do we handle OAuth flows (redirects to third-party), API key auth, or multi-factor auth? Proposal: start with session/JWT, flag OAuth and MFA as "requires manual test data" in the manifest.

22. **codeintel error feedback loop**: When a gate fails due to a codeintel extraction error (not a real bug), how does the developer report this so the code-analyzer improves? Proposal: developer adds a note to log.md: "codeintel error: field X was wrong." code-analyzer-reviewer reads previous codeintel errors on re-run and adjusts extraction accordingly.

---

## Decision Needed

Approve this architecture so we can begin implementation, starting with Phase 1 (PB feature rubrics + format definitions, now including TASK COMPLETION criteria, codeintel backend schema, manifest auth_flow schema, and reference codeintel/manifest/rubric test fixtures for Phase 2-4 development).
