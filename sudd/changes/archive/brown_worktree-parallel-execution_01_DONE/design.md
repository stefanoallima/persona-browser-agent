# Design: brown_worktree-parallel-execution_01

## Architecture Overview

```
Current SUDD Build Loop:
  for each task:
    coder → handoff-validator → persona-validator
    (all in same directory, sequential)

New Build Loop:
  analyze dependencies → group into batches

  for each batch:
    if batch.size == 1:
      coder → contract-verifier → peer-reviewer → handoff-validator
      (same directory, no worktree needed)

    if batch.size > 1:
      for each task in batch (PARALLEL):
        create worktree → coder (in worktree) → contract-verifier → peer-reviewer
      merge all worktree branches back sequentially
      handoff-validator (on merged result)

  design-reviewer (if frontend files)
  persona-validator (final gate)
```

## Component: Dependency Analyzer (in run.md/apply.md)

### Responsibility
Analyze tasks.md to identify which tasks can run in parallel.

### Algorithm
```
Input: tasks[] from tasks.md, each with { id, dependencies[], files[] }
Output: batches[][] where each batch contains independent tasks

1. Build dependency graph from Dependencies: fields
2. For tasks with no explicit Dependencies:, check Files: for overlap
3. Topological sort to get execution order
4. Group tasks at the same depth level into batches
5. Within each batch, verify no file overlap
   - If overlap found: split into sequential sub-batches

Example:
  T1: no deps, files: [a.go]
  T2: no deps, files: [b.go]
  T3: depends on T1, files: [a.go, c.go]
  T4: no deps, files: [d.go]

  Batch 1: [T1, T2, T4]  ← all independent, no file overlap
  Batch 2: [T3]           ← depends on T1
```

## Component: Worktree Manager (addition to context-manager.md)

### Responsibility
Create, setup, merge, and cleanup git worktrees for parallel task execution.

### Interface (new section in context-manager.md)

```markdown
## Worktree Management

### Create Worktree
When dispatching a parallel task:
1. Ensure `.worktrees/` directory exists and is in .gitignore:
   ```bash
   git check-ignore -q .worktrees 2>/dev/null || {
     echo ".worktrees/" >> .gitignore
     git add .gitignore && git commit -m "chore: add .worktrees to gitignore"
   }
   ```
2. Create worktree:
   ```bash
   git worktree add .worktrees/{change-id}-{task-id} -b sudd/{change-id}-{task-id}
   ```
3. Auto-detect and run project setup:
   - `package.json` → `npm install`
   - `go.mod` → `go mod download`
   - `requirements.txt` → `pip install -r requirements.txt`
   - `pyproject.toml` → `poetry install`
   - None of the above → skip setup

### Merge Worktree
After task completion:
1. Checkout target branch: `git checkout sudd/{change-id}`
2. Merge: `git merge sudd/{change-id}-{task-id} --no-ff -m "feat({change-id}): merge {task-id} from worktree"`
3. If conflict:
   - Log conflicting files to log.md
   - Abort merge: `git merge --abort`
   - Re-run task sequentially in main workspace
4. If success: cleanup worktree

### Cleanup Worktree
After successful merge or on failure:
1. `git worktree remove .worktrees/{change-id}-{task-id}`
2. `git branch -d sudd/{change-id}-{task-id}` (delete merged branch)
3. Note in log.md: "Worktree {task-id} cleaned up"

### Track Active Worktrees
Append to log.md during execution:
```markdown
## Worktree Status
| Task | Worktree Path | Branch | Status |
|------|--------------|--------|--------|
| T01  | .worktrees/{change}-T01 | sudd/{change}-T01 | merged |
| T02  | .worktrees/{change}-T02 | sudd/{change}-T02 | active |
```
```

## Component: Two-Stage Review (in apply.md)

### Responsibility
Wire Superpowers' spec-compliance → code-quality review pattern into SUDD's existing agent chain.

### Sequence
```
Current apply.md chain:
  3a. coder
  3a.5. design-reviewer (if frontend)
  3b. handoff-validator

New chain:
  3a.   coder
  3a.5. design-reviewer (if frontend)
  3b.   contract-verifier (spec compliance — does code match specs?)
  3c.   peer-reviewer (code quality — is code clean, tested, well-structured?)
  3d.   handoff-validator (boundary validation — does output match contract?)

If 3b fails: feedback → coder re-implements → re-run 3b
If 3c fails: feedback → coder fixes quality → re-run 3c
Only after 3b + 3c pass: proceed to 3d
```

### Mapping to Superpowers
| Superpowers Role | SUDD Agent | What It Checks |
|-----------------|------------|----------------|
| Implementer | coder | Writes code, tests, commits |
| Spec Reviewer | contract-verifier | Code matches specs.md requirements |
| Code Quality Reviewer | peer-reviewer | Code quality, patterns, tests |
| (no equivalent) | handoff-validator | Output format matches consumer contract |
| (no equivalent) | design-reviewer | Frontend design quality (Impeccable) |

## Component: Model Tier Selector (in run.md)

### Responsibility
Choose the cheapest model that can handle each task, based on complexity signals.

### Rules
```
Task complexity → Model tier:

if task.effort == "S" AND task.files.length <= 2:
  tier = "free"       # opencode/GLM
elif task.effort == "M" OR task.files.length <= 4:
  tier = "standard"   # sonnet
else:  # effort == "L" OR files > 4 OR architecture/design
  tier = "capable"    # opus

# Override: SUDD escalation ladder on retries
if retry >= 2: tier = max(tier, "standard")
if retry >= 4: tier = max(tier, "standard")  # sonnet for all
if retry >= 6: tier = "capable"              # opus for all
```

## File Changes

### Modified Files
- `sudd/commands/micro/apply.md` — add worktree dispatch for independent tasks, add 2-stage review (contract-verifier → peer-reviewer after coder)
- `sudd/commands/macro/run.md` — add dependency analysis, batch parallelization with worktrees, model tier selection
- `sudd/agents/context-manager.md` — add Worktree Management section (create, merge, cleanup, track)

### Files NOT Changed
- `sudd/agents/contract-verifier.md` — already exists, no changes needed
- `sudd/agents/peer-reviewer.md` — already exists, no changes needed
- `sudd/agents/coder.md` — no changes needed (works the same in worktree)
- `sudd/sudd.yaml` — no new agents added
