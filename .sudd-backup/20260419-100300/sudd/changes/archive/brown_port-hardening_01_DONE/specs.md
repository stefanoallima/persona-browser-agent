# Specifications: brown_port-hardening_01

## Functional Requirements

### FR-1: Framework Priority Resolution (W1)
- Given: auto-detection finds 2+ frameworks in the same project
- When: determining which framework to port from
- Then: apply a priority order (OpenSpec > BMAD > Generic/PRD > Superpowers) and display the resolution to the user before proceeding, with option to override

### FR-2: PRD Decomposition Confidence Scoring (W2)
- Given: a PRD section header is matched against the keyword table
- When: the header matches keywords from multiple targets OR matches no keywords
- Then: assign a confidence score (definite: 2+ keyword matches, probable: 1 keyword match, uncertain: 0 matches) and route uncertain sections to a holding area for user review rather than silently appending to vision.md

### FR-3: Ambiguous Section Handling (W2)
- Given: a PRD section has "uncertain" confidence (no keyword match) or matches multiple targets equally
- When: in autonomous mode
- Then: route to vision.md with a warning AND create an `## Ambiguous Sections` list in log.md with the section name, content preview, and suggested target for user review

### FR-4: Post-Port Validation (W3)
- Given: port has completed writing all artifacts
- When: validation step runs
- Then: compare source document section count against ported artifact section count, flag any source sections that have no corresponding ported content, and list missing sections in log.md with severity (CRITICAL: requirements dropped, WARNING: informational content dropped)

### FR-5: Source Requirement Counting (W3)
- Given: a source PRD/spec document with N requirement-like sections
- When: post-port validation runs
- Then: count sections in source matching requirement keywords, count corresponding sections in ported specs.md, report coverage percentage and list any gaps

### FR-6: Agent Collision Detection (W4)
- Given: Superpowers port would write to a SUDD agent file (e.g., sudd/agents/coder.md)
- When: that agent file already exists with non-default content
- Then: detect the collision, show a diff summary, and either (a) merge by appending Superpowers patterns as a new section, or (b) skip and log the collision — NEVER silently overwrite

### FR-7: Dry-Run Mode (W5)
- Given: user runs `/sudd:port --dry-run` or `/sudd:port {framework} --dry-run`
- When: the port executes
- Then: perform all detection, mapping, and decomposition logic but write ZERO files to disk — instead, output the full preview of what WOULD be created (file paths, content summaries, section counts) and exit

### FR-8: Git Checkpoint Before Port (W5)
- Given: the project is a git repository and port is about to write files
- When: port starts writing (after detection and preview)
- Then: create a git checkpoint commit with message `chore(sudd:port): pre-port checkpoint` so the user can `git revert` or `git reset` if the port produces bad results

### FR-9: Rollback on Failure (W5)
- Given: port encounters a critical error during writing (e.g., validation fails, empty output)
- When: the error is detected
- Then: `git reset --hard HEAD` to restore the pre-port checkpoint state, log the error, and report what went wrong

### FR-10: Iterative Decomposition Review (W6)
- Given: PRD decomposition has completed
- When: in interactive mode (not autonomous)
- Then: display the decomposition summary (which sections → which targets, confidence scores) and ask for user confirmation/correction before writing files

### FR-11: Design Token Extraction (Gap A)
- Given: a ported project contains frontend files (*.html, *.css, *.tsx, etc.)
- When: port finalizes
- Then: scan source files for design tokens (brand colors, font declarations, spacing scales) and either (a) populate a minimal `sudd.yaml` design section with discovered tokens, or (b) add a commented-out template with a warning: "Frontend files detected but no design config — configure before running design-reviewer"

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Constraint: All existing port.md behavior must continue working — new features are additive
- Rationale: Projects already using `/sudd:port` should not break

### NFR-2: Single File Scope
- Constraint: All changes are within port.md except Gap A (sudd.yaml template update)
- Rationale: Minimizes cross-file consistency risk

### NFR-3: Autonomous Mode Compatibility
- Constraint: All new features must have sensible defaults for autonomous mode (no blocking prompts)
- Rationale: `/sudd:run` calls `/sudd:port` autonomously

## API Contracts

### Interface: Dry-Run Output
- Input: `/sudd:port --dry-run` or `/sudd:port {framework} --dry-run`
- Output:
  ```
  DRY RUN — No files will be written
  ═══════════════════════════════════

  Framework: {detected}

  Would create:
    sudd/vision.md          ← {source} ({N} sections)
    sudd/personas/          ← {source} ({N} personas)
    sudd/changes/active/    ← {source} ({N} changes, {M} tasks)
    sudd/specs/             ← {source} ({N} spec domains)
    sudd/memory/lessons.md  ← {source} ({N} conventions)

  Decomposition Confidence:
    Definite: {N} sections
    Probable: {N} sections
    Uncertain: {N} sections (would go to vision.md with warnings)

  Collisions:
    {file}: exists with {N} lines of custom content — would {merge|skip}

  No files were written. Remove --dry-run to execute.
  ```

### Interface: Post-Port Validation Report
- Output appended to log.md:
  ```markdown
  ## Post-Port Validation
  - Source sections: {N}
  - Ported sections: {M}
  - Coverage: {percentage}%
  - Dropped: {list of section names not found in ported output}
  - Severity: {CRITICAL if requirements dropped, WARNING if informational}
  ```

### Interface: Framework Priority Resolution
- Output in detection display:
  ```
  Framework Detection
  ═══════════════════
    ✓ OpenSpec  (definite) — openspec/project.md  [PRIORITY: 1]
    ✓ BMAD      (definite) — .bmad-core/          [PRIORITY: 2]

  Resolution: Port OpenSpec (highest priority). BMAD artifacts available for merge.
  Override: /sudd:port merge (combine all), /sudd:port bmad (use BMAD only)
  ```

## Consumer Handoffs

### Handoff 1: port.md → orchestrator (state.json)
- Format: valid JSON
- Schema: all 15 state.json fields populated
- Validation: `imported_from` set, `active_change` points to existing directory

### Handoff 2: port.md → plan/apply (ported artifacts)
- Format: markdown files in sudd/ structure
- Schema: vision.md non-empty, specs.md has sections, personas exist
- Validation: post-port validation step confirms no silent data loss

### Handoff 3: port.md → design-reviewer (sudd.yaml design section)
- Format: YAML design config (commented or active)
- Schema: brand_colors, typography, design_system fields
- Validation: if frontend files exist, design section is present (even if commented)

## Out of Scope
- New framework support (only hardening existing 4)
- Visual regression testing of ported frontends
- Automated rubric calibration of ported design tokens
- Rewriting port.md step numbering (keep existing structure)
