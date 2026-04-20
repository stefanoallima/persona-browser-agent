# Change: brown_port-hardening_01

## Status
proposed

## Summary
Harden port.md against 6 architectural weaknesses (W1-W6) and 1 cross-change gap (Gap A) identified in the architectural review — add framework priority resolution, PRD decomposition guardrails, post-port validation, merge collision detection, dry-run/rollback capability, iterative refinement, and design config extraction.

## Motivation
Architectural review of brown_multi-framework-port_01 revealed 6 weaknesses:
- **W1**: Detection engine is brittle — multiple frameworks detected with no priority/conflict resolution
- **W2**: PRD decomposition is a black box — no mapping rules, different runs produce different decompositions
- **W3**: No validation of ported artifacts — silent requirement loss after conversion
- **W4**: Merge strategy for Superpowers is dangerous — naming collisions overwrite existing agent customizations
- **W5**: No rollback — if port produces garbage halfway, no --dry-run or undo
- **W6**: Single-pass architecture — no iterative refinement if researcher misinterprets a section

Plus **Gap A** (cross-change): ported projects arrive with no sudd.yaml design config, causing design-reviewer to score without baseline.

## Scope
What's included:
- W1: Framework priority table + conflict resolution rules in Step 1a
- W2: PRD section mapping confidence scoring + ambiguity handling rules
- W3: Post-port validation step using contract-verifier pattern
- W4: Collision detection before Superpowers merge — detect existing agent overrides, prompt or merge
- W5: --dry-run mode (preview only, write nothing) + git-based rollback (commit before port, revert on failure)
- W6: Iterative review step — preview decomposition, let user/orchestrator correct before proceeding
- Gap A: Design token extraction from source framework OR auto-generate minimal sudd.yaml design section

What's NOT included:
- Rewriting the entire port.md structure (keep existing step numbering)
- Adding new framework support beyond the 4 existing ones
- Visual regression testing of ported frontends

## Success Criteria
- [ ] Framework detection has explicit priority order when multiple frameworks found
- [ ] PRD decomposition has confidence scoring per section and handles ambiguous headers
- [ ] Post-port validation checks that no requirements from source were dropped
- [ ] Superpowers port detects existing agent files and preserves customizations
- [ ] --dry-run flag produces preview output without writing any files
- [ ] Port commits a checkpoint before writing, enabling git revert on failure
- [ ] Decomposition results are reviewable before final write (iterative mode)
- [ ] Ported projects with frontend files get a minimal sudd.yaml design section
- [ ] All 3 persona validators score >= 95/100 at gate

## Dependencies
- brown_multi-framework-port_01 (port.md exists)
- brown_validation-rubrics_01 (design-reviewer has rubrics, design context documented)

## Risks
- Scope creep: 7 fixes in one change is ambitious → mitigation: each fix is self-contained within port.md, minimal cross-file impact
- PRD confidence scoring adds complexity → mitigation: use simple keyword-count heuristic, not ML
- --dry-run may diverge from actual port behavior → mitigation: extract shared logic, both modes call same functions
- Design token extraction may produce incomplete config → mitigation: flag as "needs review" rather than silently using bad defaults
