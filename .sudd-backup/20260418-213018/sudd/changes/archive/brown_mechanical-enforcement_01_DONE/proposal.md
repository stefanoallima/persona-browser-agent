# Change: Mechanical Enforcement for Autonomous Reliability

**ID:** brown_mechanical-enforcement_01
**Size:** L
**Mode:** brown
**Priority:** 1 (critical — system cannot operate autonomously without these fixes)

## Problem Statement

SUDD relies on prose instructions for enforcement of critical system behaviors. LLMs follow markdown instructions unreliably — scoring drifts, lessons are ignored, handoff failures propagate silently, state corrupts on interruption. After 89 completed tasks, patterns.md is still empty and the same classes of errors recur.

The root cause: **prose enforcement where mechanical enforcement is needed.**

## What

Replace prose-only enforcement with mechanical checks at the 5 most critical failure points. This is not a rewrite — it's adding validation layers to the existing markdown-based system.

### Fix 1: Structured Scoring with Named Levels (W1, W7)
Replace arbitrary 0-100 scoring with named rubric levels that map to score ranges. LLMs are better at choosing between 5 named categories than producing calibrated numbers.

**Prior work:** brown_validation-rubrics_01 (2026-03-13) added 5-level anchored rubrics to design-reviewer.md and objective-based testing to persona-validator/ux-tester/persona-detector/persona-researcher. The objective-based changes SURVIVED in current agents. But the rubric scoring was only in design-reviewer.md, which was deleted when we replaced impeccable with ui-ux-pro-max. The 4 surviving validation agents (persona-validator, contract-verifier, peer-reviewer, handoff-validator) still use arbitrary 0-100 numeric scoring. This fix redistributes rubric-based scoring to those agents.

**Current:** "Score: 87/100" (arbitrary, uncalibrated)
**Proposed:** Agent picks a level → level maps to score range → score is deterministic

| Level | Range | Gate |
|-------|-------|------|
| EXEMPLARY | 95-100 | PASS |
| STRONG | 80-94 | FAIL |
| ACCEPTABLE | 60-79 | FAIL |
| WEAK | 30-59 | FAIL |
| BROKEN | 0-29 | FAIL |

Only EXEMPLARY passes the gate. Agents must justify their level choice with evidence (file:line references). This eliminates "92 vs 95" score drift — it's either EXEMPLARY or it isn't.

**Files:** standards.md, persona-validator.md, handoff-validator.md, contract-verifier.md, peer-reviewer.md, gate.md

### Fix 2: Wired Learning Injection (W2)
Make learning injection a mandatory orchestrator step, not an optional context-manager behavior.

**Current:** Context-manager documentation says "inject top-3 lessons" but nothing calls it.
**Proposed:** Add explicit step in apply.md and run.md:

```
### 3-pre-b. Lesson Injection (MANDATORY)
Read memory/lessons.md. Match by tags: {task technology}, {task domain}, {failure pattern}.
Include top-3 in coder prompt as "## Lessons (DO NOT repeat these mistakes)".
If no matching lessons: skip. Log: "No matching lessons for {tags}."
```

Also fix pattern promotion: learning-engine must scan lessons.md for 3+ occurrences of same tag combination after every task. If found, write to patterns.md.

**Files:** apply.md, run.md, learning-engine.md, context-manager.md

### Fix 3: Root-Cause Routing Instead of Blind Escalation (W5)
Route retries based on blocker-detector's root cause classification, not just retry count.

**Current:** All failures → retry with bigger model.
**Proposed:**

| Root Cause | Action | Route To |
|-----------|--------|----------|
| LOGIC_ERROR | Retry with feedback | coder (same or escalated tier) |
| SPEC_ERROR | Fix specs first | architect → then coder |
| DESIGN_FLAW | Redesign | architect (file DESIGN_ISSUE) |
| CONTEXT_DRIFT | Context reset | context-manager (re-read vision + specs) |
| EXTERNAL_DEPENDENCY | Block | BLOCKED (human action) |

Escalation ladder still applies for LOGIC_ERROR retries. But SPEC_ERROR and DESIGN_FLAW short-circuit to architect instead of wasting retries on coder.

**Files:** apply.md, run.md, blocker-detector.md

### Fix 4: Validate-on-Read for State.json (W8, W9)
Add validation when state.json is read by any command.

**Current:** Commands read state.json and trust it blindly.
**Proposed:** Every command that reads state.json runs a validation check:

```
### State Validation (on every read)
1. Parse JSON — if invalid, restore from git: `git show HEAD:sudd/state.json`
2. Verify phase is one of: inception, planning, build, validate, complete
3. Verify active_change directory exists (if set)
4. Verify tasks_completed matches count of [x] entries in tasks.md (if active change)
5. If any mismatch: log WARNING, auto-correct from source of truth (tasks.md, git)
```

Also add idempotency guard to apply.md:

```
### Idempotency Check (before each task)
If task is marked [x] in tasks.md AND git log shows commit for this task:
  → Skip. Log: "Task {id} already completed (commit: {sha})."
```

**Files:** standards.md (add State Validation section), apply.md, run.md, gate.md, done.md

### Fix 5: Mandatory Feedback Compression (W4)
Make feedback compression a concrete orchestrator step, not a context-manager guideline.

**Current:** Context-manager says "compress after retry 3" but nobody calls it.
**Proposed:** Add explicit step in apply.md retry protocol:

```
### Retry Protocol — Feedback Compression (retry_count >= 3)
Before invoking coder on retry 3+:
1. Read ALL "## Accumulated Feedback" entries from log.md
2. Compress into:
   - STILL OPEN: {numbered list of unresolved issues}
   - RESOLVED: {numbered list of fixed issues}
   - PATTERN: {the recurring blocker, if any}
3. Replace raw feedback in coder prompt with compressed version
4. Log: "Feedback compressed: {N} entries → {M} open issues"
Total context for coder on retry 3+: task + design + compressed feedback + lessons. Cap at 6000 tokens.
```

**Files:** apply.md, run.md

## Why

Without mechanical enforcement:
- Gates rubber-stamp (W1/W7): 95/100 threshold is meaningless when scores are uncalibrated
- Learning is broken (W2): 89 tasks completed, 0 patterns promoted, same errors recur
- Retries waste compute (W5): Bigger model + same broken specs = same result at higher cost
- Sessions are fragile (W8/W9): Interrupted session = corrupt state = lost work
- Context degrades (W4): Raw feedback accumulates, agent reasoning deteriorates on retries

## What This Does NOT Fix

These weaknesses are real but require larger architectural changes beyond this scope:

- **W3 (Schema validation for handoffs):** Would need a JSON schema system or test harness. Too large for this change.
- **W6 (Worktree silent failures):** Worktree parallelization is opt-in and rarely used. Low priority.
- **W10 (Agent invocation is unspecified):** Fundamental to markdown-first architecture. Fixing this means adding a shell orchestrator, which contradicts SUDD's "zero-Python" principle.

These are deferred as separate changes if needed.

## Acceptance Criteria

1. All validation agents (persona-validator, handoff-validator, contract-verifier, peer-reviewer) use named rubric levels (EXEMPLARY/STRONG/ACCEPTABLE/WEAK/BROKEN) instead of arbitrary 0-100
2. Gate.md only passes EXEMPLARY — no numeric threshold ambiguity
3. Apply.md and run.md have explicit lesson injection step before coder invocation
4. Patterns.md receives entries when lessons repeat 3+ times (verifiable by running learning-engine on current lessons.md)
5. Blocker-detector root cause routes SPEC_ERROR to architect, DESIGN_FLAW to architect, not to coder retry
6. State.json validation runs on every command read — invalid JSON auto-recovers from git
7. Completed tasks are skipped (idempotency guard checks tasks.md + git log)
8. Feedback compression is mandatory on retry 3+ — capped at 6000 tokens

## Risks

- **Named rubric levels may be too coarse.** EXEMPLARY-or-nothing is strict. But 95/100 was already strict — this just makes it unambiguous.
- **Learning injection adds context.** Top-3 lessons ≈ 200-300 tokens. Acceptable overhead.
- **Root-cause routing adds complexity to retry loop.** But it prevents 4-6 wasted retries on spec/design errors.
- **State validation adds read-time overhead.** Parsing tasks.md on every read is cheap (single file, small).

## Dependencies

- None. All changes modify existing framework files.

## Estimated Effort

5 files modified significantly (standards.md, apply.md, run.md, gate.md, blocker-detector.md)
6 files modified lightly (persona-validator.md, handoff-validator.md, contract-verifier.md, peer-reviewer.md, learning-engine.md, done.md)
Total: ~11 files, M-L effort per file = L overall
