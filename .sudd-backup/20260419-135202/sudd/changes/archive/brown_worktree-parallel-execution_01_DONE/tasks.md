# Tasks: brown_worktree-parallel-execution_01

## Implementation Tasks

- [x] T01: Add Worktree Management section to context-manager.md
  - Files: sudd/agents/context-manager.md
  - Effort: M
  - Dependencies: none
  - Details: Add new "## Worktree Management" section with 4 subsections: Create Worktree (.worktrees/ convention, .gitignore safety, auto-setup), Merge Worktree (merge back, conflict handling, abort+sequential fallback), Cleanup Worktree (remove worktree, delete branch), Track Active Worktrees (log.md table format).

- [x] T02: Add two-stage review to apply.md
  - Files: sudd/commands/micro/apply.md
  - Effort: M
  - Dependencies: none
  - Details: Insert step 3b (contract-verifier for spec compliance) and step 3c (peer-reviewer for code quality) between existing step 3a.5 (design-reviewer) and current 3b (handoff-validator, renumbered to 3d). Add retry loops: 3b fail → coder re-implements → re-verify; 3c fail → coder fixes → re-review. Both must pass before 3d.

- [x] T03: Add worktree dispatch to apply.md
  - Files: sudd/commands/micro/apply.md
  - Effort: M
  - Dependencies: T01, T02
  - Details: Before dispatching coder, check if task is independent (no deps on in-progress tasks, no file overlap). If independent AND 2+ tasks being applied: create worktree via context-manager, dispatch coder to worktree, merge back after review passes. If single task or dependent: run in main workspace as before. Add fallback: on merge conflict, abort and re-run sequentially.

- [x] T04: Add dependency analysis to run.md
  - Files: sudd/commands/macro/run.md
  - Effort: M
  - Dependencies: none
  - Details: In the build loop, before dispatching tasks: read tasks.md, extract Dependencies and Files fields, build dependency graph, identify independent task batches. Add algorithm description inline. Group tasks into batches where all tasks in a batch are independent of each other.

- [x] T05: Add parallel worktree execution to run.md build loop
  - Files: sudd/commands/macro/run.md
  - Effort: L
  - Dependencies: T01, T04
  - Details: Modify build loop to dispatch independent task batches in parallel using worktrees. For batch size > 1: create worktree per task, dispatch coder+reviewers in parallel, merge results sequentially. For batch size 1: run in main workspace. Add model tier selection based on task complexity (effort S + 1-2 files → free, M → standard, L → capable). Escalation ladder override on retries.

- [x] T06: Add worktree skip logic for non-git and single-task scenarios
  - Files: sudd/commands/micro/apply.md, sudd/commands/macro/run.md
  - Effort: S
  - Dependencies: T03, T05
  - Details: Add guards: skip worktree if not in a git repo, skip if only 1 task in batch, skip if `.worktrees/` creation fails (log warning, fall back to sequential). Ensure backward compatibility — projects without git or without worktree support work exactly as before.

## Test Tasks

- [x] T07: Verify apply.md and run.md are internally consistent
  - Files: sudd/commands/micro/apply.md, sudd/commands/macro/run.md, sudd/agents/context-manager.md
  - Effort: S
  - Dependencies: T06
  - Details: Read all 3 modified files end-to-end. Check: worktree commands match between context-manager and apply/run, step numbering consistent in apply.md, two-stage review chain correctly ordered, model tier rules consistent between run.md and sudd.yaml escalation ladder, no stale references.

---
Total: 7 tasks | Est. effort: 1L + 4M + 2S
