# Archive: brown_workflow-reliability_01

## Outcome: DONE

## Summary
Added 15 workflow reliability improvements across 7 commands and 6 agents: sudd.yaml central config, subagent invocation protocol, accumulated feedback pipes, phase enum validation, test framework detection, rollback generation, traceability checks, root cause classification, CONTRACT_REVISION escape hatch, and cost monitoring. Ported 5 critical mechanisms from SUDD v1 that were missing in v2.

## Consumers Validated
- Coder Agent: 97/100
- Gate/Orchestrator: 95/100
- Framework Maintainer: 96/100
- Learning Engine: 97/100 (fixed during gate: added Mode 4 streak detection)

## Files Changed
- `sudd/sudd.yaml` — NEW: central agent configuration (20 agents, 3 tiers, escalation ladder)
- `sudd/state.schema.json` — added phase enum + test_command field
- `sudd/commands/macro/run.md` — invocation protocol, sudd.yaml reading, QA testability review
- `sudd/commands/micro/apply.md` — invocation protocol, retry briefing, file tracking
- `sudd/commands/micro/gate.md` — accumulated feedback append on FAIL
- `sudd/commands/micro/plan.md` — artifact-based research condition (not mode-based)
- `sudd/commands/micro/test.md` — test framework detection (STEP 0)
- `sudd/commands/micro/done.md` — rollback generation + cost summary
- `sudd/agents/persona-validator.md` — traceability check (UNMAPPED caps at 80)
- `sudd/agents/blocker-detector.md` — root cause classification (5 categories)
- `sudd/agents/learning-engine.md` — structured postmortem + Mode 4 streak detection
- `sudd/agents/coder.md` — accumulated feedback reading + CONTRACT_REVISION protocol
- `sudd/agents/architect.md` — CONTRACT_REVISION handler
- `sudd/agents/qa.md` — testability review mode
- `sudd/agents/monitor.md` — cost monitoring (100K token threshold)

## Lessons Learned
- When building systems that produce classified data, add streak/pattern detection in the consuming agent
- Central config (sudd.yaml) prevents per-file drift across 7+ files
- Gate validators from consumer perspective catch gaps that implementation thinking misses

## Completed: 2026-03-13
