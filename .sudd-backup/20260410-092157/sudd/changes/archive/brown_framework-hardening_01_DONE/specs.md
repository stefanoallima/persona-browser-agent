# Specs: brown_framework-hardening_01

## Functional Requirements

### FR-1: Unified 95/100 Quality Threshold
All validation agents MUST use 95/100 as the minimum pass threshold. No exceptions.

| Agent | Current Threshold | Required Threshold | Verdict Labels |
|-------|-------------------|-------------------|----------------|
| handoff-validator | 70 (CONSUMABLE) | 95 (CONSUMABLE) | CONSUMABLE / NOT_CONSUMABLE |
| persona-validator | 70 (SATISFIED) | 95 (SATISFIED) | SATISFIED / NOT_SATISFIED |
| contract-verifier | N/A (BREAKING = fail) | 95 numeric + BREAKING = fail | COMPLIANT / NON-COMPLIANT |
| peer-reviewer | N/A | 95 numeric score added | APPROVE / REQUEST_CHANGES / REJECT |

Scoring guide for ALL validators:
| Score | Meaning |
|-------|---------|
| 95-100 | Excellent. Meets all requirements. PASS. |
| 80-94 | Good but gaps. Needs refinement. FAIL. |
| 60-79 | Marginal. Significant issues. FAIL. |
| 0-59 | Doesn't deliver value. FAIL. |

### FR-2: Agent Deduplication
- Delete `reviewer.md` (duplicate of `peer-reviewer.md`)
- All references to "reviewer" agent redirect to `peer-reviewer.md`
- peer-reviewer.md is the single code review agent

### FR-3: Contract Verifier Entry Point
- Add explicit invocation of contract-verifier in `/sudd:apply` after coder step, before handoff-validator
- Contract-verifier runs on code output, checks against specs.md contracts
- If NON-COMPLIANT with any BREAKING violation OR score < 95: fail the task

### FR-4: State Machine Hardening
- Add to `state.schema.json`:
  - `tests_passed`: boolean (default false) — set by `/sudd:test`
  - `gate_score`: integer (default 0) — set by `/sudd:gate`
  - `gate_passed`: boolean (default false) — set by `/sudd:gate`
- Phase transition enforcement in ALL micro commands:
  - `/sudd:plan` requires: `active_change != null`
  - `/sudd:apply` requires: `phase >= "build"` AND specs.md exists
  - `/sudd:test` requires: `phase >= "build"` AND code implemented
  - `/sudd:gate` requires: `tests_passed == true`
  - `/sudd:done` requires: `gate_passed == true` OR `retry_count >= 8`

### FR-5: Rollback on STUCK
When a change reaches STUCK (retry >= 8):
1. Record all modified files in log.md before archiving
2. Add rollback instructions: `git checkout sudd/{change-id} -- .` to revert
3. Preserve the branch for human review (don't delete)

### FR-6: Go CLI Bug Fixes
- `installer.go copyDir()`: Return `ErrSkipped` and print warning when destination exists and Force=false
- `installer.go copyFile()`: Same — return `ErrSkipped` with warning
- `installer.go InstallCLAUDEMD()`: Same — return `ErrSkipped` with warning
- `main.go:135`: Use comma-ok type assertion
- `main.go`: Replace `splitString()` with `strings.Split()`, `trimString()` with `strings.TrimSpace()`
- `main.go`: Remove `InstallProgressMsg` struct, unused Model fields (`installing`, `installed`, `total`)
- `tui.go`: Remove commented import, unused `InstallProgressMsg` type

### FR-7: Go CLI Tests
- `installer_test.go`: Test install with force=true/false, test component detection, test CLAUDE.md generation
- `main_test.go`: Test `splitComponents()` parsing, test `getSelectedIDs()` logic

### FR-8: Repo Hygiene
- `.gitignore`: Add `.ruff_cache/`, `sudd-go/bin/`, `sudd-go/dist/`, `*.exe~`, `*~`, `.DS_Store`, `Thumbs.db`
- Delete `sudd-go/bin/sudd.exe~`
- Delete or rename `sudd-test/` to `examples/installed-output/`
- Remove `reference/vision.md` (duplicate of `sudd/vision.md`)
- Move `add-task.md` and `init.md` from `.claude/commands/sudd/` into `sudd/commands/micro/` as source of truth
- Fix `install.sh` paths: `agents/` → `sudd/agents/`, `personas/` → `sudd/personas/`, `task-specs/` → `sudd/changes/`

### FR-9: Sync Transformation
- `sync.sh`: After copying, strip SUDD-specific front-matter and replace with CLI-appropriate metadata
- OpenCode: `name: sudd-{command}` format
- Claude Code: filename-only (no front-matter name needed)
- Crush: `name: sudd-{command}` format

### FR-10: Structured Lessons
Lesson entries in `memory/lessons.md` must follow this format:
```markdown
### [{outcome}] {task-name} — {date}
**Tags:** {comma-separated: domain, technology, failure-mode}
**Confidence:** HIGH | MEDIUM | LOW
**What worked:** ...
**What failed:** ...
**Lesson:** ...
```

### FR-11: Blocker Detector Enhancement
Add to blocker-detector.md RETRY patterns:
- "module not found" → RETRY with "install the dependency first, then re-run"
- "no such file or directory" → RETRY with "check file paths against design.md"

### FR-12: Makefile Fix
- Replace `cp bin/$(BINARY) $(GOPATH)/bin/` with `$(GO) install ./cmd/sudd`

---

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- `state.json` with version "1.0" must be auto-migrated: missing fields get defaults
- Old installations without `tests_passed`/`gate_score` continue working

### NFR-2: No New Dependencies
- All Go fixes use stdlib only (no new packages)
- Framework changes are markdown-only

### NFR-3: Idempotent Sync
- Running `sync.sh` multiple times produces identical output

---

## Consumer Handoffs

### Handoff 1: Agent Files → CLI Commands
- **Producer**: Agent markdown files (e.g., `handoff-validator.md`)
- **Consumer**: Command files (e.g., `apply.md`, `gate.md`)
- **Contract**: Threshold numbers in agent files MUST match what commands expect (95/100)
- **Validation**: Grep all `.md` files for score thresholds; no file should contain "70" as a pass threshold

### Handoff 2: State Schema → State File
- **Producer**: `state.schema.json`
- **Consumer**: `state.json` and all micro commands
- **Contract**: Every field in schema must be read/written by at least one command
- **Validation**: All new fields (`tests_passed`, `gate_score`, `gate_passed`) are set by commands and read by guards

### Handoff 3: Go CLI → Installed Project
- **Producer**: `installer.go` with embedded templates
- **Consumer**: Target project directory
- **Contract**: All files from templates/ are copied; skipped files produce visible warnings
- **Validation**: `sudd status` in target shows all components installed

---

## Out of Scope
- Multi-change concurrency / change queue
- Formal orchestration DSL / protocol specification
- CI/CD pipeline
- New agent creation
- Goreleaser homebrew/scoop repos
- Dependency upgrades beyond charmbracelet/bubbles
