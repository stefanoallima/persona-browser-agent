# Design: brown_validation-rubrics_01

## Architecture Overview

```
                      ┌─────────────────────────────┐
                      │   sudd/personas/*.md         │
                      │   + ## Objectives section    │
                      └──────────┬──────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
  ┌───────────────────┐ ┌──────────────────┐ ┌──────────────────┐
  │  ux-tester.md     │ │ persona-validator│ │ persona-detector │
  │  + Objective Test │ │ + Objective Walk │ │ (generates objs  │
  │    Results table  │ │   through table  │ │  for new personas│
  └───────────────────┘ └──────────────────┘ └──────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │               design-reviewer.md                            │
  │  + 5-level anchored rubrics per domain                      │
  │  + Level citation in output                                 │
  │  (moved to step 3b.5, after contract-verifier)              │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │               apply.md step reorder                         │
  │  3a (code) → 3b (contract) → 3b.5 (design) → 3c (quality) │
  │                                                             │
  │               context-manager.md                            │
  │  + frontend worktree constraint (max 1 active)              │
  │  + worktree status table gains "frontend" column            │
  └─────────────────────────────────────────────────────────────┘
```

## Component: Anchored Rubrics (design-reviewer.md)

### Responsibility
Replace subjective 0-100 scores with 5-level anchored scales per domain. Each level has concrete descriptors so the reviewer matches evidence to level, not invents a number.

### Dependencies
- Existing design-reviewer.md (from brown_impeccable-integration_01)
- sudd.yaml design section (optional context)

### Interface
Each domain section becomes:

```markdown
#### {Domain}: {N}/100 — Level {1-5}: {level_name}

**Rubric applied:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | {3 descriptors} |
| 2 | 21-40 | Weak | {3 descriptors} |
| 3 | 41-60 | Acceptable | {3 descriptors} |
| 4 | 61-80 | Strong | {3 descriptors} |
| 5 | 81-100 | Exemplary | {3 descriptors} |

**Matched level: {N}**
Evidence:
- {checklist_item}: {PASS/FAIL} — `{file}:{line}`
Level justification: {which descriptors matched}
```

### Implementation Notes

The 7 rubrics (one per domain) using Perplexity-style structured evaluation:

**Typography Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | No type scale; arbitrary font sizes; browser-default fonts only; no line-height control |
| 2 | 21-40 | Weak | Inconsistent type scale; generic overused font (Arial/Inter/Roboto as sole); line-height present but not rhythmic |
| 3 | 41-60 | Acceptable | Consistent type scale but not fluid; adequate font choice; line-height follows base unit; line length not constrained |
| 4 | 61-80 | Strong | Fluid type scale (clamp); distinctive font or well-used system stack; vertical rhythm; line length ~65ch; font loading optimized |
| 5 | 81-100 | Exemplary | Modular fluid scale; distinctive typography; perfect vertical rhythm; responsive sizing; weight variation for hierarchy; optimized loading |

**Color & Contrast Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | WCAG AA failures; pure black/untinted gray; no color system; dangerous combos (red/green) |
| 2 | 21-40 | Weak | WCAG AA mostly met; raw hex/HSL palette; pure grays; color as sole info carrier somewhere |
| 3 | 41-60 | Acceptable | WCAG AA met; organized palette but not OKLCH; slight gray tinting; 60-30-10 roughly followed |
| 4 | 61-80 | Strong | WCAG AA met; OKLCH or equivalent modern space; tinted neutrals; proper dark mode (not inverted); 60-30-10 rule |
| 5 | 81-100 | Exemplary | WCAG AAA where feasible; OKLCH throughout; nuanced tinted neutrals; dark mode with lighter surfaces for depth; desaturated accents; no alpha overuse |

**Spatial Design Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | No spacing system; nested cards; touch targets < 44px; no hierarchy visible |
| 2 | 21-40 | Weak | Some spacing consistency; margins instead of gap; uniform padding; cards overused |
| 3 | 41-60 | Acceptable | Consistent spacing scale; gap used sometimes; some hierarchy; no nesting; adequate touch targets |
| 4 | 61-80 | Strong | 4pt or 8pt grid; gap for siblings; clear hierarchy via space; semantic spacing tokens; 44px touch targets |
| 5 | 81-100 | Exemplary | Semantic spacing tokens; gap everywhere appropriate; multi-dimensional hierarchy (size+weight+color+space); container queries; subtle shadows; squint test passes |

**Motion Design Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | Layout-triggering animations (width/height/top); no prefers-reduced-motion; bounce/elastic easing |
| 2 | 21-40 | Weak | Some transform/opacity use; inconsistent durations; missing prefers-reduced-motion |
| 3 | 41-60 | Acceptable | Transform/opacity only; reasonable durations; prefers-reduced-motion present but incomplete |
| 4 | 61-80 | Strong | 100/300/500 rule followed; proper easing (ease-out enter, ease-in exit); exit 75% of entrance; prefers-reduced-motion complete |
| 5 | 81-100 | Exemplary | Perfect duration hierarchy; staggered reveals; grid-template-rows for height; all motion functional not decorative; reduced-motion provides crossfade alternatives |

**Interaction Design Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | No focus states; outline:none without replacement; placeholder-only labels; no error handling |
| 2 | 21-40 | Weak | Some focus states but inconsistent; :focus instead of :focus-visible; basic validation; no loading states |
| 3 | 41-60 | Acceptable | :focus-visible on most elements; visible labels; validation on submit; error messages present; loading indicated |
| 4 | 61-80 | Strong | :focus-visible everywhere; consistent focus rings (2-3px, high contrast); validate on blur; errors with aria-describedby; disabled/loading/success states |
| 5 | 81-100 | Exemplary | All 8 states handled; roving tabindex for groups; undo over confirm dialogs; error messages with what/why/fix; elegant state transitions |

**Responsive Design Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | No responsive design; fixed widths; hover-dependent functionality; no mobile consideration |
| 2 | 21-40 | Weak | Desktop-first (max-width queries); device-specific breakpoints; hover used for key features |
| 3 | 41-60 | Acceptable | Mobile-first (min-width); content-driven breakpoints; hover not required for function; adequate on common screens |
| 4 | 61-80 | Strong | Mobile-first; content breakpoints; pointer/hover media queries; safe area handling; srcset for images |
| 5 | 81-100 | Exemplary | Fully fluid; container queries for components; media queries for layout; @media(pointer:coarse) for touch; safe areas; tested on real devices |

**UX Writing Rubric:**
| Level | Range | Name | Descriptors |
|-------|-------|------|-------------|
| 1 | 0-20 | Broken | "OK"/"Submit"/"Click here" buttons; no error messages; lorem ipsum or placeholder text |
| 2 | 21-40 | Weak | Generic button labels; error messages exist but no fix guidance; inconsistent terminology (delete/remove) |
| 3 | 41-60 | Acceptable | Specific button labels mostly; error messages with what happened; consistent terminology; empty states exist |
| 4 | 61-80 | Strong | Action-specific buttons; error messages with what/why/fix; meaningful link text; empty states with direction; consistent voice |
| 5 | 81-100 | Exemplary | Precise action labels; three-part error messages; empty states with value+direction; i18n-aware (text expansion); single terminology throughout; tone adapts to context |

## Component: Persona Objectives (personas/*.md)

### Responsibility
Add structured, testable objectives to each persona definition.

### Dependencies
- Existing persona template (default.md)
- persona-detector and persona-researcher agents (generate new personas)

### Interface
New `## Objectives` section added to persona files:

```markdown
## Objectives
1. {Action verb} {specific task} — {measurable outcome}
   - Steps: {what the user would do}
   - Success: {how to verify completion}
2. {Action verb} {specific task} — {measurable outcome}
   - Steps: {what the user would do}
   - Success: {how to verify completion}
```

### Implementation Notes
- persona-detector.md updated to include objectives generation in its template
- persona-researcher.md updated to refine objectives during deep research
- default.md updated with example objectives for Stefano persona
- Objectives are written in action-verb format: "Retrieve", "Filter", "Export", "Configure", "Navigate"
- Each objective must be independently testable — no chained dependencies between objectives

## Component: Objective-Based Testing (ux-tester.md)

### Responsibility
Generate test scripts from persona objectives, execute each objective as a scenario.

### Dependencies
- Updated personas/*.md with ## Objectives
- Existing ux-tester process and browser tools

### Interface
New "Objective Test Results" section in output template.

### Implementation Notes
- After loading persona, extract ## Objectives
- For each objective: convert Steps into Playwright actions, execute, capture evidence
- Score per-objective (PASS/FAIL), then compute completion rate
- Overall score weighted: 60% objective completion + 40% existing checks (accessibility, design, errors)
- If any objective FAIL → cap score at 85 regardless of other checks

## Component: Objective-Based Validation (persona-validator.md)

### Responsibility
Walk through each persona objective in first-person, report per-objective pass/fail.

### Dependencies
- Updated personas/*.md with ## Objectives
- Existing persona-validator process

### Interface
New "Objective Walkthrough" section in output template.

### Implementation Notes
- After adopting persona identity, read ## Objectives
- For each objective: mentally walk through the output/code and narrate in first person
- Report per-objective with evidence (file:line or output snippet)
- Objectives completion rate factors into score: < 100% objectives → score capped at 90
- Discovered objectives: validator can identify ADDITIONAL objectives during walkthrough, append them

## Component: Step Reorder (apply.md)

### Responsibility
Move design review after contract verification to prevent spec-breaking design fixes.

### Design
Current order: 3a → 3a.5 → 3b → 3c → 3d
New order: 3a → 3b → 3b.5 → 3c → 3d

- Renumber 3a.5 to 3b.5
- 3b (contract-verifier) runs first — ensures code matches spec
- 3b.5 (design-reviewer) runs second — design review on spec-compliant code
- 3c (peer-reviewer) runs third — code quality on compliant, well-designed code
- 3d (handoff-validator) runs last

### Implementation Notes
- Also update run.md Step 5c to reflect new step order
- Comment references in context-manager.md and coder.md unchanged (they don't reference step numbers)

## Component: Frontend Worktree Constraint (context-manager.md)

### Responsibility
Enforce max 1 frontend-touching worktree at any time.

### Design
Before creating a worktree for a task, check if the task's `Files:` contain any frontend extensions (*.html, *.css, *.scss, *.less, *.tsx, *.jsx, *.vue, *.svelte, *.astro). If yes, check the worktree status table — if any other frontend worktree has status `active`, queue this task for sequential execution after that worktree merges.

### Implementation Notes
- Add `Frontend` column to worktree status table: `yes/no`
- Add check before worktree creation: "If task touches frontend files AND another frontend worktree is active → queue for sequential"
- This prevents Gap B (design consistency across worktrees)
- Sequential mode (default) is unaffected — this only applies when `parallelization.mode: worktree`

## Data Flow

```
personas/*.md (with ## Objectives)
       │
       ├──→ ux-tester.md
       │    Read objectives → generate test scripts → execute per-objective
       │    Output: Objective Test Results table
       │
       └──→ persona-validator.md
            Read objectives → walk through each → narrate in first person
            Output: Objective Walkthrough table + completion rate

design-reviewer.md (with anchored rubrics)
       │
       └──→ Per-domain: match evidence to rubric level → cite level name + descriptors
            Output: Level-anchored scores with justification

apply.md step chain:
  3a (coder) → 3b (contract-verifier) → 3b.5 (design-reviewer) → 3c (peer-reviewer) → 3d (handoff)

context-manager.md worktree dispatch:
  Check Files: for frontend extensions → if frontend AND active frontend worktree → queue
```

## File Changes

### Modified Files
- `sudd/agents/design-reviewer.md` — Replace "Scoring Rubric" section with 7 anchored rubrics; update AUDIT output template to include level citation
- `sudd/agents/persona-validator.md` — Add "Objective Walkthrough" section to output template; add objective completion rate to scoring
- `sudd/agents/ux-tester.md` — Add "Objective Test Results" section; change test generation from spec-based to objective-based
- `sudd/agents/persona-detector.md` — Update persona template to include ## Objectives section
- `sudd/agents/persona-researcher.md` — Update to refine objectives during deep research
- `sudd/personas/default.md` — Add ## Objectives with concrete task-based goals
- `sudd/commands/micro/apply.md` — Reorder steps: 3a.5 → 3b.5 (after contract-verifier)
- `sudd/commands/macro/run.md` — Update Step 5c step references to match new order
- `sudd/agents/context-manager.md` — Add frontend worktree constraint; add Frontend column to status table

### New Files
- None

## Configuration
- No new config needed
- No new env vars
- Existing sudd.yaml `design:` section remains optional (rubrics work without it)

## Migration Plan
- Step 1: Add rubrics to design-reviewer.md (self-contained, no dependencies)
- Step 2: Add objectives to personas (default.md first, then update persona-detector/researcher templates)
- Step 3: Update ux-tester and persona-validator to consume objectives
- Step 4: Reorder apply.md steps
- Step 5: Add frontend worktree constraint to context-manager.md
- Step 6: Update run.md references
