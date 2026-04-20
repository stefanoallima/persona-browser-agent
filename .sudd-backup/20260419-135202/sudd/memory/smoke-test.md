# SUDD Smoke Test Checklist

## Purpose
Validates the full SUDD chain works end-to-end. Run this after major framework changes to catch integration issues.

## Prerequisites
- A sample project with a PRD, BMAD, or OpenSpec structure
- Or use the minimal PRD fixture below

## Phase 1: Port

- [ ] Run `/sudd:port --dry-run` on the sample project
  - [ ] Dry-run output shows framework detection with priority ranking
  - [ ] Confidence scoring results displayed (definite/probable/uncertain counts)
  - [ ] No files were written to disk
  - [ ] No git checkpoint commit created
- [ ] Run `/sudd:port` (without --dry-run)
  - [ ] Git checkpoint commit created: `chore(sudd:port): pre-port checkpoint`
  - [ ] `sudd/vision.md` created with `<!-- ported from: ... -->` source tag
  - [ ] `sudd/personas/` has at least one persona file
  - [ ] `sudd/changes/active/{id}/` created with proposal.md
  - [ ] `state.json` has `imported_from` set, `mode: "brown"`, `phase: "build"`
  - [ ] `log.md` has port summary with section counts
  - [ ] If PRD had ambiguous sections: `## Ambiguous Sections` in log.md
  - [ ] Post-port validation in log.md shows coverage percentage

## Phase 2: Plan

- [ ] Run `/sudd:plan` on the ported change
  - [ ] `specs.md` has functional requirements with Given/When/Then format
  - [ ] `design.md` has architecture overview and component designs
  - [ ] `tasks.md` has implementation tasks with dependencies and effort estimates
  - [ ] `state.json` updated: `phase: "build"`, `last_command: "sudd:plan"`

## Phase 3: Apply

- [ ] Run `/sudd:apply` on the first task
  - [ ] Coder agent produces code files
  - [ ] Contract-verifier runs (Step 3b) — level EXEMPLARY
  - [ ] Peer-reviewer runs (Step 3c)
  - [ ] Handoff-validator runs (Step 3d)
  - [ ] Task marked `[x]` in tasks.md
  - [ ] Git commit created for the task

## Phase 4: Gate

- [ ] Run `/sudd:gate`
  - [ ] Persona-validator impersonates each consumer persona
  - [ ] Objective walkthrough table completed for each persona
  - [ ] All consumers at EXEMPLARY level for PASS, below EXEMPLARY for FAIL with specific feedback
  - [ ] If PASS: `state.json` updated: `gate_passed: true`, `phase: "complete"`

## Phase 5: Done

- [ ] Run `/sudd:done`
  - [ ] Change archived to `sudd/changes/archive/{id}_DONE/`
  - [ ] `SUMMARY.md` created with consumer scores and lessons
  - [ ] `sudd/memory/lessons.md` updated with new lessons
  - [ ] `state.json`: `active_change: null`, `phase: "inception"`

## Smoke Test Fixture: Minimal PRD

Create `test-prd.md` in a temporary project directory:

```markdown
# Test Product

## Purpose and Vision
A simple task tracker for validating the SUDD pipeline end-to-end.

## Target Users
### Developer
Role: Software developer testing the SUDD framework
Goals: Verify all pipeline stages work correctly
Deal-breakers: Silent data loss, broken validation chain

## Functional Requirements
- The app must accept task input via a form
- Tasks must be displayed in a list with status
- Users must be able to mark tasks as complete

## Technical Architecture
- Frontend: HTML + CSS + vanilla JavaScript
- Backend: None (client-side only)
- Storage: localStorage

## Timeline
Q1 2026 delivery target
```

### Expected Port Results
- Framework detected: Generic/PRD (definite)
- vision.md: Purpose and Vision section + Timeline (uncertain, routed to vision.md)
- personas/developer.md: 1 persona extracted
- specs.md: 3 functional requirements
- design.md: Technical Architecture section
- Confidence: ~3 definite, ~1 uncertain (Timeline)
