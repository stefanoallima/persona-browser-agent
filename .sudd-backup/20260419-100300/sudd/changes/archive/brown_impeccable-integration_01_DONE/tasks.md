# Tasks: brown_impeccable-integration_01

## Phase 1: Core Agent (foundation — everything depends on this)

- [x] **T01** — Create design-reviewer.md agent [L]
  - New file: `sudd/agents/design-reviewer.md`
  - ACTIVATION header (standard protocol)
  - PREREQUISITES: phase build or validate, frontend files in change
  - Frontend file detection logic (extensions list)
  - Condensed Impeccable reference for all 7 domains:
    - Typography: modular scale, font selection anti-patterns, readability
    - Color & Contrast: OKLCH, tinted neutrals, WCAG ratios, dangerous combos
    - Spatial Design: 4pt system, hierarchy, squint test, card nesting
    - Motion Design: 100/300/500 timing, easing (no bounce/elastic), prefers-reduced-motion
    - Interaction Design: 8 states, focus rings, form labels, undo > confirm
    - Responsive Design: mobile-first, container queries, input method detection
    - UX Writing: specific labels, error structure, empty states, consistency
  - Anti-pattern checklist (10 items from FR-2)
  - Scoring rubric: per-domain 0-100, weighted average for overall
  - Two output modes: audit (scored checklist) and critique (narrative UX feedback)
  - Files: `sudd/agents/design-reviewer.md` (NEW)

## Phase 2: Agent Enhancements (parallel — independent of each other)

- [x] **T02** — Add Design Quality Check to ux-tester.md [S]
  - Add "## Design Quality Check" section after Accessibility Quick Check
  - 6 checks: contrast, fonts, spacing, cards, motion, responsive
  - Add to UX Test Report template
  - Reference design-reviewer.md for full anti-pattern list
  - Files: `sudd/agents/ux-tester.md`

- [x] **T03** — Add Design Quality Gate to persona-validator.md [S]
  - Add "## Design Quality Gate (UI Changes Only)" after Traceability Check
  - Triggered only for changes with frontend files
  - Reads design-reviewer score from log.md
  - Domain < 80 = design deal-breaker
  - Add to Persona Validation template
  - Files: `sudd/agents/persona-validator.md`

## Phase 3: Configuration & Commands (parallel)

- [x] **T04** — Update sudd.yaml with design config + agent registration [S]
  - Add commented-out `design:` section (brand_colors, typography, design_system, skip_design_review)
  - Add `design-reviewer: { tier: sonnet }` to agents
  - Update agent count comments (20 → 21)
  - Files: `sudd/sudd.yaml`

- [x] **T05** — Create /sudd:audit command [S]
  - New file: `sudd/commands/micro/audit.md`
  - Read state.json, read log.md for Files Modified
  - Filter for frontend file extensions
  - If none: "No frontend files. Nothing to audit."
  - If found: invoke design-reviewer in audit mode
  - Append results to log.md
  - Files: `sudd/commands/micro/audit.md` (NEW)

- [x] **T06** — Create /sudd:critique command [S]
  - New file: `sudd/commands/micro/critique.md`
  - Same structure as audit.md but invokes critique mode
  - Narrative UX feedback instead of scored checklist
  - Files: `sudd/commands/micro/critique.md` (NEW)

## Phase 4: Workflow Wiring (depends on T01, T04)

- [x] **T07** — Wire design-reviewer into apply.md build chain [S]
  - Add step 3a.5 after coder, before handoff validation
  - Conditional: only if frontend files in "## Files Modified"
  - If design score < 80: feedback to coder for re-implementation
  - Read sudd.yaml design.skip_design_review to allow opt-out
  - Files: `sudd/commands/micro/apply.md`

- [x] **T08** — Wire design-reviewer into run.md build loop [S]
  - Add design-reviewer step in Build Loop after coder
  - Same conditional as apply.md
  - Files: `sudd/commands/macro/run.md`

- [x] **T09** — Add design context setup to init.md [S]
  - Add Step 6.5 after example change creation
  - Scan for frontend files in project root
  - If found: offer to configure design context
  - Write design section to sudd.yaml (commented template if user declines)
  - Files: `sudd/commands/micro/init.md`

## Phase 5: Verification

- [x] **T10** — Verify all wiring [S]
  - Check: design-reviewer.md exists with all 7 domains + anti-patterns + scoring
  - Check: ux-tester.md has Design Quality Check section
  - Check: persona-validator.md has Design Quality Gate section
  - Check: sudd.yaml has design-reviewer agent + design config template
  - Check: audit.md and critique.md exist and invoke design-reviewer
  - Check: apply.md has design-reviewer step in build chain
  - Check: run.md has design-reviewer step in build loop
  - Check: init.md has design context setup step
  - Check: frontend detection logic consistent across all files
  - Files: all modified files (read-only verification)

---

## Summary

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| 1: Core Agent | T01 | 1L | Critical — everything depends on this |
| 2: Agent Enhancements | T02-T03 | 2S | High — parallel |
| 3: Config & Commands | T04-T06 | 3S | High — parallel |
| 4: Workflow Wiring | T07-T09 | 3S | High — depends on T01, T04 |
| 5: Verification | T10 | 1S | High — final check |
| **Total** | **10 tasks** | **1L + 9S** | |

## Dependencies

```
T01: independent (must be first — all others reference it)
T02-T03: independent of each other, reference T01
T04-T06: independent of each other, T04 references T01
T07-T08: depend on T01 and T04 (read sudd.yaml, invoke design-reviewer)
T09: depends on T04 (writes to sudd.yaml)
T10: depends on ALL previous tasks
```
