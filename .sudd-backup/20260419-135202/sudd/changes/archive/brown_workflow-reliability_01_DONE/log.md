# Log: brown_workflow-reliability_01

## 2026-03-13 — Proposal Created
- Cross-cutting review of all 12 command files and 18 agent files identified 10 workflow weaknesses
- Review of 9 SUDD v1 reference docs identified 5 critical mechanisms not ported to v2
- Combined into 15 scope items: 10 fixes + 5 v1 ports
- Key constraint: all solutions stay markdown-first (no Python, no inter-process JSON, no typed schemas between agents)
- V1 lesson: 30+ Python modules with JSON handoffs broke constantly on formatting — we must not repeat this

## 2026-03-13 — Agent Invocation Protocol Revised
- Changed from "you ARE the agent" (sequential, single-threaded) to subagent dispatch model
- CLI tools (Claude Code, OpenCode, Crush) each have native subagent/agent spawning capabilities
- SUDD agent .md files are shared instructions; CLI tool decides HOW to dispatch
- Independent agents (researcher, persona-detector, persona-researcher) spawn in parallel
- Sequential agents (architect after solution-explorer) wait for predecessor output
- Communication is via markdown files on disk, not in-memory payloads or JSON

## 2026-03-13 — Planning Complete
- Generated specs.md: 15 functional requirements, 3 NFRs, 4 handoff contracts
- Generated design.md: component designs for all 15 scope items, 1 new file + 7 commands + 6 agents + 1 schema
- Generated tasks.md: 16 tasks across 7 phases (7S + 6M + 1L)
- Cross-change dependency: agent-sophistication should run first (adds activation headers to architect.md/coder.md), then this change adds protocols to same files
- Ready for /sudd:apply

## 2026-03-13 — T05-T08 Implemented

### T05: Accumulated feedback append in gate.md [M] — DONE
- Added "## Accumulated Feedback" append logic to FAIL path (STEP 4)
- Each retry appends a new "### Retry N" subsection with per-persona scores
- NEVER overwrites existing feedback
- Added phase transition validation comments (validate → build, validate → complete)

### T06: Brown mode research condition in plan.md [S] — DONE
- Changed STEP 2 header from "RESEARCH (IF GREEN)" to "RESEARCH (IF NEEDED)"
- Condition changed from mode-based to artifact-based:
  - If personas/*.md has only default.md → run research
  - OR if specs.md has no "### Handoff:" section → run research
- Updated GUARDRAILS to match new logic

### T07: Test framework detection in test.md [M] — DONE
- Added STEP 0 before STEP 1 with priority-ordered detection:
  1. sudd/sudd.yaml test_command (user override)
  2. Makefile with test target
  3. *_test.go files → go test ./...
  4. package.json scripts.test → npm test
  5. test_*.py / *_test.py → pytest
  6. None → QA agent creates infrastructure
- Result saved to sudd/sudd.yaml; subsequent runs skip detection

### T08: Rollback generation + cost summary in done.md [M] — DONE
- Added "Rollback Generation" section for STUCK changes:
  - Reads "## Files Modified" from log.md
  - Generates git checkout main command with all modified files
  - Included in STUCK.md archive
- Added "Cost Summary" section for ALL changes (DONE or STUCK):
  - Displays retry count, escalation tier, tasks completed/remaining
  - Included in OUTPUT and archive files
- Added phase transition validation: complete → inception (valid)

## 2026-03-13 — All Tasks Implemented (T01-T15)
- Phase 1 (T01-T02): sudd.yaml created with 20 agents across 3 tiers, state.schema.json updated with phase enum + test_command
- Phase 2 (T03-T04): Invocation protocol added to run.md and apply.md, retry briefing, file tracking, QA testability review
- Phase 3 (T05-T08): Accumulated feedback in gate.md, artifact-based research in plan.md, test detection in test.md, rollback in done.md
- Phase 4 (T09-T11): Traceability check in persona-validator, root cause in blocker-detector, structured postmortem in learning-engine
- Phase 5 (T12-T14): CONTRACT_REVISION in coder + architect, testability review mode in qa
- Phase 6 (T15): Cost monitoring in monitor (100K threshold)
- 4 agents dispatched in parallel for all phases

## 2026-03-13 — T16 Verification PASSED
- 15/15 checks passed across all modified files
- sudd.yaml: 20 agents, correct tiers (5/5/10), valid ladder, cost_mode balanced
- All commands: invocation protocol, phase transitions, feedback pipes, detection, rollback
- All agents: traceability, root cause, postmortem, CONTRACT_REVISION, testability, cost monitoring

## 2026-03-13 — Gate Attempt 1 PASSED (min 95/100)
- Coder Agent: 97/100 — all 7 checks passed, retry briefing complete
- Gate/Orchestrator: 95/100 — decomposer not explicitly invoked in run.md planning chain (minor)
- Framework Maintainer: 96/100 — all 15 FRs mapped, cross-file wiring consistent
- Learning Engine: 94→97/100 — fixed during gate: added Mode 4 root cause streak detection
- All consumers >= 95 after fix. Gate passed.
