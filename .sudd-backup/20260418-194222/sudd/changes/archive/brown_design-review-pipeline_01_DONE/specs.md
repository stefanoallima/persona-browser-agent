# Specifications: brown_design-review-pipeline_01

## Functional Requirements

### FR-1: Design Context Enforcement (W9)
- Given: design-reviewer agent runs on frontend files
- When: `sudd/sudd.yaml` has no active (uncommented) `design:` section
- Then: design-reviewer outputs a WARNING block with instructions to configure design context, downgrades all domain scores by one rubric level (cap at Level 3 / 60 max), and adds "NO_DESIGN_CONTEXT" flag to its output so downstream agents know scores are uncalibrated

### FR-2: Design Context Auto-Detection Fallback (W9)
- Given: no `design:` section in sudd.yaml AND frontend CSS/SCSS files exist
- When: design-reviewer runs
- Then: before scoring, attempt auto-detection of design tokens (colors, fonts, spacing) from existing CSS. Use discovered tokens as temporary baseline. Log: "Auto-detected design context (not configured — review sudd.yaml)"

### FR-3: Visual Verification Flags (W7)
- Given: design-reviewer completes an AUDIT and finds potential visual issues
- When: issues cannot be verified by static code review alone (z-index stacking, overflow behavior, animation timing, responsive layout at specific breakpoints)
- Then: add a `### Visual Verification Needed` section to design-reviewer output listing items that require browser-based confirmation by ux-tester

### FR-4: UX-Tester Design Verification (W7)
- Given: ux-tester runs and log.md contains a `### Visual Verification Needed` section from design-reviewer
- When: ux-tester navigates the application
- Then: ux-tester checks each flagged item during its browser session, takes screenshots as evidence, and reports results in a `### Design Verification Results` table

### FR-5: Independent Design Quality Assessment (W11)
- Given: persona-validator runs on a change with frontend files
- When: design-reviewer score exists in log.md
- Then: persona-validator performs its OWN independent visual assessment (not just checking the design-reviewer score) — specifically: (a) does the UI look like the persona expects? (b) does it match the project's stated design_system? (c) are there obvious visual issues a real user would notice? Report disagreements between own assessment and design-reviewer score

### FR-6: Design Score Disagreement Handling (W11)
- Given: persona-validator's independent assessment disagrees with design-reviewer score by more than 15 points
- When: in any mode
- Then: flag the disagreement explicitly in output: "DESIGN SCORE DISAGREEMENT: design-reviewer scored {N}, my assessment as {persona} is {M}. Discrepancy: {reasons}." Use the LOWER of the two scores for gate purposes

### FR-7: Smoke Test Checklist (Gap C)
- Given: a user wants to validate the full SUDD chain works end-to-end
- When: they run the smoke test
- Then: a documented checklist exists that exercises: (1) port from a sample framework, (2) plan the ported change, (3) apply with design review + validation, (4) gate with persona validation — with expected outputs at each step

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Constraint: All changes are additive — existing behavior without design context must still work (just with warnings)
- Rationale: Projects without sudd.yaml design section should not break

### NFR-2: No New Agents
- Constraint: All changes use existing agents (design-reviewer, ux-tester, persona-validator)
- Rationale: Agent count stays at 21

### NFR-3: Loose Coupling (W7)
- Constraint: design-reviewer → ux-tester coordination uses log.md as the communication channel (not direct agent calls)
- Rationale: Agents remain independently runnable

## API Contracts

### Interface: Visual Verification Flags (design-reviewer → ux-tester)
- Channel: log.md
- Format:
  ```markdown
  ### Visual Verification Needed
  | # | Item | Type | What to Check | Priority |
  |---|------|------|--------------|----------|
  | 1 | {component} | z-index/overflow/animation/responsive | {specific check} | HIGH/MEDIUM |
  ```
- Consumer: ux-tester reads this during its browser session

### Interface: Design Verification Results (ux-tester → persona-validator)
- Channel: log.md
- Format:
  ```markdown
  ### Design Verification Results
  | # | Item | Result | Screenshot | Notes |
  |---|------|--------|------------|-------|
  | 1 | {from Visual Verification Needed} | PASS/FAIL | {path} | {details} |
  ```
- Consumer: persona-validator reads this for its independent assessment

### Interface: Design Score Disagreement (persona-validator output)
- Channel: log.md (within persona validation section)
- Format:
  ```markdown
  ### Design Score Disagreement
  - Design-reviewer score: {N}/100
  - My assessment as {persona}: {M}/100
  - Discrepancy: {specific reasons}
  - Gate score used: {min(N, M)}/100
  ```

## Consumer Handoffs

### Handoff 1: design-reviewer → ux-tester (via log.md)
- Format: Visual Verification Needed table
- Schema: item, type, check description, priority
- Validation: ux-tester confirms each item via browser

### Handoff 2: design-reviewer + ux-tester → persona-validator (via log.md)
- Format: Design review score + verification results
- Schema: domain scores, anti-pattern summary, verification results
- Validation: persona-validator performs independent assessment

### Handoff 3: smoke test checklist → human user
- Format: markdown checklist in sudd/memory/
- Schema: step-by-step with expected outputs
- Validation: human runs and confirms

## Out of Scope
- Full browser-based visual regression testing framework
- Automated rubric calibration
- New agent creation
- Pixel-perfect screenshot comparison
- Design system theme switching
