# Specifications: brown_sudd-update-mechanism_01

## Functional Requirements

### FR-1: Framework Update via sync.sh
- Given: A project has SUDD installed (sudd/ directory exists)
- When: User runs `bash sudd/sync.sh update /path/to/project`
- Then: Framework files (agents, commands, vision, schema) are copied from source to target. Project-specific files (personas, changes, memory, state.json, sudd.yaml) are never touched.

### FR-2: Backup Before Overwrite
- Given: Target project has existing framework files
- When: Update is about to overwrite them
- Then: Existing files are backed up to `.sudd-backup/{timestamp}/` before overwriting. Backup preserves directory structure.

### FR-3: Diff Summary
- Given: Update is about to run
- When: Source and target files differ
- Then: A summary is shown listing files that will be added, modified, or unchanged. Count of each category displayed.

### FR-4: CLI Sync Mode (commands only)
- Given: User runs `bash sudd/sync.sh [opencode|claude|crush|all]` (existing behavior)
- When: No `update` subcommand is used
- Then: Existing behavior preserved — only syncs commands to CLI agent folders.

### FR-5: Go CLI Update Command
- Given: User runs `sudd update [target]`
- When: Target has SUDD installed
- Then: Embedded templates overwrite framework files, preserve project files, show diff summary, create backup. Same overwrite/preserve rules as sync.sh.

### FR-6: Dry Run Mode
- Given: User runs `sudd update --dry-run [target]`
- When: Executed
- Then: Shows what would change without writing any files.

### FR-7: Force Mode
- Given: User runs `sudd update --force [target]`
- When: Executed
- Then: Skips confirmation prompt and applies updates immediately.

### FR-8: Version Tracking
- Given: SUDD is installed or updated in a project
- When: Installation or update completes
- Then: `.sudd-version` file is written with version date, source identifier, and timestamp.

### FR-9: Status Version Check
- Given: User runs `sudd status`
- When: `.sudd-version` exists
- Then: Shows installed version and warns if framework files appear outdated (by comparing embedded version with installed version).

### FR-10: Selective Component Update
- Given: User wants to update only specific components
- When: User runs `sudd update --components sudd,claude [target]`
- Then: Only the specified components are updated.

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Constraint: Existing `sync.sh` behavior must not change. The `update` subcommand is additive.
- Rationale: Projects using `sync.sh` for CLI folder syncing should not break.

### NFR-2: No External Dependencies
- Constraint: sync.sh uses only bash builtins and standard Unix tools (cp, diff, mkdir, date). Go CLI uses only existing dependencies.
- Rationale: SUDD is zero-dependency by design.

### NFR-3: Cross-Platform
- Constraint: sync.sh works on macOS/Linux. Go CLI works on macOS/Linux/Windows. sync.bat updated for Windows.
- Rationale: Users work on all platforms.

## File Classification

### Framework Files (OVERWRITE on update)
```
sudd/agents/*.md
sudd/commands/macro/*.md
sudd/commands/micro/*.md
sudd/vision.md
sudd/state.schema.json
```

### Project Files (PRESERVE on update)
```
sudd/personas/
sudd/changes/
sudd/memory/
sudd/state.json
sudd/sudd.yaml
```

### CLI Agent Files (OVERWRITE — generated from commands)
```
.opencode/command/sudd-*.md
.claude/commands/sudd/*.md
.crush/commands/sudd-*.md
```

## Consumer Handoffs

### Handoff: sync.sh → Target Project
- **Format**: File copy with backup
- **Location**: Target project directory
- **Required fields**: Source sudd/ directory must exist
- **Validated by**: File count comparison after copy
- **Error case**: Target has no sudd/ directory → warn "SUDD not installed, use `sudd init` first"

### Handoff: Go CLI update → Target Project
- **Format**: Embedded template extraction with selective overwrite
- **Location**: Target project directory
- **Required fields**: Embedded templates must include framework files
- **Validated by**: `.sudd-version` written after successful update
- **Error case**: Target not initialized → suggest `sudd init`

## Out of Scope
- Auto-update from remote repositories
- Package manager distribution
- Merging user customizations (overwrite-or-preserve, no merge)
- Changes to SUDD workflow or agent logic
