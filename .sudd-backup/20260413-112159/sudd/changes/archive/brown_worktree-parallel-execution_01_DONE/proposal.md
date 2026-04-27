# Change: brown_worktree-parallel-execution_01

## Status
proposed

## Summary
Integrate Superpowers' git worktree isolation and subagent-driven-development review pattern into SUDD's orchestration loop. When SUDD dispatches parallel agents for independent tasks, each agent works in an isolated git worktree. Results are merged back with conflict detection. Also integrate the 2-stage review pattern (spec compliance → code quality) into SUDD's existing validation chain.

## Motivation
SUDD already dispatches agents in parallel (e.g., 6 agents for 23 tasks), but all agents work in the **same working directory**. This creates:
- File conflicts when 2+ agents modify the same file
- No isolation for experimental approaches
- Can't safely implement independent tasks in parallel when they touch overlapping files

Superpowers already solves this with three complementary skills:
1. **using-git-worktrees** — creates isolated workspaces with smart directory selection, safety verification, auto-setup
2. **subagent-driven-development** — fresh subagent per task + 2-stage review (spec compliance → code quality)
3. **dispatching-parallel-agents** — groups independent tasks, dispatches one agent per domain

SUDD should consume these patterns rather than reinvent them.

## Scope

### What's included:

#### 1. Worktree Integration in apply.md
When `apply.md` dispatches the coder agent for a task:
- If the task is independent (no deps on other in-progress tasks): create a git worktree
- Agent works in the isolated worktree
- On completion: merge worktree branch back to change branch
- On conflict: flag for manual resolution or sequential re-apply

#### 2. Worktree Integration in run.md Build Loop
The autonomous build loop should:
- Identify independent tasks from tasks.md (tasks with no shared dependencies)
- Dispatch each to a separate worktree
- Merge results sequentially after all complete
- Continue with dependent tasks in main workspace

#### 3. Two-Stage Review Pattern
Adapt Superpowers' implementer → spec-reviewer → code-quality-reviewer chain into SUDD:
- **Spec compliance**: maps to SUDD's existing `contract-verifier` agent
- **Code quality**: maps to SUDD's existing `peer-reviewer` agent
- Wire the sequence: coder → contract-verifier → peer-reviewer (before handoff-validator)

#### 4. Worktree Manager (new section in context-manager agent)
Add worktree lifecycle management to the existing context-manager agent:
- Create worktrees in `.worktrees/` (following Superpowers convention)
- Ensure `.worktrees/` is in .gitignore
- Auto-detect project setup (npm/pip/go)
- Cleanup worktrees after merge
- Track active worktrees in state

#### 5. Model Tier Selection for Subagents
Consume Superpowers' model selection strategy:
- Mechanical tasks (1-2 files, clear spec) → cheap/fast model
- Integration tasks (multi-file) → standard model
- Architecture/review tasks → most capable model
- Map to SUDD's existing escalation ladder

### What's NOT included:
- Worktrees for gate validators (they're read-only, don't need isolation)
- Worktrees for research/planning agents (they don't modify files)
- Custom worktree skill file (consume Superpowers directly, don't duplicate)
- Changes to the Go CLI installer

## Success Criteria
- [ ] `apply.md` can dispatch coder to a worktree for independent tasks
- [ ] `run.md` build loop identifies independent tasks and parallelizes with worktrees
- [ ] Two-stage review (contract-verifier → peer-reviewer) wired after coder
- [ ] context-manager handles worktree lifecycle (create, setup, merge, cleanup)
- [ ] `.worktrees/` convention followed, .gitignore safety check included
- [ ] Model tier selection integrated with SUDD escalation ladder
- [ ] Dependent tasks still run sequentially in main workspace (no regression)
- [ ] Conflict detection on merge-back with clear error messaging

## Dependencies
- Superpowers plugin installed (using-git-worktrees, subagent-driven-development skills)
- All prior SUDD changes completed (framework-hardening, workflow-reliability, impeccable-integration)

## Risks
- **Merge conflicts**: Independent tasks may turn out to share files. Mitigation: analyze task file lists before dispatching; fall back to sequential.
- **Worktree overhead**: Creating worktrees + running setup takes time. Mitigation: only use worktrees when 2+ independent tasks exist; skip for single-task changes.
- **Platform compatibility**: Git worktrees work on all platforms but `.worktrees/` path handling differs. Mitigation: use forward slashes, test on Windows.
