---
name: "sudd:run"
description: "Full autonomous SUDD workflow. Use when the user wants to build a feature end-to-end autonomously."
license: MIT
metadata:
  author: sudd
  version: "3.3"
---

Full autonomous SUDD workflow. Runs the complete loop from vision to done.

**Input**: 
- `/sudd:run` — continue with current state
- `/sudd:run green "description"` — start fresh from vision (heavy research)
- `/sudd:run brown` — continue existing work (light discovery)
- `/sudd:run {change-id}` — work on specific change

---

Agent invocation follows `sudd/standards.md` → Agent Invocation.

---

## ORCHESTRATOR STARTUP

1. **Load state**: Read `sudd/state.json`
2. **Determine mode**:
   - If `green` in args → mode = green, extensive research
   - If `brown` in args → mode = brown, continue existing
   - If change-id provided → focus on that change
   - Else use existing state
3. **Check for port**: If `imported_from` set, validate port completed
4. **Display status**:
   ```
   SUDD AUTONOMOUS SESSION
   ════════════════════════
   Mode: green | brown
   Active: {change-id} | none
   Phase: {phase}
   Tasks: N active | M completed
   ```
5. **Read config**: Read `sudd/sudd.yaml` for agent tiers, escalation ladder, cost_mode
   - If missing: warn "No sudd.yaml found, defaulting all agents to free tier"
5b. **Detect CLI**: Read `sudd.yaml -> cli`
   - Determines dispatch syntax for all agent invocations this session
   - Reference: `sudd/cli-adapter.md` for CLI-specific syntax
   - If missing: infer from environment (which CLI am I running inside?)
   - Skill invocation format: claude/crush use `/sudd:run`, opencode uses `/sudd-run`
5c. **Check for checkpoint**: If `sudd/changes/active/{id}/checkpoint.json` exists:
   → Load checkpoint state
   → Skip completed tasks
   → Resume from checkpoint's current_task and current_step
   → If checkpointed mid-squad: pass cached squad_results_so_far to next subagent
   → Log: "Resuming from checkpoint: {task} at {step}"
   → Delete checkpoint.json after successful completion

---

## MODE: GREEN (Vision → Implementation)

Used when starting from an idea/vision with minimal existing structure.

### Step 1: Discovery
```
Read: sudd/vision.md
Read: sudd/personas/*.md (if exist)
Search: codebase for related patterns

If vision.md is empty or vague:
  → Ask user for clarification (ONE question, then proceed)
  → Or use /sudd:chat to explore first
```

### Step 2: Discovery-Driven Change Generation (v3.4)

Before creating a single change, run the discovery pipeline to find ALL
work that needs doing. This replaces the old single-change approach.

```
DISCOVERY CHECK:
  Invoke /sudd:discover (follows staleness rules — may skip if recent)

  If discovery ran and generated proposals:
    → Multiple discovered_* proposals now exist in changes/active/
    → Pick the highest-priority proposal as active change
    → Continue to Step 3 with that change

  If discovery skipped (recent + no changes):
    → Check if any proposals exist in changes/active/ with status: proposed
    → If yes: pick highest-priority, continue to Step 3
    → If no: fall through to legacy single-change creation below

  LEGACY FALLBACK (no discovery results, no existing proposals):
    Generate change-id: green_{name}_{seq:02d}
      - name: kebab-case from vision content
      - seq: next available number

    Create: sudd/changes/active/{change-id}/
      - proposal.md (from vision)
      - specs.md (discovered requirements)
      - design.md (architecture)
      - tasks.md (implementation checklist)
      - log.md (execution log)

Update: sudd/state.json
  - active_change = {selected change-id}
  - phase = "planning"
  <!-- Phase transition: none → planning (valid) -->
```

NOTE: When running inside /sudd:auto, the remaining discovered proposals
stay in the queue. After this change completes, auto processes the next one.

### Step 3: Research Agents (parallel)
```
For each major component in vision:
  Dispatch(agent=researcher): Investigate technology, patterns
  Dispatch(agent=persona-detector): Discover consumers
  Dispatch(agent=persona-researcher): Deep-research each consumer

Aggregate findings into specs.md

Dispatch(agent=persona-detector, scope=change): Discover change-level consumers
Dispatch(agent=persona-researcher, scope=change): Deep-research change consumers
  Write to: sudd/changes/active/{id}/personas/
```

### Step 4: Planning
<!-- Phase transition: inception → planning (valid) -->
```
Dispatch(agent=antigravity): Back-plan from outcome
Dispatch(agent=deep-think): Align with vision
Dispatch(agent=architect): Design solution

Dispatch(agent=qa, mode=testability-review):
  - Read design.md acceptance criteria
  - Check testability of each criterion
  - Append ## Testability Notes to design.md

Write: design.md with architecture
Write: tasks.md with implementation tasks

If change involves UI (detected from proposal/vision keywords: UI, frontend, dashboard, form, page, web interface):
  Dispatch(agent=ux-architect):
    Read: proposal.md, specs.md, design.md, existing UI patterns
    Write: ## UI Specification section in design.md

  Dispatch(agent=ux-designer):
    Read ## UI Specification from design.md
    Run ui-ux-pro-max scripts to generate design-system/MASTER.md
    Generate per-page overrides in design-system/pages/
    Append ## Design Tokens to design.md

Dispatch(agent=micro-persona-generator):
  Read: tasks.md, design.md, specs.md, codebase
  Write: sudd/changes/active/{id}/tasks/{task-id}/micro-persona.md (one per task)
  Process in reverse dependency order (leaf tasks first)

Update: state.json phase = "build"
<!-- Phase transition: planning → build (valid) -->
```

### Step 5: Build Loop

#### 5a. Dependency Analysis
```
Read tasks.md. For each pending task, extract:
  - Dependencies: field (list of task IDs)
  - Files: field (list of file paths)
  - SharedFiles: field (lock files, configs, routers — files multiple tasks may touch)

Build batches:
  - Tasks are INDEPENDENT if ALL of:
    1. Neither lists the other in Dependencies:
    2. Their Files: lists have no overlap
    3. Their SharedFiles: lists have no overlap
  - Group independent tasks into ordered batches
  - Dependent tasks go into later batches

SharedFiles examples (architect should declare these):
  - package.json, go.mod, requirements.txt (dependency files)
  - database migrations with sequence numbers
  - router/route config files, index.ts barrel exports
  - .env.example, shared config files

Example:
  T1 (no deps, files: a.go) ─┐
  T2 (no deps, files: b.go) ─┼─ Batch 1
  T4 (no deps, files: d.go) ─┘
  T3 (deps: T1, files: a.go, c.go) → Batch 2 (after T1 completes)
```

#### 5a-bis. Environment Smoke Test (v3.2)

Before the first task dispatch, verify the environment works:

```
Dispatch(agent=coder, tier=low, prompt="Smoke test"):
  "Read package.json / go.mod / requirements.txt.
   Run the install command. Run the test command.
   Report: dependencies OK? tests runnable? environment issues?"
  Returns: {environment_ok: bool, issues: [string], test_command: string}

If environment_ok == false:
  Check if user_input_required (missing env var, missing tool)
  If fixable: fix and re-test (max 2 attempts)
  If not fixable: park ALL tasks as user_input_required
```

#### 5b. Model Tier Selection (v3.2)
```
Read sudd.yaml → agents[agent].tier for default tier.
Read sudd.yaml → escalation.ladder[retry_count] for floor tier.
effective_tier = max(default_tier, floor_tier)
For code-reviewer: effective_tier = tier_escalation[coder_effective_tier]
Resolve tiers[effective_tier] → (model, provider, endpoint, cli)

Effort-based initial tier (overrides default if higher):
  task.effort == "S" AND task.files.length <= 2  → coder: low, code-reviewer: mid
  task.effort == "M" OR task.files.length <= 4   → coder: mid, code-reviewer: top
  task.effort == "L" OR files > 4                → coder: top, code-reviewer: top
```

#### 5c. Execute Batches
```
Read sudd.yaml → parallelization.mode (default: "sequential")

DEFAULT MODE: SEQUENTIAL
  STEP 1b: Inject top-5 items from memory/patterns.md + ~/.sudd/learning/patterns.md + memory/lessons.md (per apply.md STEP 1b)

  CANARY (v3.1 — before first batch):
    If no tasks completed yet:
      Run full pipeline on first task as canary (see apply.md STEP 2.5)
      If systemic failure: STOP, fix root cause, then continue

  For each batch, run tasks one at a time in main workspace:
    For each task in batch:
      Idempotency check: skip if [x] + commit exists (per apply.md 3-pre-a)
      3a.  Load micro-persona for this task (generate on-demand if missing)
      3b.  Dispatch(agent=qa): Write tests from rubric (TDD — first attempt only)
      3c.  Dispatch(agent=coder): Implement task (curated context)
      3d.  Dispatch(agent=code-reviewer): Round 1 review (curated context, tier+1)
      3e.  Dispatch(agent=coder): Fix run 1 (reads review-1.md)
      3f.  Dispatch(agent=code-reviewer): Round 2 review (FULL context, tier+1)
      3g.  Dispatch(agent=coder): Fix run 2 (reads review-2.md)
      3h.  VALIDATION SQUAD:
           i.   Dispatch(agent=contract-verifier)
           ii.  Dispatch(agent=wiring-checker)
           iii. Dispatch(agent=integration-reviewer, scope=task)
           iv.  [UI only] Dispatch(agent=ux-reviewer)
           v.   Dispatch(agent=micro-persona-validator)
      3i.  [UI only] Dispatch(agent=ux-tester): Browser validation
      If squad FAIL (3h):
        → retry 1-3: feedback → coder fix → re-run from 3d (code-reviewer → fix → squad)
        → retry 4-5: architect escalation → revised design → coder retry from 3c
        → retry 6+: mark blocked_failed, skip to next independent task
      Else: mark task validated, commit

      Change-level budget check:
        total = sum(state.json.task_progress.*.tokens_used)
        Update state.json.total_tokens_used = total
        If total > sudd.yaml.token_budget.per_change_max → archive as STUCK
        If total_elapsed > sudd.yaml.time_budget.per_change_max → archive as STUCK

  CHECKPOINT (v3.1):
    After each task completes (or between batches):
      If monitor detects context window >= 80% capacity:
        Save checkpoint to sudd/changes/active/{id}/checkpoint.json:
          sudd_version, timestamp, phase, task_progress, current_task,
          squad_results_so_far, retry_counts, lessons_injected,
          accumulated_feedback, canary_passed, resume_instruction
        Log: "Checkpoint saved. Session can resume with /sudd:run"

  After all tasks in batch:
    Dispatch(agent=integration-reviewer, scope=change): cross-task integration check

  Stagnation detection:
    If score delta < 5 across 2 consecutive retries → skip to architect escalation
    If 3+ tasks blocked_failed → pause, architect reviews entire design

OPT-IN MODE: WORKTREE (sudd.yaml parallelization.mode: worktree)
  For each batch:
    If batch.size == 1 or skip conditions met:
      → Run in main workspace (same as sequential above)

    If batch.size > 1:
      → Create worktree per task (via context-manager Worktree Management)
      → Dispatch each task in parallel:
          3a.  Load micro-persona
          3b.  Dispatch(agent=qa): Write tests (TDD)
          3c.  Dispatch(agent=coder, tier={from 5b}): Implement task
          3d.  VALIDATION SQUAD (runs INSIDE worktree before merge):
               NOTE: This worktree pipeline is INCOMPLETE — missing 3d-3g (code-reviewer rounds).
               Do NOT re-enable worktree mode until this pipeline is updated to match the full 3c-3i sequential pipeline.
               i-iv. Same as sequential mode
      → After all tasks complete, merge sequentially:
          - Before each merge: rebase worktree branch against current base
          - If rebase/merge conflicts: abort, mark task for sequential re-run
          - After each successful merge: run integration-reviewer on merged result
          - If integration fails post-merge: git revert the merge commit, mark for sequential re-run
          - Cleanup all worktrees
      → Re-run any conflict/failed tasks sequentially in main workspace
      → All lifecycle events logged to log.md

    After batch completes (all tasks merged or re-run):
      Dispatch(agent=integration-reviewer, scope=change): cross-task integration check

    Skip worktrees even in worktree mode if:
      - batch.size == 1
      - All tasks have Effort: S (overhead exceeds benefit)
      - Not in a git repo
      - git worktree add fails mid-batch → log warning, cleanup, fall back to sequential
```

#### 5d. Per-Task Retry Tracking
```
Track retry counts per task in state.json.task_progress:
  task_progress: { "T01": { "retries": 0, ... }, "T02": { "retries": 3, ... } }

Benefits:
  - Task that passed doesn't get re-run at higher tier unnecessarily
  - Escalation ladder applies per-task: T01 at free, T02 at sonnet (retry 3)
  - STUCK determination is per-task: T02 can be STUCK while T01 continues
```

### Step 6: Validate & Complete (AUTONOMOUS — no user intervention)
<!-- Phase transition: build → validate (valid) -->

This step runs as a **continuous loop** until PASS or STUCK. Do NOT stop and tell the user to run commands manually.

```
VALIDATION LOOP:
  6a. TEST PHASE (inline /sudd:test logic):
      - Detect test command (sudd.yaml or auto-detect)
      - Run all tests (unit, integration, coverage)
      - If tests fail:
          → Dispatch(agent=blocker-detector): classify failure
          → Dispatch(agent=coder): fix bugs
          → Re-run tests (max 3 quick-fix attempts)
          → If still failing after 3 attempts: increment retry, escalate tier, go to 5c
      - Update state.json: tests_passed = true

  6a-bis. MACRO-WIRING CHECK (v3.0):
      Dispatch(agent=macro-wiring-checker):
        - Git diff against base branch → all new artifacts
        - Trace from entry point to each artifact
        - Check DEFERRED resolutions from per-task wiring reports
        - Any DEAD END/ORPHANED/DEFERRED_UNRESOLVED → FAIL → route to coder to fix wiring

  6b. REVIEW PHASE:
      Dispatch(agent=peer-reviewer): Final code review
      Dispatch(agent=ux-tester): If UI components exist, browser test

  6c. GATE PHASE (v3.1 — parallel dispatch):
      PARALLEL (dispatch simultaneously):
        Dispatch(agent=persona-validator):
          Input: change persona + micro-persona results as evidence + macro-wiring report
          Target: 98/100 EXEMPLARY
        Dispatch(agent=persona-validator):
          Input: repo persona + change persona results
          Target: 98/100 EXEMPLARY
        [If UI] Dispatch(agent=ux-tester):
          Input: running UI, persona objectives, UI spec

      WAIT for all, then:
        Critical assessment (mandatory second pass, see gate.md STEP 3b)

      If ALL consumers EXEMPLARY (>= 98/100):
        → GATE PASSED
        → Continue to 6d
      Else (ANY consumer below EXEMPLARY):
        → Log feedback to log.md (## Accumulated Feedback)
        → retry_count++ (per-task)
        → If retry < 8: escalate tier per ladder, GO BACK TO Step 5c (re-apply with feedback)
        → If retry >= 8: mark STUCK, continue to 6d

  6d. ARCHIVE PHASE (inline /sudd:done logic):
      - If PASSED:
          → Step 2a: Dispatch(agent=learning-engine, mode=1): extract lessons to memory/lessons.md
          → Step 2b: Dispatch(agent=learning-engine, mode=3): PATTERN PROMOTION (MANDATORY)
            - Scan ALL lessons, build tag frequency map
            - Promote patterns (3+ occurrences from different changes)
            - Write to memory/patterns.md AND ~/.sudd/learning/patterns.md (if enabled)
            - This step MUST run — see done.md Step 2b for full algorithm
          → Step 2c: INDEX SESSION IN MEMPALACE (if mempalace.enabled)
            - Index full log.md into sessions room for rich context preservation
            - Index lesson + new patterns into respective rooms
            - See done.md Step 2c for details
          → Move to sudd/changes/archive/{change-id}_DONE/
          → Create SUMMARY.md
      - If STUCK:
          → Step 2a: Dispatch(agent=learning-engine, mode=1): extract lessons (failures too)
          → Step 2b: Dispatch(agent=learning-engine, mode=3): PATTERN PROMOTION (still runs)
          → Step 2c: INDEX SESSION IN MEMPALACE (if mempalace.enabled)
          → Move to sudd/changes/archive/{change-id}_STUCK/
          → Create STUCK.md with rollback commands
          → Copy to sudd/memory/stuck-history/
      - Update state.json: clear active_change, reset phase to inception
      - Git commit and merge to main (if DONE)
      <!-- Phase transition: validate → complete (valid) -->
```

#### 6e. Post-Completion Verification (v3.2)

After archiving as DONE:

```
FINAL VERIFICATION:
  1. Start the application (detect start command from sudd.yaml or package.json)
  2. Wait for startup (health check endpoint or port listen, timeout 30s)
  3. If UI change: Dispatch(agent=ux-tester, scope=final):
       Screenshot main routes, verify renders, no console errors
  4. If API change: curl key endpoints, verify 200 responses
  5. Write: sudd/changes/archive/{id}_DONE/verification.md

If verification FAILS:
  → Do NOT un-archive (code passed all gates)
  → Log failure details in verification.md
  → User decides whether to fix or ship
```

**CRITICAL**: This entire step is autonomous. The orchestrator MUST NOT stop after tests pass and say "run /sudd:gate". It MUST NOT stop after gate passes and say "run /sudd:done". The loop runs continuously until the change is archived as DONE or STUCK.

---

## MODE: BROWN (Continue Existing)

Used when specs/code already exist.

### Step 1: Assess State
```
Read: sudd/state.json
Read: sudd/changes/active/{active_change}/*.md
Read: codebase for context

If no active change:
  → List available changes
  → Auto-select if only one
  → Else ask user
```

### Step 2: Continue from Phase
```
Switch on phase:
  case "inception": → run planning   <!-- Phase transition: inception → planning (valid) -->
  case "planning":  → continue design <!-- Phase transition: planning → build (valid) -->
  case "build":     → continue tasks  <!-- Phase transition: build → validate (valid) -->
  case "validate":  → run validation  <!-- Phase transition: validate → complete (valid) -->
  case "complete":  → archive
```

### Step 3: Build Loop
```
Same as green mode Step 5 (dependency analysis → per-task validation squad), including:
  - Per-task validation squad: contract-verifier → wiring-checker → integration-reviewer → micro-persona-validator
  - Micro-persona loading and on-demand generation
  - Task retry budget (3 coder + 2 architect = 5 max)
  - Stagnation detection
  - Cross-task integration check after each batch
  - SharedFiles: overlap check for dependency analysis
  - Per-task retry tracking and escalation
  - Worktree parallelization if opted in via sudd.yaml
But:
  - Skip research phase (already done)
  - Use existing specs/design
  - Only run missing validations
```

---

## ESCALATION (v3.2 — floor-based)

```
The escalation ladder sets per-role FLOOR tiers. Never downgrades.
Retry 0-1: floor=low   (all agents use default tiers)
Retry 2-3: coder stays low, squad+code-reviewer floor=mid
Retry 4-5: default floor=mid, code-reviewer floor=top
Retry 6-7: floor=top   (all agents at top)
After 8:   STUCK → sudd/memory/stuck-history/{change-id}.md
```

---

## ERROR HANDLING

```
On any error:
  Dispatch(agent=blocker-detector):
    - Classify: RETRY | BLOCKED | STUCK
    - Root Cause: LOGIC_ERROR | SPEC_ERROR | DESIGN_FLAW | CONTEXT_DRIFT | EXTERNAL_DEPENDENCY
    - Route To: coder | architect | context-manager | BLOCKED

  Route based on "Route To" field:
    "coder":           increment retry, escalate tier per ladder, restart from 3a
    "architect":       invoke architect to revise specs/design, restart with retry reset to 0
    "context-manager": re-read vision + specs, clear stale context, restart from 3a
    "BLOCKED":         log to sudd/results/{change-id}_BLOCKED.md, skip task

  STUCK: log to sudd/memory/stuck-history/, move on
```

---

## SESSION END

```
Update: sudd/state.json
  - last_run = now
  - stats updated

Output:
  ═══════════════════════════════════════
  SUDD SESSION COMPLETE
  ═══════════════════════════════════════
  Mode: green | brown
  Tasks completed: N
  Tasks stuck: N
  Tasks blocked: N
  Lessons learned: M new
  ═══════════════════════════════════════
```

---

## GUARDRAILS

1. **Never ask user** unless scope is unclear or major decision needed
2. **Never skip validation squad** — every task gets contract → wiring → integration → micro-persona check
3. **Never skip persona gate** — mandatory for completion
4. **Always escalate on retry** — same tier won't magically succeed (per-task retry count)
5. **Always write files to disk** — no in-memory only
6. **Always read actual files for validation** — not summaries
7. **Budget conscious** — use free models when possible, select model tier by task complexity
8. **Sequential by default** — worktree parallelization is opt-in via `sudd.yaml` → `parallelization.mode: worktree`. Default is sequential: reliable, no merge risk
9. **Spec compliance before code quality** — always run contract-verifier before peer-reviewer (fix what's wrong before polishing)
10. **SharedFiles must be declared** — architect must list lock files, configs, routers in `SharedFiles:` per task. Tasks sharing any `SharedFiles:` entry are DEPENDENT
11. **Worktree mode only**: cleanup is mandatory — always remove worktrees after merge or conflict. Rebase before merge. Revert on post-merge validation failure
12. **Per-task validation before proceeding** — validation squad (contract → wiring → integration → micro-persona) runs after every task. No task is "done" until PASS (100/100).
13. **Context window management** — validation squad agents are lightweight (narrow scope). After each task, compress validation history to one line in state.json. If context window reaches 80% capacity, save state and continue in fresh session.
