---
name: "sudd-gate"
description: "Persona validation gate. Use when the user wants to validate if work is ready."
license: MIT
metadata:
  author: sudd
  version: "3.3"
---

Persona validation gate. The critical check: does this deliver actual value?

**Input**:
- `/sudd:gate` — validate active change
- `/sudd:gate {change-id}` — validate specific change
- `/sudd:gate {persona}` — validate as specific persona

---

## ORCHESTRATOR CHECK

## PHASE GUARD
Read sudd/state.json. If tests_passed != true: STOP. "Run /sudd:test first."

---

## STEP 0: MACRO-WIRING CHECK (v3.0)

Dispatch(agent=macro-wiring-checker): verify all new code is reachable via git diff + full codebase.
If ANY dead end, orphaned, or deferred-unresolved → FAIL, log to log.md, route to coder to fix wiring.

---

## STEP 1: IDENTIFY CONSUMERS

Read `sudd/changes/active/{id}/specs.md`. Identify all consumers: immediate, downstream, end user, AI agents.

---

## STEP 2a: CODE INTELLIGENCE EXTRACTION (v3.3)

Only for UI changes. If no UI files detected: skip Steps 2a-2d, use non-UI gate flow.

```
IF change has UI files:

  Pre-flight:
  1. [ ] persona-browser-agent installed?
  2. [ ] $OPENROUTER_API_KEY set?
  3. [ ] At least one persona file in changes/{id}/personas/?
  If 1-2 fail: technical-checks-only, cap score at 90
  If 3 fails: FAIL — "No personas"

  Sequential dispatch:

  1. Dispatch(agent=code-analyzer-fe): Haiku → fe_codeintel.json
  2. Dispatch(agent=code-analyzer-be): Haiku → be_codeintel.json
     (1 and 2 run IN PARALLEL. Skip be if no backend.)

  3. Dispatch(agent=code-analyzer-reviewer): Sonnet
     Input: fe/be_codeintel.json, specs.md, design.md, personas/*.md
     Output: codeintel.json, manifest.json, rubric.md (DRAFT)

  4a. Dispatch(agent=rubric-adversary): Haiku → critique of draft rubric
  4b. Dispatch(agent=code-analyzer-reviewer, mode=revision) → rubric.md (v2)
  4c. Dispatch(agent=rubric-adversary): Haiku → critique of v2
  4d. Dispatch(agent=code-analyzer-reviewer, mode=revision) → rubric.md (FINAL)

  Re-runs on retry if code changed (git SHA check).

  Post-flight:
  4. [ ] codeintel.json exists?
  5. [ ] manifest.json exists?
  6. [ ] rubric.md exists?
  7. [ ] codeintel from current commit?
  If 4-6 fail: FAIL — "Code-analyzer failed"
  If 7 fails: re-run code-analyzer
```

---

## STEP 2b: BROWSER TESTING (v3.3)

```
  1. Start dev server (ONCE for entire gate):
     Auto-detect command, health check with timeout, save PID + CDP port.
     If server fails: FAIL — "Dev server not running"

  2. FOR EACH persona in changes/{id}/personas/:
     persona-test \
       --persona "changes/{id}/personas/{name}.md" \
       --url {dev_server_url} \
       --objectives "{from persona ## Objectives}" \
       --manifest "changes/{id}/manifest.json" \
       --rubric "changes/{id}/rubric.md" \
       --codeintel "changes/{id}/codeintel.json" \
       --scope gate --max-steps 50 --timeout 120 \
       --screenshots-dir "changes/{id}/screenshots/gate/{name}/" \
       --output "changes/{id}/browser-reports/{name}.json"

     DONE → continue | SKIP → cap score at 90 | ERROR → -5 penalty, continue
     Personas CAN run IN PARALLEL. Save Chrome CDP port for ux-tester.
```

---

## STEP 2c: PERSONA VALIDATION (v3.3 — reads reports, no browser)

```
PARALLEL dispatch per persona:
  Dispatch(agent=persona-validator):
    Input: browser_report, change + repo persona research, micro-persona results,
           macro-wiring report, specs.md, design.md, tasks.md
    Target: 98/100 EXEMPLARY
    Returns: {score, level, objectives_met, critical_assessment, confidence}
    Note: reads PB report only. No browser, no PB calls, no dev server.
    cli_override: claude-code
```

---

## STEP 2d: UX TESTING — SPOT CHECK + TECHNICAL (v3.3)

```
  [If UI] Dispatch(agent=ux-tester):
    Input: browser_report, CDP port from Step 2b, design-system/MASTER.md
    Returns: {verdict, score, spot_check_results[], technical_issues[], confidence}
    Note: Playwright-over-CDP. Spot check + technical checks. No PB calls.
    cli_override: claude-code

  Steps 2c and 2d run IN PARALLEL.
```

WAIT for all to complete.

---

## STEP 2e: UNIFIED SCORING (v3.3)

```
FOR EACH persona:
  Read: browser-reports/{name}.json, persona-validator output, ux-tester output

  Compute scores (weights from sudd.yaml → browser_use.scoring):
    pb_score = pb_criteria_passed / pb_criteria_total * 100
      deal-breaker at HIGH confidence → instant 0
    consumer_score = weighted criteria score
      "Must Pass" failures × must_pass_weight (1.0)
      "Should Pass" failures × should_pass_weight (0.5)
      deal-breaker → instant 0
    verification_score = verification_tasks_passed / total * 100
    penalties:
      network: -network_error_penalty per API error; instant 0 on 500 or auth handover fail
      manifest: -manifest_missing_penalty per missing page; 0% coverage → auto FAIL
      spot_check: -spot_check_mismatch_penalty per mismatch;
    informational (included in report, does NOT affect score):
      experience: navigator satisfaction + "would recommend" (LLM-fabricated, for human review only)
                  gate FAIL on critical/deal-breaker mismatch;
                  gate FAIL + "PB UNRELIABLE" on 2+ mismatches

  CHECK ALL (must ALL pass):
    □ pb_score >= rubric_threshold.pb (default 98)
    □ consumer_score >= rubric_threshold.consumer (default 98)
    □ verification_score >= rubric_threshold.verification (default 100)
    □ No deal-breakers triggered at HIGH confidence
    □ No API 500 errors during normal user flow
    □ Auth flow verified (token set, persists, sent on protected requests)
    □ Manifest coverage = 100% (all pages visited)
    □ persona-validator level == EXEMPLARY
    □ ux-tester spot check passed (no critical mismatches)

  ALL pass → GATE PASS | ANY fail → GATE FAIL with reasons + action items

ALL personas pass → Step 3 | ANY fails → GATE FAIL + targeted feedback

Failure report (append to log.md):
  ## Gate: FAILED
  ### Persona: {name}
  **PB Criteria**: {passed}/{total} ({score}%) — per-page breakdown:
    Page /{page}: ✓/✗ {criterion} — {evidence from PB report}
  **Consumer Criteria**: {passed}/{total} ({score}%)
  **Verification Tasks**: {passed}/{total}
  **Network Verification**: {issues count} — {specific API errors or auth failures}
  **Spot Check**: {ALL_MATCH/PARTIAL_MISMATCH/...} — {mismatched criterion_ids}
  **Navigator Experience**: {score}/10

  ### Action Items for Coder (priority order):
  1. [WIRING] {fix description — e.g., "settings page not reading name from API"}
  2. [FRONTEND] {fix description — e.g., "add confirm_password field"}
  3. [BACKEND] {fix description — e.g., "add created_at to GET /api/user/me"}
  4. [AUTH] {fix description — e.g., "session cookie not persisting after refresh"}

  ### Do NOT Touch:
  - {pages/endpoints that passed all criteria}
```

---

## DEV SERVER CLEANUP

After Step 2e (or any gate exit): kill dev server PID, kill Chrome instances, ensure no orphaned processes.

---

## STEP 3: AGGREGATE SCORES

```
Gate: {change-id}
  Consumer: {name} — Level: EXEMPLARY ({score}/100)
  ...per consumer...
  Lowest Level: {level}
  Result: PASS/FAIL
```

---

## STEP 3b: CRITICAL ASSESSMENT (MANDATORY — even when all EXEMPLARY)

```
For each EXEMPLARY consumer:
  Dispatch(agent=persona-validator, mode=critical-assessment):

  Review PB report evidence — specifically check these fields:
  - network_verification.issues — any API contract violations, even minor?
  - verification_tasks — any that barely passed or had ambiguous evidence?
  - discrepancies[] — where text scorer and visual scorer disagreed
  - experience.hesitation_points — where did the navigator struggle?
  - pb_criteria with confidence "medium" — uncertain assessments

  1. WEAKNESSES: Top 3 from the PB evidence above
  2. WOW FACTOR: 3 concrete improvements
  3. GUT CHECK: One honest sentence

  If ANY weakness would cause hesitation recommending,
  or a Score Reconciler discrepancy was resolved with medium confidence,
  or a verification task barely passed → DOWNGRADE to STRONG, RETRY.

  Only maintain EXEMPLARY if "I would use this RIGHT NOW and recommend without caveats."
```

Log to log.md under `## Critical Assessment`.

---

## STEP 4: PASS/FAIL

### PASS (all EXEMPLARY after critical assessment)
Update log.md with score + timestamp. Update state.json: gate_passed=true, gate_score={min}, phase="complete".
If autonomous → proceed to archive. If standalone → /sudd:done.

### FAIL (any consumer below EXEMPLARY)
Append to log.md `## Accumulated Feedback` → `### Retry {N} — Gate Score: {min}/100` with per-persona scores + issues. Never overwrite previous feedback.

retry_count++. If < 8 → escalate tier, return to /sudd:apply. If >= 8 → STUCK, run /sudd:done.

---

## ESCALATION

Follow `sudd/sudd.yaml` → `escalation.ladder` (floor-based, never downgrades). See run.md for full ladder semantics.

---

## OUTPUT

### Pass
```
Gate: PASSED ✓
  All consumers validated
  Minimum score: {min}/100 (must be >= 98)
If autonomous: archiving now...
If standalone: Run /sudd:done to archive
```

### Fail
```
Gate: FAILED ✗
  Lowest: {consumer} ({score}/100)
  Issues: {list}
  Retry: {N}/8 — Escalating to {tier}...
  Returning to /sudd:apply with feedback
```

---

## GUARDRAILS

- ALL consumers must be EXEMPLARY level
- Read ACTUAL code, not summaries
- Check for placeholders, not just functionality
- Accumulate ALL feedback across retries
- Always escalate on retry
