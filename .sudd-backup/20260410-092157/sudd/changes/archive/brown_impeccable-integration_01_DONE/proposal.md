# Change: brown_impeccable-integration_01

## Status
proposed

## Summary
Integrate Impeccable (github.com/pbakaus/impeccable) design skills into the SUDD workflow to give AI agents structured UI/UX quality guidance — covering typography, color theory, spatial design, motion, interaction patterns, responsive design, and UX writing.

## Motivation
SUDD's `ux-tester` agent currently does browser-level testing (navigate, click, check errors) but has no design quality scoring. When AI agents generate frontend code, they produce generic, template-looking UIs with common anti-patterns: overused fonts, gray-on-color text, pure blacks, nested cards, dated animations. Impeccable provides 17 steering commands and 7 reference modules that combat exactly these problems. Integrating it into SUDD means every frontend task automatically gets design quality checks at build, validation, and gate phases.

## Scope

### What's included:

### 1. Design-Reviewer Agent
- New `sudd/agents/design-reviewer.md` agent that wraps Impeccable's reference modules
- Activation: triggered when change involves frontend/UI files (*.html, *.css, *.tsx, *.vue, *.svelte, etc.)
- Runs Impeccable's `/audit` (technical quality) + `/critique` (UX review) as build-chain steps
- Produces a design score (0-100) with specific issues tagged by severity
- Sits in the Build chain between `coder` and `contract-verifier`

### 2. Enhanced ux-tester Agent
- Wire Impeccable's `/polish` and `/normalize` checks into existing `ux-tester.md`
- Add visual quality assessment alongside existing functional testing
- Check for Impeccable anti-patterns: overused fonts, poor contrast, pure blacks, nested cards, dated easing

### 3. Persona-Validator UI Scoring
- When persona-validator evaluates a UI consumer persona, invoke Impeccable's reference modules
- Score design quality as part of the persona gate (typography, color, spatial, motion, interaction, responsive, UX writing)
- Fail gate if design score < 95 for UI-facing changes

### 4. Impeccable Reference Modules in Templates
- Bundle Impeccable's 7 reference modules into `sudd/agents/references/` or `sudd/agents/design/`
- Include: typography, color theory, spatial design, motion, interaction patterns, responsive, UX writing
- Make available to all agents via standard file read

### 5. Init Flow Integration
- During `sudd init`, if project has frontend files, offer to configure Impeccable design context
- Store design preferences in `sudd/sudd.yaml` (brand colors, typography choices, design system)
- Equivalent of Impeccable's `/teach-impeccable` one-time setup

### 6. SUDD Commands
- Add `/sudd:audit` micro command — runs Impeccable audit on current change's frontend files
- Add `/sudd:critique` micro command — runs Impeccable UX critique on current change

### What's NOT included:
- Installing Impeccable itself (SUDD embeds the relevant knowledge, not the tool)
- Backend/API design review (this is purely UI/UX)
- Modifying Impeccable's source — we consume its reference modules as-is
- Browser automation for visual regression testing (that's a separate concern)

## Success Criteria
- [ ] `design-reviewer` agent produces actionable design scores for frontend changes
- [ ] `ux-tester` catches Impeccable anti-patterns (poor contrast, overused fonts, nested cards)
- [ ] `persona-validator` includes design quality in UI consumer persona scoring
- [ ] Impeccable reference modules are accessible to all agents
- [ ] `/sudd:audit` and `/sudd:critique` commands work as standalone checks
- [ ] Projects with no frontend files skip design checks automatically (no noise)
- [ ] Design context stored in `sudd.yaml` and used by design-reviewer

## Dependencies
- brown_sudd-update-mechanism_01 (in progress) — update mechanism needed to distribute new agent
- Impeccable reference modules (github.com/pbakaus/impeccable) — need to extract and embed

## Risks
- Risk: Impeccable reference modules may be too large to embed in agent files → Mitigation: extract key anti-patterns and scoring criteria only, link to full reference
- Risk: Design scoring may be subjective/noisy for non-UI projects → Mitigation: auto-detect frontend files, skip design checks for backend-only changes
- Risk: Impeccable evolves independently → Mitigation: pin to specific version, track in .sudd-version

## Size: M
