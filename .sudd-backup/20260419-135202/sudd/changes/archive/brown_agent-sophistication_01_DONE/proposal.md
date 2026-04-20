# Change: brown_agent-sophistication_01

## Status
proposed

## Summary
Upgrade SUDD's 18 agents from advisory instruction files to an autonomous, self-chaining agent system that can decompose a PRD + high-level architecture into executable work without human intervention. Adds structured solution exploration (divergent thinking before committing to an approach), red team critique loops, and a decomposer agent. Inspired by BMAD's maturity but adapted to SUDD's markdown-first, persona-driven philosophy.

## Motivation

Once a PRD.md and high-level architecture are defined, SUDD agents should be able to autonomously:
1. Decompose the PRD into changes (epics)
2. Break changes into granular tasks (stories)
3. Implement, test, validate, and learn — all without asking the user

**Current state:** Agents are advisory prose. They describe what SHOULD happen but don't enforce boundaries, don't chain autonomously, and don't decompose work. The jump from architect → coder is too large. There's no PM/PO equivalent that breaks high-level requirements into implementable units.

**BMAD comparison:** BMAD uses 10 agents with strict permission boundaries, executable task workflows, blocking conditions, and a PM → PO → SM → DEV → QA pipeline. SUDD can adopt these patterns while keeping its unique strengths (persona-first validation, handoff contracts, learning memory, escalation ladder).

## Scope

### 1. Agent Activation Protocol (All agents)
Every agent file gets a standardized header defining:
```markdown
## ACTIVATION
1. Read this entire file
2. Load context via context-manager for YOUR role
3. Read sudd/state.json for current phase
4. Check PREREQUISITES before proceeding
5. Execute steps in order
6. Write output to specified location
7. Update state.json
8. Hand off to NEXT agent (or return control)

## PREREQUISITES
- Required phase: {phase}
- Required files: {list}
- Blocking conditions: {list — halt and report if any are true}

## OUTPUTS
- Writes to: {file path}
- Updates: {state fields}
- Next agent: {agent name} or RETURN

## PERMISSIONS
- CAN modify: {list of files/sections}
- CANNOT modify: {list — prevents overwriting other agents' work}
```

### 2. New Agent: Decomposer (replaces manual task creation)
**Role:** Takes a PRD/vision + architecture and produces executable changes with granular tasks.

Equivalent to BMAD's PM+PO+SM combined, but automated:
```
Input:  PRD.md (or vision.md) + design.md (architecture)
Output: Multiple change proposals, each with:
        - proposal.md (scoped change, not the whole project)
        - specs.md (requirements for THIS change)
        - tasks.md (granular tasks, each completable in one cycle)

Process:
1. Read PRD, extract feature groups → these become CHANGES
2. For each change, extract requirements → these become SPECS
3. For each spec, break into implementation steps → these become TASKS
4. Order tasks by dependency
5. Estimate effort (S/M/L)
6. Identify which tasks can run in parallel
```

This is the missing link. Currently `/sudd:plan` does this manually. With the decomposer, `/sudd:run green` can go from PRD → fully planned changes autonomously.

### 3. Agent Permission Boundaries
Each agent gets explicit file permissions:

| Agent | CAN Modify | CANNOT Modify |
|-------|-----------|---------------|
| researcher | memory/research-cache/ | code, specs, design |
| persona-detector | personas/ | code, specs, design |
| persona-researcher | personas/ | code, specs, design |
| antigravity | changes/{id}/specs.md (handoff section) | code, design |
| deep-think | changes/{id}/log.md (alignment notes) | code, specs, design |
| architect | changes/{id}/design.md | code, specs, personas |
| decomposer (NEW) | changes/{id}/tasks.md, new change dirs | code, design |
| qa | tests/ | source code, specs, design |
| coder | source code only | specs, design, tests, personas |
| peer-reviewer | changes/{id}/log.md (review notes) | code, specs, design |
| handoff-validator | changes/{id}/log.md (validation) | code, specs, design |
| contract-verifier | changes/{id}/log.md (compliance) | code, specs, design |
| persona-validator | changes/{id}/log.md (gate score) | code, specs, design |
| blocker-detector | state.json (retry/stuck) | code, specs, design |
| learning-engine | memory/ | code, specs, design |
| context-manager | (reads only, writes nothing) | everything |
| monitor | state.json (health), changes/{id}/log.md | code, specs, design |
| ux-tester | changes/{id}/log.md (ux results) | code, specs, design |
| solution-explorer (NEW) | changes/{id}/solutions.md | code, design, tests |
| task-discoverer | changes/ (new proposals only) | existing code/specs |

### 4. Blocking Conditions (All agents)
Each agent defines when it MUST halt:

**Coder blocks when:**
- Design.md doesn't exist or is empty
- Tests from QA don't exist yet (TDD enforcement)
- Specs reference dependencies that aren't installed
- 3 consecutive failures on same task

**Architect blocks when:**
- No persona research available
- Vision.md is empty or vague
- Conflicting requirements detected in specs

**QA blocks when:**
- Design.md doesn't exist
- Acceptance criteria are missing or vague

**Solution Explorer blocks when:**
- Specs have fewer than 3 concrete requirements (not enough to differentiate candidates)
- No persona research available (can't score persona fit)
- Researcher output is empty (can't identify viable patterns)
- Can only generate fewer than 3 candidates (problem space not understood — request more research)

**Decomposer blocks when:**
- PRD/vision has no clear feature groups
- Architecture has no component boundaries
- Estimated total effort exceeds session budget

### 5. New Agent: Solution Explorer (divergent thinking before architecture)
**Role:** Generates and evaluates multiple candidate solutions before the architect commits to one. Currently the system jumps from "what do we need?" to "here's THE design" — no alternatives explored, no trade-offs documented, no rationale for why THIS approach over others.

```
Input:  specs.md + researcher output + persona research + antigravity back-plan
Output: changes/{id}/solutions.md — structured decision record

Process:
1. DIVERGE — Generate 3-5 candidate approaches (FORCED — cannot produce just one)
   Per candidate: name, architectural pattern, key tech choices, persona fit,
   complexity (S/M/L), biggest risk

2. EVALUATE — Score each candidate against weighted criteria:
   Persona fit (25%) | Cost/dependencies (20%) | Speed (15%) | Maintainability (20%) | Scalability (10%) | Risk (10%)
   Cost scoring: all open-source = 10, free tiers = 7, any paid dependency = 3-5 (must justify)
   Weights are defaults — explorer adjusts for context (prototype → speed↑, regulated → risk↑)

3. DECIDE & DOCUMENT — Select winner, reject others, all with explicit rationale
   For each rejected: WHY it lost
   For the winner: WHAT would make this the wrong choice (conditions for reconsideration)
   Trade-offs accepted: what was sacrificed and what was gained
```

**Why 3-5?** Two creates a false binary. Three is the minimum for genuine divergence. Five is the cap before evaluation becomes superficial. If only 2 come to mind → block, request more research.

**Quality layers:** Explorer picks the *right approach* (strategic) → Architect designs it in detail (tactical) → Critique loop stress-tests the design (verification). Three distinct failure modes caught at three distinct stages.

### 6. Red Team Critique Loop (Architecture + Coding)

**The core idea:** Every architecture decision and every code implementation goes through 3 iterations with forced self-critique. The agent doesn't just produce output — it attacks its own output, finds weaknesses, and fixes them BEFORE handing off.

#### Architecture Critique Loop (3 iterations)
```
ITERATION 1: Architect produces initial design.md
  ↓
ITERATION 2: CRITIQUE — Same or different agent adopts "Senior AI Architect Reviewer" stance.
  Instruction: "You are reviewing this architecture. Find exactly 10 weaknesses,
  blindspots, scalability issues, security gaps, over-engineering, missing edge cases,
  or assumptions that will break in production. Be ruthless. Number them 1-10."

  Output: 10 numbered weaknesses with severity (CRITICAL/HIGH/MEDIUM)
  ↓
  Architect reads the 10 weaknesses and produces REVISED design.md
  Log: which weaknesses were addressed, which were acknowledged but deferred (with reason)
  ↓
ITERATION 3: CRITIQUE AGAIN — "You reviewed this architecture before and found 10 issues.
  The architect addressed them. Review the REVISED design. Find 10 NEW weaknesses
  that weren't in your first review — dig deeper. Look at interactions between components,
  failure modes, data consistency, deployment concerns, monitoring gaps."

  Output: 10 NEW numbered weaknesses
  ↓
  Architect reads the 10 NEW weaknesses and produces FINAL design.md
  Log: all 20 weaknesses reviewed, final disposition for each

  Result: design.md has survived 2 rounds of adversarial review (20 weakness checks)
  before a single line of code is written.
```

#### Coding Critique Loop (3 iterations)
```
ITERATION 1: Coder produces initial implementation
  ↓
ITERATION 2: CRITIQUE — "You are a senior code reviewer. This code was just written.
  Find exactly 10 weaknesses: bugs, edge cases not handled, security vulnerabilities,
  performance issues, missing error handling, contract violations, empty data scenarios,
  race conditions, resource leaks, or assumptions that will fail. Number them 1-10."

  Output: 10 numbered code weaknesses with severity
  ↓
  Coder reads the 10 weaknesses and produces REVISED code
  Run tests after revision to verify nothing broke
  ↓
ITERATION 3: CRITIQUE AGAIN — "Review the REVISED code. The coder fixed the first 10 issues.
  Find 10 NEW weaknesses — look deeper. Check error propagation paths, check what happens
  when external services are down, check data validation at boundaries, check that the
  code actually serves the persona's needs (not just passes tests)."

  Output: 10 NEW numbered weaknesses
  ↓
  Coder reads the 10 NEW weaknesses and produces FINAL code
  Run tests again

  Result: Code has survived 2 rounds of adversarial review (20 weakness checks)
  before reaching the normal validation chain.
```

#### Why 3 iterations, not 2 or 5?
- **1 iteration**: No self-critique. Produces first-draft quality.
- **2 iterations**: One critique round catches obvious issues but misses deeper problems.
- **3 iterations**: Two critique rounds force progressively deeper analysis. The second critique MUST find NEW issues (not repeat the first), which forces examination of subtle interactions, edge cases, and production concerns.
- **4+ iterations**: Diminishing returns. The third review typically catches remaining issues; beyond that, the critic starts nitpicking or inventing problems.

#### Critique Loop Rules
1. **Each critique MUST produce exactly 10 weaknesses** — not 3, not "a few". The number 10 forces thoroughness. If the critic can only find 7 real issues, the remaining 3 must still be identified (even if MEDIUM severity).
2. **Second critique MUST find NEW weaknesses** — repeating issues from round 1 is forbidden. This prevents lazy reviewing.
3. **Every weakness gets a disposition**: FIXED, DEFERRED (with reason), or ACKNOWLEDGED (acceptable risk). No weakness is silently ignored.
4. **All 20 weaknesses are logged** in `changes/{id}/log.md` for learning-engine to capture patterns.
5. **The critique can be the SAME agent in a different stance** (cheaper) or a DIFFERENT model (more diverse perspective). Escalation tier determines which:
   - Retry 0-3: Same agent, different prompt stance
   - Retry 4+: Different model for critique (e.g., architect=Sonnet, critic=Opus)

### 7. Autonomous Agent Chaining (Updated with Critique Loops)
Define explicit chains so agents invoke the next agent automatically:

**Planning Chain (runs once per change):**
```
researcher → persona-detector → persona-researcher → antigravity → deep-think
  → solution-explorer (generate 3-5 candidates, evaluate, select winner)
  → architect (iteration 1: detailed design of selected approach)
  → architect-critic (iteration 2: find 10 weaknesses)
  → architect (iteration 2: fix weaknesses)
  → architect-critic (iteration 3: find 10 NEW weaknesses)
  → architect (iteration 3: fix weaknesses → FINAL design)
  → decomposer
```

**Build Chain (runs per task in tasks.md):**
```
qa (write tests)
  → coder (iteration 1: implement)
  → code-critic (iteration 2: find 10 weaknesses)
  → coder (iteration 2: fix weaknesses, run tests)
  → code-critic (iteration 3: find 10 NEW weaknesses)
  → coder (iteration 3: fix weaknesses, run tests → FINAL code)
  → contract-verifier → handoff-validator → peer-reviewer
```

**Validation Chain (runs after all tasks complete):**
```
persona-validator → [if UI: ux-tester] → learning-engine
```

**Error Chain (runs on any failure):**
```
blocker-detector → {RETRY: back to failed agent | BLOCKED: halt | STUCK: learning-engine + archive}
```

Each agent's output section specifies `Next: {agent}` so the orchestrator knows where to route.

### 8. PRD-to-Execution Autonomous Pipeline (Updated)
The full autonomous flow once PRD + architecture exist:

```
PRD.md + architecture.md
  ↓
decomposer: extract feature groups → create N changes
  ↓
For each change (can be parallel if independent):
  ↓
  Planning Chain:
    research → personas → back-plan → deep-think
    → solution-explorer (3-5 candidates → decision matrix → winner)
    → architect × 3 iterations (with 2 critique rounds = 20 weaknesses reviewed)
    → decomposer(tasks)
    ↓
  For each task (sequential within change):
    ↓
    Build Chain:
      qa(tests) → coder × 3 iterations (with 2 critique rounds = 20 weaknesses reviewed)
      → contract-verifier → handoff → peer-review
      ↓
    If fail → Error Chain → retry/escalate/stuck
      ↓
    If pass → mark task complete, next task
  ↓
  All tasks done → Validation Chain: persona-validator → ux-tester → learning-engine
    ↓
  If gate >= 95 → archive change, start next change
  If gate < 95 → accumulate feedback, retry change
```

### 9. Coder Agent Enhancement
Current coder is constrained ("follow design exactly, if wrong say so"). Upgrade to:
- **Read tests first** (TDD: understand what must pass)
- **Read design second** (understand approach)
- **Read specs third** (understand contracts)
- **Read lessons** (avoid known pitfalls)
- **Implement incrementally** (one function → run tests → next function)
- **Self-validate** before handoff (run tests locally, check contracts)
- **If design is flawed**: produce a DESIGN_ISSUE report instead of broken code — route to architect for redesign (not just "say so")
- **Participate in critique loop**: Accept 10 weaknesses from critic, fix them, accept 10 more, fix those. Output FINAL code only after iteration 3.

### 10. QA Agent Enhancement
Current QA just writes pytest files. Upgrade to:
- **Risk profiling** before writing tests (probability × impact matrix)
- **Requirements tracing** (Given-When-Then from specs → test cases)
- **Coverage targets** per risk level (HIGH risk = 100% coverage, LOW = smoke test)
- **NFR assessment** (security, performance, reliability — not just functional tests)
- **Test design document** alongside test code (explains what and why)

### 11. Architect Agent Enhancement
Current architect produces a design doc. Upgrade to:
- **Read PRD section relevant to THIS change** (not whole PRD)
- **Produce file-level design** (which files, which functions, which interfaces)
- **Define handoff contracts explicitly** (input/output schemas, not just prose)
- **Estimate complexity** (S/M/L per component)
- **Identify parallelizable work** (which tasks can run concurrently)
- **Produce acceptance criteria** that are directly testable by QA

### 12. Open Source First (Technology Selection Default)
**When the brief is silent** on technology choices, all agents default to open-source and free tools. This is a default, not a gate — if the PRD/brief explicitly specifies a paid service or states that accuracy is paramount due to legal/monetary risk, respect that decision and note expected costs in design.md.

**Default ladder (when brief doesn't specify):**
```
1. OPEN SOURCE — self-hosted, no API keys, no per-unit costs
2. FREE TIER — if open source genuinely can't do the job, within free limits at scale
3. PAID — only when ROI is massive and justified
```

**ROI threshold for paid (when not specified in brief):**
- Justified: free accuracy < 80% AND paid > 95%, or saves 100h+ engineering
- Not justified: marginal gains (97→99) at significant cost, or per-unit costs that scale with volume

**If the brief DOES specify:**
- "Use Landing.ai for PDF" → use it, note cost in design.md
- "Accuracy paramount, legal risk" → go premium, note expected costs
- The brief is the authority. This principle only fills the gap when the brief is silent.

**Agent behavior:**
- **Solution explorer**: Cost is 20% of candidate scoring. Paid dependencies start at a penalty unless brief justifies them.
- **Architect**: Flag any paid dependency in design.md: `PAID: {service} — {cost/month} — {brief reference or justification}`
- **Researcher**: Present open-source option first. Paid recommendation requires: what's free, why it's insufficient, cost delta.

**LLM model selection:** Handled by the existing escalation ladder (retry 0-1 free, 2-3 Sonnet, 4-5 Sonnet, 6-7 Opus, 8+ STUCK). No changes needed.

### 13. Learning Engine Enhancement
Currently write-only (captures lessons, doesn't enforce). Upgrade to:
- **Pre-task briefing**: Before each agent runs, inject top-3 relevant lessons
- **Pattern-based routing**: If a pattern matches (e.g., "API returns empty data" seen 3x), automatically add a specific test for it
- **Confidence decay**: Lessons lose confidence over time unless reinforced
- **Cross-change learning**: Lessons from change A inform change B within same session

### 14. Lightweight Changes + Task Discoverer Fix
**Problem:** task-discoverer and add-task create standalone `task-specs/{name}.md` files — a v1 leftover. These don't integrate with the v2 change lifecycle (no tracking, no completion, no archiving). Meanwhile, a trivial fix (move a button) shouldn't require 5 markdown files with 200 lines each.

**Fix — size-aware change proposals:**
Task-discoverer and add-task now create change proposals in `changes/active/{id}/`, with documentation depth scaling to effort:

```
SIZE S (< 1 hour): Lightweight
  proposal.md — what, why, persona reference, handoff line, acceptance criteria
  tasks.md    — single task with checkbox
  Persona-validator still runs at gate. No new persona creation — must reference existing.

SIZE M/L (1+ hours): Full Suite
  proposal.md + specs.md + design.md + tasks.md + log.md
  Full planning chain: persona-detector, persona-researcher, antigravity (handoffs),
  solution-explorer, architect, critique loops. specs.md has full Consumer Handoffs.
```

Why two tiers: tasks.md is always where completion lives. Anything over an hour needs specs + design + handoff contracts — without them, things don't wire properly. Even S-size must name the persona and what consumes the output — SUDD's core promise is persona-driven validation.

**Completion tracking** — every change, regardless of size, gets:
- `[x]` checkboxes in tasks.md (always the single source of truth)
- Archive to `changes/archive/{id}_DONE/` on completion
- Entry in state.json stats

**Task-discoverer update:**
- Fix stale paths: `openspec/project.md` → `sudd/vision.md`, `results/` → `sudd/changes/archive/`, `task-specs/` → `sudd/changes/active/`
- Output: change proposals (not standalone task-spec files)
- Estimate size (S/M/L) and create appropriate documentation level

**Add-task command update:**
- Same path fixes
- Creates `changes/active/{id}/proposal.md` instead of `task-specs/{name}.md`

### What's NOT included:
- New agent creation beyond decomposer and solution-explorer
- UI/TUI changes to the Go CLI
- Multi-agent concurrent execution (agents still run sequentially within a chain)

## Success Criteria
- [ ] All 18 agents + decomposer + solution-explorer have standardized ACTIVATION / PREREQUISITES / OUTPUTS / PERMISSIONS headers
- [ ] Solution explorer generates 3-5 candidate approaches with decision matrix for every change
- [ ] Rejected candidates documented with explicit rationale (why not)
- [ ] Architect receives selected approach from solution-explorer (not inventing from scratch)
- [ ] Decomposer agent can take a PRD + architecture and produce multiple changes with tasks
- [ ] Every agent defines explicit blocking conditions (halt, don't produce garbage)
- [ ] Agent chaining: each agent's OUTPUTS section names the NEXT agent
- [ ] Coder produces DESIGN_ISSUE report instead of broken code when design is flawed
- [ ] QA produces risk profile + requirements trace alongside test code
- [ ] Architect produces file-level design with testable acceptance criteria
- [ ] Permission boundaries: coder CANNOT modify specs/design, architect CANNOT modify code
- [ ] Learning engine injects top-3 lessons before each agent runs
- [ ] Open-source-first: when brief is silent, agents default to open-source tech stacks
- [ ] Paid dependencies flagged in design.md with cost estimate and justification
- [ ] Solution explorer scores cost at 20% weight; paid deps penalized unless brief justifies
- [ ] Task-discoverer creates change proposals (not standalone task-spec files)
- [ ] Documentation scales with size: S = proposal+tasks only, M = +specs, L = full suite
- [ ] Every change has completion tracking ([x] checkboxes + archive)
- [ ] Full autonomous run: PRD → implemented + validated changes without human input

## Dependencies
- `brown_framework-hardening_01` (completed — thresholds, state machine)
- `brown_multi-framework-port_01` (proposed — port command handles PRD ingestion)

## Risks
- **Over-constraining agents**: Too-strict permissions may cause deadlocks when agents need to fix cross-cutting issues. Mitigation: DESIGN_ISSUE escape hatch routes back to architect.
- **Decomposer quality**: Automated PRD decomposition may produce poorly scoped changes. Mitigation: deep-think validates alignment before build starts.
- **Chain rigidity**: Fixed chains may not suit all project types. Mitigation: chains are defaults, not mandates — `/sudd:run` can skip steps if artifacts already exist.
- **Context window pressure**: Activation headers + permissions add tokens to every agent call. Mitigation: context-manager strips non-relevant sections.
