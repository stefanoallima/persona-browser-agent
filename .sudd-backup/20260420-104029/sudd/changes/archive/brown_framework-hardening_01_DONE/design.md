# Design: brown_framework-hardening_01

## Architecture Overview

This change modifies existing files across 4 layers. No new components are introduced.

```
Layer 1: Agent Instructions (sudd/agents/*.md)
  └── Threshold alignment, deduplication, entry points

Layer 2: Command Files (sudd/commands/micro/*.md)
  └── Phase guards, state field usage, contract-verifier step

Layer 3: State & Schema (sudd/state.json, state.schema.json)
  └── New fields, migration logic

Layer 4: Go CLI (sudd-go/)
  └── Bug fixes, dead code removal, tests

Layer 5: Repo Meta (.gitignore, install.sh, sync.sh)
  └── Hygiene fixes, sync transformation
```

## Component Changes

### 1. Agent Files — Threshold Unification

**handoff-validator.md** changes:
- Replace "70+ = CONSUMABLE" with "95+ = CONSUMABLE"
- Replace "Below 70 = NOT_CONSUMABLE" with "Below 95 = NOT_CONSUMABLE"
- Update scoring guide: 95-100 = CONSUMABLE, below 95 = NOT_CONSUMABLE
- Update rule 5: "Score honestly (95+ = CONSUMABLE)"

**persona-validator.md** changes:
- Replace scoring guide table:
  - 95-100: Excellent. SATISFIED.
  - 80-94: Good but gaps. NOT_SATISFIED.
  - 60-79: Significant issues. NOT_SATISFIED.
  - 0-59: Completely wrong. NOT_SATISFIED.
- Replace "70 is the threshold" with "95 is the threshold"

**contract-verifier.md** changes:
- Add numeric scoring (0-100) alongside COMPLIANT/NON-COMPLIANT
- Score < 95 OR any BREAKING violation = NON-COMPLIANT
- Add entry point documentation: "Called by /sudd:apply after coder, before handoff-validator"

**peer-reviewer.md** changes:
- Add numeric scoring (0-100) alongside APPROVE/REQUEST_CHANGES/REJECT
- Score < 95 = REQUEST_CHANGES
- Absorb unique content from reviewer.md (persona check emphasis)

**reviewer.md**: DELETE (duplicate)

**blocker-detector.md** changes:
- Add "install the dependency first" to RETRY action for "module not found"
- Add "check file paths against design.md" for "no such file" pattern

### 2. Command Files — Phase Guards & Contract Verifier

**apply.md** changes:
- Add after coder step, before handoff-validator:
  ```
  ### 3a-bis. Contract Verification
  Task(agent=contract-verifier)
  Read: agents/contract-verifier.md
  Input: specs.md contracts, code output
  If NON-COMPLIANT with BREAKING: fail task, provide feedback
  ```
- Add explicit phase guard at top:
  ```
  GUARD: phase must be >= "build" AND specs.md must exist
  If not: "Run /sudd:plan first"
  ```

**test.md** changes:
- After tests pass, update state:
  ```json
  { "tests_passed": true }
  ```
- Add phase guard: code must be implemented

**gate.md** changes:
- Add guard: `tests_passed` must be `true` in state.json
- After gate passes, update state:
  ```json
  { "gate_score": {score}, "gate_passed": true }
  ```

**done.md** changes:
- Add guard: `gate_passed == true` OR `retry_count >= 8`
- Add rollback instructions for STUCK outcome

### 3. State Schema

**state.schema.json** additions:
```json
{
  "tests_passed": {
    "type": "boolean",
    "default": false,
    "description": "Set to true by /sudd:test when all tests pass"
  },
  "gate_score": {
    "type": "integer",
    "default": 0,
    "minimum": 0,
    "maximum": 100,
    "description": "Minimum consumer score from /sudd:gate"
  },
  "gate_passed": {
    "type": "boolean",
    "default": false,
    "description": "Set to true by /sudd:gate when all consumers >= 95"
  }
}
```

**state.json** migration: Commands that read state.json must treat missing fields as defaults (false/0). No explicit migration script needed — JSON parsing with defaults handles it.

### 4. Go CLI Fixes

**installer.go**:
```go
// Before (silent skip):
if _, err := os.Stat(dst); err == nil && !i.Force {
    return nil
}

// After (warning):
if _, err := os.Stat(dst); err == nil && !i.Force {
    fmt.Printf("  ⊘ Skipped (exists): %s\n", dst)
    return nil
}
```

**main.go**:
```go
// Before (panic risk):
m := finalModel.(tui.Model)

// After (safe):
m, ok := finalModel.(tui.Model)
if !ok {
    fmt.Fprintf(os.Stderr, "Error: unexpected model type\n")
    os.Exit(1)
}
```

```go
// Before (custom stdlib reimplementation):
func splitString(s, sep string) []string { ... }
func trimString(s string) string { ... }

// After (use stdlib):
import "strings"
// Delete splitString and trimString
// In splitComponents: use strings.Split and strings.TrimSpace
```

**tui.go**:
- Remove commented `lipgloss` import
- Remove `InstallProgressMsg` struct
- Remove unused fields: `installing`, `installed`, `total` from Model

**Makefile**:
```makefile
# Before:
install: build
	cp bin/$(BINARY) $(GOPATH)/bin/

# After:
install:
	$(GO) install $(GOFLAGS) ./cmd/sudd
```

### 5. Repo Hygiene

**.gitignore** additions:
```
.ruff_cache/
sudd-go/bin/
sudd-go/dist/
*.exe~
*~
.DS_Store
Thumbs.db
```

**install.sh** path fixes:
```bash
# Before:
mkdir -p "$TARGET/agents"
cp "$SUDD2_SOURCE/agents/"*.md "$TARGET/agents/"

# After:
mkdir -p "$TARGET/sudd/agents"
cp "$SUDD2_SOURCE/sudd/agents/"*.md "$TARGET/sudd/agents/"
```

Same pattern for personas, commands, memory directories.

**sync.sh** transformation:
After copying, for OpenCode and Crush targets, ensure front-matter `name:` field matches expected format. For Claude Code, strip front-matter name (uses filename only).

### 6. Structured Lessons Format

**memory/lessons.md** template update:
```markdown
### [{DONE|STUCK|BLOCKED}] {task-name} — {YYYY-MM-DD}
**Tags:** {domain}, {technology}, {failure-mode}
**Confidence:** HIGH | MEDIUM | LOW
**What worked:** {approach that succeeded}
**What failed:** {approach that didn't work}
**Lesson:** {takeaway for future tasks}
```

---

## Data Flow

```
/sudd:apply
  → coder agent (writes code)
  → contract-verifier agent (checks code vs specs) [NEW]
  → handoff-validator agent (scores >= 95)
  → if pass: commit, next task
  → if fail: feedback loop

/sudd:test
  → run tests
  → if pass: state.tests_passed = true [NEW]
  → if fail: blocker-detector → fix → retry

/sudd:gate
  → GUARD: state.tests_passed must be true [NEW]
  → persona-validator (scores >= 95)
  → if pass: state.gate_passed = true, state.gate_score = N [NEW]
  → if fail: retry with escalation

/sudd:done
  → GUARD: state.gate_passed must be true OR retry >= 8 [NEW]
  → learning-engine (structured lessons with tags) [ENHANCED]
  → archive
```

---

## File Changes Summary

| File | Action | Effort |
|------|--------|--------|
| `sudd/agents/handoff-validator.md` | Modify thresholds | S |
| `sudd/agents/persona-validator.md` | Modify thresholds + scoring guide | S |
| `sudd/agents/contract-verifier.md` | Add numeric scoring + entry point | S |
| `sudd/agents/peer-reviewer.md` | Add scoring + absorb reviewer.md | M |
| `sudd/agents/reviewer.md` | DELETE | S |
| `sudd/agents/blocker-detector.md` | Add retry actions | S |
| `sudd/commands/micro/apply.md` | Add contract-verifier step + guard | M |
| `sudd/commands/micro/test.md` | Add tests_passed state update | S |
| `sudd/commands/micro/gate.md` | Add tests_passed guard + gate_score | S |
| `sudd/commands/micro/done.md` | Add gate_passed guard + rollback | S |
| `sudd/state.schema.json` | Add 3 new fields | S |
| `sudd/state.json` | Add 3 new fields with defaults | S |
| `sudd-go/internal/installer/installer.go` | Fix silent failures | M |
| `sudd-go/cmd/sudd/main.go` | Type safety + stdlib + dead code | M |
| `sudd-go/internal/tui/tui.go` | Remove dead code | S |
| `sudd-go/Makefile` | Fix install target | S |
| `sudd-go/internal/installer/installer_test.go` | NEW: tests | L |
| `sudd-go/cmd/sudd/main_test.go` | NEW: tests | M |
| `.gitignore` | Add patterns | S |
| `install.sh` | Fix paths | M |
| `sudd/sync.sh` | Add metadata transform | M |
| `sudd/sync.bat` | Add metadata transform | M |
| `sudd/memory/lessons.md` | Update template format | S |
| `sudd-go/bin/sudd.exe~` | DELETE | S |
| `reference/vision.md` | DELETE (duplicate) | S |
| `sudd/commands/micro/add-task.md` | NEW: move from .claude/ | S |
| `sudd/commands/micro/init.md` | NEW: move from .claude/ | S |

**Total: 27 file changes (20 modify, 3 delete, 4 new)**
