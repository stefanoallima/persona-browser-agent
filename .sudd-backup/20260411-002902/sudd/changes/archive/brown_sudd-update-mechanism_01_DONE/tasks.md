# Tasks: brown_sudd-update-mechanism_01

## Phase 1: sync.sh Update Mode (immediate value)

- [x] **T01** — Add `update` subcommand to sync.sh [M]
  - Add `sync_update()` function: accept target dir, verify sudd/ exists, copy framework files
  - Framework dirs: agents/, commands/
  - Framework files: vision.md, state.schema.json
  - Preserve: personas/, changes/, memory/, state.json, sudd.yaml
  - Add to case statement: `update) sync_update "$2" "$3" ;;`
  - Files: `sudd/sync.sh`
  - Completed: 2026-03-13

- [x] **T02** — Add backup + diff summary to sync.sh [S]
  - Before overwriting: copy existing framework files to `.sudd-backup/{YYYYMMDD_HHMMSS}/`
  - Compute diff: count added/modified/unchanged files
  - Show summary before proceeding
  - Add `--dry-run` support (show diff, don't copy)
  - Files: `sudd/sync.sh`
  - Completed: 2026-03-13

- [x] **T03** — Add .sudd-version writing to sync.sh [S]
  - After successful update: write `.sudd-version` to target root
  - Format: version (date), source (git short hash or "manual"), updated (ISO timestamp)
  - Files: `sudd/sync.sh`
  - Completed: 2026-03-13

- [x] **T04** — Add sync.bat Windows equivalent [S]
  - Port the update subcommand to sync.bat
  - Same overwrite/preserve rules, backup, version tracking
  - Files: `sudd/sync.bat`
  - Completed: 2026-03-13

## Phase 2: Go CLI Update Command

- [x] **T05** — Add `update` cobra command to main.go [M]
  - Add `updateCmd` with `--dry-run`, `--force`, `--components` flags
  - Add `runUpdate()` function: resolve target, check SUDD installed, delegate to installer
  - Register command in `init()`
  - Files: `sudd-go/cmd/sudd/main.go`
  - Completed: 2026-03-13

- [x] **T06** — Add `Update()` method to installer [M]
  - Add `PreservedPaths()` function returning paths to skip
  - Add `Update(component)` method: same as Install but always overwrites framework files, skips preserved paths
  - Add `DiffSummary()` method: compare embedded templates with target, return counts
  - Files: `sudd-go/internal/installer/installer.go`
  - Completed: 2026-03-13

- [x] **T07** — Add `Backup()` and `WriteVersion()` to installer [S]
  - `Backup(component)`: copy existing framework files to `.sudd-backup/{timestamp}/`
  - `WriteVersion()`: write `.sudd-version` with embedded version date + build info
  - Add version constant to embed alongside templates
  - Files: `sudd-go/internal/installer/installer.go`
  - Completed: 2026-03-13

- [x] **T08** — Enhance `runStatus()` with version check [S]
  - Read `.sudd-version` from target directory
  - Display installed version
  - Compare with embedded version — warn if outdated
  - Files: `sudd-go/cmd/sudd/main.go`
  - Completed: 2026-03-13

## Phase 3: Template Refresh

- [x] **T09** — Refresh embedded templates with latest agents [S]
  - Copy current sudd/ framework files to sudd-go/cmd/sudd/templates/sudd/
  - Ensure all 20 agents, updated commands, vision.md are in templates
  - Verify templates build correctly with `go build`
  - Files: `sudd-go/cmd/sudd/templates/sudd/`
  - Completed: 2026-03-13

## Phase 4: Verification

- [x] **T10** — Test sync.sh update on sudd-test/ [S]
  - Run `bash sudd/sync.sh update sudd-test/`
  - Verify: framework files updated, project files preserved, backup created, .sudd-version written
  - Verify: `--dry-run` shows diff without writing
  - Files: verification only
  - Completed: 2026-03-13 — all 7 checks passed

- [x] **T11** — Test Go CLI update [S]
  - Build `sudd` binary: `cd sudd-go && make build`
  - Run `sudd update sudd-test/`
  - Verify same as T10
  - Verify: `sudd status` shows version info
  - Files: verification only
  - Completed: 2026-03-13 — all 6 checks passed

---

## Summary

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| 1: sync.sh | T01-T04 | 1M + 3S | Critical — immediate value |
| 2: Go CLI | T05-T08 | 2M + 2S | High — long-term solution |
| 3: Templates | T09 | 1S | High — required before Go CLI works |
| 4: Verification | T10-T11 | 2S | High — final check |
| **Total** | **11 tasks** | **3M + 8S** | |

## Dependencies

```
T01: independent (core update logic)
T02: depends on T01 (adds backup/diff to update)
T03: depends on T01 (adds version tracking to update)
T04: depends on T01-T03 (Windows port of final sync.sh)
T05: independent (can parallel with T01)
T06: depends on T05 (installer methods for update command)
T07: depends on T06 (backup/version for installer)
T08: independent (status enhancement)
T09: independent (template refresh)
T10: depends on T01-T03 (test sync.sh)
T11: depends on T05-T09 (test Go CLI)
```
