---
name: "sudd:apply"
description: "Implement tasks from the task list. Use when the user wants to start building."
license: MIT
metadata:
  author: sudd
  version: "3.8.0"
---

Implement tasks from the change’s task list.

**Input**:
- `/sudd:apply` — implement next pending tasks
- `/sudd:apply {task-id}` — implement specific task
- `/sudd:apply all` — implement all pending tasks

---

Agent invocation follows `sudd/standards.md` → Agent Invocation.

---

## ORCHESTRATOR CHECK

## PHASE GUARD
<!-- Phase guard: requires phase >= "build" -->
If phase < "build": STOP. "Run /sudd:plan first."
If specs.md does not exist: STOP. "Run /sudd:plan first — specs.md is required."

```bash
cat sudd/state.json
```

If phase < "build":
- "Planning not complete. Run `/sudd:plan` first."
- Or auto-run if autonomous

If no active change:
- Find available changes
- Auto-select or ask

---

## STEP 1: READ CONTEXT + VALIDATE STATE

Read state.json and validate per `sudd/standards.md` → State Validation.

Read:
- `sudd/sudd.yaml` (agent tiers, cost_mode)
- `sudd/changes/active/{id}/proposal.md`
- `sudd/changes/active/{id}/specs.md`
- `sudd/changes/active/{id}/design.md`
- `sudd/changes/active/{id}/tasks.md`
- `sudd/memory/lessons.md`

---

## STEP 1b: LESSON INJECTION (MANDATORY)

Read these sources (in priority order):
1. `sudd/memory/patterns.md` — local promoted patterns (highest weight, validated)
2. `~/.sudd/learning/patterns.md` — global patterns from ALL repos (if exists and `sudd.yaml → learning.inject_global: true`)
3. `sudd/memory/lessons.md` — local raw lessons (lower weight, single-occurrence)

For current task, extract tags from:
- Task technology (from design.md file extensions / frameworks)
- Task domain (from proposal.md / specs.md)
- Prior failure patterns (from log.md if retry)

Match patterns AND lessons by tag overlap. Prioritize: patterns > lessons.
Select top-5 (configurable via `sudd.yaml → learning.max_injected_items`) by: source type (pattern 2x weight) > tag match count > confidence > recency.

If matches found, include in ALL agent prompts for this task:
```
## Lessons for This Task (DO NOT repeat these mistakes)
### Patterns (validated across multiple changes):
1. {pattern rule} (confidence: VERY HIGH, occurrences: {N}, source: {local|global:repo})
### Lessons (single-change observations):
2. {lesson} (from: {change-id}, confidence: {level})
3. {lesson}
```

Log: "Injected {N} items ({P} patterns, {L} lessons) for tags: {tags}"
If no matches: Log: "No matching lessons/patterns for tags: {tags}"

---

## STEP 1c: DISPATCH MODE (v3.2)

Read `sudd/sudd.yaml` → `tiers` for dispatch configuration.
Read `sudd/sudd.yaml` → `agents` for per-agent tier and context mode.

For agents with `tier: inline`:
  Execute in orchestrator context (unchanged from v3.1).

For agents with `tier: low | mid | top`:
  Resolve tier → (model, provider, endpoint, cli) from `tiers` config.
  Dispatch via CLI subprocess:
    Dispatch(agent=X): see `sudd/standards.md` → Agent Invocation (v3.2)

  Context preparation (by context-manager, inline):
    If agent.context == "curated": write `tasks/{task-id}/context-{agent}.md`
    If agent.context == "full": list raw file paths in dispatch prompt
    If agent.context == [curated, full]: curated for round 1, full for round 2

  Model selection:
    base_tier = sudd.yaml.agents[agent].tier
    floor_tier = sudd.yaml.escalation.ladder[retry_count]
    effective_tier = max(base_tier, floor_tier)
    For code-reviewer: effective_tier = tier_escalation[coder’s effective_tier]

---

## STEP 2: SHOW PROGRESS

```
Tasks: {change-id}

  ✓ T1: Setup database schema
  ✓ T2: Create model classes
  ○ T3: Implement API endpoints
  ○ T4: Add validation
  ○ T5: Write tests

Progress: 2/5 complete
```


## STEP 2.5: CANARY VALIDATION (v3.1)

If this is the first task in the change (no tasks completed yet):
  Run the full pipeline on T1 as a canary:
    Dispatch(coder) → Dispatch(qa) → parallel(Dispatch(cv), Dispatch(wc)) → Dispatch(ir) → [Dispatch(ux-r)] → Dispatch(mpv)

  If T1 PASSES cleanly (all rubric criteria met, HIGH confidence):
    → Proceed with remaining tasks normally

  If T1 FAILS on TASK-SPECIFIC issue (bug in T1's code):
    → Normal retry for T1, then proceed

  If T1 FAILS on SYSTEMIC issue:
    Systemic indicators:
    - Multiple rubric categories fail simultaneously
    - Rubric criteria reference specs that are ambiguous/wrong
    - Micro-persona contract doesn't match actual codebase patterns
    - Wiring fails because design assumed wrong file structure
    → STOP. Fix systemic root cause FIRST:
      - Spec issue → architect revises specs
      - Persona issue → re-run micro-persona-generator
      - Design issue → architect revises design
    → THEN proceed with remaining tasks
---

## RETRY PROTOCOL (if retry_count > 0)

### For retry 1-2: Full Feedback
1. Read `## Accumulated Feedback` from log.md
2. Read latest critique dispositions from log.md
3. Lessons already injected by STEP 1b
4. Include in coder's prompt:

```
RETRY BRIEFING (attempt {retry_count} of 8):
  Previous level: {gate_level}
  Tier: {current tier from sudd.yaml escalation ladder}
  Failures:
    {list from accumulated feedback}
  Key lessons:
    {top-3 from STEP 1b}

  FIX THESE SPECIFIC ISSUES. Do not rewrite from scratch.
```

### For retry 3+: Compressed Feedback (MANDATORY)
1. Read ALL `## Accumulated Feedback` entries from log.md
2. Compress into:
```
## Compressed Feedback (retry {N})
### STILL OPEN (fix these):
1. {issue} — first seen retry {N}, still failing
### RESOLVED (don't regress):
1. {issue} — fixed in retry {N}
### PATTERN (recurring blocker):
{the issue that keeps coming back}
```
3. Include ONLY compressed version in coder prompt (discard raw entries)
4. Context budget: task + design + compressed feedback + lessons ≤ 6000 tokens
5. Log: "Feedback compressed: {N} raw entries → {M} open issues"

---

## STEP 3: IMPLEMENT TASKS

For each pending task (or specified task):

### 3-pre. Task Ordering & Dispatch

When `/sudd:apply all` or multiple tasks are pending:

1. **Analyze dependencies**: Read each task's `Dependencies:`, `Files:`, and `SharedFiles:` fields
2. **Order tasks**:
   - Tasks are INDEPENDENT if: neither depends on the other AND their `Files:` AND `SharedFiles:` lists don't overlap
   - Group independent tasks into batches; dependent tasks go into later batches
   - Within each batch, execute tasks **sequentially** (default) or in parallel (opt-in)
3. **Default: Sequential execution** (one task at a time in main workspace):
   - Run tasks in dependency order within each batch
   - No worktree overhead, no merge risk, no implicit dependency issues
   - This is the default and recommended mode
4. **Opt-in: Worktree parallelization** (if `sudd.yaml` → `parallelization.mode: worktree`):
   - Only when batch size > 1 AND all conditions met (see `sudd/agents/context-manager.md` → Worktree Management)
   - Create worktree per task, dispatch in parallel, merge back sequentially
   - IMPORTANT: validation squad runs INSIDE the worktree before merge
   - Before each merge: rebase worktree branch against current base to reduce conflicts
   - On merge conflict: abort, re-run that task sequentially in main workspace
   - On post-merge validation failure: `git revert` the merge commit, re-run task sequentially
   - Cleanup all worktrees after merge or conflict
   - **Skip worktrees even in worktree mode** if: only 1 task in batch, all Effort: S, not in a git repo, or `git worktree add` fails mid-batch

5. **Model tier selection** (v3.2):
   - Read `sudd/sudd.yaml` → `agents[agent].tier` for default tier
   - Read `sudd/sudd.yaml` → `escalation.ladder[retry_count]` for floor tier
   - `effective_tier = max(default_tier, floor_tier)`
   - For code-reviewer: `effective_tier = tier_escalation[coder_effective_tier]`
   - Resolve `tiers[effective_tier]` → (model, provider, endpoint, cli)
   - Retry escalation uses floor semantics (never downgrades):
     - retry 0-1: floor=low (all agents use defaults)
     - retry 2-3: coder stays low, squad+code-reviewer floor=mid
     - retry 4-5: floor=mid (coder now mid), code-reviewer floor=top
     - retry 6-7: floor=top (all at top)
     - retry 8+: STUCK
   - Floor resolution: `floor = escalation.ladder[retry_count].{agent_role}_floor ?? escalation.ladder[retry_count].default_floor`

For single task (`/sudd:apply {task-id}`): always run in main workspace.

### 3-pre-a. Idempotency Check
For each task about to execute:
1. Read tasks.md — is this task marked `[x]`?
2. If `[x]`: check git log for commit message containing this task ID
3. If both `[x]` AND commit exists → **Skip.** Log: "Task {id} already completed (commit: {sha})"
4. If `[x]` but NO commit → WARNING: "Task marked complete but no commit found. Re-running."

### 3a. Load Micro-Persona (v3.0)
```
Read: sudd/changes/active/{id}/tasks/{task-id}/micro-persona.md

If micro-persona missing:
  → Run micro-persona-generator for this task
  → Log: "Generated micro-persona for {task-id} on-demand"
```

### 3b. Dispatch(agent=qa) — TDD
```
Read: agents/qa.md

For NEW tasks (retry_count == 0):
  QA writes tests BEFORE coder implements (TDD)
  → Step order for first attempt: 3a → 3b → 3c → 3d
  NOTE: This is an intentional change from v2 (where coder ran before QA).

For RETRIES (retry_count > 0):
  Coder fixes first, then tests re-run
  → Step order for retries: 3a → 3c → 3b → 3d
```

### 3-pre-b. Budget Tracking (v3.2)

Before each agent dispatch in this task:
1. If `task_progress.{task-id}.start_time` is not set: set it to current ISO 8601 timestamp
2. After each subprocess returns: increment `task_progress.{task-id}.tokens_used` += tokens consumed by this dispatch

After each dispatch completes, check budgets:
```
tokens = state.json.task_progress.{task-id}.tokens_used
elapsed = now - state.json.task_progress.{task-id}.start_time

If tokens > sudd.yaml.token_budget.per_task_max:
  -> Dispatch(agent=blocker-detector) with root_cause="TOKEN_BUDGET_EXCEEDED"
  -> Mark task blocked_failed, skip to next task

If elapsed > sudd.yaml.time_budget.per_task_max:
  -> Dispatch(agent=blocker-detector) with root_cause="TIME_BUDGET_EXCEEDED"  
  -> Mark task blocked_failed, skip to next task

If tokens > sudd.yaml.token_budget.per_task_max * sudd.yaml.token_budget.warning_threshold:
  -> Log: "WARNING: task {id} at {percent}% of token budget"
```

Change-level budget check (after each task completes):
```
total = sum(state.json.task_progress.*.tokens_used)
state.json.total_tokens_used = total

If total > sudd.yaml.token_budget.per_change_max:
  -> Log: "CHANGE TOKEN BUDGET EXCEEDED ({total} > {max})"
  -> Archive change as STUCK with reason "token budget exhausted"
  -> STOP processing further tasks

total_elapsed = now - earliest(task_progress.*.start_time)
If total_elapsed > sudd.yaml.time_budget.per_change_max:
  -> Log: "CHANGE TIME BUDGET EXCEEDED ({elapsed}s > {max}s)"
  -> Archive change as STUCK with reason "time budget exhausted"
  -> STOP processing further tasks
```

### 3c. Dispatch(agent=coder) — implement (v3.2)

```
Dispatch(agent=coder, context=curated):
  Context file: tasks/{task-id}/context-coder.md
    Contains: task description, design section, specs interfaces,
              micro-persona with rubric, top-3 lessons, design tokens (if UI task),
              accumulated feedback (if retry)
  Instruction: "Implement the task. Run tests. Write results to tasks/{task-id}/test-results-3c.md."
  Returns: {files_changed, commit_sha, confidence}
```

After dispatch: verify test-results-3c.md exists and shows PASS. If tests failed and coder didn’t fix them, retry coder dispatch once before proceeding.

### 3d. Dispatch(agent=code-reviewer) — round 1 (v3.2)

```
Dispatch(agent=code-reviewer, context=curated, tier=coder_tier+1):
  Context file: tasks/{task-id}/context-code-reviewer.md
    Contains: task description, design section, micro-persona,
              files changed by coder, test results,
              design-system/MASTER.md (if UI task)
  Instruction: "Review round 1. Write to tasks/{task-id}/review-1.md."
  Returns: {issues, design_adherence, design_issue_detected, contract_revision_detected, confidence}
```

If `design_issue_detected` or `contract_revision_detected`:
  → Dispatch(agent=architect) to revise design/contract
  → After revision, restart from 3c with retry count reset to 0

### 3e. Dispatch(agent=coder) — fix run 1 (v3.2)

```
Dispatch(agent=coder, context=curated, mode=fix):
  Context file: tasks/{task-id}/context-coder-fix.md
    Contains: review-1.md issues, task description, design section,
              micro-persona (coder needs full task understanding to fix correctly)
  Instruction: "Fix run. Read review-1.md. Fix ONLY listed issues. Run tests. Write to test-results-3e.md."
  Returns: {files_changed, commit_sha, confidence}
```

### 3f. Dispatch(agent=code-reviewer) — round 2, FULL context (v3.2)

```
Dispatch(agent=code-reviewer, context=full, tier=coder_tier+1):
  Full file paths in prompt:
    - design.md, specs.md, micro-persona.md, tasks.md
    - All code files from task
    - design-system/MASTER.md (if UI task)
    - test-results-3e.md
    - review-1.md (to verify issues were fixed)
  Instruction: "Review round 2 with FULL context. Write to tasks/{task-id}/review-2.md."
  Returns: {issues, design_adherence, design_issue_detected, contract_revision_detected, confidence}
```

### 3g. Dispatch(agent=coder) — fix run 2 (v3.2)

```
Dispatch(agent=coder, context=curated, mode=fix):
  Context file: tasks/{task-id}/context-coder-fix.md
    Contains: review-2.md issues, task description, design section, micro-persona
  Instruction: "Fix run. Read review-2.md. Fix ONLY listed issues. Run tests. Write to test-results-3g.md."
  Returns: {files_changed, commit_sha, confidence}
```

### 3h. VALIDATION SQUAD (v3.2 — dispatch per tier)

Dispatch pattern (unchanged from v3.1 except dispatch mechanism):

PARALLEL (independent — dispatch simultaneously):
  i.  Dispatch(agent=contract-verifier, context=curated)
  ii. Dispatch(agent=wiring-checker, context=curated)

WAIT for both, then SEQUENTIAL:
  iii. Dispatch(agent=integration-reviewer, context=curated)
  iv.  [UI only] Dispatch(agent=ux-reviewer, context=curated)
  v.   Dispatch(agent=micro-persona-validator, context=full)

Return schemas and failure handling: unchanged from v3.1.

### 3i. [UI tasks only] Dispatch(agent=ux-tester) — browser validation (v3.2)

```
Dispatch(agent=ux-tester, context=curated, backend=claude-code):
  NOTE: ux-tester MUST use claude-code backend for Playwright MCP tools,
        regardless of tier assignment. Override cli to claude-code.
  Instruction: "Start the app. Open browser. Navigate routes for this task.
               Verify: renders, no console errors, interactive elements work.
               Check design-system/MASTER.md consistency.
               Save screenshots to tasks/{task-id}/screenshots/.
               Write report to tasks/{task-id}/ux-test-results.md."
  Returns: {verdict, scenarios_tested, issues, screenshots, confidence}

  Browser-use persona simulation (if sudd.yaml → browser_use.enabled and browser_use.run_on.per_task):
    The ux-tester runs via Bash inside its subprocess:
      python -m persona_browser.cli \
        --persona "sudd/changes/active/{id}/tasks/{task-id}/micro-persona.md" \
        --url {dev_server_url} \
        --objectives "{objectives extracted from micro-persona ## Objectives or ## Contract}" \
        --scope task --task-id {task-id} \
        --output "sudd/changes/active/{id}/tasks/{task-id}/browser-use-report.json" \
        --config persona-browser-agent/config.yaml \
        --screenshots-dir "sudd/changes/active/{id}/tasks/{task-id}/screenshots/"
    Parse JSON stdout: status DONE → incorporate agent_result into verdict.
    status SKIP → log + Playwright-only. status ERROR → log + -5 score penalty.
    See standards.md → Persona Browser Agent Integration for full contract.
```

If FAIL: route issues back to coder (fix run), then re-run ux-tester. Max 2 ux-tester retries per task.

### 3j. Task Retry Budget (v3.0)

```
If validation squad FAIL:
  retry_count++ for this task

  retry 1-3: Inject feedback → coder fixes → re-run from 3d (code-reviewer → fix → squad)
  retry 4:   Escalate to architect → revise task design → coder retries
  retry 5:   Architect + coder one more attempt
  retry 6+:  Mark task as blocked_failed
             Log: "Task {id} BLOCKED after {retries} attempts: {last failure reason}"
             Move to next independent task

Stagnation detection:
  If score delta < 5 across 2 consecutive retries → skip to architect escalation
```

### 3k. Mark Complete

Update `tasks.md`:
```markdown
- [x] T3: Implement API endpoints
  - Completed: {timestamp}
  - Validated: micro-persona PASS (100/100)
  - Files: api/endpoints.py, api/routes.py
```

Append to `log.md`:
```markdown
## {timestamp}
- Completed T3: Implement API endpoints
- Micro-persona: PASS (100/100) — consumer: {consumer name}
- Validation squad: contract ✓ wiring ✓ integration ✓
- Files created/modified: api/endpoints.py
- Retries: {N}
```

### 3k-bis. SQUAD DISAGREEMENT DETECTION (v3.1)

After marking task complete or failed, log squad verdicts with artifact names:

```markdown
## Squad Tracking: {task-id}
| Retry | Agent | Artifact Flagged | Reason |
|-------|-------|-----------------|--------|
| {N} | {agent} | {artifact} | {reason} |
```

Check for patterns:
1. Same artifact flagged by 2+ squad members for DIFFERENT reasons
   → Systemic issue → route to architect (not coder)
2. Same artifact fails 3+ retries across different squad members
   → BLOCKED → don't waste more retries, escalate immediately
3. Recurring field across tasks (T3, T5, T8 all fail on same issue)
   → Systemic → fix at design level, not per-task

### 3l. Track Files Modified
Append to `## Files Modified` in log.md:
```markdown
## Files Modified
- `{file_path}` — {task_id}: {description}
```

---

## STEP 4: CHECKPOINT

After each task or batch:
- Commit: `git add . && git commit -m "feat({change-id}): complete {task}"`
- Update state if phase change needed
  <!-- Phase transition: build → validate (valid, only when all tasks complete) -->

### Post-Batch Cross-Task Integration Check (v3.0)

After all tasks in a batch complete:
```
Dispatch(agent=integration-reviewer, scope=change):
  Input: all micro-persona contracts, all task integration reports, SharedFiles conflicts
  Verdict: PASS / FAIL
  If FAIL: identify conflicting tasks, route to coder with both task contexts
```

---

## OUTPUT

```
Applied: {change-id}

  ✓ T3: Implement API endpoints
    Files: api/endpoints.py, api/routes.py
    Micro-persona: PASS (100/100)
    Squad: contract ✓ wiring ✓ integration ✓

  ✗ T5: Add payment webhooks
    Status: blocked_failed (5 retries)
    Last failure: wiring-checker — PaymentWebhook handler not registered in router

Progress: 4/5 complete, 1 blocked

If running autonomously (from /sudd:run): proceed directly to test phase. Do NOT stop.
If running standalone: Next → /sudd:test
```

---

## ERROR HANDLING (after validation squad failure)

```
Dispatch(agent=blocker-detector): Classify error from squad feedback

Read blocker-detector output → "Route To" field:
  - "coder":           increment retry, escalate tier per ladder, restart from 3c
  - "architect":       invoke architect to revise design, restart from 3c with retry reset
  - "context-manager": re-read context, clear stale state, restart from 3c
  - "BLOCKED":         log blocker, mark task blocked_failed, skip to next task
```

Root-cause routing prevents wasting retries. SPEC_ERROR and DESIGN_FLAW go to architect, not coder with bigger model.

---

## DISPATCH ERROR PROTOCOL (v3.2)

```
If dispatch returns unstructured narrative (not the expected schema):
  -> Retry with: "Return ONLY this JSON schema: {schema}. No prose."
  -> Max 2 retries

If dispatch times out:
  -> Retry with reduced context (drop lessons, keep essential)
  -> Max 1 retry

If dispatch returns wrong schema (missing fields):
  -> Retry with: "Missing fields: {list}. Return complete schema."
  -> Max 1 retry

If 3 consecutive failures from same agent:
  -> Escalate model tier (low -> mid -> top)
  -> If already top -> mark agent BLOCKED, orchestrator handles manually
```

---

## GUARDRAILS

- Always read design before implementing
- Follow specs for interfaces exactly
- Run full validation squad after each task (contract → wiring → integration → micro-persona)
- Peer-reviewer runs at gate level only (removed from per-task loop in v3.0)
- Commit after each task
- Update tasks.md checkboxes immediately
- Log progress to log.md
- Context window management: validation squad agents are lightweight (narrow scope). After each task, compress validation history to one line in state.json. If context window reaches 80% capacity, save state and continue in fresh session.
