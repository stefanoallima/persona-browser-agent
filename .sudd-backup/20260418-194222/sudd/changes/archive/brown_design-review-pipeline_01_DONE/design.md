# Design: brown_design-review-pipeline_01

## Architecture Overview

The design review pipeline currently has a gap between static code review (design-reviewer) and browser-based testing (ux-tester), with persona-validator rubber-stamping design scores. This change creates a feedback loop through log.md:

```
CURRENT FLOW (disconnected):
  design-reviewer ──→ peer-reviewer ──→ ...
                                          ux-tester ──→ persona-validator
                                          (no awareness of design-reviewer findings)

NEW FLOW (coordinated via log.md):
  design-reviewer ──→ peer-reviewer ──→ ...
    │ writes:                             ux-tester ──→ persona-validator
    │  - domain scores                      │ reads:       │ reads:
    │  - Visual Verification Needed         │  - flags     │  - design score
    │  - NO_DESIGN_CONTEXT flag            │ writes:      │  - verification results
    └──────────────────────────────────────┘  - results   │ writes:
                                                           │  - independent assessment
                                                           │  - disagreement (if any)
```

## Component: Design Context Enforcement (W9)

### Responsibility
Ensure design-reviewer has a baseline before scoring, or explicitly flags uncalibrated scores.

### Design
Add to design-reviewer.md `## Design Context` section:

```markdown
### Design Context Enforcement

Before scoring, check `sudd/sudd.yaml` for design context:

1. **If `design:` section exists and is uncommented** → use as baseline (current behavior)

2. **If `design:` section is missing or fully commented**:
   a. **Auto-detect attempt**: Scan CSS/SCSS files in the change for:
      - Color declarations → infer palette
      - Font-family → infer typography
      - Spacing values → infer scale
   b. **If tokens found**: Use as temporary baseline, add warning:
      ```
      ⚠ DESIGN CONTEXT: Auto-detected from CSS (not configured in sudd.yaml)
        Colors: {discovered}
        Fonts: {discovered}
        Configure sudd.yaml for consistent scoring across runs.
      ```
   c. **If no tokens found**: Add warning and cap:
      ```
      ⚠ NO DESIGN CONTEXT: sudd.yaml has no design section and no CSS tokens found.
        All domain scores capped at Level 3 (60/100 max).
        Configure sudd.yaml design section for accurate scoring.
      ```
   d. Add `NO_DESIGN_CONTEXT: true` flag to output header
   e. Cap all domain scores at rubric Level 3 (max 60) when no context

3. **If `skip_design_review: true`** → SKIP (current behavior, unchanged)
```

### Implementation Notes
- Auto-detection uses same regex patterns as port.md Step 8e (design token extraction)
- Cap at Level 3 is conservative — prevents inflated scores without baseline
- The flag `NO_DESIGN_CONTEXT` lets downstream agents (persona-validator) know scores are uncalibrated

## Component: Visual Verification Flags (W7)

### Responsibility
Bridge the gap between static code review and browser-based testing.

### Design
Add to design-reviewer.md after the Anti-Pattern Summary:

```markdown
### Visual Verification Needed

After static code review, identify items that CANNOT be verified without rendering:

1. **Auto-flag these categories**:
   - z-index values > 10 or competing stacking contexts → "Check visual stacking"
   - overflow: hidden on containers with dynamic content → "Check content clipping"
   - CSS animations/transitions with complex timing → "Verify animation feel"
   - Responsive layout with multiple breakpoints → "Test at {breakpoint} viewport"
   - Position: fixed/sticky elements → "Check scroll behavior"
   - Dark mode toggles → "Verify dark mode rendering"

2. **Output table** (appended to design review in log.md):
   ```markdown
   ### Visual Verification Needed
   | # | Item | Type | What to Check | File | Priority |
   |---|------|------|--------------|------|----------|
   | 1 | {component/element} | {category} | {specific check} | {file:line} | HIGH/MEDIUM |
   ```

3. If NO items need visual verification: omit this section entirely
```

### Implementation Notes
- This is a static analysis step — design-reviewer reads code and flags what it can't verify
- Priority: HIGH for z-index/overflow (visual breakage), MEDIUM for animation/responsive (quality)
- The table is written to log.md where ux-tester reads it

## Component: UX-Tester Design Verification (W7)

### Responsibility
During browser session, verify items flagged by design-reviewer.

### Design
Add to ux-tester.md process, after step 2 (Navigate as Persona) and before step 3 (Judge):

```markdown
### 2.5. Design Verification (if flagged)

Read log.md for `### Visual Verification Needed` from design-reviewer.

If found:
1. For each flagged item:
   - Navigate to the component/page containing the item
   - Perform the specific check described
   - Take a screenshot showing the result
   - Record PASS/FAIL with evidence

2. Output table (in UX Test Report):
   ```markdown
   ### Design Verification Results
   | # | Item | Result | Screenshot | Notes |
   |---|------|--------|------------|-------|
   | 1 | {from flag table} | PASS/FAIL | {screenshot path} | {what was observed} |
   ```

3. If any HIGH priority item FAIL → add to Issues Found as [CRITICAL]

If no `### Visual Verification Needed` in log.md: skip this section.
```

## Component: Independent Design Assessment (W11)

### Responsibility
Give persona-validator its own design quality judgment beyond checking scores.

### Design
Modify persona-validator.md `## Design Quality Gate` section:

```markdown
## Design Quality Gate (UI Changes Only)

### Step 1: Check for Design Review
Read log.md for "## Design Review" section from design-reviewer agent.

### Step 2: Independent Visual Assessment (NEW)
Regardless of design-reviewer score, perform YOUR OWN assessment as the persona:

1. **Persona expectation match**: Does the UI look like what {persona} would expect from this type of product?
   - A fintech app should look professional and trustworthy
   - A creative tool should feel expressive and dynamic
   - A developer tool should be clean and information-dense

2. **Design system coherence**: If sudd.yaml specifies a design_system (minimalist/brutalist/etc.), does the UI match that system?

3. **Obvious issues**: Would a real user of this persona notice anything off?
   - Elements that look broken or misaligned
   - Colors that feel jarring or inconsistent
   - Text that's hard to read
   - Interactions that feel sluggish or wrong

4. **Assign your own score** (0-100) based on "Would {persona} think this looks professional?"

### Step 3: Check Design Verification Results (NEW)
Read log.md for `### Design Verification Results` from ux-tester.
- If any HIGH-priority items FAILED → design deal-breaker
- If MEDIUM items FAILED → note but not deal-breaker

### Step 4: Compare and Resolve
- If design-reviewer score exists:
  - Compare with your independent assessment
  - If difference > 15 points: flag DESIGN SCORE DISAGREEMENT
  - Use LOWER of the two scores for gate purposes
  - Log disagreement reasons

- If design-reviewer has `NO_DESIGN_CONTEXT: true`:
  - Note: "Design scores are uncalibrated — no design context in sudd.yaml"
  - Treat domain scores as advisory, not binding
  - Rely more heavily on your independent assessment

### Step 5: Include in Output
Add to Persona Validation output:
```markdown
### Design Quality Gate
- Applies: YES/NO (frontend files: {list or "none"})
- Design-Reviewer Score: {N}/100 or "NOT RUN"
- Design Context: configured/auto-detected/missing
- My Assessment as {persona}: {M}/100
- Design Score Disagreement: YES/NO ({details if yes})
- Visual Verification: {N} items checked, {M} passed (or "none flagged")
- Design Deal-Breaker: YES/NO
- Gate Score Used: {min(reviewer, my_assessment)}/100
```
```

## Component: Smoke Test Checklist (Gap C)

### Responsibility
Provide a documented checklist for validating the full SUDD chain end-to-end.

### Design
Create `sudd/memory/smoke-test.md`:

```markdown
# SUDD Smoke Test Checklist

## Purpose
Validates the full SUDD chain works end-to-end. Run this after major framework changes.

## Prerequisites
- A sample project with a PRD or BMAD structure
- Or use the smoke test fixtures below

## Steps

### Phase 1: Port
- [ ] Run `/sudd:port --dry-run` on the sample project
- [ ] Verify: dry-run output shows framework detection, file mapping, confidence scoring
- [ ] Verify: no files were written
- [ ] Run `/sudd:port` (without --dry-run)
- [ ] Verify: git checkpoint commit created
- [ ] Verify: vision.md, specs/, personas/ created with source tags
- [ ] Verify: state.json has `imported_from` set, `mode: "brown"`
- [ ] Verify: log.md has port summary with section counts

### Phase 2: Plan
- [ ] Run `/sudd:plan` on the ported change
- [ ] Verify: specs.md has functional requirements with Given/When/Then
- [ ] Verify: design.md has architecture diagram and component designs
- [ ] Verify: tasks.md has implementation tasks with dependencies
- [ ] Verify: state.json `phase: "build"`

### Phase 3: Apply
- [ ] Run `/sudd:apply` on the first task
- [ ] Verify: coder agent produces code
- [ ] Verify: contract-verifier runs (Step 3b)
- [ ] If frontend files: verify design-reviewer runs (Step 3b.5)
  - [ ] If no design context: verify warning + score cap at 60
  - [ ] If visual verification items flagged: noted for Phase 3.5
- [ ] Verify: peer-reviewer runs (Step 3c)
- [ ] Verify: handoff-validator runs (Step 3d)
- [ ] Verify: task marked complete in tasks.md
- [ ] Verify: git commit created

### Phase 3.5: Visual Verification (if frontend)
- [ ] Verify: ux-tester reads Visual Verification flags from log.md
- [ ] Verify: ux-tester checks each flagged item with screenshots
- [ ] Verify: Design Verification Results table in log.md

### Phase 4: Gate
- [ ] Run `/sudd:gate`
- [ ] Verify: persona-validator impersonates each consumer
- [ ] Verify: objective walkthrough completed for each persona
- [ ] If frontend: verify independent design assessment performed
- [ ] If design score disagreement: verify lower score used
- [ ] Verify: score ≥ 95 for PASS, < 95 for FAIL with feedback
- [ ] If PASS: verify state.json `gate_passed: true`

### Phase 5: Done
- [ ] Run `/sudd:done`
- [ ] Verify: change archived to sudd/changes/archive/{id}_DONE/
- [ ] Verify: SUMMARY.md created with scores and lessons
- [ ] Verify: lessons.md updated
- [ ] Verify: state.json `active_change: null`

## Smoke Test Fixtures

### Minimal PRD for testing
Create a file `test-prd.md`:
```
# Test Product

## Purpose
A test application for validating the SUDD pipeline.

## Target Users
- Developer: builds and tests the system

## Requirements
- Must accept input and produce output
- Must have a simple UI with a form and results display

## Technical Architecture
- Frontend: HTML/CSS/JS
- Backend: Node.js or Python
```

### Expected Results
- Port: 1 vision, 1 persona, 1 change, 1 spec domain
- Plan: specs.md with 2+ FRs, design.md with architecture, tasks.md with 3+ tasks
- Apply: code files created, all validation agents run
- Gate: scores ≥ 95 for PASS
```

## File Changes

### Modified Files
- `sudd/agents/design-reviewer.md` — Design context enforcement (W9), visual verification flags (W7)
- `sudd/agents/ux-tester.md` — Design verification step (W7)
- `sudd/agents/persona-validator.md` — Independent design assessment, disagreement handling (W11)

### New Files
- `sudd/memory/smoke-test.md` — End-to-end validation checklist (Gap C)

## Migration Plan
- Step 1: Add design context enforcement to design-reviewer (W9)
- Step 2: Add visual verification flags to design-reviewer (W7)
- Step 3: Add design verification to ux-tester (W7)
- Step 4: Update persona-validator with independent assessment (W11)
- Step 5: Create smoke test checklist (Gap C)
- Step 6: Cross-reference consistency check
