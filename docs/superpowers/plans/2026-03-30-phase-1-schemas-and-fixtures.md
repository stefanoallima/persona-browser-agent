# Phase 1: PB Rubrics, Schemas & Test Fixtures

> **Status: COMPLETED** (2026-03-30). Schemas in `schemas/`, fixtures in `fixtures/`, rubric in `rubrics/`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define all JSON schemas, the PB feature rubric, consumer rubric format, and hand-written test fixtures so Phase 2-4 development can proceed without blocking on SUDD code-analyzer.

**Architecture:** Extract the already-designed schemas from `architecture-proposal-v3.md` into standalone files. Create realistic test fixtures matching the `poc/test_app/` signup+dashboard app. No runtime code — documentation and data files only.

**Tech Stack:** JSON, Markdown, JSON Schema (for validation in later phases)

**Key references:**
- `docs/architecture-proposal-v3.md` — all schemas are defined here (codeintel.json format at line ~1216, manifest.json at ~1226, navigator output at ~271, scorer output at ~424/~530, reconciler output at ~732, consumer rubric at ~1607, network_log at ~309)
- `poc/test_app/server.js` — the app the fixtures should match
- `poc/FINDINGS.md` — PoC results informing the network_log schema

---

## File Structure

```
persona-browser-agent/
├── schemas/                          # JSON schema definitions
│   ├── codeintel.schema.json         # codeintel.json structure
│   ├── manifest.schema.json          # manifest.json structure
│   ├── navigator-output.schema.json  # Navigator output (pages, network_log, experience)
│   ├── network-log-entry.schema.json # Single network_log[] entry
│   ├── text-scorer-output.schema.json    # Text scorer per-page output
│   ├── visual-scorer-output.schema.json  # Visual scorer per-page output
│   ├── network-verifier-output.schema.json # Network verifier output
│   └── final-report.schema.json      # Score Reconciler final report
├── rubrics/
│   └── pb-feature-rubric.md          # PB feature-based rubric (forms, nav, CTA, etc.)
├── fixtures/                         # Hand-written reference fixtures
│   ├── sample_codeintel.json         # Realistic codeintel for poc/test_app
│   ├── sample_manifest.json          # Matching manifest with auth_flow + verification
│   ├── sample_rubric.md              # Matching consumer rubric
│   ├── sample_navigator_output.json  # Expected navigator output for the test app
│   └── sample_network_verifier_output.json  # Expected network verifier output
└── docs/
    └── consumer-rubric-format.md     # Consumer rubric format spec for code-analyzer
```

---

## Task 1: PB Feature Rubric

**Files:**
- Create: `rubrics/pb-feature-rubric.md`

The PB rubric is already fully defined in `architecture-proposal-v3.md` lines 862-1000. Extract it into its own file with proper structure: each feature category, its criteria with stable IDs, and deal-breakers.

- [ ] **Step 1: Create the rubric file**

Extract the 7 feature categories from the architecture doc into `rubrics/pb-feature-rubric.md`. Each criterion needs a **stable ID** (used by scorers and reconciler for tracking across retries):

```markdown
# PB Feature Rubric v1.0

Feature-based rubric for persona-browser-agent scoring. Each feature category activates when the relevant UI elements are detected on a page. Criteria have stable IDs for tracking across retries and circuit-breaker detection.

## How Criteria Are Applied

The Visual Scorer detects which features are present on each page screenshot and activates the relevant criteria. A signup page with a nav bar gets both FORMS and NAVIGATION criteria. No page-type classification step.

## Criterion Result Values

- **PASS** — criterion met, with evidence
- **FAIL** — criterion not met, with evidence
- **UNKNOWN** — scorer could not assess from its information source (not a failure)

---

## FORMS

**Activates when:** form fields are visible on the page

### Labels & Inputs

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.labels_visible` | Every field has a visible label (not just placeholder text) | Visual + Text |
| `forms.required_marked` | Required fields are marked (asterisk, "required" text, or equivalent) | Visual |
| `forms.input_types_match` | Input types match content (email → email keyboard, password → masked) | Text |
| `forms.tab_order` | Tab order is logical | Text |

### Validation & Errors

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.error_on_empty_submit` | Required-field error appears on empty submit | Text |
| `forms.error_on_invalid` | Format error appears on invalid input | Text |
| `forms.error_near_field` | Error message appears NEAR the triggering field (not only at page top) | Visual |
| `forms.error_specific` | Error message is specific (not generic "Invalid input") | Text |
| `forms.error_clears` | Valid input clears previous errors | Text |
| `forms.data_preserved_on_error` | User doesn't lose entered data on error | Text |

### Submission

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.submit_visible` | Submit button is visible without scrolling | Visual |
| `forms.loading_state` | Button shows loading state during async submission | Text + Visual |
| `forms.success_confirmation` | Success confirmation is clear and immediate | Text + Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `forms.db_empty_submit` | Form submits with empty required fields and no error | high |
| `forms.db_data_lost` | Submitted data is silently lost | high |
| `forms.db_no_error_recovery` | No way to correct errors without re-entering everything | high |

---

## NAVIGATION

**Activates when:** nav elements are visible

| ID | Criterion | Scorer |
|----|-----------|--------|
| `nav.current_indicated` | Current page/section is indicated in nav | Visual |
| `nav.logo_links_home` | Logo or brand links to home | Text |
| `nav.no_dead_ends` | No dead-end pages (always a path forward or back) | Text |
| `nav.back_works` | Back button / breadcrumb works as expected | Text |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `nav.db_404` | Navigation leads to 404 or blank page | high |
| `nav.db_trapped` | User gets trapped (no way back) | high |

---

## CTA

**Activates when:** call-to-action buttons are visible

| ID | Criterion | Scorer |
|----|-----------|--------|
| `cta.prominent` | Primary CTA is the most visually prominent element | Visual |
| `cta.text_clear` | CTA text is action-oriented and clear | Visual + Text |
| `cta.destination_correct` | CTA leads to expected destination (not 404) | Text |
| `cta.no_competing` | No more than 2 competing CTAs on the same page | Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `cta.db_nonfunctional` | Primary CTA is non-functional | high |

---

## DATA_DISPLAY

**Activates when:** tables, cards, lists, or data are visible

| ID | Criterion | Scorer |
|----|-----------|--------|
| `data.above_fold` | Most important data is above the fold | Visual |
| `data.grouped_logically` | Data is grouped logically | Visual |
| `data.empty_states` | Empty states have helpful messaging (not blank) | Visual + Text |
| `data.loading_indicator` | Dynamic content loads with visible loading indicator | Text + Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `data.db_wrong` | Data is visibly wrong or contradictory | high |
| `data.db_unreachable` | Key data is unreachable | high |

---

## ERROR_STATES

**Activates when:** error messages or error pages are visible

| ID | Criterion | Scorer |
|----|-----------|--------|
| `error.plain_language` | Error message explains what happened in plain language | Text |
| `error.recovery_path` | Clear recovery path exists (link, button, or instruction) | Text + Visual |
| `error.no_jargon` | No technical jargon (no stack traces, raw error codes) | Text |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `error.db_blank` | Blank page with no guidance | high |
| `error.db_no_recovery` | Error page with no way to recover | high |

---

## BASELINE

**Activates:** ALWAYS — applies to every page

| ID | Criterion | Scorer |
|----|-----------|--------|
| `baseline.no_errors` | Page loads without visible errors | Text + Visual |
| `baseline.readable` | Text is readable (sufficient contrast, reasonable size) | Visual |
| `baseline.no_broken_assets` | No broken images or missing assets | Visual |
| `baseline.responsive` | Page is responsive to viewport (no horizontal scroll on standard widths) | Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `baseline.db_blank` | Page is blank or non-functional | high |
| `baseline.db_console_errors` | Console errors that affect user experience | Text |

---

## TASK_COMPLETION

**Activates when:** navigator's network_log contains API calls AND codeintel includes api_endpoints. Skipped for static sites with no backend.

### End-to-End Flow

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.backend_outcome` | Primary user action produces expected backend outcome (not just visual feedback) | Text + Network Verifier |
| `task.data_on_next_page` | Data submitted via forms appears correctly on subsequent pages | Text + Visual |
| `task.api_status_correct` | API calls return expected status codes (no silent 4xx/5xx) | Network Verifier |
| `task.no_network_errors` | No network errors or failed requests during normal flow | Network Verifier |

### Data Persistence

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.survives_refresh` | Page state survives browser refresh | Text |
| `task.data_consistent` | Data is consistent across all pages that display it | Text + Visual |
| `task.loading_resolves` | Empty/loading states resolve to real data within reasonable time | Text |

### Authentication & Authorization

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.auth_access` | Auth-protected pages accessible after successful auth flow | Text + Network Verifier |
| `task.auth_persists_nav` | Auth state persists across page navigations | Text + Network Verifier |
| `task.auth_persists_refresh` | Auth state survives page refresh | Text + Network Verifier |
| `task.unauth_redirect` | Unauthenticated users redirected to login | Text + Network Verifier |

### Backend-Frontend Handover

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.data_matches_api` | Frontend displays data matching backend API response | Text + Network Verifier |
| `task.error_matches_api` | Error messages match what backend actually sent | Text + Network Verifier |
| `task.loading_during_async` | Loading states appear during async operations | Text + Visual |
| `task.graceful_error_handling` | Frontend gracefully handles backend errors | Text + Visual |

### Deal-Breakers (requires HIGH confidence)

| ID | Criterion | Confidence Required |
|----|-----------|-------------------|
| `task.db_silent_fail` | Primary action silently fails (success shown but no backend effect) | high |
| `task.db_data_lost` | Data entered by user is lost or corrupted between pages | high |
| `task.db_wrong_auth` | Authenticated user gets 401/403 on accessible page | high |
| `task.db_no_result` | User completes flow but cannot verify/access result | high |
| `task.db_500` | API returns 500 during normal user flow | high |
| `task.db_success_but_fail` | Frontend shows success but network log reveals failure | high |

**Deal-breaker confidence rule:** At confidence "high" → instant FAIL. At confidence "medium" → PENALTY (-20 points), not instant FAIL. This prevents false positives from codeintel extraction errors.
```

Write this content to `rubrics/pb-feature-rubric.md`.

- [ ] **Step 2: Commit**

```bash
git add rubrics/pb-feature-rubric.md
git commit -m "feat: PB feature rubric v1.0 with stable criterion IDs"
```

---

## Task 2: JSON Schemas — codeintel, manifest, network_log

**Files:**
- Create: `schemas/codeintel.schema.json`
- Create: `schemas/manifest.schema.json`
- Create: `schemas/network-log-entry.schema.json`

These are JSON Schema files that define the structure of the three input artifacts that SUDD provides to persona-browser-agent. They are extracted from the examples in `architecture-proposal-v3.md`.

- [ ] **Step 1: Create codeintel.schema.json**

Define the JSON Schema for `codeintel.json` based on the format at architecture-proposal-v3.md lines 1216-1215. The schema must validate documents with:
- `version` (string)
- `generated_from` (string, git SHA)
- `generated_at` (string, ISO datetime)
- `pages[]` — array of page objects, each with: `id`, `routes[]`, `component`, `purpose`, `elements` (forms with fields, submit_button, error_messages, on_success, api_call; navigation with links), `design_tokens`, `accessibility`
- `api_endpoints[]` — array with: `method`, `path`, `source_file`, `auth_required`, `middleware[]`, `request_body`, `responses` (keyed by status code, each with body, side_effects, sets_auth, when)
- `auth` — object with: `mechanism`, `cookie_name`/`token_name`, `cookie_attributes`, `session_store`, `login_endpoint`, `register_endpoint`, `logout_endpoint`, `refresh_mechanism`, `protected_routes` (frontend[], backend[]), `redirect_on_unauth`
- `data_flows[]` — array with: `trigger`, `writes_to`, `then_readable_from[]`, `verification`

Use JSON Schema draft-07. Required fields: `version`, `pages`, `api_endpoints`. Everything else optional (codeintel may not find auth or data flows for every project).

Write to `schemas/codeintel.schema.json`.

- [ ] **Step 2: Create manifest.schema.json**

Define the JSON Schema for `manifest.json` based on architecture-proposal-v3.md lines 1226-1300. Structure:
- `pages[]` — array with: `id` (required), `purpose`, `how_to_reach`, `expected_features[]`, `auth_required` (boolean), `expected_data[]`
- `auth_flow` (optional) — object with: `pre_auth_pages[]`, `auth_action` (string), `post_auth_pages[]`, `verify_auth_persistence` (boolean), `verify_logout` (boolean), `unauthenticated_behavior` (expected, test)
- `tasks[]` — array of strings
- `verification_tasks[]` — array with: `id`, `type` (enum: data_persistence, cross_page_consistency, auth_persistence, auth_boundary), `description`, `check`, `derived_from`

Write to `schemas/manifest.schema.json`.

- [ ] **Step 3: Create network-log-entry.schema.json**

Define the JSON Schema for a single `network_log[]` entry based on architecture-proposal-v3.md lines 309-320 and PoC-2 findings. Structure:
- `method` (string, required) — HTTP method
- `url` (string, required) — request URL path
- `status` (integer, required) — HTTP status code
- `timing_ms` (number) — request duration
- `trigger` (string) — which navigator step triggered this request
- `request_content_type` (string)
- `request_body` (string) — for POST/PUT requests
- `response_summary` (string) — truncated response body
- `set_cookie` (string) — if Set-Cookie header present (Note: may not be available for httpOnly cookies via HAR — see PoC-2 findings)
- `request_headers_note` (string) — notable request headers

Write to `schemas/network-log-entry.schema.json`.

- [ ] **Step 4: Commit**

```bash
git add schemas/
git commit -m "feat: JSON schemas for codeintel, manifest, and network_log"
```

---

## Task 3: JSON Schemas — scorer outputs and final report

**Files:**
- Create: `schemas/text-scorer-output.schema.json`
- Create: `schemas/visual-scorer-output.schema.json`
- Create: `schemas/network-verifier-output.schema.json`
- Create: `schemas/navigator-output.schema.json`
- Create: `schemas/final-report.schema.json`

- [ ] **Step 1: Create text-scorer-output.schema.json**

Per-page output from the Text Scorer (architecture-proposal-v3.md lines 424-477):
- `page_id` (string, required)
- `pb_criteria[]` — array with: `feature`, `criterion`, `result` (enum: PASS/FAIL/UNKNOWN), `evidence`, `confidence` (enum: high/medium/low), `note` (optional)
- `consumer_criteria[]` — array with: `criterion`, `result`, `evidence`, `confidence`, `codeintel_ref` (optional), `note` (optional)

Write to `schemas/text-scorer-output.schema.json`.

- [ ] **Step 2: Create visual-scorer-output.schema.json**

Per-page output from the Visual Scorer (architecture-proposal-v3.md lines 530-573):
- `page_id` (string, required)
- `features_detected[]` — array of strings
- `pb_criteria[]` — same structure as text scorer
- `consumer_criteria[]` — same structure as text scorer

Write to `schemas/visual-scorer-output.schema.json`.

- [ ] **Step 3: Create network-verifier-output.schema.json**

Output from the deterministic Network Verifier (architecture-proposal-v3.md lines 630-649):
- `api_calls_total` (integer)
- `api_calls_matched_codeintel` (integer)
- `api_calls_unmatched` (integer)
- `api_errors_during_normal_flow` (integer)
- `auth_token_set_after_auth` (boolean)
- `auth_token_sent_on_protected_requests` (boolean)
- `auth_persists_after_refresh` (boolean)
- `deal_breakers[]` — array of strings
- `issues[]` — array of strings
- `per_endpoint[]` — array with: `method`, `path`, `matched_codeintel`, `status`, `expected_status`, `contract_match`, `auth_check`

Write to `schemas/network-verifier-output.schema.json`.

- [ ] **Step 4: Create navigator-output.schema.json**

Full navigator output (architecture-proposal-v3.md lines 271-372):
- `version` (string)
- `status` (enum: DONE/ERROR/SKIP/PARTIAL)
- `elapsed_seconds` (number)
- `persona` (string)
- `url` (string)
- `scope` (string)
- `agent_result` (string — backward compat)
- `manifest_coverage` — object with expected_pages[], visited[], not_visited[], unexpected_pages[]
- `pages[]` — array with: id, url_visited, screenshot, observations (description, actions[], forms[]), network_log[]
- `auth_flow_verification` — object with auth_completed, auth_mechanism_observed, post_auth_access, persistence_after_refresh, logout_test
- `experience` — object with first_impression, easy[], hard[], hesitation_points[], would_return, would_recommend, satisfaction, satisfaction_reason
- `screenshots[]` — array of paths
- `video` (string, optional)

Write to `schemas/navigator-output.schema.json`.

- [ ] **Step 5: Create final-report.schema.json**

Full Score Reconciler report (architecture-proposal-v3.md lines 732-857):
- Combines navigator output + reconciled scores + network verification + verification tasks + summary
- `version`, `status`, `elapsed_seconds`, `persona`, `url`, `scope`
- `agent_result` (string)
- `manifest_coverage`
- `pages[]` with reconciled criteria: `text_result`, `visual_result`, `reconciled`, `confidence`, `evidence`, `discrepancy`
- `experience`
- `network_verification` (from Network Verifier)
- `verification_tasks[]` — with id, type, result, evidence
- `summary` — counts of passed/failed/unknown for pb, consumer, verification, network, discrepancies, deal_breakers

Write to `schemas/final-report.schema.json`.

- [ ] **Step 6: Commit**

```bash
git add schemas/
git commit -m "feat: JSON schemas for scorer outputs, navigator output, and final report"
```

---

## Task 4: Consumer Rubric Format Spec

**Files:**
- Create: `docs/consumer-rubric-format.md`

Document the format spec that SUDD's code-analyzer uses to generate consumer rubrics. Based on architecture-proposal-v3.md lines 1607-1647.

- [ ] **Step 1: Create the format spec**

```markdown
# Consumer Rubric Format Specification

This document defines the format for consumer rubrics generated by SUDD's code-analyzer pipeline. persona-browser-agent's scorers parse this format to evaluate per-page, per-criterion results.

## Overview

A consumer rubric is a Markdown file with per-page sections. Each page section has three priority levels: Must Pass, Should Pass, and Deal-Breakers. Criteria are specific, testable statements derived from the project's specs, design, and code.

## Format

```markdown
# Consumer Rubric: {change_id}

Generated from: specs.md, design.md, codebase analysis
Change scope: {description of what the change covers}

## {Page Name}
Identified by: {how to identify this page — URL pattern, content, or feature}

### Must Pass
- {Specific, testable criterion}
- {Another criterion}

### Should Pass
- {Criterion that's important but not blocking}

### Deal-Breakers
- {Criterion that, if failed, means instant FAIL for this page}
```

## Rules

1. **Page identification**: Use content/feature description, not URL (SPAs may not change URL). Example: "page with signup/registration form" not "/register".

2. **Must Pass** criteria:
   - Core functionality that defines the feature
   - If any fails, the feature is not working as specified
   - Scored at 100% weight

3. **Should Pass** criteria:
   - Important quality attributes
   - Failure is a real issue but doesn't block the feature
   - Scored at 50% weight

4. **Deal-Breakers**:
   - Fundamental failures that override all other scoring
   - If triggered at HIGH confidence → instant FAIL (score = 0)
   - If triggered at MEDIUM confidence → -20 penalty (not instant fail)
   - Use sparingly — only for things that make the feature unusable

5. **Specificity**: Every criterion must be verifiable from browser observation (text + screenshots + network). Never reference DB state, server logs, or other non-observable data.

6. **Codeintel references**: Criteria derived from code analysis should note the source:
   ```
   - Email format validation happens inline (codeintel: registration.elements.forms[0].fields[1].validation)
   ```

## Example

See `fixtures/sample_rubric.md` for a complete example matching the signup+dashboard test app.
```

Write to `docs/consumer-rubric-format.md`.

- [ ] **Step 2: Commit**

```bash
git add docs/consumer-rubric-format.md
git commit -m "docs: consumer rubric format specification for code-analyzer"
```

---

## Task 5: Test Fixtures — codeintel, manifest, rubric

**Files:**
- Create: `fixtures/sample_codeintel.json`
- Create: `fixtures/sample_manifest.json`
- Create: `fixtures/sample_rubric.md`

Hand-written reference fixtures matching `poc/test_app/` (signup form + dashboard). These decouple Phase 2-4 development from Phase 5 (code-analyzer). Developers use these to test the navigator, scorers, and reconciler without needing the SUDD code-analyzer to be built yet.

- [ ] **Step 1: Create sample_codeintel.json**

Write a realistic codeintel.json for the `poc/test_app/`. Match the actual endpoints and UI in `poc/test_app/server.js`:
- Registration page at /register with 3 fields (name, email, password) — note: the test app has 3 fields, not 4 (no confirm_password)
- Dashboard page at /dashboard showing personalized greeting
- POST /api/auth/register endpoint (201/400/409)
- GET /api/user/me endpoint (200/401)
- Session cookie auth (httpOnly)
- Data flow: register writes user → /user/me reads user

Must validate against `schemas/codeintel.schema.json`.

Write to `fixtures/sample_codeintel.json`.

- [ ] **Step 2: Create sample_manifest.json**

Write the matching manifest.json:
- Pages: registration, dashboard
- Auth flow: register first → dashboard after
- Verification tasks: V1 (data persistence — refresh dashboard), V3 (auth persistence — refresh after signup), V4 (auth boundary — access dashboard before signup)

Must validate against `schemas/manifest.schema.json`.

Write to `fixtures/sample_manifest.json`.

- [ ] **Step 3: Create sample_rubric.md**

Write a consumer rubric matching the test app, following the format in `docs/consumer-rubric-format.md`:
- Registration page: Must Pass (3 fields present, validates email/password, success redirects), Should Pass (form remembers data on error), Deal-Breakers (submits with empty fields, data lost)
- Dashboard page: Must Pass (shows user name, has navigation), Deal-Breakers (blank after signup)

Write to `fixtures/sample_rubric.md`.

- [ ] **Step 4: Commit**

```bash
git add fixtures/
git commit -m "feat: hand-written test fixtures for poc/test_app (codeintel, manifest, rubric)"
```

---

## Task 6: Test Fixtures — expected pipeline outputs

**Files:**
- Create: `fixtures/sample_navigator_output.json`
- Create: `fixtures/sample_network_verifier_output.json`

Hand-written expected outputs that show what the pipeline SHOULD produce when run against the test app with the sample fixtures. Used for integration testing in Phase 2-4.

- [ ] **Step 1: Create sample_navigator_output.json**

Write a realistic navigator output for a successful signup flow on `poc/test_app/`. Include:
- 2 pages: registration, dashboard
- Actions: navigate to /register, fill 3 fields, submit, see dashboard, verify refresh
- Network log entries for API calls (from PoC-2 findings)
- Experience narrative
- Auth flow verification (cookie set, persists after refresh)
- Manifest coverage: 100%

Must match `schemas/navigator-output.schema.json`.

Write to `fixtures/sample_navigator_output.json`.

- [ ] **Step 2: Create sample_network_verifier_output.json**

Write the expected Network Verifier output for the same flow:
- 2 API calls matched to codeintel
- No errors
- Auth token set after register
- Auth persists after refresh
- All checks pass

Must match `schemas/network-verifier-output.schema.json`.

Write to `fixtures/sample_network_verifier_output.json`.

- [ ] **Step 3: Commit**

```bash
git add fixtures/
git commit -m "feat: expected pipeline output fixtures for integration testing"
```
