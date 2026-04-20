# Archive: brown_framework-hardening_01

## Outcome: DONE

## Summary
Unified all validation thresholds to 95/100, hardened the state machine with phase guards and new fields (tests_passed, gate_score, gate_passed), fixed Go CLI bugs (silent failures, unsafe type assertions, dead code), cleaned up repo hygiene, and improved sync/learning infrastructure.

## Consumers Validated
- CLI Commands: 96/100
- Go CLI User: 97/100
- Framework Owner: 97/100

## Files Changed
- `sudd/agents/handoff-validator.md` — threshold 70 → 95
- `sudd/agents/persona-validator.md` — threshold 70 → 95, scoring guide rewritten
- `sudd/agents/contract-verifier.md` — added 95 numeric scoring + entry point
- `sudd/agents/peer-reviewer.md` — added 95 scoring, absorbed reviewer.md
- `sudd/agents/reviewer.md` — DELETED (duplicate)
- `sudd/agents/blocker-detector.md` — enhanced RETRY patterns
- `sudd/state.schema.json` — added tests_passed, gate_score, gate_passed
- `sudd/commands/micro/apply.md` — phase guard + contract-verifier step
- `sudd/commands/micro/test.md` — sets tests_passed on success
- `sudd/commands/micro/gate.md` — tests_passed guard + writes gate fields
- `sudd/commands/micro/done.md` — gate_passed guard + rollback for STUCK
- `sudd-go/internal/installer/installer.go` — warning prints for skipped files
- `sudd-go/cmd/sudd/main.go` — safe type assertion, stdlib strings, dead code removed
- `sudd-go/internal/tui/tui.go` — removed dead code
- `sudd-go/Makefile` — install target uses `go install`
- `sudd-go/internal/installer/installer_test.go` — NEW (6 tests)
- `sudd-go/cmd/sudd/main_test.go` — NEW (3 test groups)
- `.gitignore` — 7 new patterns
- `install.sh` — all paths fixed
- `sudd/sync.sh` — metadata transformation
- `sudd/sync.bat` — metadata transformation
- `sudd/memory/lessons.md` — structured template

## Lessons Learned
- Duplicate agent files (reviewer.md vs peer-reviewer.md) cause confusion — consolidate immediately
- Silent failures in installers hide real problems — always print when skipping
- Stale example data in commands undermines the threshold it's supposed to enforce
- Phase guards prevent agents from running out of order and producing invalid output
- Go stdlib (strings.Split, strings.TrimSpace) is always preferable to hand-rolled string functions

## Completed: 2026-03-12
