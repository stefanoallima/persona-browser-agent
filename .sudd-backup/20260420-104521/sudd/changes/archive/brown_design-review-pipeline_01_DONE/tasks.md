# Tasks: brown_design-review-pipeline_01

## Implementation Tasks

- [x] T1: Add design context enforcement to design-reviewer (W9)
  - Files: sudd/agents/design-reviewer.md
  - SharedFiles:
  - Effort: M
  - Dependencies:
  - Details: Expand "## Design Context" section: add auto-detection fallback (scan CSS for colors/fonts/spacing), add NO_DESIGN_CONTEXT flag, cap all domain scores at Level 3 (60 max) when no context. Add warning output block.

- [x] T2: Add visual verification flags to design-reviewer (W7)
  - Files: sudd/agents/design-reviewer.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Details: After Anti-Pattern Summary, add "### Visual Verification Needed" section. Auto-flag: z-index >10, overflow:hidden on dynamic, CSS animations, responsive breakpoints, position:fixed/sticky, dark mode. Output table with item/type/check/file/priority.

- [x] T3: Add design verification step to ux-tester (W7)
  - Files: sudd/agents/ux-tester.md
  - SharedFiles:
  - Effort: S
  - Dependencies: T2
  - Details: Add step 2.5 between Navigate and Judge. Read log.md for Visual Verification Needed. For each item: navigate, check, screenshot, record PASS/FAIL. Output "### Design Verification Results" table. HIGH priority FAIL → CRITICAL issue.

- [x] T4: Update persona-validator independent design assessment (W11)
  - Files: sudd/agents/persona-validator.md
  - SharedFiles:
  - Effort: M
  - Dependencies: T1, T3
  - Details: Replace current Design Quality Gate with 5-step process: check for review, independent assessment (persona expectation + design system + obvious issues), check verification results, compare and resolve (disagreement >15 → flag, use lower score), include in output with full Design Quality Gate template.

- [x] T5: Create smoke test checklist (Gap C)
  - Files: sudd/memory/smoke-test.md
  - SharedFiles:
  - Effort: S
  - Dependencies:
  - Details: Create smoke-test.md with 5-phase checklist (port, plan, apply, visual verification, gate, done). Include minimal PRD fixture and expected results. Cover dry-run, design context enforcement, visual verification, independent assessment, disagreement handling.

- [x] T6: Cross-reference consistency check
  - Files: sudd/agents/design-reviewer.md, sudd/agents/ux-tester.md, sudd/agents/persona-validator.md, sudd/memory/smoke-test.md
  - SharedFiles:
  - Effort: S
  - Dependencies: T1, T2, T3, T4, T5
  - Details: Verify: Visual Verification Needed table format matches between design-reviewer output and ux-tester input. Design Verification Results format matches between ux-tester output and persona-validator input. NO_DESIGN_CONTEXT flag name consistent. Score cap values consistent. Frontend file extension lists match. Smoke test checklist references correct step numbers.

---
Total: 6 tasks | Est. effort: 2M + 4S = ~5 hours
