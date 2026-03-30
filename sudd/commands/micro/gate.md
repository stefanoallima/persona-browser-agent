---
name: sudd:gate
description: Persona validation gate — does this deliver value?
phase: validate
micro: true
prereq: sudd:test (tests passing)
creates: validation score
---

Persona validation gate. The critical check: does this deliver actual value?

**Input**:
- `/sudd:gate` — validate active change
- `/sudd:gate {change-id}` — validate specific change
- `/sudd:gate {persona}` — validate as specific persona

---

## ORCHESTRATOR CHECK

## PHASE GUARD
Read sudd/state.json
If tests_passed != true: STOP. "Run /sudd:test first — tests must pass before gate."

```bash
cat sudd/state.json
```

If tests not passing:
- "Tests not passing. Run `/sudd:test` first."
- Or auto-run if autonomous

---

## STEP 0: MACRO-WIRING CHECK (v3.0)

Before any persona validation, verify all new code is reachable:

```
Dispatch(agent=macro-wiring-checker):
  Input: git diff against base branch, full codebase
  Output: change-level wiring report

  If ANY dead end, orphaned, or deferred-unresolved:
    → FAIL — cannot proceed to persona validation
    → Log wiring failures to log.md
    → Route to coder to fix wiring, then re-run gate
```

Dead code cannot satisfy any persona. Fix wiring before validating value.

---

## STEP 1: IDENTIFY CONSUMERS

Read `sudd/changes/active/{id}/specs.md` for consumer handoffs.

Identify ALL consumers:
1. **Immediate consumer** — next component in chain
2. **Downstream consumers** — further in pipeline
3. **End user** — human who uses the feature
4. **AI agents** — other SUDD agents consuming output

---

## STEP 2: PERSONA VALIDATION (v3.1 — parallel dispatch)

PARALLEL (dispatch simultaneously):
  Dispatch(agent=persona-validator):
    Input:
      - Change persona research (from changes/active/{id}/personas/)
      - All micro-persona results as evidence
      - Macro-wiring report
      - [If UI] mode=browser, dev server command, design-system/MASTER.md
    Target: 98/100 EXEMPLARY (named rubric from standards.md)
    Returns: {score, level, objectives_met, critical_assessment, intuitiveness_verdict, confidence}
    Note: For UI changes, persona-validator NAVIGATES the live app via Playwright.
          Uses cli_override: claude-code for browser tool access.

  Dispatch(agent=persona-validator):
    Input:
      - Repo persona research (from sudd/personas/)
      - Change persona results
      - [If UI] mode=browser, dev server command
    Target: 98/100 EXEMPLARY
    Returns: {score, level, objectives_met, critical_assessment, intuitiveness_verdict, confidence}
    Note: For UI changes, persona-validator NAVIGATES the live app via Playwright.
          Uses cli_override: claude-code for browser tool access.

  [If UI] Dispatch(agent=ux-tester):
    Input: running UI, persona objectives, UI spec
    Returns: {verdict, score, scenarios_tested, issues, confidence}

  [If UI] Browser-Use Persona Simulation (if sudd.yaml → browser_use.enabled and browser_use.run_on.gate):
    Both persona-validator AND ux-tester invoke browser-use via Bash in their subprocesses:

    persona-validator runs:
      python -m persona_browser.cli \
        --persona "sudd/changes/active/{id}/personas/{persona}.md" \
        --url {dev_server_url} \
        --objectives "{ALL objectives from persona ## Objectives, comma-separated}" \
        --scope gate \
        --output "sudd/changes/active/{id}/browser-use-gate-report.json" \
        --config persona-browser-agent/config.yaml \
        --screenshots-dir "sudd/changes/active/{id}/screenshots/gate/"

    ux-tester runs:
      python -m persona_browser.cli \
        --persona "sudd/changes/active/{id}/personas/{persona}.md" \
        --url {dev_server_url} \
        --objectives "{objectives}" \
        --scope gate \
        --output "sudd/changes/active/{id}/browser-use-ux-gate-report.json" \
        --config persona-browser-agent/config.yaml

    Parse JSON stdout: DONE → incorporate findings. SKIP → Playwright-only. ERROR → -5 penalty.
    See standards.md → Persona Browser Agent Integration for full contract.

WAIT for all to complete.

For each persona validator result, the validator acts AS the consumer:

```
You ARE this consumer. Walk through using the output.

Check:
1. Handoff contract compliance (format, schema, encoding)
2. Deal-breakers addressed
3. Real data, not placeholders
4. Error handling works
5. Documentation usable
6. [If UI] Intuitiveness — can the persona find features and complete tasks without help?
7. [If UI] Visual quality — does it look professional and match the design system?
8. [If UI] Browser-use persona simulation — did the AI persona navigate successfully and fill forms?

Level (from standards.md → Scoring):
  EXEMPLARY:  All requirements met → PASS
  STRONG:     Good but gaps → FAIL
  ACCEPTABLE: Significant issues → FAIL
  WEAK:       Major problems → FAIL
  BROKEN:     Non-functional → FAIL

Feedback: {specific issues}
```

---

## STEP 3: AGGREGATE SCORES

```
Gate: {change-id}

  Consumer: API Client
    Level: EXEMPLARY (99/100)
    Issues: None blocking

  Consumer: Frontend
    Level: EXEMPLARY (98/100)
    Issues: None blocking

  Consumer: End User (Admin)
    Level: EXEMPLARY (100/100)
    Issues: None

  ────────────────────────────
  Lowest Level: EXEMPLARY

  Result: PASS (all EXEMPLARY)
```

---

## STEP 3b: CRITICAL ASSESSMENT (MANDATORY — runs even when all EXEMPLARY)

Before declaring PASS, force a second critical pass on the output:

```
For each consumer that scored EXEMPLARY:
  Dispatch(agent=persona-validator, mode=critical-assessment):

  You already passed this consumer at EXEMPLARY. Now be BRUTALLY HONEST:

  1. WEAKNESSES: What are the top 3 weaknesses of this implementation,
     even if they didn't block you? What felt clunky, slow, or unclear?

  2. WOW FACTOR: What 3 concrete improvements would make this a WOW
     experience for the persona? Not "nice to haves" — specific things
     that would make the consumer say "this is amazing."

  3. GUT CHECK: In one sentence, what's your honest first impression?
     Not the score — the raw human reaction.

  If the critical assessment reveals ANY weakness that:
    - Would cause the consumer to hesitate before recommending this
    - Would require a workaround in real usage
    - Makes the consumer think "this is fine but not great"
  Then: DOWNGRADE to STRONG, provide specific feedback, RETRY.

  Only if the consumer genuinely says "I would use this RIGHT NOW
  and recommend it to others without caveats" → maintain EXEMPLARY.
```

Log the critical assessment to log.md under `## Critical Assessment`.

---

## STEP 4: PASS/FAIL

### If ALL consumers at EXEMPLARY (after critical assessment): PASS
```
Update log.md:
  ## {timestamp}
  - Gate PASSED
  - All consumers: EXEMPLARY
  - All consumers validated

Update state.json:
  phase: "complete"

If running autonomously (from /sudd:run): proceed directly to archive. Do NOT stop.
If running standalone: Next → /sudd:done
```

Update sudd/state.json:
  - gate_passed = true
  - gate_score = {minimum_consumer_score}
  - phase = "complete"
  - last_command = "sudd:gate"

### If ANY consumer below EXEMPLARY: FAIL

**Phase transition: validate → build (on retry) — valid**
**Phase transition: validate → complete (on pass) — valid (handled in PASS above)**

```
Update log.md:
  ## {timestamp}
  - Gate FAILED
  - Lowest score: 45/100 (API Client)
  - Feedback: [detailed issues]

APPEND to log.md under "## Accumulated Feedback" section:
  (Create the section if it does not exist yet. NEVER overwrite existing feedback.)

  ## Accumulated Feedback (read this FIRST on retry)
  ### Retry {retry_count} — Gate Score: {min_score}/100
  - Persona "{consumer_name}": {score}/100 — {specific issues}
  - Persona "{consumer_name}": {score}/100 — {specific issues}
  ...for each consumer evaluated in this gate run.

  Each retry APPENDS a new "### Retry N" subsection below the previous ones.
  Previous retry feedback must be preserved verbatim.

retry_count++

If retry < 8:
  → Escalate tier
  → Return to /sudd:apply with feedback
Else:
  → Mark STUCK
  → Run /sudd:done (will archive as stuck)
```

---

## ESCALATION

Escalation follows `sudd/sudd.yaml` -> `escalation.ladder` (floor-based, never downgrades).

```
Floor-based escalation (v3.2):
  Retry 0-1: floor=low   (agents use their default tiers)
  Retry 2-3: floor=mid   (low-tier agents upgraded to mid)
  Retry 4-5: floor=mid   (coder now mid, code-reviewer top via tier+1)
  Retry 6-7: floor=top   (all agents at top)
  After 8:   STUCK -> sudd/memory/stuck-history/{change-id}.md
```

See run.md ESCALATION section for the full ladder semantics.

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

  Lowest: API Client (45/100)
  
  Issues:
  - Missing pagination support
  - Timeout handling incomplete
  
  Retry: 3/8
  Escalating to Sonnet...
  
  Returning to /sudd:apply with feedback
```

---

## GUARDRAILS

- ALL consumers must be EXEMPLARY level
- Read ACTUAL code, not summaries
- Check for placeholders, not just functionality
- Accumulate ALL feedback across retries
- Always escalate on retry
