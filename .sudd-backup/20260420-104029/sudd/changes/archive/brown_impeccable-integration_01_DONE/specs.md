# Specifications: brown_impeccable-integration_01

## Functional Requirements

### FR-1: Design-Reviewer Agent
- Given: a change involves frontend files (*.html, *.css, *.scss, *.less, *.tsx, *.jsx, *.vue, *.svelte, *.astro)
- When: the build chain runs after coder produces output
- Then: design-reviewer agent evaluates code against 7 Impeccable domains (typography, color, spatial, motion, interaction, responsive, UX writing) and produces a score 0-100 with per-domain breakdown and specific anti-pattern violations

### FR-2: Design Anti-Pattern Detection
- Given: frontend code produced by coder
- When: design-reviewer runs
- Then: it detects these explicit anti-patterns:
  - Overused typefaces (Arial, Inter, Roboto, Open Sans as sole font)
  - Gray text on colored backgrounds
  - Pure black (#000) or pure gray without tinting
  - Nested cards (cards inside cards)
  - Dated easing (bounce, elastic effects)
  - Cyan-on-dark, purple-to-blue gradients, neon accents (AI slop markers)
  - Missing focus states for interactive elements
  - Placeholder-only form labels
  - Uniform spacing (no hierarchy)
  - Missing prefers-reduced-motion support

### FR-3: Enhanced UX-Tester
- Given: ux-tester runs on a UI task
- When: browser tools are available
- Then: ux-tester includes a "Design Quality" section checking contrast ratios, font choices, spacing hierarchy, card nesting, animation easing, and responsive behavior — alongside existing functional checks

### FR-4: Persona-Validator UI Scoring
- Given: persona-validator evaluates a consumer who uses UI output
- When: the change modifies frontend files
- Then: persona-validator includes a "Design Quality Gate" subsection scoring the 7 Impeccable domains, with any domain scoring < 80 flagged as a design deal-breaker

### FR-5: Impeccable Reference Integration
- Given: agents need design guidance
- When: design-reviewer, ux-tester, or persona-validator runs on UI tasks
- Then: condensed reference knowledge from all 7 Impeccable modules is embedded in the design-reviewer agent file (single source of truth for design quality)

### FR-6: Design Context in sudd.yaml
- Given: a project has frontend components
- When: user configures design preferences
- Then: sudd.yaml accepts optional `design` section with brand_colors, typography, design_system, and skip_design_review flag

### FR-7: /sudd:audit Command
- Given: user runs `/sudd:audit`
- When: active change has frontend files
- Then: runs design-reviewer in audit mode on all frontend files in the change, outputs scored report to log.md

### FR-8: /sudd:critique Command
- Given: user runs `/sudd:critique`
- When: active change has frontend files
- Then: runs design-reviewer in critique mode focused on UX patterns, outputs narrative-style feedback

### FR-9: Frontend Detection
- Given: any SUDD change
- When: build chain starts
- Then: auto-detect whether frontend files exist in the change's modified files list; if none, skip all design review steps silently

### FR-10: Init Flow Integration
- Given: user runs `/sudd:init` on a project with frontend files
- When: frontend files detected
- Then: prompt to configure design context in sudd.yaml

### FR-11: sudd.yaml Agent Registration
- Given: design-reviewer agent is created
- When: sudd.yaml is updated
- Then: design-reviewer is registered at sonnet tier (needs analytical depth for design judgment)

## Non-Functional Requirements

### NFR-1: No External Dependencies
- Impeccable knowledge is embedded in agent markdown, not fetched at runtime

### NFR-2: Backend-Only Changes Unaffected
- Design review adds zero overhead to changes with no frontend files

### NFR-3: Condensed Reference
- All 7 Impeccable modules condensed into actionable checklists — anti-patterns and scoring criteria only

## Consumer Handoffs

### Handoff: Coder → Design-Reviewer
- Format: source code files on disk
- Schema: design-reviewer reads files at paths listed in log.md "## Files Modified"
- Trigger: only when frontend files present

### Handoff: Design-Reviewer → Contract-Verifier
- Format: design score appended to log.md
- Schema: `## Design Review — {timestamp}\n### Score: {N}/100\n### Per-Domain\n- Typography: {N}/100\n...`
- Gate: score < 80 → feedback to coder for retry

### Handoff: Design-Reviewer → Persona-Validator
- Format: design score in log.md
- Usage: persona-validator references design score in UI consumer assessments

### Handoff: /sudd:audit → log.md
- Format: full audit report appended to log.md

## Out of Scope
- Visual regression testing (screenshot comparison)
- Figma/design tool integration
- Custom design system creation
- Backend/API design review
- Installing Impeccable as a dependency
