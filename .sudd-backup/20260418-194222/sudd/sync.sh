#!/usr/bin/env bash
# SUDD Command Sync Script
# Syncs commands from sudd/commands/ to CLI agent folders
# Also supports 'update' subcommand for updating SUDD framework in target projects

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SUDD_COMMANDS="$PROJECT_ROOT/sudd/commands"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[sudd:sync]${NC} $1"; }
ok() { echo -e "${GREEN}â${NC} $1"; }
warn() { echo -e "${YELLOW}â ${NC} $1"; }
err() { echo -e "${RED}â${NC} $1" >&2; }

# Sync to OpenCode CLI
sync_opencode() {
    local target="$PROJECT_ROOT/.opencode/command"
    mkdir -p "$target"
    
    # Macro commands
    for cmd in "$SUDD_COMMANDS/macro"/*.md; do
        [ -f "$cmd" ] || continue
        local name=$(basename "$cmd" .md)
        local dest="$target/sudd-$name.md"
        cp "$cmd" "$dest"
        sed -i '' "s/^name: sudd:.*/name: sudd-$name/" "$dest"
        ok "opencode: sudd-$name"
    done

    # Micro commands
    for cmd in "$SUDD_COMMANDS/micro"/*.md; do
        [ -f "$cmd" ] || continue
        local name=$(basename "$cmd" .md)
        local dest="$target/sudd-$name.md"
        cp "$cmd" "$dest"
        sed -i '' "s/^name: sudd:.*/name: sudd-$name/" "$dest"
        ok "opencode: sudd-$name"
    done
}

# Skill description lookup (bash 3.2 compatible — no associative arrays)
get_skill_desc() {
    case "$1" in
        run)      echo "Full autonomous SUDD workflow. Use when the user wants to build a feature end-to-end autonomously." ;;
        new)      echo "Create a new change proposal. Use when the user wants to start a new feature or fix." ;;
        plan)     echo "Create specs, design, and tasks for a change. Use when the user wants to plan implementation." ;;
        apply)    echo "Implement tasks from the task list. Use when the user wants to start building." ;;
        test)     echo "Run tests and validate implementation. Use when the user wants to test code." ;;
        gate)     echo "Persona validation gate. Use when the user wants to validate if work is ready." ;;
        done)     echo "Archive completed or stuck change. Use when implementation is complete." ;;
        port)     echo "Import or upgrade SUDD. Use when the user wants to upgrade or migrate." ;;
        chat)     echo "Thinking partner mode. Use when the user wants to explore ideas." ;;
        status)   echo "Show SUDD state and progress. Use when the user wants to check status." ;;
        init)     echo "Initialize SUDD in a project. Use when setting up SUDD for the first time." ;;
        add-task) echo "Add a new change proposal to the backlog." ;;
        auto)     echo "Fully autonomous mode. Use when you want to process all queued changes in sequence." ;;
        *)        echo "SUDD $1 command." ;;
    esac
}

# Sync to Claude Code CLI — generate skills (v3.1)
sync_claude() {
    local SUDD_DIR="$PROJECT_ROOT/sudd"
    local SKILLS_DIR="$PROJECT_ROOT/.claude/skills"

    # Remove old commands directory if it exists
    if [ -d "$PROJECT_ROOT/.claude/commands/sudd" ]; then
        rm -rf "$PROJECT_ROOT/.claude/commands/sudd"
        ok "Removed old .claude/commands/sudd/"
    fi

    for cmd_file in "$SUDD_DIR/commands/micro/"*.md "$SUDD_DIR/commands/macro/"*.md; do
        if [ ! -f "$cmd_file" ]; then continue; fi
        local cmd_name=$(basename "$cmd_file" .md)
        local skill_dir="$SKILLS_DIR/sudd-$cmd_name"
        mkdir -p "$skill_dir"

        local desc
        desc="$(get_skill_desc "$cmd_name")"

        # Write SKILL.md with frontmatter + command content
        {
            echo "---"
            echo "name: sudd-$cmd_name"
            echo "description: $desc"
            echo "license: MIT"
            echo "metadata:"
            echo "  author: sudd"
            echo "  version: \"3.1\""
            echo "---"
            echo ""
            # Strip original YAML frontmatter if present (between --- markers)
            awk 'BEGIN{skip=0; first=1} /^---$/{if(first){skip=1; first=0; next} if(skip){skip=0; next}} skip{next} {print}' "$cmd_file"
        } > "$skill_dir/SKILL.md"

        ok "claude: sudd-$cmd_name"
    done
}

# Sync to Crush CLI — generate skills in .crush/skills/ (SKILL.md format)
sync_crush() {
    local SUDD_DIR="$PROJECT_ROOT/sudd"
    local SKILLS_DIR="$PROJECT_ROOT/.crush/skills"

    # Remove old commands directory if it exists
    if [ -d "$PROJECT_ROOT/.crush/commands" ]; then
        rm -rf "$PROJECT_ROOT/.crush/commands"
        ok "Removed old .crush/commands/"
    fi

    for cmd_file in "$SUDD_DIR/commands/micro/"*.md "$SUDD_DIR/commands/macro/"*.md; do
        if [ ! -f "$cmd_file" ]; then continue; fi
        local cmd_name=$(basename "$cmd_file" .md)
        local skill_dir="$SKILLS_DIR/sudd-$cmd_name"
        mkdir -p "$skill_dir"

        local desc
        desc="$(get_skill_desc "$cmd_name")"

        # Write SKILL.md with frontmatter + command content
        {
            echo "---"
            echo "name: sudd:$cmd_name"
            echo "description: $desc"
            echo "license: MIT"
            echo "metadata:"
            echo "  author: sudd"
            echo "  version: \"3.3\""
            echo "---"
            echo ""
            # Strip original YAML frontmatter if present (between --- markers)
            awk 'BEGIN{skip=0; first=1} /^---$/{if(first){skip=1; first=0; next} if(skip){skip=0; next}} skip{next} {print}' "$cmd_file"
        } > "$skill_dir/SKILL.md"

        ok "crush: sudd:$cmd_name"
    done
}

# âââ Update subcommand âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# Updates the SUDD framework in a target project directory.
# Overwrites: agents/, commands/, context/, specs/, vision.md, state.schema.json
# Preserves: personas/, changes/, memory/, state.json, sudd.yaml

sync_update() {
    local target_dir="$1"
    local dry_run=false
    local force=false

    # Parse flags from any position
    for arg in "$@"; do
        if [ "$arg" = "--dry-run" ]; then
            dry_run=true
        fi
        if [ "$arg" = "--force" ]; then
            force=true
        fi
    done

    # Default target to PROJECT_ROOT if not provided or if first arg is a flag
    if [ -z "$target_dir" ] || [[ "$target_dir" == --* ]]; then
        target_dir="$PROJECT_ROOT"
    fi

    # Resolve to absolute path
    target_dir="$(cd "$target_dir" 2>/dev/null && pwd)" || {
        err "Target directory does not exist: $1"
        exit 1
    }

    local target_sudd="$target_dir/sudd"
    local source_sudd="$SCRIPT_DIR"

    # Verify SUDD is installed in target
    if [ \! -d "$target_sudd" ]; then
        err "SUDD not installed, run 'sudd init' first"
        exit 1
    fi

    log "Updating SUDD framework in: $target_dir"
    if $dry_run; then
        warn "DRY RUN - no files will be modified"
    fi

    # Framework dirs and files to OVERWRITE
    local overwrite_dirs=("agents" "commands" "context" "specs")
    local overwrite_files=("vision.md" "state.schema.json")

    # Compute diff summary
    local added=0
    local modified=0
    local unchanged=0

    # Collect all source files that will be synced
    local all_source_files=()

    # Files from overwrite dirs
    for dir in "${overwrite_dirs[@]}"; do
        if [ -d "$source_sudd/$dir" ]; then
            while IFS= read -r -d '' f; do
                local rel="${f#$source_sudd/}"
                all_source_files+=("$rel")
            done < <(find "$source_sudd/$dir" -type f -print0)
        fi
    done

    # Individual overwrite files
    for file in "${overwrite_files[@]}"; do
        if [ -f "$source_sudd/$file" ]; then
            all_source_files+=("$file")
        fi
    done

    # Classify each file
    for rel in "${all_source_files[@]}"; do
        if [ ! -f "$target_sudd/$rel" ]; then
            added=$((added + 1))
        elif ! diff -q "$source_sudd/$rel" "$target_sudd/$rel" > /dev/null 2>&1; then
            modified=$((modified + 1))
        else
            unchanged=$((unchanged + 1))
        fi
    done

    echo ""
    log "Diff summary:"
    echo "  Files to add:      $added"
    echo "  Files to modify:   $modified"
    echo "  Files unchanged:   $unchanged"
    echo "  Total:             ${#all_source_files[@]}"
    echo ""

    if [ "$added" -eq 0 ] && [ "$modified" -eq 0 ]; then
        log "Nothing to update - framework is already current."
        return 0
    fi

    if $dry_run; then
        # Show details for dry run
        for rel in "${all_source_files[@]}"; do
            if [ ! -f "$target_sudd/$rel" ]; then
                echo -e "  ${GREEN}+ ADD${NC}      $rel"
            elif ! diff -q "$source_sudd/$rel" "$target_sudd/$rel" > /dev/null 2>&1; then
                echo -e "  ${YELLOW}~ MODIFY${NC}   $rel"
            fi
        done
        echo ""
        warn "Dry run complete. Re-run without --dry-run to apply."
        return 0
    fi

    # Confirmation prompt (skip if --force)
    if ! $force; then
        read -r -p "Proceed with update? [y/N] " answer
        if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
            log "Update cancelled."
            return 0
        fi
    fi

    # Backup existing framework files
    local timestamp
    timestamp="$(date +%Y%m%d_%H%M%S)"
    local backup_dir="$target_dir/.sudd-backup/$timestamp"

    log "Backing up to: .sudd-backup/$timestamp/"

    for rel in "${all_source_files[@]}"; do
        if [ -f "$target_sudd/$rel" ]; then
            local dest_dir
            dest_dir="$(dirname "$backup_dir/$rel")"
            mkdir -p "$dest_dir"
            cp "$target_sudd/$rel" "$backup_dir/$rel"
        fi
    done
    ok "Backup complete"

    # Overwrite framework dirs
    for dir in "${overwrite_dirs[@]}"; do
        if [ -d "$source_sudd/$dir" ]; then
            if [ -d "$target_sudd/$dir" ]; then
                rm -rf "$target_sudd/$dir"
            fi
            cp -r "$source_sudd/$dir" "$target_sudd/$dir"
            ok "Updated sudd/$dir/"
        fi
    done

    # Overwrite framework files
    for file in "${overwrite_files[@]}"; do
        if [ -f "$source_sudd/$file" ]; then
            cp "$source_sudd/$file" "$target_sudd/$file"
            ok "Updated sudd/$file"
        fi
    done

    # Write .sudd-version
    local git_hash="manual"
    if command -v git > /dev/null 2>&1; then
        git_hash="$(git -C "$source_sudd" rev-parse --short HEAD 2>/dev/null || echo "manual")"
    fi

    local iso_timestamp
    iso_timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)"

    local sudd_version="3.1.0"

    printf 'version: %s
source: %s
updated: %s
' "$sudd_version" "$git_hash" "$iso_timestamp" > "$target_dir/.sudd-version"

    ok "Wrote .sudd-version"

    echo ""
    log "Update complete! $added added, $modified modified, $unchanged unchanged."
}

# âââ Main ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

case "${1:-all}" in
    opencode)
        log "Syncing SUDD commands..."
        sync_opencode
        log "Done!"
        ;;
    claude)
        log "Syncing SUDD commands..."
        sync_claude
        log "Done!"
        ;;
    crush)
        log "Syncing SUDD commands..."
        sync_crush
        log "Done!"
        ;;
    all)
        log "Syncing SUDD commands..."
        sync_opencode
        sync_claude
        sync_crush
        log "Done!"
        ;;
    update)
        sync_update "$2" "$3" "$4"
        ;;
    *)
        echo "Usage: $0 [opencode|claude|crush|all|update <target-dir> [--dry-run] [--force]]"
        exit 1
        ;;
esac
