# Design: brown_workflow-reliability_01

## Architecture Overview

This change modifies command files and agent files to wire the reliability gaps. No new agents are created. One new file is introduced (sudd.yaml). The rest is adding sections to existing files.

```
sudd/
  sudd.yaml (NEW) ──────────── central config: tiers, escalation, cost_mode
  state.schema.json ─────────── add phase enum, test_command
  commands/
    macro/run.md ─────────────── add invocation protocol, read sudd.yaml
    micro/plan.md ────────────── fix brown mode research condition
    micro/apply.md ───────────── add retry briefing, file tracking, invocation protocol
    micro/test.md ────────────── add test framework detection
    micro/gate.md ────────────── add accumulated feedback append
    micro/done.md ────────────── add rollback from file tracking, cost summary
  agents/
    persona-validator.md ─────── add traceability check
    blocker-detector.md ──────── add root cause classification
    learning-engine.md ────────── add structured postmortem template
    coder.md ─────────────────── add CONTRACT_REVISION protocol, read feedback on retry
    qa.md ────────────────────── add testability review mode
    architect.md ─────────────── add CONTRACT_REVISION handler
```

## Component: sudd.yaml

### File: `sudd/sudd.yaml` (NEW)
Central configuration for all agent model assignments, escalation, and cost mode.

Schema:
```yaml
escalation:
  default_tier: free          # fallback if agent not listed
  ladder:                     # retry_count → tier mapping
    0-1: free
    2-3: sonnet
    4-5: sonnet
    6-7: opus
    8: stuck

agents:                       # per-agent tier assignment
  {agent-name}: { tier: free|sonnet|opus }

test_command: null            # auto-detected or user-set
cost_mode: balanced           # balanced | free-first | quality-first
```

### How commands read it
Commands check for `sudd/sudd.yaml` at the start. If missing, warn user and default all agents to `free`. YAML is read once per command execution, not per-agent (no repeated file reads).

### Cost mode resolution
```
balanced:     use per-agent tiers as defined
free-first:   ignore per-agent tiers, use free for all, escalate on retry
quality-first: promote sonnet-tier agents to opus (all judgment + analytical = opus)
```

## Component: Invocation Protocol Addition

### Added to: run.md, apply.md (and referenced by all commands)

```markdown
## How Agent Invocation Works
"Task(agent=X)" means:
1. Read `sudd/sudd.yaml` for X's tier
2. Read `sudd/agents/X.md` for instructions
3. Spawn subagent via CLI's native dispatch with X.md as prompt
4. Include X.md's PREREQUISITES files in the prompt
5. Subagent writes output to X.md's OUTPUTS location
6. Orchestrator reads output, continues to NEXT agent

Parallel: spawn independent agents simultaneously
Sequential: wait for predecessor output files before spawning
```

## Component: Accumulated Feedback Section

### Added to: gate.md (writer), apply.md (reader)

**gate.md appends on fail:**
```markdown
## Accumulated Feedback (read this FIRST on retry)
### Retry {N} — Gate Score: {score}/100
- Persona "{name}": {specific issues}
```

**apply.md reads on retry:**
```
If retry_count > 0:
  1. Read ## Accumulated Feedback from log.md
  2. Read latest critique dispositions
  3. Read learning-engine top-3 lessons
  4. Build RETRY BRIEFING and include in coder prompt
```

## Component: Phase Enum

### Added to: state.schema.json

```json
"phase": {
  "type": "string",
  "enum": ["inception", "planning", "build", "validate", "complete"]
}
```

### Transition validation (added as comments in each command that sets phase)
```
new.md:   inception → planning     ✓
plan.md:  planning  → build        ✓
test.md:  build     → validate     ✓
gate.md:  validate  → build (fail) ✓
gate.md:  validate  → complete     ✓
done.md:  complete  → inception    ✓
```

## Component: Handoff Contract Schema

### Standardized format for specs.md Consumer Handoffs section
```markdown
### Handoff: {Producer} → {Consumer}
- **Format**: markdown | json | binary | CLI output
- **Location**: {file path or stdout}
- **Required fields**: {comma-separated list}
- **Validated by**: handoff-validator checks {what specifically}
- **Error case**: if {condition}, then {what happens}
```

No changes to validator logic — just standardizing what it reads.

## Component: QA Testability Review

### Added to: qa.md (new mode), planning chain in run.md

QA agent gets a second mode: `testability-review` (lightweight, runs in planning chain).

```markdown
## TESTABILITY REVIEW MODE
When invoked during planning (not build):
1. Read design.md acceptance criteria
2. For each criterion:
   - Is it testable? (can you write a concrete test for it?)
   - If vague → flag: "Criterion X is not testable: {reason}"
3. Identify untestable components (if any)
4. Recommend test framework based on tech stack
5. Append ## Testability Notes to design.md
```

## Component: Brown Mode Research Fix

### Changed in: plan.md

```
Before: if mode == "green" → run research agents
After:  if (personas/ has only default.md) OR (specs.md has no "### Handoff:" section) → run research
```

One condition change. Mode field is irrelevant — what matters is whether artifacts exist.

## Component: Test Framework Detection

### Added to: test.md

```markdown
## Test Framework Detection (runs once, result saved to sudd.yaml)
Priority order:
1. sudd.yaml test_command (user override) → use it
2. Makefile with "test" target → make test
3. *_test.go files → go test ./...
4. package.json scripts.test → npm test / npx vitest
5. test_*.py or *_test.py → pytest
6. If none found → QA creates test infrastructure
```

Result saved to sudd.yaml `test_command` field.

## Component: File Tracking for Rollback

### Added to: apply.md (writer), done.md (reader)

**apply.md appends after each task:**
```markdown
## Files Modified
- `{path}` — {task_id}: {description}
```

**done.md reads on STUCK:**
```bash
# Generated from ## Files Modified
git checkout main -- {file1} {file2} {file3}
```

## Component: Traceability Check

### Added to: persona-validator.md

```markdown
## Traceability Check
After scoring each criterion:
1. For "pass" criteria → identify WHICH code/output satisfies it
2. If no traceable implementation → UNMAPPED
3. Any UNMAPPED criterion → score capped at 80
4. Log: "UNMAPPED SUCCESS: {criterion} — appears to pass but no traceable implementation"
```

## Component: Root Cause Classification

### Added to: blocker-detector.md

Add to output format:
```markdown
## Classification
- Action: RETRY | BLOCKED | STUCK
- Root Cause: LOGIC_ERROR | SPEC_ERROR | EXTERNAL_DEPENDENCY | CONTEXT_DRIFT | DESIGN_FLAW
```

## Component: Structured Postmortem

### Added to: learning-engine.md

Extend template for failures:
```markdown
### [STUCK] {task-name} — {date}
**Tags:** {domain}, {technology}
**Root Cause:** {from blocker-detector}
**Agent:** {which agent failed}
**Error:** {specific error}
**Hypothesis:** {why this happened}
**Resolution:** {what fixed it, or UNRESOLVED}
**Prevention:** {what would prevent this}
```

## Component: CONTRACT_REVISION Protocol

### Added to: coder.md (raiser), architect.md (handler)

**coder.md — raises when:**
- 2+ retries on same contract violation
- Contract in specs.md is impossible to implement as written

**architect.md — handles by:**
- Reading the CONTRACT_REVISION report
- Modifying ONLY the flagged handoff contract in specs.md
- Preserving original in log.md
- Retry count resets to 0 for that task

## Component: Cost Log

### Added to: all agent files (self-report), monitor.md (threshold check)

Agents append to `## Cost Log` in log.md after execution. Monitor flags if total > ~100K tokens.

## File Changes

### New Files (1)
- `sudd/sudd.yaml` — central agent configuration

### Modified Files — Commands (7)
- `sudd/commands/macro/run.md` — add invocation protocol, sudd.yaml reading, QA testability step in planning chain
- `sudd/commands/micro/plan.md` — fix brown mode research condition
- `sudd/commands/micro/apply.md` — add invocation protocol, retry briefing, file tracking
- `sudd/commands/micro/test.md` — add test framework detection
- `sudd/commands/micro/gate.md` — add accumulated feedback append, phase transition validation
- `sudd/commands/micro/done.md` — add rollback from file tracking, cost summary
- `sudd/commands/micro/add-task.md` — already handled by agent-sophistication change

### Modified Files — Agents (6)
- `sudd/agents/persona-validator.md` — add traceability check
- `sudd/agents/blocker-detector.md` — add root cause classification
- `sudd/agents/learning-engine.md` — add structured postmortem template
- `sudd/agents/coder.md` — add CONTRACT_REVISION raising, read accumulated feedback
- `sudd/agents/qa.md` — add testability review mode
- `sudd/agents/architect.md` — add CONTRACT_REVISION handler

### Modified Files — Schema (1)
- `sudd/state.schema.json` — add phase enum

### No changes needed
- Go CLI (sudd-go/) — no changes
- Agent files not listed above — handled by agent-sophistication change (activation headers)
