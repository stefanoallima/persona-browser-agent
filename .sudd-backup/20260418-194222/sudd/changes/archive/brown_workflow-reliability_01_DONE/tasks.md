# Tasks: brown_workflow-reliability_01

## Phase 1: Central Configuration (foundation — others depend on this)

- [x] **T01** — Create sudd/sudd.yaml [M]
  - Create file with: escalation ladder, per-agent tier assignments (5 opus + 5 sonnet + 10 free), cost_mode: balanced, test_command: null
  - Include comments explaining each tier and cost mode
  - Files: `sudd/sudd.yaml` (NEW)

- [x] **T02** — Update state.schema.json with phase enum [S]
  - Add `"enum": ["inception", "planning", "build", "validate", "complete"]` to phase field
  - Files: `sudd/state.schema.json`

## Phase 2: Command Wiring — Invocation & Config (core protocol)

- [x] **T03** — Add invocation protocol to run.md [M]
  - Add "How Agent Invocation Works" section (subagent dispatch model)
  - Add sudd.yaml reading at startup
  - Add QA testability review step in planning chain (after architect, before decomposer)
  - Add phase transition validation comments
  - Files: `sudd/commands/macro/run.md`

- [x] **T04** — Add invocation protocol + retry briefing + file tracking to apply.md [L]
  - Add "How Agent Invocation Works" section
  - Add sudd.yaml reading for agent tiers
  - Add retry briefing protocol: if retry_count > 0, read Accumulated Feedback + critique dispositions + lessons, build RETRY BRIEFING block for coder
  - Add file tracking: after each task, append to `## Files Modified` in log.md
  - Add phase transition validation
  - Files: `sudd/commands/micro/apply.md`

## Phase 3: Command Wiring — Feedback & Detection

- [x] **T05** — Add accumulated feedback append to gate.md [M]
  - On gate FAIL: append to `## Accumulated Feedback` in log.md with retry number, score, per-persona feedback
  - Never overwrite — always append new retry subsection
  - Add phase transition validation (validate → build on fail, validate → complete on pass)
  - Files: `sudd/commands/micro/gate.md`

- [x] **T06** — Fix brown mode research condition in plan.md [S]
  - Change `if mode == "green"` to `if personas/ has only default.md OR specs.md has no "### Handoff:" section`
  - Files: `sudd/commands/micro/plan.md`

- [x] **T07** — Add test framework detection to test.md [M]
  - Add detection logic: check sudd.yaml override → Makefile → *_test.go → package.json → pytest
  - Save detected command to sudd.yaml test_command field
  - If none found, note that QA creates test infrastructure
  - Files: `sudd/commands/micro/test.md`

- [x] **T08** — Add rollback generation + cost summary to done.md [M]
  - On STUCK: read `## Files Modified` from log.md, generate rollback command
  - On DONE or STUCK: read `## Cost Log` from log.md, display summary
  - Add phase transition validation (complete → inception)
  - Files: `sudd/commands/micro/done.md`

## Phase 4: Agent Enhancements — V1 Ports

- [x] **T09** — Add traceability check to persona-validator.md [M]
  - Add `## Traceability Check` section after scoring
  - For each "pass" criterion: identify which code/output satisfies it
  - If no traceable implementation → UNMAPPED, score capped at 80
  - Log "UNMAPPED SUCCESS" to log.md
  - Files: `sudd/agents/persona-validator.md`

- [x] **T10** — Add root cause classification to blocker-detector.md [S]
  - Extend classification output: add Root Cause field alongside Action
  - Five categories: LOGIC_ERROR, SPEC_ERROR, EXTERNAL_DEPENDENCY, CONTEXT_DRIFT, DESIGN_FLAW
  - Add pattern descriptions for each category
  - Files: `sudd/agents/blocker-detector.md`

- [x] **T11** — Add structured postmortem template to learning-engine.md [S]
  - Extend failure template: add Root Cause, Agent, Error, Hypothesis, Resolution, Prevention fields
  - Add instruction: hypothesis is mandatory, forces theorizing not just logging
  - Files: `sudd/agents/learning-engine.md`

## Phase 5: Agent Enhancements — Escape Hatches

- [x] **T12** — Add CONTRACT_REVISION protocol to coder.md [M]
  - Add CONTRACT_REVISION raising conditions (2+ retries on same contract violation)
  - Add report format: Task, Contract, Problem, Evidence, Suggested revision, Routing
  - Add instruction: read `## Accumulated Feedback` from log.md when retry_count > 0
  - Files: `sudd/agents/coder.md`

- [x] **T13** — Add CONTRACT_REVISION handler to architect.md [S]
  - Add handler: read CONTRACT_REVISION report, modify ONLY the flagged handoff contract
  - Preserve original contract in log.md for audit trail
  - Reset retry count to 0 for that task after revision
  - Files: `sudd/agents/architect.md`

- [x] **T14** — Add testability review mode to qa.md [S]
  - Add `## TESTABILITY REVIEW MODE` section for planning chain use
  - Check: acceptance criteria testable? Untestable components? Recommended test framework?
  - Output: append `## Testability Notes` to design.md
  - Files: `sudd/agents/qa.md`

## Phase 6: Cost Logging

- [x] **T15** — Add cost log self-reporting instruction to agent template [S]
  - Add instruction to the activation protocol template (from agent-sophistication change): after execution, append row to `## Cost Log` in log.md
  - Add monitor threshold: flag if total > ~100K tokens
  - Files: `sudd/agents/monitor.md` (threshold), activation protocol template reference

## Phase 7: Verification

- [x] **T16** — Verify all wiring [S]
  - Check: sudd.yaml exists with all 20 agents, correct tiers, valid ladder
  - Check: every command that sets phase validates the transition
  - Check: gate.md appends to Accumulated Feedback
  - Check: apply.md reads Accumulated Feedback on retry
  - Check: apply.md appends to Files Modified after each task
  - Check: done.md reads Files Modified for rollback
  - Check: persona-validator has traceability check
  - Check: blocker-detector has root cause classification
  - Check: coder has CONTRACT_REVISION protocol
  - Check: architect handles CONTRACT_REVISION
  - Check: qa has testability review mode
  - Check: brown mode research condition is artifact-based, not mode-based
  - Files: all modified files (read-only verification)

---

## Summary

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| 1: Central Config | T01-T02 | 1M + 1S | Critical — foundation |
| 2: Invocation & Config | T03-T04 | 1M + 1L | Critical — core protocol |
| 3: Feedback & Detection | T05-T08 | 3M + 1S | High — reliability |
| 4: V1 Ports | T09-T11 | 1M + 2S | High — quality gaps |
| 5: Escape Hatches | T12-T14 | 1M + 2S | Medium-High |
| 6: Cost Logging | T15 | 1S | Medium |
| 7: Verification | T16 | 1S | High — final check |
| **Total** | **16 tasks** | **7S + 6M + 1L** | |

## Dependencies

```
T01: independent (sudd.yaml must exist before T03-T04)
T02: independent
T03-T04: depend on T01 (read sudd.yaml)
T05-T08: independent of each other, depend on T02 (phase enum)
T09-T11: independent of each other
T12-T13: T12 depends on T09 (coder reads feedback), T13 independent
T14: independent
T15: independent
T16: depends on ALL previous tasks
```

## Cross-Change Dependencies

```
brown_agent-sophistication_01 tasks T08 (architect) and T10 (coder) add activation headers.
This change (T12, T13) adds CONTRACT_REVISION to those same files.
Order: run agent-sophistication first (adds headers), then this change (adds protocols to existing files).
Alternatively: run in parallel, merge carefully on architect.md and coder.md.
```
