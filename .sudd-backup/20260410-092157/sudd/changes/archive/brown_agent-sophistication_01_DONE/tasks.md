# Tasks: brown_agent-sophistication_01

## Phase 1: New Agent Files (must exist before other agents reference them)

- [x] **T01** — Create solution-explorer.md [M]
  - Write `sudd/agents/solution-explorer.md` with full ACTIVATION/PREREQUISITES/OUTPUTS/PERMISSIONS headers
  - Include: DIVERGE (3-5 candidates), EVALUATE (6 weighted criteria with cost at 20%), DECIDE & DOCUMENT
  - Include: solutions.md output schema, blocking conditions (< 3 candidates → halt)
  - Include: open-source-first technology selection principle
  - Files: `sudd/agents/solution-explorer.md` (NEW)

- [x] **T02** — Create decomposer.md [M]
  - Write `sudd/agents/decomposer.md` with full headers
  - Include: PRD → feature groups → changes, specs extraction, task breakdown
  - Include: dependency ordering, effort estimation (S/M/L), parallelization flags
  - Include: blocking conditions (no feature groups, no component boundaries, effort exceeds budget)
  - Files: `sudd/agents/decomposer.md` (NEW)

## Phase 2: Planning Chain Agents (activation headers + enhancements)

- [x] **T03** — Update researcher.md with activation headers [S]
  - Add ACTIVATION, PREREQUISITES (phase: planning, required: vision.md or proposal.md), OUTPUTS (next: persona-detector), PERMISSIONS (CAN: memory/research-cache/, CANNOT: code, specs, design)
  - Preserve existing content
  - Files: `sudd/agents/researcher.md`

- [x] **T04** — Update persona-detector.md with activation headers [S]
  - Add headers. Next: persona-researcher. CAN: personas/. CANNOT: code, specs, design
  - Files: `sudd/agents/persona-detector.md`

- [x] **T05** — Update persona-researcher.md with activation headers [S]
  - Add headers. Next: antigravity. CAN: personas/. CANNOT: code, specs, design
  - Files: `sudd/agents/persona-researcher.md`

- [x] **T06** — Update antigravity.md with activation headers [S]
  - Add headers. Next: deep-think. CAN: changes/{id}/specs.md (handoff section). CANNOT: code, design
  - Files: `sudd/agents/antigravity.md`

- [x] **T07** — Update deep-think.md with activation headers [S]
  - Add headers. Next: solution-explorer (changed from "before implementation"). CAN: log.md. CANNOT: code, specs, design
  - Files: `sudd/agents/deep-think.md`

## Phase 3: Architecture Agents (headers + major enhancements)

- [x] **T08** — Update architect.md with headers + critique loop + solutions.md input [L]
  - Add ACTIVATION, PREREQUISITES (phase: planning, required: solutions.md + specs.md), OUTPUTS (next: architect-critic loop), PERMISSIONS
  - Add CRITIQUE LOOP section: 3 iterations, 10 weaknesses per round, disposition logging
  - Add: read solutions.md first (selected approach), produce file-level design, handoff contracts, complexity estimates, acceptance criteria
  - Preserve existing RULES
  - Files: `sudd/agents/architect.md`

## Phase 4: Build Chain Agents (headers + major enhancements)

- [x] **T09** — Update qa.md with headers + risk profiling [M]
  - Add headers. Next: coder. CAN: tests/. CANNOT: source code, specs, design
  - Add: risk profiling (probability × impact), requirements tracing (Given-When-Then), coverage targets per risk level, NFR assessment
  - Files: `sudd/agents/qa.md`

- [x] **T10** — Update coder.md with headers + critique loop + DESIGN_ISSUE + TDD order [L]
  - Add headers. CAN: source code only. CANNOT: specs, design, tests, personas
  - Add CRITIQUE LOOP section: same pattern as architect (3 iterations, 10 weaknesses, run tests between)
  - Add DESIGN_ISSUE protocol: structured report format, routing back to architect
  - Change reading order: tests first → design second → specs third → lessons fourth
  - Add incremental implementation: one function → test → next
  - Files: `sudd/agents/coder.md`

- [x] **T11** — Update contract-verifier.md with activation headers [S]
  - Add ACTIVATION, PREREQUISITES, PERMISSIONS. Entry point already documented. Next: handoff-validator
  - CAN: log.md (compliance). CANNOT: code, specs, design
  - Files: `sudd/agents/contract-verifier.md`

- [x] **T12** — Update handoff-validator.md with activation headers [S]
  - Add headers. Next: peer-reviewer. CAN: log.md (validation). CANNOT: code, specs, design
  - Files: `sudd/agents/handoff-validator.md`

- [x] **T13** — Update peer-reviewer.md with activation headers [S]
  - Add headers. Next: RETURN (task complete). CAN: log.md (review notes). CANNOT: code, specs, design
  - Files: `sudd/agents/peer-reviewer.md`

## Phase 5: Validation Chain Agents (headers)

- [x] **T14** — Update persona-validator.md with activation headers [S]
  - Add headers. Next: ux-tester (if UI) or learning-engine. CAN: log.md (gate score). CANNOT: code, specs, design
  - Files: `sudd/agents/persona-validator.md`

- [x] **T15** — Update ux-tester.md with activation headers [S]
  - Add headers. Next: learning-engine. CAN: log.md (ux results). CANNOT: code, specs, design
  - Files: `sudd/agents/ux-tester.md`

## Phase 6: System Agents (headers + learning engine enhancement)

- [x] **T16** — Update learning-engine.md with headers + pre-task injection [M]
  - Add headers. CAN: memory/. CANNOT: code, specs, design
  - Add pre-task injection protocol: read lessons, match by tags, inject top-3 into agent context
  - Add pattern promotion: 3+ occurrences → patterns.md
  - Add confidence decay: lessons lose confidence unless reinforced
  - Files: `sudd/agents/learning-engine.md`

- [x] **T17** — Update blocker-detector.md with activation headers [S]
  - Add headers. CAN: state.json (retry/stuck). CANNOT: code, specs, design
  - Files: `sudd/agents/blocker-detector.md`

- [x] **T18** — Update context-manager.md with activation headers [S]
  - Add headers. CAN: (reads only). CANNOT: everything
  - Files: `sudd/agents/context-manager.md`

- [x] **T19** — Update monitor.md with activation headers [S]
  - Add headers. CAN: state.json (health), log.md. CANNOT: code, specs, design
  - Files: `sudd/agents/monitor.md`

- [x] **T20** — Update task-discoverer.md: headers + v2 integration + size-aware proposals [M]
  - Add ACTIVATION, PREREQUISITES, OUTPUTS, PERMISSIONS headers
  - Fix stale paths: `openspec/project.md` → `sudd/vision.md`, `results/` → `sudd/changes/archive/`, `task-specs/` → `sudd/changes/active/`
  - Output change proposals (`changes/active/{id}/proposal.md`) instead of `task-specs/{name}.md`
  - Add size estimation (S/M/L) and create documentation appropriate to size
  - S-size: proposal.md (brief) + tasks.md (single checkbox)
  - M/L-size: full suite (proposal + specs + design + tasks + log)
  - tasks.md always present — single source of truth for completion
  - Files: `sudd/agents/task-discoverer.md`

- [x] **T21** — Update add-task.md command: v2 paths + change proposals [S]
  - Fix paths: `task-specs/` → `sudd/changes/active/`
  - Output change proposal instead of standalone task-spec
  - Use change ID format: `task_{name}_{seq:02d}`
  - Files: `sudd/commands/micro/add-task.md`

## Phase 7: Vision + State Updates

- [x] **T22** — Update vision.md agent table [S]
  - Add solution-explorer (Planning phase) and decomposer (Planning phase) to agent roles table
  - Update agent count from 18 to 20
  - Files: `sudd/vision.md`

## Phase 8: Verification

- [x] **T23** — Verify all 20 agents have standardized headers [S]
  - Check every agent file has: ACTIVATION, PREREQUISITES, OUTPUTS, PERMISSIONS
  - Check every OUTPUTS section names a Next agent
  - Check every PERMISSIONS section has CAN and CANNOT lists
  - Verify planning chain: researcher → persona-detector → persona-researcher → antigravity → deep-think → solution-explorer → architect (×3) → decomposer
  - Verify build chain: qa → coder (×3) → contract-verifier → handoff-validator → peer-reviewer
  - Verify validation chain: persona-validator → ux-tester → learning-engine
  - Files: all 20 agent files (read-only verification)

---

## Summary

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| 1: New Agents | T01-T02 | 2M | Critical — others depend on these |
| 2: Planning Chain | T03-T07 | 5S | High |
| 3: Architecture | T08 | 1L | Critical — critique loop |
| 4: Build Chain | T09-T13 | 2S + 1M + 1L | Critical — critique loop + TDD |
| 5: Validation Chain | T14-T15 | 2S | Medium |
| 6: System Agents | T16-T21 | 4S + 2M | Medium-High |
| 7: Vision Update | T22 | 1S | Low |
| 8: Verification | T23 | 1S | High — final check |
| **Total** | **23 tasks** | **14S + 5M + 2L** | |

## Dependencies

```
T01-T02: independent (can run in parallel)
T03-T07: independent of each other, depend on T01 (solution-explorer referenced by T07)
T08: depends on T01 (architect reads solutions.md from solution-explorer)
T09: independent
T10: independent
T11-T13: independent of each other
T14-T15: independent of each other
T16-T21: independent of each other (T20 upgraded to M, T21 is new S)
T22: depends on T01-T02 (needs new agent names)
T23: depends on ALL previous tasks
```
