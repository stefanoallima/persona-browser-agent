# Design: brown_impeccable-integration_01

## Architecture Overview

```
                    sudd.yaml (design config)
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
design-reviewer.md    ux-tester.md         persona-validator.md
(NEW — core)          (ENHANCED)           (ENHANCED)
    │                      │                      │
    ├─ /audit mode         ├─ Design Quality      ├─ Design Quality Gate
    ├─ /critique mode      │  section added        │  for UI consumers
    └─ build chain step    └─ anti-pattern         └─ 7-domain scoring
                              checks
    ▲
    │
audit.md / critique.md (NEW commands — invoke design-reviewer)
```

## Component: design-reviewer.md (NEW)

### Responsibility
Central design quality agent. Contains condensed Impeccable reference knowledge and scoring logic for all 7 domains.

### Interface
- Input: frontend file paths from log.md "## Files Modified"
- Output: design score to log.md "## Design Review"
- Modes: audit (technical quality), critique (UX narrative)

### Implementation Notes
Single markdown file containing:
1. ACTIVATION header (standard agent protocol)
2. Frontend file detection logic
3. Condensed reference for each of 7 domains (anti-patterns, good patterns, scoring criteria)
4. Anti-pattern checklist (the 10 explicit checks from FR-2)
5. Scoring rubric (per-domain 0-100, overall weighted average)
6. Output templates for audit mode and critique mode

The 7 domains are embedded as sections within the agent file, NOT as separate reference files. This keeps the agent self-contained and avoids file proliferation.

### Tier Assignment
Sonnet — needs analytical reasoning to evaluate design quality, not just checklist verification.

## Component: ux-tester.md (MODIFIED)

### Changes
Add "## Design Quality Check" section after existing "### Accessibility Quick Check":
- Check contrast ratios (WCAG AA 4.5:1 for text, 3:1 for large text)
- Check font choices (flag overused defaults)
- Check spacing hierarchy (squint test — uniform vs varied)
- Check card nesting (nested cards = violation)
- Check animation easing (bounce/elastic = violation)
- Check responsive behavior (mobile viewport)
- Reference: "See design-reviewer.md for full anti-pattern list"

### Output Addition
Add to UX Test Report template:
```
### Design Quality
- Contrast: PASS/FAIL (ratio: X:1)
- Typography: PASS/FAIL (font: X)
- Spacing: PASS/FAIL (hierarchy: yes/no)
- Cards: PASS/FAIL (nested: yes/no)
- Motion: PASS/FAIL (easing: X)
- Responsive: PASS/FAIL
```

## Component: persona-validator.md (MODIFIED)

### Changes
Add "## Design Quality Gate (UI Changes Only)" section after Traceability Check:
- Triggered only when change includes frontend files
- Reads design-reviewer score from log.md
- If no design-reviewer score: run inline mini-assessment
- Any domain < 80: flag as design deal-breaker
- Include in scoring: design quality can cap overall score

### Output Addition
Add to Persona Validation template:
```
### Design Quality Gate
- Applies: YES/NO (frontend files in change)
- Design Score: {N}/100 (from design-reviewer)
- Domain Flags: {list any < 80}
- Design Deal-Breaker: YES/NO
```

## Component: sudd.yaml (MODIFIED)

### Changes
Add optional `design` section:
```yaml
# Design context (optional — for projects with frontend)
# design:
#   brand_colors:
#     primary: "oklch(60% 0.15 250)"
#     neutral_tint: "warm"  # warm | cool | none
#   typography:
#     heading_font: "Plus Jakarta Sans"
#     body_font: "system-ui"
#   design_system: "minimalist"  # minimalist | brutalist | maximalist | retro-futuristic
#   skip_design_review: false
```

Add design-reviewer to agents section:
```yaml
design-reviewer: { tier: sonnet }  # needs analytical depth for design judgment
```

## Component: audit.md (NEW command)

### Location
`sudd/commands/micro/audit.md`

### Behavior
1. Read state.json for active change
2. Read log.md for "## Files Modified"
3. Filter for frontend files
4. If none: "No frontend files in this change. Nothing to audit."
5. If found: invoke design-reviewer in audit mode
6. Append results to log.md

## Component: critique.md (NEW command)

### Location
`sudd/commands/micro/critique.md`

### Behavior
Same as audit.md but invokes design-reviewer in critique mode (narrative UX feedback instead of scored checklist).

## Component: init.md (MODIFIED)

### Changes
Add Step 6.5: "Design Context Setup" after example change creation:
- Scan for frontend files in project
- If found: ask about design preferences
- Write design section to sudd.yaml (commented-out template if user declines)

## Component: apply.md (MODIFIED)

### Changes
Add design-reviewer step in build chain:
- After "3a. Task(agent=coder)" and before "3b. Handoff Validation"
- Add "3a.5: If frontend files modified → Task(agent=design-reviewer)"
- If design score < 80: feedback to coder, re-implement

## Component: run.md (MODIFIED)

### Changes
Add design-reviewer to Build Loop:
- After coder, before contract-verifier
- Same conditional: only if frontend files in modified list

## File Changes Summary

### New Files
- `sudd/agents/design-reviewer.md` — core design quality agent with embedded Impeccable reference
- `sudd/commands/micro/audit.md` — /sudd:audit command
- `sudd/commands/micro/critique.md` — /sudd:critique command

### Modified Files
- `sudd/agents/ux-tester.md` — add Design Quality Check section
- `sudd/agents/persona-validator.md` — add Design Quality Gate section
- `sudd/sudd.yaml` — add design section + design-reviewer agent
- `sudd/commands/micro/init.md` — add design context setup step
- `sudd/commands/micro/apply.md` — add design-reviewer in build chain
- `sudd/commands/macro/run.md` — add design-reviewer in build loop
