# Design: brown_port-hardening_01

## Architecture Overview

All changes are within port.md except Gap A (sudd.yaml). The existing step structure is preserved — new logic is inserted into existing steps or added as new sub-steps.

```
STEP 1: DETECTION
  ├── 1a: Auto-detect ──→ + Priority resolution table (W1)
  ├── 1b: Display    ──→ + Priority ranking in output
  ├── 1c: Ensure dirs   (unchanged)
  ├── 1d: Preview    ──→ + Dry-run mode output (W5)
  ├── 1e: Handle     ──→ + Auto-select by priority (W1)
  └── NEW 1f: Git checkpoint (W5)

STEP 3: PORT — BMAD
  └── 3.1: PRD Decomp ──→ + Confidence scoring (W2)
                          + Ambiguous section handling (W2)

STEP 4: PORT — GENERIC/PRD
  └── 4.2: PRD Decomp ──→ + Same confidence scoring (W2)

STEP 5: PORT — SUPERPOWERS
  └── 5.3: Skill patterns ──→ + Collision detection (W4)

STEP 8: FINALIZE
  └── NEW 8d: Post-port validation (W3)
  └── NEW 8e: Design token extraction (Gap A)
  └── NEW 8f: Iterative review (W6, interactive only)

STEP 9: ERROR HANDLING
  └── + Rollback on critical failure (W5)
```

## Component: Framework Priority Resolution (W1)

### Responsibility
When multiple frameworks detected, resolve which to port from automatically.

### Design
Add a priority table to Step 1a:

```markdown
### Framework Priority (when multiple detected)
| Priority | Framework | Rationale |
|----------|-----------|-----------|
| 1 | OpenSpec | Most structured — has specs, changes, tasks |
| 2 | BMAD | Has epics, stories, acceptance criteria |
| 3 | Generic/PRD | Less structured but has requirements |
| 4 | Superpowers | Skills/patterns only, least SUDD-mappable |

When 2+ frameworks detected:
- Auto-select highest priority framework for primary port
- Display resolution with override options
- In merge mode (/sudd:port merge): port all, merge in priority order (highest first)
- Existing BMAD+PRD dedup rule (Guardrail 6) still applies
```

### Implementation Notes
- Add to Step 1e handling: instead of just listing options and asking, auto-recommend the highest-priority framework
- In autonomous mode: auto-select highest priority, log the choice
- In interactive mode: show recommendation, let user override

## Component: PRD Decomposition Confidence (W2)

### Responsibility
Replace blind keyword matching with confidence-scored decomposition.

### Design
Modify the keyword table usage in Steps 3.1 and 4.2:

```markdown
### Confidence Scoring for PRD Section Routing

For each PRD section header, count keyword matches:

| Confidence | Condition | Action |
|------------|-----------|--------|
| definite | 2+ keywords match a single target | Route to that target |
| probable | 1 keyword matches a single target | Route to that target, log: "Probable match: '{header}' → {target} (keyword: {matched})" |
| ambiguous | Keywords match 2+ targets equally | Route to first-priority target, log warning with both targets |
| uncertain | 0 keywords match | Route to vision.md, add to ## Ambiguous Sections in log.md |

### Ambiguous Sections in log.md
After decomposition, if any uncertain sections exist, append:

## Ambiguous Sections (from PRD decomposition)
| Section | Content Preview (first 50 chars) | Routed To | Suggested Target |
|---------|----------------------------------|-----------|-----------------|
| {header} | {preview...} | vision.md (default) | {best guess or "unknown"} |

In interactive mode: display this table and ask for corrections before writing.
In autonomous mode: write with defaults, log for later review.
```

### Implementation Notes
- Confidence scoring is a wrapper around the existing keyword table — not a replacement
- Multi-match (ambiguous) prefers: specs > design > personas > vision (requirement-preserving order)

## Component: Post-Port Validation (W3)

### Responsibility
After port completes, verify nothing was silently dropped.

### Design
Add Step 8d after the summary log:

```markdown
### 8d. Post-Port Validation

1. **Count source sections**: Read the original source document(s), count `##`/`###` headers
2. **Count ported sections**: Read all generated SUDD files, count `##`/`###` headers
3. **Compare**:
   - If ported >= source: PASS
   - If ported < source: check which source sections have no match
4. **Classify gaps**:
   - Source section contains requirement keywords → CRITICAL (requirement may be lost)
   - Source section is informational → WARNING (content dropped but not blocking)
5. **Report** in log.md:

## Post-Port Validation
- Source documents: {list}
- Source sections: {N}
- Ported sections: {M}
- Coverage: {M/N * 100}%
- Missing:
  - [CRITICAL] "{section name}" — contains requirements, not ported
  - [WARNING] "{section name}" — informational, not ported
- Result: PASS (all requirements covered) | FAIL (requirements missing)

6. **On FAIL**: If autonomous mode, log and continue. If interactive, display and ask user.
```

## Component: Agent Collision Detection (W4)

### Responsibility
Detect existing agent customizations before Superpowers port overwrites them.

### Design
Modify Step 5.3 (Skill patterns):

```markdown
### Collision Detection (before writing agent notes)

Before appending patterns to any agent file or lessons.md:

1. **Check for existing SUDD agents**: For each skill that maps to a SUDD agent:
   - Read `sudd/agents/{agent-name}.md`
   - Check if file has been modified from default (compare first 10 lines to template)
   - If modified: COLLISION detected

2. **Handle collision**:
   - In interactive mode: "Agent {name}.md has custom content ({N} lines). Merge Superpowers patterns? (y/n/diff)"
   - In autonomous mode: MERGE by appending Superpowers notes as a new section `## Superpowers Patterns (ported)` — never overwrite existing content
   - Log: "Collision: {agent}.md — merged (preserved {N} lines of existing content)"

3. **Skip if identical**: If Superpowers skill maps to the same pattern already in the agent, skip silently
```

## Component: Dry-Run and Rollback (W5)

### Responsibility
Enable preview-only mode and safe rollback.

### Design

**Dry-run (Step 1d enhancement):**
```markdown
### Dry-Run Mode

If `--dry-run` flag is present (parsed from input args):

1. Run ALL detection and decomposition logic normally
2. Instead of writing files, collect all would-be writes into a preview list
3. Display the full preview (paths, content summaries, section counts, collisions)
4. Display confidence scoring results
5. Exit with: "No files were written. Remove --dry-run to execute."

The --dry-run flag is parsed from the input: `/sudd:port --dry-run` or `/sudd:port bmad --dry-run`
```

**Git checkpoint (new Step 1f):**
```markdown
### 1f. Git Checkpoint

Before writing any ported files:

1. Check if in a git repo: `git rev-parse --git-dir 2>/dev/null`
2. If yes:
   - Stage any unstaged changes: `git add -A`
   - Commit: `git commit -m "chore(sudd:port): pre-port checkpoint" --allow-empty`
   - Log: "Git checkpoint created — revert with: git reset --hard HEAD~1"
3. If not in git repo: log warning "Not in git repo — no rollback available"
```

**Rollback (Step 9 enhancement):**
```markdown
### Rollback on Critical Failure

If post-port validation reports CRITICAL failures AND more than 30% of requirements are missing:

1. In interactive mode: "Port validation failed — {N} requirements missing. Rollback? (y/n)"
2. In autonomous mode: auto-rollback
3. Rollback: `git reset --hard HEAD~1` (to pre-port checkpoint)
4. Log: "Port rolled back — {reason}. Original files restored."
```

## Component: Iterative Review (W6)

### Responsibility
Allow user to review and correct decomposition before final write.

### Design
Add Step 8f (interactive mode only):

```markdown
### 8f. Iterative Review (interactive mode only)

If NOT autonomous mode AND decomposition produced any "probable" or "uncertain" sections:

1. Display decomposition summary:
   ```
   PRD Decomposition Review
   ════════════════════════
   Definite: 8 sections (auto-routed)
   Probable: 2 sections (review recommended)
   Uncertain: 1 section (needs your input)

   Probable:
     "Technical Stack" → design.md (keyword: "technical")
     "Timeline" → vision.md (keyword: none — closest: "goals")

   Uncertain:
     "Appendix A: Glossary" → vision.md (default)

   Accept decomposition? (y/n/edit)
   ```

2. If "edit": let user reassign sections by number
3. If "y": proceed with current routing
4. If "n": abort, user can re-run with manual overrides

In autonomous mode: skip this step entirely — use defaults.
```

## Component: Design Token Extraction (Gap A)

### Responsibility
Ensure ported projects with frontend files get design-reviewer context.

### Design
Add Step 8e:

```markdown
### 8e. Design Token Extraction

After port completes, check if ported project has frontend files:

1. Glob for: `**/*.html, **/*.css, **/*.scss, **/*.tsx, **/*.jsx, **/*.vue, **/*.svelte`
   (exclude node_modules/, dist/, build/, .worktrees/)

2. If frontend files found AND `sudd/sudd.yaml` has no `design:` section:
   - Scan CSS/SCSS files for:
     - Color declarations → extract dominant palette
     - Font-family declarations → extract typography
     - Spacing/gap patterns → identify spacing scale
   - If tokens found: add commented-out design section to sudd.yaml with discovered values
   - If no tokens found: add commented-out template with warning

3. Output:
   ```yaml
   # Design context (auto-detected from ported frontend files)
   # Review and uncomment to enable design-reviewer baseline
   # design:
   #   brand_colors:
   #     primary: "{discovered or 'oklch(60% 0.15 250)'}"
   #   typography:
   #     heading_font: "{discovered or 'system-ui'}"
   #     body_font: "{discovered or 'system-ui'}"
   #   design_system: "minimalist"
   ```

4. Log: "Frontend files detected — design config template added to sudd.yaml (commented out, review needed)"
```

### Implementation Notes
- Token extraction is best-effort — regex-based, not a CSS parser
- Always commented out — user must review and uncomment
- If sudd.yaml doesn't exist, create it with the design section only

## File Changes

### Modified Files
- `sudd/commands/macro/port.md` — All W1-W6 fixes (priority, confidence, validation, collision, dry-run, checkpoint, rollback, iterative review, design tokens)
- `sudd/sudd.yaml` — Add note about design token extraction for ported projects (documentation only)

### New Files
- None

## Migration Plan
- Step 1: Add framework priority table and dry-run mode to Step 1 (W1, W5 partial)
- Step 2: Add confidence scoring to PRD decomposition in Steps 3 and 4 (W2)
- Step 3: Add collision detection to Step 5 (W4)
- Step 4: Add post-port validation, design tokens, and iterative review to Step 8 (W3, Gap A, W6)
- Step 5: Add git checkpoint and rollback to Steps 1f and 9 (W5)
- Step 6: Cross-reference consistency check
