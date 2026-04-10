# Archive: brown_agent-sophistication_01

## Outcome: DONE

## Summary
Added standardized activation protocol (ACTIVATION, PREREQUISITES, OUTPUTS, PERMISSIONS) to all 20 SUDD agents, created 2 new agents (solution-explorer, decomposer), and enhanced 4 agents with critique loops, TDD order, risk profiling, and pre-task injection.

## Consumers Validated
- Architect (solutions.md consumer): 97/100
- Decomposer (design.md consumer): 97/100
- Critique Loop (architecture + code): 97/100
- Learning Engine → All Agents: 97/100
- Framework Owner (consistency): 97/100

## Files Changed

### New Files (2)
- `sudd/agents/solution-explorer.md` — divergent solution exploration with weighted decision matrix
- `sudd/agents/decomposer.md` — PRD/architecture decomposition into executable changes

### Modified Agent Files (18)
- `sudd/agents/researcher.md` — activation headers
- `sudd/agents/persona-detector.md` — activation headers
- `sudd/agents/persona-researcher.md` — activation headers
- `sudd/agents/antigravity.md` — activation headers
- `sudd/agents/deep-think.md` — activation headers + fixed stale openspec paths
- `sudd/agents/architect.md` — headers + critique loop (2×10 weaknesses) + solutions.md input + file-level design
- `sudd/agents/qa.md` — headers + risk profiling + requirements tracing + coverage targets
- `sudd/agents/coder.md` — headers + critique loop + DESIGN_ISSUE protocol + TDD reading order
- `sudd/agents/contract-verifier.md` — headers + fixed stale openspec paths
- `sudd/agents/handoff-validator.md` — activation headers
- `sudd/agents/peer-reviewer.md` — activation headers
- `sudd/agents/persona-validator.md` — activation headers
- `sudd/agents/ux-tester.md` — headers + fixed stale results/ path
- `sudd/agents/blocker-detector.md` — activation headers
- `sudd/agents/learning-engine.md` — headers + pre-task injection + pattern promotion + confidence decay + root cause classification
- `sudd/agents/context-manager.md` — headers + aligned lesson count to 3
- `sudd/agents/monitor.md` — headers + fixed stale task-specs reference
- `sudd/agents/task-discoverer.md` — headers + v2 paths + size-aware proposals + blocking conditions

### Modified Command/Other Files (3)
- `sudd/commands/micro/add-task.md` — v2 paths, change proposals instead of task-specs
- `sudd/commands/micro/init.md` — 20 agents, v2 paths, removed stale task-specs/results
- `sudd/vision.md` — 20 agents, correct phase assignments

## Lessons Learned
1. Stale v1 paths lurk in files you don't expect (init.md, monitor.md, deep-think.md) — grep ALL files for old paths, not just the ones you're modifying
2. Gate validation catches real issues — first attempt scored 78/100, fixes raised it to 97/100. The retry was worth it.
3. Parallel agent dispatch (6 agents for 23 tasks) is effective for batch operations — completed in one pass
4. Code review before gate catches structural issues (stale paths, chain inconsistencies) that persona validators also catch but from different angles
5. Cross-change scoping matters — plan.md/run.md wiring belongs in workflow-reliability, not agent-sophistication. Validators flagged it but it was correctly out of scope.

## Completed: 2026-03-13
