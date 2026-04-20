# Tasks: brown_framework-hardening_01

## Phase 1: Agent Threshold Unification (Critical)

- [x] **T01** — Update handoff-validator.md: change 70 → 95 threshold everywhere [S]
  - Replace "70+ = CONSUMABLE" with "95+ = CONSUMABLE"
  - Replace "Below 70" with "Below 95"
  - Update rule 5 scoring text
  - Files: `sudd/agents/handoff-validator.md`

- [x] **T02** — Update persona-validator.md: change 70 → 95 threshold everywhere [S]
  - Replace scoring guide table (95-100 = SATISFIED, below 95 = NOT_SATISFIED)
  - Replace "70 is the threshold" with "95 is the threshold"
  - Files: `sudd/agents/persona-validator.md`

- [x] **T03** — Update contract-verifier.md: add 95 numeric scoring [S]
  - Add 0-100 scoring alongside COMPLIANT/NON-COMPLIANT
  - Score < 95 OR BREAKING = NON-COMPLIANT
  - Add entry point: "Called by /sudd:apply after coder, before handoff-validator"
  - Files: `sudd/agents/contract-verifier.md`

- [x] **T04** — Update peer-reviewer.md: add 95 scoring + absorb reviewer.md [M]
  - Add 0-100 scoring alongside APPROVE/REQUEST_CHANGES/REJECT
  - Score < 95 = REQUEST_CHANGES
  - Absorb unique content from reviewer.md (persona check, security checklist)
  - Files: `sudd/agents/peer-reviewer.md`

- [x] **T05** — Delete reviewer.md [S]
  - Remove duplicate agent file
  - Files: `sudd/agents/reviewer.md` (DELETE)

- [x] **T06** — Update blocker-detector.md: enhance RETRY actions [S]
  - "module not found" → RETRY + "install the dependency first"
  - "no such file" → RETRY + "check paths against design.md"
  - Files: `sudd/agents/blocker-detector.md`

## Phase 2: State Machine Hardening (Critical)

- [x] **T07** — Update state.schema.json: add 3 new fields [S]
  - Add `tests_passed` (boolean, default false)
  - Add `gate_score` (integer, default 0, min 0, max 100)
  - Add `gate_passed` (boolean, default false)
  - Files: `sudd/state.schema.json`

- [x] **T08** — Update state.json: add new fields with defaults [S]
  - Add `tests_passed: false`, `gate_score: 0`, `gate_passed: false`
  - Files: `sudd/state.json`

- [x] **T09** — Update apply.md: add contract-verifier step + phase guard [M]
  - Add explicit guard: phase >= "build" AND specs.md exists
  - Add contract-verifier invocation after coder, before handoff-validator
  - Files: `sudd/commands/micro/apply.md`

- [x] **T10** — Update test.md: set tests_passed in state [S]
  - After all tests pass, update state.json: `tests_passed: true`
  - Files: `sudd/commands/micro/test.md`

- [x] **T11** — Update gate.md: add tests_passed guard + write gate_score [S]
  - Add guard: state.json `tests_passed` must be `true`
  - On pass: write `gate_passed: true`, `gate_score: {min_score}`
  - Files: `sudd/commands/micro/gate.md`

- [x] **T12** — Update done.md: add gate_passed guard + rollback [M]
  - Add guard: `gate_passed == true` OR `retry_count >= 8`
  - For STUCK: add rollback instructions (list modified files, git checkout command)
  - Files: `sudd/commands/micro/done.md`

## Phase 3: Go CLI Fixes (Critical)

- [x] **T13** — Fix installer.go silent failures [M]
  - `copyDir()`: print warning when skipping existing directory
  - `copyFile()`: print warning when skipping existing file
  - `InstallCLAUDEMD()`: print warning when skipping
  - Files: `sudd-go/internal/installer/installer.go`

- [x] **T14** — Fix main.go type assertion + stdlib [M]
  - Line 135: use comma-ok pattern for type assertion
  - Delete `splitString()`, `trimString()` functions
  - Rewrite `splitComponents()` using `strings.Split` + `strings.TrimSpace`
  - Add `"strings"` import
  - Files: `sudd-go/cmd/sudd/main.go`

- [x] **T15** — Remove dead code from tui.go [S]
  - Remove commented `lipgloss` import
  - Remove `InstallProgressMsg` struct
  - Remove unused fields: `installing`, `installed`, `total` from Model
  - Files: `sudd-go/internal/tui/tui.go`

- [x] **T16** — Fix Makefile install target [S]
  - Replace `cp bin/$(BINARY) $(GOPATH)/bin/` with `$(GO) install $(GOFLAGS) ./cmd/sudd`
  - Files: `sudd-go/Makefile`

- [x] **T17** — Add installer_test.go [L]
  - Test: install with force=false skips existing, prints warning
  - Test: install with force=true overwrites
  - Test: DetectContext() identifies git repos
  - Test: component list completeness
  - Files: `sudd-go/internal/installer/installer_test.go` (NEW)

- [x] **T18** — Add main_test.go [M]
  - Test: splitComponents("a,b,c") returns ["a","b","c"]
  - Test: splitComponents("a, b , c") trims whitespace
  - Test: getSelectedIDs() returns correct map
  - Files: `sudd-go/cmd/sudd/main_test.go` (NEW)

## Phase 4: Repo Hygiene (High)

- [x] **T19** — Fix .gitignore [S]
  - Add: `.ruff_cache/`, `sudd-go/bin/`, `sudd-go/dist/`, `*.exe~`, `*~`, `.DS_Store`, `Thumbs.db`
  - Files: `.gitignore`

- [x] **T20** — Delete junk files [S]
  - Delete `sudd-go/bin/sudd.exe~`
  - Delete `reference/vision.md` (duplicate of `sudd/vision.md`)
  - Files: 2 deletions

- [x] **T21** — Fix install.sh paths [M]
  - Change all `$TARGET/agents` → `$TARGET/sudd/agents`
  - Change `$TARGET/personas` → `$TARGET/sudd/personas`
  - Change `$TARGET/task-specs` → `$TARGET/sudd/changes`
  - Change `$SUDD2_SOURCE/agents/` → `$SUDD2_SOURCE/sudd/agents/`
  - Change command copy paths to match current structure
  - Files: `install.sh`

- [x] **T22** — Move orphaned commands to source of truth [S]
  - Copy `add-task.md` from `.claude/commands/sudd/` to `sudd/commands/micro/`
  - Copy `init.md` from `.claude/commands/sudd/` to `sudd/commands/micro/`
  - Files: 2 new files in `sudd/commands/micro/`

- [x] **T23** — Rename sudd-test/ [S]
  - Rename to `examples/installed-output/` or delete entirely
  - Files: directory rename

## Phase 5: Sync & Learning (Medium)

- [x] **T24** — Update sync.sh metadata transformation [M]
  - After copy, for OpenCode/Crush: ensure front-matter `name:` uses `sudd-{command}` format
  - For Claude Code: use filename only, strip `name:` from front-matter if present
  - Files: `sudd/sync.sh`

- [x] **T25** — Update sync.bat metadata transformation [M]
  - Same logic as sync.sh but in batch syntax
  - Files: `sudd/sync.bat`

- [x] **T26** — Update lessons.md template format [S]
  - Add structured format with Tags, Confidence fields
  - Update template section
  - Files: `sudd/memory/lessons.md`

---

## Summary

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| 1: Agent Thresholds | T01-T06 | 5S + 1M | Critical |
| 2: State Machine | T07-T12 | 3S + 3M | Critical |
| 3: Go CLI | T13-T18 | 2S + 3M + 1L | Critical |
| 4: Repo Hygiene | T19-T23 | 4S + 1M | High |
| 5: Sync & Learning | T24-T26 | 1S + 2M | Medium |
| **Total** | **26 tasks** | **15S + 9M + 2L** | |

## Dependencies

```
T01-T06: independent (can run in parallel)
T07-T08: must complete before T09-T12
T09-T12: independent of each other (can run in parallel)
T13-T16: independent (can run in parallel)
T17-T18: depend on T13-T14 (test the fixes)
T19-T23: independent (can run in parallel)
T24-T25: depend on T22 (need add-task.md and init.md as source)
T26: independent
```
