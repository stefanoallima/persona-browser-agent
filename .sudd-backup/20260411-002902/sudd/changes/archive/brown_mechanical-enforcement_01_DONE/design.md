# Design: brown_mechanical-enforcement_01

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ standards.md │────→│ All Agents   │     │ learning-     │
│ (rubric def) │     │ (reference)  │     │ engine.md     │
└─────────────┘     └──────────────┘     │ (pattern      │
                                          │  promotion)   │
┌─────────────┐     ┌──────────────┐     └───────┬───────┘
│ blocker-     │────→│ apply.md /   │             │
│ detector.md  │     │ run.md       │             ▼
│ (root cause) │     │ (routing)    │     ┌───────────────┐
└─────────────┘     └──────┬───────┘     │ patterns.md   │
                           │              │ (promoted)    │
                    ┌──────▼───────┐     └───────────────┘
                    │ state.json   │
                    │ (validate-   │
                    │  on-read)    │
                    └──────────────┘
```

No new files created. All changes modify existing files.

## Component 1: Rubric Scoring System

### Responsibility
Define canonical rubric levels in standards.md. Update 4 validation agents + gate.md to use levels instead of arbitrary 0-100.

### Changes

**standards.md** — Replace Scoring section:
```markdown
## Scoring

All validation uses named rubric levels. Agents select a level and justify with evidence.

| Level | Score | Gate | Criteria |
|-------|-------|------|----------|
| EXEMPLARY | 95-100 | PASS | All requirements met. No gaps. Consumer would use immediately. |
| STRONG | 80-94 | FAIL | Good but has gaps. Consumer needs refinements. |
| ACCEPTABLE | 60-79 | FAIL | Functional but significant issues. Consumer struggles. |
| WEAK | 30-59 | FAIL | Major problems. Consumer cannot use effectively. |
| BROKEN | 0-29 | FAIL | Non-functional or empty. Consumer rejects outright. |

Only EXEMPLARY passes the gate. Every level choice must cite evidence (file:line or specific output).
```

**persona-validator.md** — Replace Scoring Guide section. Change output template `### Score: [0-100]` to:
```markdown
### Level: EXEMPLARY / STRONG / ACCEPTABLE / WEAK / BROKEN
### Score: [mapped from level]
### Level Justification:
- Evidence for this level: [file:line or specific observation]
- Why not one level higher: [what's missing]
```

**contract-verifier.md** — Replace Numeric Scoring section. Map COMPLIANT = EXEMPLARY, NON-COMPLIANT = level based on severity.

**peer-reviewer.md** — Replace Scoring Guide. Map APPROVE = EXEMPLARY, REQUEST_CHANGES = STRONG/ACCEPTABLE, REJECT = WEAK/BROKEN.

**handoff-validator.md** — Add level to output. CONSUMABLE = EXEMPLARY, NOT_CONSUMABLE = level based on gaps.

**gate.md** — Replace Step 4 threshold check:
```
If ALL consumers at EXEMPLARY: PASS
If ANY consumer below EXEMPLARY: FAIL (lowest level determines feedback severity)
```

### Complexity: M (6 files, consistent pattern)

## Component 2: Wired Learning Injection

### Responsibility
Add mandatory lesson injection step to orchestrator commands. Fix pattern promotion in learning-engine.

### Changes

**apply.md** — Add step between STEP 1 (READ CONTEXT) and STEP 2 (SHOW PROGRESS):

```markdown
## STEP 1b: LESSON INJECTION (MANDATORY)

Read `sudd/memory/lessons.md`. For current task, extract tags from:
- Task technology (from design.md file extensions / frameworks)
- Task domain (from proposal.md / specs.md)
- Prior failure patterns (from log.md if retry)

Match lessons by tag overlap. Select top-3 by: tag match count > confidence > recency.

If matches found, include in ALL agent prompts for this task:
  ## Lessons (DO NOT repeat these mistakes)
  1. {lesson} (from: {change-id}, confidence: {level})
  2. {lesson}
  3. {lesson}

Log: "Injected {N} lessons for tags: {tags}"
If no matches: Log: "No matching lessons for tags: {tags}"
```

**run.md** — Same injection step in Step 5c before coder invocation.

**learning-engine.md** — Add to Mode 3 (Pattern Promotion):
```markdown
### Promotion Trigger
After EVERY task completion (not just on-demand):
1. Read all lessons in memory/lessons.md
2. Group by tag combinations (e.g., "go, testing" appears in 4 lessons)
3. If any tag combination appears in 3+ lessons from DIFFERENT changes:
   → Check if pattern already exists in patterns.md
   → If not: create new pattern entry
   → If exists: update occurrence count
4. Log: "Pattern check: {N} tag groups scanned, {M} patterns promoted"
```

### Complexity: M (3 files)

## Component 3: Root-Cause Routing

### Responsibility
Make blocker-detector's root cause classification actionable in the retry loop.

### Changes

**blocker-detector.md** — Add routing recommendation to output template:
```markdown
### Routing
- **Route to**: coder | architect | context-manager | BLOCKED
- **Reason**: [why this route, not default coder retry]
```

Add routing rules section:
```markdown
## Routing Rules
| Root Cause | Route To | Why |
|-----------|----------|-----|
| LOGIC_ERROR | coder | Implementation bug — coder can fix |
| SPEC_ERROR | architect | Specs are ambiguous/wrong — coder can't fix what's not specified |
| DESIGN_FLAW | architect | Architecture doesn't support requirement — redesign needed |
| CONTEXT_DRIFT | context-manager | Agent lost requirements — reset context |
| EXTERNAL_DEPENDENCY | BLOCKED | Human must resolve external issue |
```

**apply.md** — Modify error handling to read root cause:
```markdown
## ERROR HANDLING (after step 3d failure)

Task(agent=blocker-detector): Classify error

Read blocker-detector output → Route To field:
- If "coder": increment retry, escalate tier per ladder, restart from 3a
- If "architect": invoke architect to revise specs.md or design.md, then restart from 3a with retry_count reset to 0
- If "context-manager": re-read vision.md + specs.md, clear stale context, restart from 3a
- If "BLOCKED": log blocker, skip to next task
```

**run.md** — Same routing logic in ERROR HANDLING section.

### Complexity: M (3 files)

## Component 4: State Validation & Idempotency

### Responsibility
Validate state.json on every read. Skip completed tasks.

### Changes

**standards.md** — Add State Validation section:
```markdown
## State Validation

Every command that reads state.json must validate:
1. Valid JSON — if corrupt, restore: `git show HEAD:sudd/state.json > sudd/state.json`
2. `phase` ∈ {inception, planning, build, validate, complete}
3. If `active_change` set → `sudd/changes/active/{active_change}/` exists
4. If active change has tasks.md → `tasks_completed` matches `[x]` count
5. Mismatch → log WARNING, auto-correct from source of truth
```

**apply.md** — Add idempotency guard before step 3a:
```markdown
### 3-pre-a. Idempotency Check
For each task about to execute:
1. Read tasks.md — is this task marked [x]?
2. If [x]: check git log for commit message containing this task ID
3. If both [x] AND commit exists → Skip. Log: "Task {id} already completed (commit: {sha})"
4. If [x] but NO commit → WARNING: "Task marked complete but no commit found. Re-running."
```

### Complexity: S (2 files)

## Component 5: Feedback Compression

### Responsibility
Enforce compression at retry 3+ with token cap.

### Changes

**apply.md** — Replace RETRY PROTOCOL section:
```markdown
## RETRY PROTOCOL (if retry_count > 0)

### For retry 1-2: Full Feedback
Include raw accumulated feedback in RETRY BRIEFING.

### For retry 3+: Compressed Feedback (MANDATORY)
1. Read ALL "## Accumulated Feedback" entries from log.md
2. Compress:
   ```
   ## Compressed Feedback (retry {N})
   ### STILL OPEN (fix these):
   1. {issue} — first seen retry {N}, still failing
   2. {issue}
   ### RESOLVED (don't regress):
   1. {issue} — fixed in retry {N}
   ### PATTERN (recurring blocker):
   {the issue that keeps coming back}
   ```
3. Include ONLY compressed version in coder prompt (discard raw entries)
4. Context budget for coder: task + design + compressed feedback + lessons ≤ 6000 tokens
5. Log: "Feedback compressed: {N} raw entries → {M} open issues, {K} resolved"
```

### Complexity: S (1 file, apply.md — run.md references apply.md's retry protocol)

## File Changes Summary

### Modified Files
| File | Component | Effort |
|------|-----------|--------|
| sudd/standards.md | C1 (rubric), C4 (state validation) | M |
| sudd/agents/persona-validator.md | C1 (rubric levels) | S |
| sudd/agents/contract-verifier.md | C1 (rubric levels) | S |
| sudd/agents/peer-reviewer.md | C1 (rubric levels) | S |
| sudd/agents/handoff-validator.md | C1 (rubric levels) | S |
| sudd/agents/blocker-detector.md | C3 (routing rules) | S |
| sudd/agents/learning-engine.md | C2 (pattern promotion trigger) | S |
| sudd/commands/micro/apply.md | C2 (injection), C3 (routing), C4 (idempotency), C5 (compression) | L |
| sudd/commands/macro/run.md | C2 (injection), C3 (routing) | M |
| sudd/commands/micro/gate.md | C1 (EXEMPLARY-only pass) | S |

### New Files
None.

## Acceptance Criteria Mapping

| AC | Component | How Verified |
|----|-----------|-------------|
| AC1: Named rubric levels | C1 | All 4 agents output EXEMPLARY/STRONG/etc. instead of raw numbers |
| AC2: Gate passes EXEMPLARY only | C1 | gate.md checks level, not numeric threshold |
| AC3: Lesson injection before coder | C2 | apply.md STEP 1b exists, log shows "Injected N lessons" |
| AC4: Pattern promotion works | C2 | Run learning-engine on current lessons.md → patterns.md gets entries |
| AC5: Root-cause routing | C3 | blocker-detector output has "Route to" field, apply.md reads it |
| AC6: State validation on read | C4 | standards.md has State Validation section, commands reference it |
| AC7: Idempotency guard | C4 | apply.md 3-pre-a skips [x] tasks with commit evidence |
| AC8: Feedback compression | C5 | apply.md RETRY PROTOCOL compresses at retry 3+, context ≤ 6000 |
