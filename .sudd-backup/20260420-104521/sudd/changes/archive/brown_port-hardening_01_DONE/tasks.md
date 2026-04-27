# Tasks: brown_port-hardening_01

## Implementation Tasks

- [x] T1: Add framework priority resolution to Step 1 (W1)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Details: Add priority table (OpenSpec>BMAD>PRD>Superpowers) to Step 1a. Update Step 1e to auto-recommend highest-priority framework. In autonomous mode: auto-select. In interactive: show recommendation with override.

- [x] T2: Add dry-run mode to Step 1d (W5 partial)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: M
  - Dependencies:
  - Details: Parse --dry-run flag from input. When present: run all detection/mapping/decomposition but collect writes instead of executing them. Display full preview (paths, content summaries, section counts, collisions, confidence). Exit without writing files.

- [x] T3: Add git checkpoint and rollback (W5 partial)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Details: Add Step 1f: git checkpoint commit before writing. Add rollback logic to Step 9: if post-port validation CRITICAL and >30% missing → git reset --hard HEAD~1. Log revert with reason.

- [x] T4: Add PRD decomposition confidence scoring (W2)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: M
  - Dependencies:
  - Details: Wrap keyword table with confidence scoring (definite: 2+, probable: 1, uncertain: 0). Add Ambiguous Sections table to log.md. Multi-match prefers specs>design>personas>vision. Apply to both BMAD Step 3.1 and Generic/PRD Step 4.2.

- [x] T5: Add agent collision detection for Superpowers (W4)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Details: Before Superpowers port writes to agent files, check if they exist with non-default content. Interactive: ask. Autonomous: merge by appending as ## Superpowers Patterns section. Never silently overwrite. Log all collisions.

- [x] T6: Add post-port validation step (W3)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: M
  - Dependencies:
  - Details: Add Step 8d: count source sections, count ported sections, compare coverage, classify gaps (CRITICAL for requirements, WARNING for informational). Report in log.md. On CRITICAL+>30% missing: trigger rollback (from T3).

- [x] T7: Add iterative decomposition review (W6)
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: S
  - Dependencies: T4
  - Details: Add Step 8f: if interactive mode AND any probable/uncertain sections exist, display decomposition summary, let user accept/edit/abort. In autonomous mode: skip entirely. Uses confidence data from T4.

- [x] T8: Add design token extraction (Gap A)
  - Files: sudd/commands/macro/port.md, sudd/sudd.yaml
  - SharedFiles: sudd/sudd.yaml
  - Effort: M
  - Dependencies:
  - Details: Add Step 8e: glob for frontend files, scan CSS/SCSS for colors/fonts/spacing, add commented-out design section to sudd.yaml. Always commented — user must review. If no sudd.yaml exists, create minimal one.

- [x] T9: Update guardrails and documentation
  - Files: sudd/commands/macro/port.md
  - SharedFiles:
  - Effort: S
  - Dependencies: T1, T2, T3, T4, T5, T6, T7, T8
  - Details: Add new guardrails for priority resolution, dry-run, rollback, confidence scoring. Update OUTPUT section to show new features. Ensure all new behavior is documented in the guardrails section.

## Verification Tasks

- [x] T10: Cross-reference consistency check
  - Files: sudd/commands/macro/port.md, sudd/sudd.yaml
  - SharedFiles:
  - Effort: S
  - Dependencies: T1, T2, T3, T4, T5, T6, T7, T8, T9
  - Details: Verify: frontend extension lists match other files, step numbering is consistent, confidence scoring terminology is consistent between BMAD and PRD sections, dry-run output matches actual port output format, rollback references correct step numbers.

---
Total: 10 tasks | Est. effort: 4M + 5S + 1S(verify) = ~8 hours
