# Change: brown_validation-rubrics_01

## Status
proposed

## Summary
Replace subjective scoring in design-reviewer and persona-validator with anchored rubrics, objective-based UX testing, and a single-frontend-worktree constraint to eliminate inconsistency across validation runs.

## Motivation
Architectural review of the last 3 changes revealed:
- **W8 (Scoring subjectivity)**: design-reviewer scores 7 domains 0-100 with no rubric. Two runs produce different scores. No calibration or reference examples.
- **W12 (Shallow persona simulation)**: ux-tester "becomes" a persona but has no concrete objectives. Tests are generated from specs, not from realistic user tasks — misses real usability failures.
- **Gap B (Worktree + design consistency)**: In worktree mode, multiple frontend tasks run in parallel worktrees. Each scores well individually but can clash visually when merged. No post-merge design re-check.

These weaknesses undermine the reliability of the entire validation gate.

## Scope
What's included:
- Anchored scoring rubrics for design-reviewer's 7 domains (Perplexity-style structured criteria with level descriptors, not color-based)
- Objective-based persona task definitions — each persona pre-defines concrete tasks they'd accomplish (e.g., "retrieve prospecting info for target companies", "filter leads by industry and revenue")
- ux-tester and persona-validator updated to test navigation against those predefined objectives
- Single frontend worktree constraint: only 1 UI/UX-related worktree active at any time, enforced in context-manager.md
- W10 fix: swap step 3a.5 and 3b in apply.md (design review after contract verification, not before)

What's NOT included:
- Visual regression testing / screenshot diffing (requires external tooling)
- Runtime rendering validation (stays static code analysis)
- Automated rubric calibration across projects (manual rubric definitions for now)

## Success Criteria
- [ ] Each of design-reviewer's 7 domains has a 5-level anchored rubric (0-20, 21-40, 41-60, 61-80, 81-100) with concrete descriptors
- [ ] Persona definitions include an `## Objectives` section with 3-5 task-based goals per persona
- [ ] ux-tester test scripts are generated from persona objectives, not just specs
- [ ] persona-validator walks through each objective and scores completion success
- [ ] context-manager enforces max 1 frontend worktree at any time (queues or serializes additional frontend tasks)
- [ ] apply.md step order is: 3a (code) → 3b (contract) → 3a.5 (design review) → 3c (quality) → 3d (handoff)
- [ ] All 3 persona validators score >= 95/100 at gate

## Dependencies
- brown_impeccable-integration_01 (design-reviewer agent exists)
- brown_worktree-parallel-execution_01 (worktree management exists, sequential default)

## Risks
- Rubric rigidity: overly prescriptive rubrics might reject valid creative approaches → mitigation: make rubrics descriptive not prescriptive, score "intent and execution" not "exact technique"
- Objective coverage: pre-defined objectives might miss edge cases → mitigation: allow persona-validator to discover additional objectives during testing, append to list
- Frontend worktree serialization could slow down parallel batches with multiple UI tasks → mitigation: only applies to worktree opt-in mode; sequential mode (default) is unaffected
