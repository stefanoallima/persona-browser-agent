# Log: brown_framework-hardening_01

## 2026-03-12 — Proposal Created
- Created from critical review findings
- 5 phases identified: state machine, Go CLI, agents, repo hygiene, sync/learning
- Type: brown (modifying existing framework)

## 2026-03-12 — Planning Complete
- specs.md: 12 functional requirements, 3 non-functional, 3 handoff contracts
- design.md: 6 layers of changes, 27 file changes (20 modify, 3 delete, 4 new)
- tasks.md: 26 tasks across 5 phases (15S + 9M + 2L)
- Key decision: ALL validation thresholds unified to 95/100 (old 70 produces garbage)
- Key decision: reviewer.md to be deleted (duplicate of peer-reviewer.md)
- Key decision: contract-verifier gets entry point in /sudd:apply
- Phase advanced to BUILD

## 2026-03-12 — Build Complete (All 26 Tasks)

### Phase 1: Agent Thresholds (T01-T06)
- handoff-validator.md: 70 → 95 threshold
- persona-validator.md: 70 → 95 threshold, scoring guide rewritten
- contract-verifier.md: added 95 numeric scoring + entry point
- peer-reviewer.md: added 95 scoring, absorbed reviewer.md content
- reviewer.md: DELETED (duplicate)
- blocker-detector.md: enhanced RETRY patterns

### Phase 2: State Machine (T07-T12)
- state.schema.json: added tests_passed, gate_score, gate_passed fields
- state.json: fields already present from earlier
- apply.md: added phase guard + contract-verifier step
- test.md: sets tests_passed = true on success
- gate.md: guards on tests_passed, writes gate_score/gate_passed
- done.md: guards on gate_passed, rollback instructions for STUCK

### Phase 3: Go CLI (T13-T18)
- installer.go: silent failures now print warnings
- main.go: safe type assertion, stdlib strings, dead code removed
- tui.go: removed InstallProgressMsg, unused fields, commented import
- Makefile: install target uses `go install`
- installer_test.go: NEW — 6 tests (components, profiles, context detection)
- main_test.go: NEW — 3 test groups (splitComponents, getSelectedIDs)
- All tests pass, code compiles clean

### Phase 4: Repo Hygiene (T19-T23)
- .gitignore: 7 new patterns added
- Deleted sudd-go/bin/sudd.exe~ and reference/vision.md
- install.sh: all paths fixed to use sudd/ prefix
- Moved add-task.md and init.md to sudd/commands/micro/
- Renamed sudd-test/ → examples/installed-output/

### Phase 5: Sync & Learning (T24-T26)
- sync.sh: added sed transformation for opencode/crush front-matter
- sync.bat: added PowerShell transformation equivalent
- lessons.md: structured template with Tags/Confidence fields

### Verification
- Go CLI compiles clean
- All Go tests pass (2 packages, 0 failures)
- No "70" threshold remaining in any agent file
- "95" threshold confirmed in handoff-validator and persona-validator
- reviewer.md and sudd.exe~ confirmed deleted

## 2026-03-12 — Gate PASSED
- CLI Commands consumer: 96/100 (stale example data in gate.md — fixed)
- Go CLI User consumer: 97/100 (tui package has no tests — minor)
- Framework Owner consumer: 97/100 (.ruff_cache dir cosmetic — non-blocking)
- Minimum score: 96/100
- All consumers >= 95 threshold
- Fixed gate.md example data (72/85/90 → 97/95/98 to match 95 threshold)
- Phase advanced to COMPLETE
