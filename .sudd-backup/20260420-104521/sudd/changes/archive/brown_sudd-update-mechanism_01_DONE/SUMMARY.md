# Archive: brown_sudd-update-mechanism_01

## Outcome: DONE

## Summary
Added update mechanism so projects with SUDD installed can receive framework updates (agents, commands, vision, schema) without losing project-specific data. Implemented via sync.sh `update` subcommand (immediate value) and Go CLI `sudd update` command (long-term), with backup, diff summary, confirmation prompt, dry-run, force mode, and version tracking.

## Consumers Validated
- Project Maintainer: 96/100
- Go CLI User: 96/100
- Windows Developer: 95/100
- Framework Owner: 97/100

## Files Changed
### New Files (1)
- `sudd/sync.bat` — Windows batch equivalent with full update subcommand

### Modified Files — sync.sh (1)
- `sudd/sync.sh` — added `sync_update()` with backup, diff summary, confirmation prompt (--force to skip), dry-run, .sudd-version writing; overwrite dirs: agents, commands, context, specs

### Modified Files — Go CLI (2)
- `sudd-go/cmd/sudd/main.go` — added `updateCmd` with --dry-run/--force/--components/--agent flags, `runUpdate()`, enhanced `runStatus()` with version comparison and staleness warning
- `sudd-go/internal/installer/installer.go` — added `Update()`, `DiffSummary()`, `Backup()`, `WriteVersion()`, `PreservedPaths()`, `isPreserved()` methods

### Templates Refreshed (1)
- `sudd-go/cmd/sudd/templates/sudd/` — 20 agents, 12 commands, vision.md, state.schema.json refreshed from source

## Lessons Learned
1. Version format must be consistent across all distribution paths — sync.sh date format vs Go CLI semver caused false staleness warnings
2. Explicit overwrite lists (sync.sh) must match implicit preserve lists (Go CLI) — missing dirs in sync.sh caused inconsistent distribution
3. Dead code flags (--force with no prompt) get caught by persona validators — always implement the behavior a flag implies
4. Gate retry loop (62→90→97) efficiently converges when fixes are targeted at specific validator feedback

## Completed: 2026-03-13
