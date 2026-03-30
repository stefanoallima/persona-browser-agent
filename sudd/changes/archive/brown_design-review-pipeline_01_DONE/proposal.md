# Change: brown_design-review-pipeline_01

## Status
proposed

## Summary
Address the 4 remaining improvement plan weaknesses: W7 (static-only design review), W9 (missing design context enforcement), W11 (persona-validator rubber-stamping design scores), and Gap C (no integration test for the full SUDD chain).

## Motivation
The first two improvement plan changes (brown_validation-rubrics_01, brown_port-hardening_01) fixed all high and medium-severity issues. These 4 remaining items are lower priority but collectively represent gaps in the design review pipeline and overall system confidence:

- **W7**: Design-reviewer reads code but never renders it. A component can score 95/100 while being visually broken. The ux-tester renders later but in a separate phase with no coordination.
- **W9**: sudd.yaml design section is commented out by default. Without brand_colors/typography/design_system, the design-reviewer scores against its own aesthetic preferences — inconsistent across runs. Gap A (design token extraction from port) partially addresses this but doesn't enforce config before scoring.
- **W11**: persona-validator checks that design-reviewer ran and scored well, but can't independently assess design quality. If design-reviewer is miscalibrated, persona-validator rubber-stamps it.
- **Gap C**: No integration test or smoke test exercises the full chain: port → plan → apply (with design review + worktree) → gate. The first real user will be the test.

## Scope
What's included:
- W7: Add visual verification coordination between design-reviewer and ux-tester
- W9: Enforce design context configuration before design scoring (skip or warn if unconfigured)
- W11: Add independent design quality checks to persona-validator (beyond checking scores)
- Gap C: Add a smoke test example/checklist that exercises the full SUDD chain

What's NOT included:
- Full browser-based visual regression testing (W7 is coordination, not a new rendering engine)
- Automated rubric calibration
- New agent creation (use existing agents)

## Success Criteria
- [ ] Design-reviewer skips or warns when no design context configured (W9)
- [ ] Design-reviewer flags items for ux-tester visual verification (W7)
- [ ] Persona-validator has independent design quality checks beyond score passthrough (W11)
- [ ] Smoke test checklist exists for full chain validation (Gap C)
- [ ] All changes backward-compatible with existing workflows

## Dependencies
- brown_validation-rubrics_01 (anchored rubrics, step reorder)
- brown_port-hardening_01 (design token extraction in port.md)

## Risks
- W7 coordination between design-reviewer and ux-tester could create implicit coupling — mitigate with loose coupling (flags in log, not direct agent calls)
- Gap C smoke test could become stale — mitigate by keeping it as a checklist, not automated scripts
