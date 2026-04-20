# Tasks: brown_validation-rubrics_01

## Implementation Tasks

- [x] T1: Add anchored rubrics to design-reviewer
  - Files: sudd/agents/design-reviewer.md
  - SharedFiles:
  - Effort: M
  - Dependencies:
  - Completed: 2026-03-13
  - Details: Replaced "Scoring Rubric" with 7 anchored rubrics (Broken/Weak/Acceptable/Strong/Exemplary). Added level citation to all 7 domain sections in AUDIT template. Fixed next-agent reference and duplicate text.

- [x] T2: Add objectives to default persona and update persona templates
  - Files: sudd/personas/default.md, sudd/agents/persona-detector.md, sudd/agents/persona-researcher.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Completed: 2026-03-13
  - Details: Added ## Objectives to default.md (4 goals). Added ### Objectives to persona-detector template. Added Phase 7 and ## Objectives to persona-researcher.

- [x] T3: Update ux-tester for objective-based testing
  - Files: sudd/agents/ux-tester.md
  - SharedFiles:
  - Effort: M
  - Dependencies: T2
  - Completed: 2026-03-13
  - Details: Added Objective Test Results table, scoring formula (60/40 split), cap at 85, rule 8.

- [x] T4: Update persona-validator for objective-based validation
  - Files: sudd/agents/persona-validator.md
  - SharedFiles:
  - Effort: M
  - Dependencies: T2
  - Completed: 2026-03-13
  - Details: Added Objective Walkthrough table, objective completion impact on scoring (cap 90/<100%, cap 70/<75%), discovered objectives, rule 9.

- [x] T5: Reorder apply.md steps (design review after contract verification)
  - Files: sudd/commands/micro/apply.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Completed: 2026-03-13
  - Details: Moved 3a.5 → 3b.5. Updated 3b note (→3b.5), 3c note (after 3b and 3b.5). New order: 3a→3b→3b.5→3c→3d.

- [x] T6: Add frontend worktree constraint to context-manager
  - Files: sudd/agents/context-manager.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Completed: 2026-03-13
  - Details: Added Frontend Worktree Constraint section. Added Frontend column to worktree status table. Added queued status.

- [x] T7: Update run.md step references
  - Files: sudd/commands/macro/run.md
  - SharedFiles:
  - Effort: S
  - Dependencies: T5
  - Completed: 2026-03-13
  - Details: Updated Step 5c sequential and worktree sections to 3a→3b→3b.5→3c→3d. No remaining 3a.5 references.

## Verification Tasks

- [x] T8: Cross-file consistency check
  - Files: all modified files
  - SharedFiles:
  - Effort: S
  - Dependencies: T1, T2, T3, T4, T5, T6, T7
  - Completed: 2026-03-13
  - Details: Verified: frontend extension lists (5 files), step order (3 files), rubric level names (7 tables), objective format (5 files), score caps, next-agent reference. Fixed: duplicate text in design-reviewer.md line 58, wrong next-agent (contract-verifier→peer-reviewer).

---
Total: 8 tasks | Est. effort: 3M + 4S + 1S(verify) = ~6 hours
All complete.
