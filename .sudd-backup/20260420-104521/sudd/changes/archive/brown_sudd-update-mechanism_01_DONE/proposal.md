# Change: brown_sudd-update-mechanism_01

## Status
proposed

## Summary
Add update mechanism so projects with SUDD installed can receive framework updates (agents, commands, vision, schema) without losing their project-specific data (personas, changes, memory, state).

## Motivation
SUDD framework files (agents, commands, vision.md) evolve continuously — new agents added, headers standardized, stale paths fixed, critique loops introduced. But projects that already have SUDD installed are stuck on their install-time snapshot. There is no way to push updates to them. This means every project slowly drifts out of sync with the framework, accumulating stale paths and missing capabilities.

## Scope

### What's included:

### 1. Enhanced `sync.sh` (short-term, works now)
- Extend `sudd/sync.sh` to copy framework files to target project directories
- Copy: `agents/*.md`, `commands/**/*.md`, `vision.md`, `state.schema.json`
- Preserve: `personas/`, `changes/`, `memory/`, `state.json`, `sudd.yaml`
- Accept target directory as argument: `bash sudd/sync.sh /path/to/project`
- Show what changed (diff summary) before overwriting
- Backup existing files before overwrite (`.sudd-backup/` with timestamp)

### 2. `sudd update` Go CLI command (long-term)
- Add `update` subcommand to `sudd-go` alongside existing `init` and `status`
- Re-reads embedded templates and overwrites framework files in target directory
- Same overwrite/preserve rules as sync.sh
- Interactive confirmation with diff preview
- `--force` flag to skip confirmation
- `--dry-run` flag to show what would change without writing
- Version tracking: write `.sudd-version` file on install/update with timestamp + commit hash

### 3. Version tracking
- `.sudd-version` file in target project root: records which version of SUDD framework is installed
- Format: `version: {date}`, `source: {commit-hash or "manual"}`, `updated: {timestamp}`
- `sudd status` reads this file and warns if framework is outdated

### What's NOT included:
- Auto-update (no pull/push without user action)
- Package manager distribution (npm, pip, brew)
- Remote update from GitHub (local file copy only)
- Changes to the SUDD workflow itself

## Success Criteria
- [ ] `sync.sh` can update a target project's SUDD framework files in one command
- [ ] Project-specific files (personas, changes, memory, state) are never overwritten
- [ ] Diff summary shown before overwriting
- [ ] Backup created before overwrite
- [ ] `sudd update` CLI command works with embedded templates
- [ ] `.sudd-version` tracks installed version
- [ ] `sudd status` warns when framework is outdated

## Dependencies
- brown_agent-sophistication_01 (gate passed) — agents must be in final form before update mechanism distributes them
- brown_workflow-reliability_01 (pending) — command wiring should be complete before distribution

## Risks
- Risk: overwriting user customizations to agent files → Mitigation: backup before overwrite, preserve list is explicit
- Risk: partial update leaves inconsistent state → Mitigation: atomic copy (all-or-nothing with rollback on failure)
- Risk: version tracking drift if user manually edits → Mitigation: `.sudd-version` is informational only, not enforced

## Size: M
