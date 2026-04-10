# Design: brown_agent-sophistication_01

## Architecture Overview

```
                         PLANNING CHAIN
  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
  │researcher│→ │persona-   │→ │antigravity│→ │deep-think │→ │solution- │
  │          │  │detector + │  │(back-plan)│  │(alignment)│  │explorer  │
  │          │  │researcher │  │           │  │           │  │(3-5 opts)│
  └──────────┘  └───────────┘  └──────────┘  └───────────┘  └────┬─────┘
                                                                  │
                              CRITIQUE LOOP (×3 iterations)       ▼
                         ┌──────────┐     ┌──────────────┐  ┌──────────┐
                         │architect │ ←── │architect-    │← │architect │
                         │(fix v2)  │     │critic (10    │  │(design   │
                         │          │ ──→ │NEW weakness) │  │v1)       │
                         └────┬─────┘     └──────────────┘  └──────────┘
                              │
                              ▼
                         ┌──────────┐
                         │decomposer│ → tasks.md
                         └──────────┘

                         BUILD CHAIN (per task)
  ┌──────────┐  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │qa (tests)│→ │coder v1  │ ←── │code-critic│ ←── │coder v2  │ → ...
  │          │  │          │ ──→ │(10 weak) │ ──→ │(fix)     │
  └──────────┘  └──────────┘     └──────────┘     └──────────┘
                                                        │
                         ┌──────────┐  ┌──────────┐     │
                         │contract- │← │handoff-  │← ───┘
                         │verifier  │→ │validator │→ peer-reviewer
                         └──────────┘  └──────────┘

                         VALIDATION CHAIN
  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
  │persona-      │→ │ux-tester │→ │learning-     │
  │validator     │  │(if UI)   │  │engine        │
  └──────────────┘  └──────────┘  └──────────────┘
```

## Approach

Add standardized headers to all 18 existing agents + create 2 new agent files. No structural changes to the markdown format — only additions. The activation protocol is a convention enforced by agent instructions, not by code.

## Component: Activation Protocol Header

### Template (added to top of every agent file, after title)
```markdown
## ACTIVATION
1. Read this entire file
2. Load context via context-manager for YOUR role
3. Read sudd/state.json for current phase
4. Check PREREQUISITES before proceeding
5. Execute your process steps in order
6. Write output to specified location
7. Update state.json if required
8. Hand off to NEXT agent (or RETURN control)

## PREREQUISITES
- Required phase: {phase}
- Required files: {list}
- Blocking conditions: {list}

## OUTPUTS
- Writes to: {path}
- Updates: {state fields}
- Next agent: {name} or RETURN

## PERMISSIONS
- CAN modify: {list}
- CANNOT modify: {list}
```

### Per-Agent Values

| Agent | Phase | Required Files | Writes To | Next Agent |
|-------|-------|---------------|-----------|------------|
| researcher | planning | vision.md or proposal.md | memory/research-cache/ | persona-detector |
| persona-detector | planning | vision.md or proposal.md | personas/ | persona-researcher |
| persona-researcher | planning | personas/{detected}.md | personas/{name}.md | antigravity |
| antigravity | planning | personas/*.md, proposal.md | specs.md (handoff section) | deep-think |
| deep-think | planning | proposal.md, specs.md | log.md (alignment notes) | solution-explorer |
| solution-explorer | planning | specs.md, research output | solutions.md | architect |
| architect | planning | solutions.md, specs.md | design.md | architect-critic (loop) |
| decomposer | planning | design.md (final) | tasks.md | RETURN (start build) |
| qa | build | design.md, specs.md | tests/ | coder |
| coder | build | tests/, design.md, specs.md | source code | code-critic (loop) |
| contract-verifier | build | specs.md, source code | log.md (compliance) | handoff-validator |
| handoff-validator | build | source code, specs.md | log.md (validation) | peer-reviewer |
| peer-reviewer | build | source code, design.md | log.md (review) | RETURN (next task) |
| persona-validator | validate | all outputs, persona research | log.md (gate score) | ux-tester or learning-engine |
| ux-tester | validate | running UI, persona research | log.md (ux results) | learning-engine |
| blocker-detector | any | error output | state.json (retry/stuck) | RETRY or RETURN |
| learning-engine | any | log.md, task outcomes | memory/ | RETURN |
| monitor | any | state.json, log.md | state.json (health) | RETURN |
| context-manager | any | (reads all) | (writes nothing) | RETURN |
| task-discoverer | inception | codebase, memory/ | changes/ (new proposals) | RETURN |

## Component: Solution Explorer (NEW)

### File: `sudd/agents/solution-explorer.md`
### Responsibility
Generate 3-5 candidate solutions, evaluate against weighted criteria, select winner with documented rationale.

### Interface
- Input: specs.md, researcher output, persona research, antigravity back-plan
- Output: `changes/{id}/solutions.md`

### solutions.md Schema
```markdown
# Solutions: {change-id}

## Candidates

### Candidate A: {name}
- Pattern: {architectural pattern}
- Tech stack: {key technologies}
- Persona fit: {how it serves each persona}
- Complexity: S/M/L
- Biggest risk: {risk}
- Cost profile: {open-source/free-tier/paid — with justification if paid}

### Candidate B: {name}
{same structure}

### Candidate C: {name}
{same structure}

## Decision Matrix

| Criterion | Weight | A | B | C |
|-----------|--------|---|---|---|
| Persona fit | 25% | /10 | /10 | /10 |
| Cost/deps | 20% | /10 | /10 | /10 |
| Speed | 15% | /10 | /10 | /10 |
| Maintainability | 20% | /10 | /10 | /10 |
| Scalability | 10% | /10 | /10 | /10 |
| Risk | 10% | /10 | /10 | /10 |
| **Weighted** | | **/10** | **/10** | **/10** |

## Decision

### Selected: Candidate {X} — {name}
**Because:** {rationale}
**Conditions for reconsideration:** {what would make this wrong}

### Rejected: Candidate {Y} — {name}
**Because:** {rationale}

### Rejected: Candidate {Z} — {name}
**Because:** {rationale}

## Trade-offs Accepted
- Accepted {tradeoff} in exchange for {benefit}
```

## Component: Decomposer (NEW)

### File: `sudd/agents/decomposer.md`
### Responsibility
Take PRD/vision + architecture and decompose into executable changes with granular tasks.

### Interface
- Input: vision.md or PRD.md, design.md (final, post-critique)
- Output: N × (proposal.md + specs.md + tasks.md) in `changes/active/{id}/`

### Process
1. Read PRD/vision, identify distinct feature groups
2. For each feature group → create a change directory
3. Write proposal.md (scoped to this feature, not the whole project)
4. Extract requirements → specs.md
5. Break specs into implementation steps → tasks.md
6. Order tasks by dependency, estimate S/M/L, flag parallelizable tasks

## Component: Critique Loop Integration

### How it works in agent files
The critique loop is NOT a separate agent file. It's a protocol defined in the architect and coder agents:

**In architect.md** — after OUTPUTS section:
```markdown
## CRITIQUE LOOP
After producing initial design.md:
1. Adopt "Senior AI Architect Reviewer" stance
2. Find exactly 10 weaknesses (numbered, with CRITICAL/HIGH/MEDIUM severity)
3. Fix weaknesses, produce revised design.md
4. Log dispositions in log.md
5. Adopt reviewer stance again — find 10 NEW weaknesses (no repeats)
6. Fix weaknesses, produce FINAL design.md
7. Log all 20 dispositions in log.md
```

**In coder.md** — after OUTPUTS section:
```markdown
## CRITIQUE LOOP
After producing initial implementation:
1. Adopt "Senior Code Reviewer" stance
2. Find exactly 10 weaknesses (numbered, with severity)
3. Fix weaknesses, run tests
4. Log dispositions in log.md
5. Adopt reviewer stance again — find 10 NEW weaknesses (no repeats)
6. Fix weaknesses, run tests
7. Log all 20 dispositions in log.md
```

### Critique output format (appended to log.md)
```markdown
## Critique Round {1|2} — {Architecture|Code}
### Weaknesses Found
1. [CRITICAL] {description}
2. [HIGH] {description}
...
10. [MEDIUM] {description}

### Dispositions
1. FIXED — {what was changed}
2. DEFERRED — {reason}
...
```

## Component: DESIGN_ISSUE Report

### Format (written by coder to log.md when design is flawed)
```markdown
## DESIGN_ISSUE — {timestamp}
**Task:** {task being implemented}
**Problem:** {what's wrong with the design}
**Attempted:** {what coder tried}
**Why it fails:** {specific technical reason}
**Suggested fix:** {what architect should change}
**Routing:** → architect (re-enter critique loop with this feedback)
```

## Component: Size-Aware Change Documentation

### Size estimation (by task-discoverer, add-task, decomposer)
```
S (< 1 hour):  "Move button to header", "Fix typo in error message", "Add env var"
M (1-4 hours): "Add pagination to API", "Refactor auth middleware"
L (4+ hours):  "Build notification system", "Add multi-tenant support"
```

### Documentation by size

**S — Lightweight (< 1 hour):**
```
changes/active/{id}/
  proposal.md   — what, why, persona, handoff, acceptance criteria
  tasks.md      — single task with [x] checkbox
```
No separate specs/design, but proposal.md MUST include persona reference and handoff line.
No full planning chain — but persona-validator still runs at gate.

**M/L — Full Suite (1+ hours):**
```
changes/active/{id}/
  proposal.md + specs.md + design.md + tasks.md + log.md
```
Full planning chain including persona-detector → persona-researcher → antigravity (handoffs).
specs.md has full Consumer Handoffs section with format/schema/validation per handoff.

### S-size templates

**proposal.md:**
```markdown
# Change: {id}

## Status
active

## What
{1-2 sentences}

## Why
{1 sentence — persona need}

## Persona
{persona-name} (see `personas/{name}.md`)

## Handoff
{what this produces} → consumed by {who/what}

## Acceptance Criteria
1. {criterion}

## Size: S
```

**tasks.md:**
```markdown
# Tasks: {id}

- [ ] {single task description matching acceptance criteria}
```

### Persona & handoff rules by size

| | S | M/L |
|---|---|---|
| Persona reference | Required in proposal.md (name + link to existing persona file) | Full persona-detector + persona-researcher creates/updates persona files |
| Handoff contract | 1-line in proposal.md: "X → consumed by Y" | Full Consumer Handoffs in specs.md (format, schema, validation per handoff) |
| Persona validation at gate | Yes — persona-validator still runs | Yes — full validation chain |
| New persona creation | No — must reference existing persona | Yes — persona-detector discovers, persona-researcher deep-researches |

### Completion tracking (all sizes)
tasks.md is always the single source of truth for what's done. One place to check, never two.

## Component: Task Discoverer v2

### Changes to `sudd/agents/task-discoverer.md`
- Fix paths: `openspec/project.md` → `sudd/vision.md`, `results/` → `sudd/changes/archive/`, `task-specs/` → `sudd/changes/active/`
- Output: creates `changes/active/{id}/proposal.md` (not `task-specs/{name}.md`)
- Estimate size (S/M/L) and create documentation appropriate to that size
- Change ID format: `discovered_{name}_{seq:02d}`

### Changes to `sudd/commands/micro/add-task.md`
- Fix paths: same as task-discoverer
- Output: creates `changes/active/{id}/proposal.md`
- Change ID format: `task_{name}_{seq:02d}`

## File Changes

### New Files (2)
- `sudd/agents/solution-explorer.md` — new agent (~80 lines)
- `sudd/agents/decomposer.md` — new agent (~80 lines)

### Modified Files (18 agent files)
Each gets ACTIVATION + PREREQUISITES + OUTPUTS (updated) + PERMISSIONS header added after the title line. Existing content preserved.

- `sudd/agents/researcher.md` — add headers (~15 lines added)
- `sudd/agents/persona-detector.md` — add headers
- `sudd/agents/persona-researcher.md` — add headers
- `sudd/agents/antigravity.md` — add headers
- `sudd/agents/deep-think.md` — add headers, update Next to solution-explorer
- `sudd/agents/architect.md` — add headers + CRITIQUE LOOP section + read solutions.md
- `sudd/agents/coder.md` — add headers + CRITIQUE LOOP section + DESIGN_ISSUE protocol + TDD order
- `sudd/agents/qa.md` — add headers + risk profiling + requirements tracing
- `sudd/agents/contract-verifier.md` — add headers (entry point already exists)
- `sudd/agents/handoff-validator.md` — add headers
- `sudd/agents/peer-reviewer.md` — add headers
- `sudd/agents/persona-validator.md` — add headers
- `sudd/agents/blocker-detector.md` — add headers
- `sudd/agents/learning-engine.md` — add headers + pre-task injection protocol
- `sudd/agents/context-manager.md` — add headers
- `sudd/agents/monitor.md` — add headers
- `sudd/agents/ux-tester.md` — add headers
- `sudd/agents/task-discoverer.md` — add headers + fix stale paths + output change proposals + size estimation

### Modified Files (other)
- `sudd/vision.md` — update agent table to include solution-explorer and decomposer (20 agents)
- `sudd/commands/micro/add-task.md` — fix paths, output change proposals instead of task-specs

### No changes needed
- `sudd/state.json` — no new fields required (existing escalation ladder unchanged)
- Go CLI (`sudd-go/`) — no changes needed
