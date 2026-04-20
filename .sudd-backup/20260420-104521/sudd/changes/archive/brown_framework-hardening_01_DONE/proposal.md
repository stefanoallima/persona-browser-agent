# Change: brown_framework-hardening_01

## Status
proposed

## Summary
Harden the SUDD framework by fixing critical architectural gaps, Go CLI bugs, agent conflicts, repo hygiene issues, and the incomplete state machine — turning SUDD from a design document into a production-ready framework.

## Motivation
A critical review exposed that SUDD has a sound philosophy but fails in practice due to:
1. **The orchestration layer is implicit** — commands describe what should happen in prose, not in enforceable specifications. Every CLI implementation interprets them differently.
2. **State machine is incomplete** — no tracking of test status, no phase transition enforcement, no concurrent change support, no rollback on failure.
3. **Go CLI has critical bugs** — silent installation failures, panic-prone type assertions, reimplemented stdlib, zero test coverage.
4. **Agent roles conflict & quality bar too low** — handoff-validator uses a 70/100 threshold which produces garbage. ALL gates must be 95/100. Also: duplicate reviewer agents, dead contract-verifier with no entry point.
5. **Repo hygiene is broken** — install.sh references non-existent paths, orphaned commands, nothing committed to git, inadequate .gitignore.

## Scope
What's included:

### Phase 1: State Machine & Orchestration (Critical)
- Add `tests_passed` and `gate_score` fields to `state.json` schema
- Add phase transition validation to all micro commands (e.g., `/sudd:apply` requires phase >= "planning")
- Add rollback instructions for stuck changes (revert modified source files)
- Document the orchestration protocol formally (not prose — a machine-readable flow)

### Phase 2: Go CLI Fixes (Critical)
- Fix silent failures in `installer.go` — `copyDir()`, `copyFile()`, `InstallCLAUDEMD()` must warn when skipping
- Add comma-ok type assertion in `main.go:135`
- Replace custom `splitString()`/`trimString()` with `strings.Split()`/`strings.TrimSpace()`
- Remove dead code: `InstallProgressMsg`, unused Model fields, commented imports
- Upgrade `charmbracelet/bubbles` from pre-release commit to latest stable
- Add error wrapping with `fmt.Errorf("%w", err)` throughout
- Fix Makefile `install` target to not assume `$GOPATH`
- Add unit tests for installer, component selection, string parsing

### Phase 3: Agent Cleanup (High)
- Merge `reviewer.md` into `peer-reviewer.md` (one agent, one job)
- **Unify all validation thresholds to 95/100** — both handoff-validator AND persona-validator must require >= 95. The old 70 threshold produced garbage. Every validation gate in the framework must hold to 95.
- Give contract-verifier an entry point in `/sudd:apply` or remove it
- Fix blocker-detector to include dependency installation in RETRY instructions

### Phase 4: Repo Hygiene (High)
- Fix `install.sh` to match current directory structure (`sudd/agents/` not `agents/`)
- Add orphaned commands (`add-task.md`, `init.md`) to `sudd/commands/micro/` as source of truth
- Fix `.gitignore`: add `.ruff_cache/`, `sudd-go/bin/`, `sudd-go/dist/`, `*.exe~`, `.DS_Store`
- Delete `sudd-go/bin/sudd.exe~` backup file
- Remove or rename `sudd-test/` (it tests nothing)
- Resolve duplicate `reference/vision.md` vs `sudd/vision.md`

### Phase 5: Sync & Learning (Medium)
- Fix `sync.sh`/`sync.bat` to transform front-matter metadata for each CLI target (not raw copy)
- Add structured metadata to `memory/lessons.md` entries (tags, confidence, domain)
- Add lesson injection step to `/sudd:apply` that selects top-5 relevant lessons by tag matching

What's NOT included:
- Multi-change concurrency (future work — requires queue system)
- Formal orchestration DSL (future work — requires protocol design)
- CI/CD pipeline setup
- New agent creation
- Goreleaser homebrew/scoop repo creation

## Success Criteria
- [ ] `state.json` schema includes `tests_passed` boolean and `gate_score` integer
- [ ] All micro commands validate current phase before executing
- [ ] Go CLI: `copyDir()`/`copyFile()` print warnings when skipping existing files
- [ ] Go CLI: `main.go` uses comma-ok type assertion
- [ ] Go CLI: no custom string functions — uses `strings` stdlib
- [ ] Go CLI: `go test ./...` passes with >= 1 test file per package
- [ ] Only one review agent exists (`peer-reviewer.md`)
- [ ] ALL validator agents (handoff-validator, persona-validator, contract-verifier) use 95/100 as the pass threshold — no exceptions
- [ ] Old 70/100 threshold removed from every agent file in the framework
- [ ] Contract-verifier has an explicit invocation point or is removed
- [ ] `install.sh` succeeds when run on a fresh directory
- [ ] `.gitignore` covers all generated artifacts
- [ ] `sync.sh` transforms command metadata per CLI target
- [ ] `memory/lessons.md` has a structured entry format with tags

## Dependencies
- None — all changes are internal to the SUDD framework

## Risks
- **Scope creep**: 5 phases is large. Mitigation: phases are independent; ship each phase separately.
- **Breaking existing installations**: Changing state.json schema may invalidate existing state files. Mitigation: add schema version migration (check `version` field).
- **Agent instruction changes break existing workflows**: Merging reviewer agents or changing thresholds affects active users. Mitigation: document changes in `memory/lessons.md`.
- **Sync transformation complexity**: Different CLI frameworks have different metadata expectations. Mitigation: start with just Claude Code (best documented), add others incrementally.
