# Change: brown_workflow-reliability_01

## Status
proposed

## Summary
Fix 10 workflow reliability gaps and port 5 critical v1 mechanisms to v2 — without reintroducing v1's fatal flaw (chained Python modules passing JSON between steps that constantly broke on formatting). Every solution stays markdown-first: agents read/write markdown files, not JSON payloads between process boundaries.

## Motivation

**The 10 weaknesses** found in a cross-cutting review of all commands and agents reveal that SUDD v2 has a solid *concept* but an unreliable *wiring*. Agents are invoked but HOW is undefined. Escalation is described but never implemented. Feedback accumulates but has no pipe. Phases exist but have no formal transitions.

**The v1 gaps** reveal that v2 dropped several mechanisms that prevented real failures: traceability (anti-cheating), root cause classification, structured postmortems, contract revision, and cost tracking.

**The v1 lesson we MUST NOT repeat:** SUDD v1 had 30+ Python modules chained together, passing JSON between steps. The JSON formatting broke constantly — field name mismatches, boolean logic errors, schema drift. This killed the system. Every solution in this proposal MUST stay within v2's markdown-first model: agents read markdown files, produce markdown files, and the CLI agent orchestrates by reading state.json and invoking the next agent prompt. No inter-process JSON, no typed schemas between agents, no Python glue.

## Scope

### 1. Agent Invocation Protocol
**Problem:** Commands say `Task(agent=coder)` but never define what that means mechanically.

**Solution:** SUDD agents are dispatched as **subagents** using the CLI tool's native agent/subagent capabilities. The orchestrator (the command being executed) reads the agent .md file and spawns it as a subagent with that markdown as its instructions.

```markdown
## How Agent Invocation Works
"Task(agent=X)" means:
1. Read `sudd/agents/X.md`
2. Spawn a subagent with X.md content as its prompt/instructions
3. Include in the prompt: the files listed in X.md's PREREQUISITES
4. Subagent executes X.md's process steps
5. Subagent writes output to X.md's OUTPUTS location
6. Orchestrator reads the output and continues to NEXT agent

Independent agents can be spawned IN PARALLEL:
  Task(agent=researcher)        ─┐
  Task(agent=persona-detector)  ─┼─ all spawn simultaneously
  Task(agent=persona-researcher) ─┘

Sequential agents wait for predecessor output:
  Task(agent=architect)  → waits for solutions.md
  Task(agent=coder)      → waits for design.md + tests
```

**CLI-specific mechanics:**
- **Claude Code**: uses the Agent tool to spawn subagents with agent .md as prompt
- **OpenCode**: uses the built-in agent dispatch (opencode agents are defined in .opencode/)
- **Crush**: uses crush's command/agent dispatch

Each CLI tool has its own subagent mechanism. SUDD agent .md files are the shared instructions — the CLI tool decides HOW to dispatch them. sync.sh already copies commands to each CLI's folder; agent files work the same way.

**What this is NOT:**
- Not a Python process spawner
- Not JSON-passing between processes
- Not a custom orchestrator — the CLI tool IS the orchestrator
- Agents communicate via markdown files on disk, not in-memory payloads

### 2. Centralized Agent Configuration (sudd.yaml)
**Problem:** "Retry 2-3: use Sonnet" — but how? No command implements this. Model selection is undocumented. Users would need to search through 20+ markdown files to change agent behavior.

**Solution:** Centralize all agent configuration in `sudd/sudd.yaml`. One file to control model assignments, escalation tiers, and per-agent overrides. V1 referenced `sudd.yaml` but never defined its schema — now we do.

```yaml
# sudd/sudd.yaml — Central agent configuration
# Change models here, not in agent .md files

# Default escalation ladder (applies to all agents unless overridden)
escalation:
  default_tier: free
  ladder:
    0-1: free        # GLM, opencode, local models
    2-3: sonnet      # + Sonnet for validation agents
    4-5: sonnet      # Sonnet for all agents
    6-7: opus        # Opus for all agents
    8: stuck          # Mark STUCK, stop retrying

# Per-agent model assignment
# Principle: judgment/strategic agents → opus, analytical → sonnet, execution → free
agents:
  # JUDGMENT TIER (opus) — these make critical decisions that shape everything downstream
  solution-explorer: { tier: opus }   # picks the approach — wrong choice wastes the entire change
  architect:         { tier: opus }   # designs the solution — bad design = bad code
  deep-think:        { tier: opus }   # alignment validation — catches vision drift
  decomposer:        { tier: opus }   # breaks down work — bad decomposition = bad tasks
  persona-validator: { tier: opus }   # THE gate — must catch real issues, not rubber-stamp

  # ANALYTICAL TIER (sonnet) — need reasoning depth but within constrained formats
  researcher:        { tier: sonnet } # needs to find and evaluate information
  antigravity:       { tier: sonnet } # back-planning requires working backward from outcomes
  qa:                { tier: sonnet } # test design needs understanding of edge cases
  peer-reviewer:     { tier: sonnet } # code review needs technical depth
  coder:             { tier: sonnet } # implementation needs problem-solving ability

  # EXECUTION TIER (free) — follow templates, check boxes, classify, route
  persona-detector:  { tier: free }   # pattern matching against consumer types
  persona-researcher:{ tier: free }   # structured research following a template
  contract-verifier: { tier: free }   # checklist verification against schema
  handoff-validator: { tier: free }   # checklist verification of outputs
  blocker-detector:  { tier: free }   # classification into 3 categories
  learning-engine:   { tier: free }   # append to lessons.md following template
  context-manager:   { tier: free }   # reads and filters, writes nothing
  monitor:           { tier: free }   # reads state, flags thresholds
  task-discoverer:   { tier: free }   # scans codebase, creates proposals
  ux-tester:         { tier: free }   # follows test script with browser

# Test framework (auto-detected, can be overridden)
# test_command: "go test ./..."

# Cost mode (determines which tier assignments above are active)
# balanced:      use the per-agent tiers above (opus/sonnet/free as assigned) — DEFAULT
# free-first:    override ALL agents to free, escalate only on failure
# quality-first: override analytical tier to opus (15 opus + 5 free)
#
# User sets this explicitly. SUDD never switches cost_mode on its own.
cost_mode: balanced
```

**How it works:**
- Commands read `sudd/sudd.yaml` to determine which model/tier to use when spawning each agent
- On retry, blocker-detector updates the active tier based on the escalation ladder
- The user edits ONE file to change model assignments — no searching through agent .md files
- Agent .md files contain behavior instructions only, not model configuration
- `sudd.yaml` ships with `free` defaults for everything — user upgrades specific agents as needed

**Escalation mechanics:**
- On retry, the orchestrator reads `retry_count` from state.json
- Looks up the ladder in sudd.yaml: retry 3 → tier `sonnet`
- When spawning the next agent, passes the tier as context
- CLI tool maps tier to actual model (e.g., sonnet → claude-sonnet-4-6)

**Cost modes:**
```
balanced (DEFAULT):
  Uses per-agent tiers as assigned above (5 opus + 5 sonnet + 10 free)
  Best balance of quality and cost for most projects.

free-first (user-initiated):
  Overrides ALL agents to free tier. Escalation ladder promotes on failure.
  For: budget-constrained work, experimentation, simple changes.
  Set: cost_mode: free-first

quality-first (user-initiated):
  Promotes analytical agents to opus (15 opus + 5 free).
  For: critical projects, regulated industries, complex architecture.
  Set: cost_mode: quality-first
```

SUDD never switches cost_mode on its own. The user sets it explicitly in sudd.yaml. The default ships as `balanced` because judgment agents need strong models to avoid wasting entire changes on bad decisions.

### 3. Feedback Pipe Between Retries
**Problem:** Gate fails → "accumulate feedback" → but where? The coder on retry has no structured way to receive prior feedback.

**Solution:** Dedicated feedback section in log.md, with a stable heading the coder always reads:

```markdown
## Accumulated Feedback (read this FIRST on retry)
### Retry 1 — Gate Score: 72/100
- Persona "API Client": pagination missing, error messages vague
- Persona "Admin": all good (97/100)
### Retry 2 — Gate Score: 81/100
- Persona "API Client": pagination added but cursor-based needed, not offset
```

**Rule changes:**
- Gate command APPENDS to `## Accumulated Feedback` section (never overwrites)
- Apply command: coder's PREREQUISITES now include "Read ## Accumulated Feedback in log.md"
- Context-manager compresses old feedback if > 3 retries (keeps latest 2 + summary of older)

No new files. No JSON. Just a markdown section with a stable heading.

### 4. Formal Phase Enum + Transitions
**Problem:** Phases are strings with no formal definition. An agent could set phase to anything.

**Solution:** Define the enum and legal transitions in state.schema.json:

```
inception → planning → build → validate → complete
                         ↑        │
                         └────────┘  (gate fail → retry)
```

Valid transitions:
```
inception → planning     (triggered by: /sudd:new or /sudd:plan)
planning  → build        (triggered by: /sudd:plan completion)
build     → validate     (triggered by: /sudd:test pass)
validate  → build        (triggered by: /sudd:gate fail → retry)
validate  → complete     (triggered by: /sudd:gate pass)
complete  → inception    (triggered by: /sudd:done)
```

Add validation: before writing phase to state.json, check that the transition is legal. If not, log a warning and don't update. This is a markdown comment in every command that sets phase — not code enforcement.

### 5. Handoff Contract Schema
**Problem:** specs.md has "Consumer Handoffs" but no standard format. Validators have nothing machine-readable to check against.

**Solution:** Standardize the handoff section format in specs.md as structured markdown (not JSON — learned from v1):

```markdown
### Handoff: {Producer} → {Consumer}
- **Format**: markdown | json | binary | CLI output
- **Location**: {file path or stdout}
- **Required fields**: {comma-separated list}
- **Validated by**: handoff-validator checks {what specifically}
- **Error case**: if {condition}, then {what happens}
```

This is structured enough for a validator to parse (headings + bullet points with bold keys) but is still readable markdown. Not JSON. Not YAML. Just markdown with conventions.

### 6. QA Early Involvement in Planning Chain
**Problem:** QA sees the design for the first time at build time. No early input on testability.

**Solution:** Add a lightweight QA review step after architect produces FINAL design (post-critique-loop, pre-decomposer):

```
Planning chain:
  ... → architect (FINAL design) → qa-review → decomposer
```

QA-review is NOT the full QA agent. It's a focused check:
- Are acceptance criteria testable? (vague criteria = block)
- Are there components that can't be tested? (flag for architect)
- What test framework/approach is appropriate?

Output: append `## Testability Notes` to design.md. Takes < 5 minutes, prevents building untestable designs.

This uses the existing QA agent with a constrained scope, not a new agent.

### 7. Brown Mode Research Gap
**Problem:** Brown mode skips research entirely, even when no persona research exists.

**Solution:** Change the condition from `if mode == green` to `if research artifacts don't exist`:

```
Before:  if mode == green → run research agents
After:   if personas/*.md has only default.md OR specs.md has no Consumer Handoffs → run research agents
```

This is a one-line condition change in plan.md. Brown mode that HAS research skips it (fast). Brown mode that DOESN'T have research runs it (correct).

### 8. Test Framework Detection
**Problem:** `/sudd:test` assumes pytest. Projects use Go tests, Jest, Vitest, etc.

**Solution:** Add test framework detection to the test command:

```markdown
## Test Framework Detection
1. Check for existing test files:
   - `*_test.go` → `go test ./...`
   - `*.test.ts` or `*.spec.ts` → look for vitest/jest config
   - `test_*.py` or `*_test.py` → `pytest`
   - `Makefile` with `test` target → `make test`
2. Check config files: package.json (scripts.test), Makefile, pyproject.toml
3. If multiple found, list and ask user (once per project, save to state.json)
4. If none found, QA agent creates test infrastructure as first task
```

Store detected framework in state.json: `"test_command": "go test ./..."`. One-time detection, reused across retries.

### 9. Retry Context Continuity
**Problem:** When gate fails and routes back to coder, there's no protocol ensuring the coder reads prior feedback, critique results, or failure context.

**Solution:** Define a "retry briefing" protocol in the apply command:

```markdown
## On Retry (retry_count > 0)
Before invoking coder, prepare retry context:
1. Read `## Accumulated Feedback` from log.md (from scope item 3)
2. Read latest critique dispositions from log.md
3. Read learning-engine's top-3 relevant lessons
4. Summarize in a RETRY BRIEFING block passed to coder:

RETRY BRIEFING (attempt {N} of 8):
  Previous score: {gate_score}/100
  Failures: {list from feedback}
  Tier: {recommended_tier}
  Key lesson: {top lesson}

  FIX THESE SPECIFIC ISSUES. Do not rewrite from scratch.
```

This ensures the coder doesn't start fresh — it gets a focused briefing on what to fix. Context-manager strips everything else to keep the window clean.

### 10. Stuck Change Rollback
**Problem:** STUCK changes say "rollback" but never generate the file list or commands.

**Solution:** Track modified files in log.md as they're created:

```markdown
## Files Modified
- `src/api/routes.py` — T03: added pagination endpoint
- `src/api/models.py` — T03: added cursor model
- `tests/test_routes.py` — T04: pagination tests
```

Apply command appends to this section after each task. Done command reads it to generate rollback:

```bash
# Rollback for brown_feature_01 (STUCK at task T05)
git checkout main -- src/api/routes.py src/api/models.py tests/test_routes.py
```

No new files. Just a section in log.md that accumulates, and done.md reads it.

### 11. Traceability Report (from v1 persona-engine)
**Problem:** V1 had anti-cheating: detect if the persona's goal was achieved via side effects (unmapped success). V2 persona-validator doesn't check this.

**Solution:** Add a traceability check to persona-validator:

```markdown
## Traceability Check
After scoring, verify that success is MAPPED:
1. For each acceptance criterion marked "pass":
   - Identify WHICH code/output satisfies it
   - If no specific code maps to it → flag as UNMAPPED
2. If any criterion is UNMAPPED:
   - Score cannot exceed 80 regardless of apparent success
   - Log: "UNMAPPED SUCCESS: {criterion} — appears to pass but no traceable implementation found"
```

This prevents the gate from passing when tests accidentally succeed (e.g., test passes because data is empty, not because the feature works).

### 12. Root Cause Classification (from v1 learning-layer)
**Problem:** V2 blocker-detector classifies as RETRY/BLOCKED/STUCK but not WHY. Learning engine can't detect patterns without cause categories.

**Solution:** Add root cause classification to blocker-detector output:

```markdown
## Classification
- Action: RETRY | BLOCKED | STUCK
- Root Cause: LOGIC_ERROR | SPEC_ERROR | EXTERNAL_DEPENDENCY | CONTEXT_DRIFT | DESIGN_FLAW
```

Five categories:
- **LOGIC_ERROR**: Bug in implementation (wrong algorithm, off-by-one, null check)
- **SPEC_ERROR**: Specs are wrong or ambiguous (requirement contradiction, missing case)
- **EXTERNAL_DEPENDENCY**: Missing API key, service down, package not available
- **CONTEXT_DRIFT**: Agent lost track of requirements mid-implementation
- **DESIGN_FLAW**: Architecture doesn't support what's needed (→ DESIGN_ISSUE to architect)

Learning engine uses root cause to detect patterns: "3 SPEC_ERRORs in a row → specs need review before more coding."

### 13. Structured Postmortems (from v1 learning-layer)
**Problem:** V2 lessons.md captures what worked/failed but not structured failure analysis with hypothesis and resolution.

**Solution:** Extend the lessons.md template for failed tasks:

```markdown
### [STUCK] {task-name} — {date}
**Tags:** {domain}, {technology}
**Root Cause:** {from blocker-detector classification}
**Agent:** {which agent failed}
**Error:** {specific error or failure}
**Hypothesis:** {why this happened — agent's best guess}
**Resolution:** {what fixed it, or "UNRESOLVED" if stuck}
**Prevention:** {what would prevent this in future tasks}
```

The hypothesis field is critical — it forces the learning engine to theorize, not just log. Future agents read these and avoid the same trap.

### 14. Contract Revision on Escalation
**Problem:** When implementation repeatedly fails because specs/contracts are wrong, the architect can't fix them (specs are in the CANNOT-modify list).

**Solution:** Add a CONTRACT_REVISION escape hatch, similar to DESIGN_ISSUE:

```markdown
## CONTRACT_REVISION — {timestamp}
**Task:** {task being implemented}
**Contract:** {which handoff contract in specs.md}
**Problem:** {why the contract is wrong/impossible}
**Evidence:** {what was tried, how it failed}
**Suggested revision:** {what the contract should say instead}
**Routing:** → architect (revise specs.md handoff contract, then re-enter build)
```

Rules:
- Only triggered after 2+ failed retries on the SAME contract violation
- Architect can ONLY modify the specific handoff contract flagged (not rewrite all specs)
- Original contract preserved in log.md for audit trail
- After revision, retry count resets to 0 for that task

This is the missing feedback loop: coder → "this contract is impossible" → architect → revise → coder retries.

### 15. Per-Change Cost Awareness
**Problem:** V1 tracked token costs per task. V2 has zero cost visibility.

**Solution:** Lightweight cost logging in log.md (not precise tracking — that requires Python tooling we don't want):

```markdown
## Cost Log
| Step | Agent | Tier | Est. Tokens |
|------|-------|------|-------------|
| Planning | researcher | free | ~2K |
| Planning | architect ×3 | free | ~8K |
| Build T01 | qa | free | ~1K |
| Build T01 | coder ×3 | free | ~6K |
| Gate | persona-validator ×3 | free | ~3K |
| **Total** | | | **~20K** |
```

This is approximate — agents self-report their estimated token usage. Not precise, but gives visibility into where budget goes. If a change exceeds ~100K tokens, monitor agent flags it.

No Python, no API calls for usage stats. Just self-reported estimates in a markdown table.

### What's NOT included:
- Auto-rollback on deployment (v1 sentinel-ops — out of scope for framework)
- Smart CI skipping (v1 sentinel-ops — deployment concern, not framework)
- mem0 or external memory dependency (v2 stays file-based)
- Per-task cost enforcement/budget gates (too complex without Python; awareness is enough)

## Success Criteria
- [ ] Agent invocation protocol documented in every command file
- [ ] `sudd/sudd.yaml` exists with per-agent tier config, escalation ladder, and cost_mode
- [ ] Commands read sudd.yaml for model tier when spawning agents
- [ ] Escalation tier displayed on retry: "Retry N/8 — Escalating to: {tier}"
- [ ] log.md has `## Accumulated Feedback` section, coder reads it on retry
- [ ] Phase transitions formally defined with validation in commands
- [ ] Handoff contracts have standardized markdown schema in specs.md
- [ ] QA review step added to planning chain (after architect, before decomposer)
- [ ] Brown mode runs research when persona/handoff artifacts are missing
- [ ] Test framework auto-detected and stored in state.json
- [ ] Retry briefing protocol ensures coder receives prior failure context
- [ ] Files Modified section in log.md enables rollback on STUCK
- [ ] Persona-validator has traceability check (unmapped success = max 80)
- [ ] Blocker-detector classifies root cause (5 categories)
- [ ] Lessons.md has structured postmortem format for failed tasks
- [ ] CONTRACT_REVISION escape hatch allows architect to fix impossible contracts
- [ ] Cost log in log.md provides per-change visibility

## Dependencies
- `brown_framework-hardening_01` (completed)
- `brown_agent-sophistication_01` (proposed — activation headers, permissions, critique loops referenced here)

## Risks
- **Over-specifying markdown conventions**: Too many required sections in log.md/specs.md adds cognitive load. Mitigation: sections are only populated when relevant (retry briefing only on retry, postmortem only on failure).
- **Self-reported cost estimates are inaccurate**: Agents may over/under-estimate tokens. Mitigation: this is for awareness, not enforcement. Order-of-magnitude is sufficient.
- **Contract revision abuse**: Coder might route every failure to CONTRACT_REVISION instead of fixing code. Mitigation: requires 2+ retries on same violation before allowed. Peer-reviewer checks if revision was justified.
