# Specifications: brown_worktree-parallel-execution_01

## Functional Requirements

### FR-1: Worktree-Isolated Task Execution in apply.md
- Given: A task from tasks.md with no dependencies on other in-progress tasks
- When: `/sudd:apply` dispatches the coder agent
- Then:
  - Create a git worktree at `.worktrees/{change-id}-{task-id}/` with branch `sudd/{change-id}-{task-id}`
  - Verify `.worktrees/` is in .gitignore (add if missing)
  - Dispatch coder agent to work in the worktree directory
  - On coder completion: merge worktree branch back to `sudd/{change-id}` branch
  - On merge conflict: log conflict details, flag for sequential re-apply
  - Cleanup worktree after successful merge
- If task has dependencies on in-progress tasks: skip worktree, run in main workspace

### FR-2: Parallel Independent Tasks in run.md Build Loop
- Given: tasks.md with N pending tasks, some independent (no shared deps)
- When: `/sudd:run` enters build phase
- Then:
  - Analyze task dependencies from tasks.md `Dependencies:` field
  - Group independent tasks (no shared dependencies, no overlapping `Files:` lists)
  - Dispatch independent tasks in parallel, each in its own worktree
  - Merge results sequentially after all complete (first-finished merges first)
  - Continue with dependent tasks in main workspace after merge
- If only 1 task or all tasks dependent: skip worktree, run sequentially as before

### FR-3: Two-Stage Review After Coder
- Given: Coder agent completes a task (in worktree or main workspace)
- When: Task output is ready for validation
- Then:
  - Stage 1: `Task(agent=contract-verifier)` — verify code matches specs (spec compliance)
  - Stage 2: `Task(agent=peer-reviewer)` — verify code quality (clean, tested, documented)
  - If Stage 1 fails: feedback to coder, re-implement, re-verify
  - If Stage 2 fails: feedback to coder, fix quality issues, re-review
  - Only after both stages pass: proceed to handoff-validator
- Existing handoff-validator and design-reviewer steps remain unchanged

### FR-4: Worktree Lifecycle in context-manager
- Given: Need to create, manage, or cleanup git worktrees
- When: Worktree operations are needed during task execution
- Then:
  - **Create**: `git worktree add .worktrees/{name} -b {branch}`
  - **Safety**: Verify `.worktrees/` in .gitignore via `git check-ignore -q .worktrees`; fix if not ignored
  - **Setup**: Auto-detect project type and run setup (npm install / pip install / go mod download)
  - **Merge**: `git checkout {target-branch} && git merge {worktree-branch}`
  - **Cleanup**: `git worktree remove .worktrees/{name}` after successful merge
  - **Track**: Note active worktrees in log.md

### FR-5: Model Tier Selection for Parallel Agents
- Given: A task dispatched to a subagent
- When: Choosing which model tier to use
- Then:
  - Check task complexity signals:
    - `Effort: S` AND `Files:` lists ≤2 files → use free/cheap tier
    - `Effort: M` OR `Files:` lists ≤4 files → use standard tier (sonnet)
    - `Effort: L` OR `Files:` lists >4 files → use capable tier (opus)
  - Override: SUDD escalation ladder takes precedence on retries:
    - retry 0-1: free for all
    - retry 2-3: free for coder, sonnet for validation agents
    - retry 4-5: sonnet for all
    - retry 6-7: opus for all
    - retry 8+: STUCK

### FR-6: Dependency Analysis for Parallelization
- Given: tasks.md with `Dependencies:` and `Files:` fields per task
- When: Deciding which tasks can run in parallel
- Then:
  - Two tasks are INDEPENDENT if:
    1. Neither lists the other in `Dependencies:`
    2. Their `Files:` lists have no overlap
  - Two tasks are DEPENDENT if either condition fails
  - Group all independent tasks into parallel batches
  - Within a batch: all tasks run concurrently in worktrees
  - Between batches: sequential execution

## Non-Functional Requirements

### NFR-1: Backward Compatible
- Constraint: Projects without git or without `.worktrees/` support fall back to sequential execution
- Rationale: Worktrees are an optimization, not a requirement

### NFR-2: Minimal Overhead
- Constraint: Only create worktrees when 2+ independent tasks exist in a batch
- Rationale: Single-task execution doesn't benefit from worktree isolation

### NFR-3: Clean State
- Constraint: All worktrees must be cleaned up after merge (success or failure)
- Rationale: Orphaned worktrees waste disk space and confuse git status

### NFR-4: Platform Compatible
- Constraint: Worktree commands must work on macOS, Linux, and Windows (Git Bash)
- Rationale: SUDD targets all platforms

## Consumer Handoffs

### Handoff 1: apply.md → context-manager (worktree creation)
- Format: Worktree request with change-id, task-id, branch name
- Validation: Worktree created, .gitignore verified, setup complete

### Handoff 2: coder → contract-verifier (spec compliance)
- Format: Code output + specs.md reference
- Validation: All spec requirements met, nothing extra added

### Handoff 3: contract-verifier → peer-reviewer (code quality)
- Format: Code output + spec compliance confirmation
- Validation: Code is clean, tested, follows patterns

### Handoff 4: worktree branch → change branch (merge)
- Format: Git merge
- Validation: No conflicts, tests pass after merge

## Out of Scope
- Worktrees for gate validators (read-only)
- Worktrees for research/planning agents (don't modify files)
- Custom worktree skill file (consume Superpowers directly)
- Go CLI installer changes
- Worktree support for non-git projects
