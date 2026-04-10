# Design: brown_sudd-update-mechanism_01

## Architecture Overview

```
SOURCE REPO (sudd2/)                    TARGET PROJECT
┌─────────────────────┐                 ┌─────────────────────┐
│ sudd/               │                 │ sudd/               │
│   agents/*.md       │──── sync.sh ───→│   agents/*.md       │ OVERWRITE
│   commands/**/*.md  │    update       │   commands/**/*.md  │ OVERWRITE
│   vision.md         │                 │   vision.md         │ OVERWRITE
│   state.schema.json │                 │   state.schema.json │ OVERWRITE
│                     │                 │   personas/         │ PRESERVE
│                     │                 │   changes/          │ PRESERVE
│                     │                 │   memory/           │ PRESERVE
│                     │                 │   state.json        │ PRESERVE
│                     │                 │   sudd.yaml         │ PRESERVE
└─────────────────────┘                 │   .sudd-version     │ WRITE
                                        └─────────────────────┘
                                        │ .sudd-backup/{ts}/  │ BACKUP
                                        └─────────────────────┘

EMBEDDED (sudd-go binary)               TARGET PROJECT
┌─────────────────────┐                 ┌─────────────────────┐
│ templates/sudd/     │── sudd update ─→│ (same as above)     │
│ templates/.claude/  │                 │                     │
│ templates/.opencode/│                 │                     │
└─────────────────────┘                 └─────────────────────┘
```

## Component: sync.sh Update Mode

### Responsibility
Copy framework files from source repo to target project, with backup and diff.

### Interface
```bash
# Existing (unchanged):
bash sudd/sync.sh [opencode|claude|crush|all]

# New:
bash sudd/sync.sh update /path/to/target [--dry-run]
```

### Implementation

```bash
sync_update() {
    local target="$1"
    local dry_run="${2:-}"
    local sudd_src="$SCRIPT_DIR"  # sudd/ directory in source repo
    local sudd_dst="$target/sudd"

    # 1. Verify target has SUDD installed
    if [ ! -d "$sudd_dst" ]; then
        echo "ERROR: $target does not have SUDD installed. Run 'sudd init' first."
        exit 1
    fi

    # 2. Define framework files to overwrite
    FRAMEWORK_DIRS=("agents" "commands")
    FRAMEWORK_FILES=("vision.md" "state.schema.json")

    # 3. Compute diff summary
    local added=0 modified=0 unchanged=0
    # ... compare files, count changes

    # 4. Show summary
    echo "Update summary: $added new, $modified changed, $unchanged unchanged"

    # 5. If dry-run, stop here
    if [ "$dry_run" = "--dry-run" ]; then return; fi

    # 6. Create backup
    local backup_dir="$target/.sudd-backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    # Copy existing framework files to backup

    # 7. Overwrite framework files
    # Copy agents/, commands/, vision.md, state.schema.json

    # 8. Sync CLI folders (existing behavior)
    # Run opencode/claude/crush sync for target

    # 9. Write .sudd-version
    echo "version: $(date +%Y-%m-%d)" > "$target/.sudd-version"
    echo "source: $(git rev-parse --short HEAD 2>/dev/null || echo 'manual')" >> "$target/.sudd-version"
    echo "updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$target/.sudd-version"
}
```

## Component: Go CLI Update Command

### Responsibility
Same as sync.sh but uses embedded templates instead of source directory.

### Interface
```
sudd update [target] [--dry-run] [--force] [--components list]
```

### Implementation Notes

Add to `main.go`:
```go
var updateCmd = &cobra.Command{
    Use:   "update [target]",
    Short: "Update SUDD framework files in a project",
    Args:  cobra.MaximumNArgs(1),
    Run:   runUpdate,
}

var dryRunFlag bool

func init() {
    updateCmd.Flags().BoolVar(&dryRunFlag, "dry-run", false, "Show changes without writing")
    updateCmd.Flags().BoolVarP(&forceFlag, "force", "f", false, "Skip confirmation")
    updateCmd.Flags().StringVarP(&componentsFlag, "components", "c", "", "Components to update")
    rootCmd.AddCommand(updateCmd)
}
```

Add to `installer.go`:
```go
// Update overwrites framework files while preserving project files
func (i *Installer) Update(component Component) (added, modified, unchanged int, err error) {
    // Same as Install but:
    // 1. Never skips existing files (always overwrites framework files)
    // 2. Skips preserve-listed directories
    // 3. Returns change counts
}

// Backup copies existing framework files to .sudd-backup/
func (i *Installer) Backup(component Component) error {
    // Copy existing files to timestamped backup dir
}

// PreservedPaths returns paths that should never be overwritten
func PreservedPaths() []string {
    return []string{
        "sudd/personas",
        "sudd/changes",
        "sudd/memory",
        "sudd/state.json",
        "sudd/sudd.yaml",
    }
}

// WriteVersion writes .sudd-version to target
func (i *Installer) WriteVersion() error {
    // Write version file with date + source
}
```

## Component: .sudd-version File

### Format
```
version: 2026-03-13
source: abc1234
updated: 2026-03-13T15:30:00Z
```

### Written by
- `sudd init` — on fresh install
- `sudd update` — on update
- `sync.sh update` — on update

### Read by
- `sudd status` — compare with embedded version

## Component: Status Version Check

### Enhancement to runStatus()
```go
func runStatus(cmd *cobra.Command, args []string) {
    // ... existing component check ...

    // Read .sudd-version
    versionFile := filepath.Join(target, ".sudd-version")
    if data, err := os.ReadFile(versionFile); err == nil {
        fmt.Printf("\nVersion: %s", string(data))
    } else {
        fmt.Println("\nNo .sudd-version found (installed before version tracking)")
    }
}
```

## File Changes

### Modified Files (2)
- `sudd/sync.sh` — add `update` subcommand with backup, diff, version tracking
- `sudd/sync.bat` — add equivalent Windows update functionality

### Modified Files — Go CLI (3)
- `sudd-go/cmd/sudd/main.go` — add `updateCmd`, `dryRunFlag`, `runUpdate()` function
- `sudd-go/internal/installer/installer.go` — add `Update()`, `Backup()`, `PreservedPaths()`, `WriteVersion()`, `DiffSummary()` methods
- `sudd-go/cmd/sudd/main.go` — enhance `runStatus()` to read `.sudd-version`

### New Files (0)
No new files — all functionality added to existing files.

### Templates Updated (1)
- `sudd-go/cmd/sudd/templates/` — embedded templates must be refreshed to include latest agents (this is a manual step before building)
