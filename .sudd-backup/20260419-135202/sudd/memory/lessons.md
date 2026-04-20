# SUDD2 Lessons Learned

This file is updated automatically after each task. Agents read it to avoid repeating mistakes.

## Template

### [{DONE|STUCK|BLOCKED}] {task-name} � {YYYY-MM-DD}
**Tags:** {domain}, {technology}, {failure-mode}
**Confidence:** HIGH | MEDIUM | LOW
**What worked:** {approach that succeeded}
**What failed:** {approach that didn't work}
**Lesson:** {takeaway for future tasks}

---

### [DONE] brown_framework-hardening_01 — 2026-03-12
**Tags:** framework, agents, state-machine, go-cli, repo-hygiene
**Confidence:** HIGH
**What worked:** Phased approach (agents → state → CLI → hygiene → sync) with parallel tasks within each phase. Go stdlib replacements for hand-rolled string functions. Absorbing duplicate agents into one canonical file.
**What failed:** Stale example data in gate.md showed 72/85/90 as "PASS" despite 95 threshold — contradicted the very rule it enforced. Go test files (T17/T18) were planned but not auto-created by agents — had to create manually.
**Lesson:** When changing thresholds, grep ALL files for old values including examples and comments. Always verify test file existence after planning — agents don't create files, they describe what to create. Silent failures in tooling (installer skipping files) hide real problems — always emit warnings.

### [DONE] brown_agent-sophistication_01 — 2026-03-13
**Tags:** framework, agents, activation-protocol, critique-loop, stale-paths
**Confidence:** HIGH
**What worked:** Parallel agent dispatch (6 agents for 23 tasks) completed batch implementation in one pass. Code review before gate caught structural issues. Gate retry loop (attempt 1 → fix → attempt 2) raised scores from 78→97.
**What failed:** Stale v1 paths in files outside the change scope (init.md, monitor.md, deep-think.md, contract-verifier.md, ux-tester.md) — were not in the original task list but gate validators caught them. First gate attempt scored 78/100 due to these missed files.
**Lesson:** When updating agent files, grep the ENTIRE sudd/ directory for stale paths (openspec/, task-specs/, results/) — not just the files in your task list. Gate validators test from the consumer's perspective and catch issues the implementer misses. Always run code review before gate to catch the easy wins first.

### [DONE] brown_sudd-update-mechanism_01 — 2026-03-13
**Tags:** framework, update-mechanism, sync, go-cli, version-tracking, cross-platform
**Confidence:** HIGH
**What worked:** Parallel agent dispatch (3 agents for phases 1-3, 2 agents for phase 4 verification). Gate retry loop converged in 3 attempts (62→90→97). Persona validators caught real interoperability bugs (version format mismatch) that unit-level thinking would miss.
**What failed:** Version format inconsistency — sync.sh wrote dates while Go CLI wrote semver, causing false staleness warnings. Dead code flags (--force with no confirmation prompt to skip). Missing overwrite dirs (context/, specs/) in sync.sh that Go CLI handled implicitly. sync.bat had a paren-on-echo-line bug producing garbled output.
**Lesson:** When implementing the same feature across multiple tools (bash + Go + batch), validate format consistency across all paths BEFORE gate — especially for shared data files like .sudd-version. Dead flags are worse than missing flags because they create false confidence. Explicit allowlists (sync.sh overwrite_dirs) must be kept in sync with implicit preserve lists (Go CLI PreservedPaths).

### [DONE] brown_workflow-reliability_01 — 2026-03-13
**Tags:** framework, workflow, agents, sudd-yaml, invocation-protocol, feedback-pipes, escalation, traceability
**Confidence:** HIGH
**What worked:** Parallel agent dispatch (4 agents across 7 phases, 16 tasks) completed all implementation in one pass. Gate passed on first attempt after one inline fix (learning-engine Mode 4 streak detection). sudd.yaml central config made agent tier management declarative. Artifact-based research condition (plan.md) eliminates mode-coupling. CONTRACT_REVISION escape hatch gives coder a way out of impossible contracts without retrying forever.
**What failed:** Learning-engine initially scored 94/100 — had generic pattern promotion but lacked specific instructions for detecting consecutive root cause classifications from blocker-detector. The gap was between having the data (root cause classifications) and having the logic to act on streaks of the same classification.
**Lesson:** When building systems that produce classified data (like root cause categories), always add streak/pattern detection logic in the consuming agent — not just logging. Data without analysis is noise. Also: when adding protocols across 7+ files, use a central reference (sudd.yaml) to avoid per-file drift. Gate validators from the consumer perspective catch gaps that implementation-focused thinking misses (learning-engine consumer saw the missing Mode 4 that implementers didn't notice).

### [DONE] brown_impeccable-integration_01 — 2026-03-13
**Tags:** framework, agents, design-quality, impeccable, frontend, anti-patterns, ux, scoring
**Confidence:** HIGH
**What worked:** Fetching all 7 Impeccable reference modules from GitHub and condensing them into a single agent file (design-reviewer.md) rather than separate reference files — keeps the agent self-contained. Parallel agent dispatch (3 agents for T02-T06) while orchestrator handled T07-T09. Gate retry loop converged in 3 attempts (82→88→97). Priority markers [BLOCKER/POLISH/NICE-TO-HAVE] in critique template give developers clear triage order.
**What failed:** Agent count propagation — changed from 20 to 21 agents but missed 2 of 4 occurrences in init.md (CLAUDE.md template block and verification report). replace_all caught "20 agents" but missed "20 agent instruction files" and "Agents: 20" because the text patterns differed. Frontend Developer gate validator launched before fixes were applied, causing it to report issues already fixed — timing matters when running fixes and re-validation in parallel.
**Lesson:** When adding a new agent to the framework, grep ALL files for the old agent count in every textual variation ("20 agents", "20 agent", "Agents: 20", "Agents:    20") — not just the exact string "20 agents". Also: when fixing issues during gate and re-running validators, ensure the validators are launched AFTER all fixes are committed to disk, not in parallel with fixes. Template output format matters — violation locations must be structurally enforced (file:line) in the template, not just requested in rules, because agents follow templates more reliably than prose rules.

### [DONE] brown_worktree-parallel-execution_01 — 2026-03-13
**Tags:** framework, commands, agents, worktrees, parallel-execution, two-stage-review, escalation, cross-file-consistency
**Confidence:** HIGH
**What worked:** Consuming Superpowers patterns (worktrees, subagent-driven-development, parallel dispatch) and mapping them to existing SUDD agents rather than creating new ones. Adding worktree management to context-manager.md kept agent count at 21. Inline skip conditions in execution sections (not just guardrails) satisfied all 3 validators. Full lifecycle logging (create→dispatch→review-pass→merge→cleanup) with explicit log.md entries.
**What failed:** Escalation ladder nuance (retry 2-3: free for coder, sonnet for validation only) was initially summarized as "retry ≥2 → at least standard" in run.md Step 5b — contradicted the nuanced version in apply.md and the ESCALATION section. Skip conditions initially only in guardrails, not in run.md Step 5c execution block — validators flagged discoverability gap. Handoff-validator timing rationale initially only in apply.md, missing from run.md. Gate required 6 attempts to pass (87→96/91/87→72/96/88→91/88/88→88/88/88→97/98/98).
**Lesson:** When the same concept (escalation ladder, skip conditions, timing rationale) appears in multiple files, use identical language in every occurrence — abbreviating or summarizing creates contradictions that validators catch. Skip conditions and decision logic must be inline at the point of execution, not relegated to appendix/guardrails sections. Cross-file references ("see run.md Step 5b") are insufficient — inline the full content and note it matches. Gate validators from different personas catch different consistency issues — run all 3 in parallel.

### [DONE] brown_multi-framework-port_01 — 2026-03-13
**Tags:** framework, commands, port, multi-framework, bmad, openspec, prd, superpowers, persona-extraction
**Confidence:** HIGH
**What worked:** Complete rewrite of port.md as single self-contained file (135→545 lines). Gate retry loop converged in 3 attempts (81/83/88 → 96/97/93 → 96/97/97). Portfolio scan before planning confirmed real directory structures (no docs/epics/ in any BMAD project). Keyword table shared between BMAD and Generic/PRD with explicit label and cross-reference. Error handling table (edge case → action) more actionable than prose. Preview step significantly boosted Developer User trust score.
**What failed:** Superpowers section initially vague ("scan and note") — failed all 3 validators. state.json template only showed 3 fields instead of full 15-field schema — downstream commands would fail reading missing fields. "Step 3.1" cross-reference didn't match any labeled section. Idempotency guardrail contradicted append-to-lessons logic. Fuzzy matching ("80% word overlap") not mechanical enough for coder agent.
**Lesson:** Agent-pattern sections (Superpowers) need the same specificity as data-driven mappers — glob patterns, structured templates, explicit skill-to-agent mapping tables. state.json templates must include ALL schema fields, not just changed ones. Cross-references must use labels that actually exist in the document. Idempotency claims must be verified against every write operation — append contradicts overwrite. Preview/dry-run steps are cheap to add and dramatically increase user trust. Error handling tables beat prose.

### [DONE] brown_validation-rubrics_01 — 2026-03-13
**Tags:** framework, agents, validation, rubrics, scoring, personas, objectives, worktrees, frontend, step-order
**Confidence:** HIGH
**What worked:** Gate passed on first attempt (97/96/96). Parallel batch dispatch (4 agents for Batch 1) with clean dependency ordering. Cross-file consistency check (T8) caught two bugs before gate: duplicate text in design-reviewer.md and stale next-agent reference (contract-verifier should have been peer-reviewer after step reorder). Anchored rubrics with 5 named levels (Broken/Weak/Acceptable/Strong/Exemplary) eliminate subjective scoring. Objective-based persona testing gives validators concrete tasks to walk through instead of generic "does it work?"
**What failed:** T1 agent produced duplicate "(weighted average of domain levels)" text on line 58 — automated agents sometimes echo instructions too literally when told "update X to Y". design-reviewer.md OUTPUTS section still referenced contract-verifier as next agent even after step reorder — the OUTPUTS metadata section is easy to miss when reordering steps because it's far from the step definitions.
**Lesson:** When reordering agent steps in command files (apply.md, run.md), also check each agent's own OUTPUTS/NEXT metadata section — those reference which agent comes next and fall out of sync silently. Cross-file consistency checks should be a standard task, not optional — they catch bugs that per-file editing misses. Rubric-based scoring is more reliable than threshold-based: "Level 2: Weak" with descriptors is actionable, "45/100" is not. Objective-based persona testing (action-verb + steps + success criteria) bridges the gap between "what persona wants" and "what validator tests."

### [DONE] brown_port-hardening_01 — 2026-03-13
**Tags:** framework, commands, port, hardening, dry-run, rollback, confidence-scoring, collision-detection, design-tokens
**Confidence:** HIGH
**What worked:** Gate passed on first attempt (97/98/98). All 10 tasks implemented sequentially since they all modify port.md — no parallelization overhead. Clean specs and design docs led to zero implementation ambiguity. Cross-reference consistency check (T10) verified step numbering, confidence terminology, dry-run format, and rollback references were all internally consistent.
**What failed:** Nothing significant — clean execution. Minor gate notes: dry-run implicitly covers state.json skipping but doesn't explicitly call it out; confidence scoring cross-reference between Steps 3 and 4 relies on textual reference rather than a single canonical definition.
**Lesson:** Single-file changes with many interrelated sections benefit from sequential implementation even when tasks are "independent" — avoids merge conflicts and ensures each addition is aware of prior additions. When the same logic (keyword table, confidence scoring) is shared between two steps, a canonical definition with explicit cross-reference is better than duplicating. Design token extraction should always be commented out and best-effort — never auto-activate design configs.

### [DONE] brown_design-review-pipeline_01 — 2026-03-13
**Tags:** framework, agents, design-review, visual-verification, scoring, pipeline, smoke-test
**Confidence:** HIGH
**What worked:** Third consecutive first-attempt gate pass (96-98/100). Using log.md as inter-agent communication channel kept agents loosely coupled while enabling the design-reviewer → ux-tester → persona-validator pipeline. Reusing port.md's CSS token extraction patterns for design context auto-detection avoided duplicating logic. Score cap at Level 3/60 for uncalibrated scores is conservative but prevents inflated gates.
**What failed:** Nothing significant. One minor spec deviation: Visual Verification Needed table in implementation has a File column not in the spec's API contract — additive and non-breaking but shows specs should include all columns.
**Lesson:** When building inter-agent pipelines, use structured sections in log.md with exact header names as the communication protocol — agents look for specific `### Section Name` strings. Always define the exact table schema in specs, including every column, because additive columns can confuse downstream parsers. Design context enforcement should cap scores conservatively (Level 3/60) rather than blocking — this keeps the pipeline flowing while clearly flagging uncalibrated results.

### [DONE] brown_mechanical-enforcement_01 — 2026-03-16
**Tags:** framework, scoring, rubrics, learning, routing, state-management, retry, compression, mechanical-enforcement
**Confidence:** HIGH
**What worked:** Named rubric levels (EXEMPLARY/STRONG/ACCEPTABLE/WEAK/BROKEN) replace arbitrary 0-100 scoring — eliminates "92 vs 95" drift by making the gate binary (EXEMPLARY or fail). Root-cause routing in blocker-detector sends SPEC_ERROR/DESIGN_FLAW to architect instead of wasting retries on coder. Lesson injection as a mandatory STEP 1b in apply.md ensures lessons reach agents on first attempt, not just retries. Pattern promotion trigger in learning-engine explicitly calls out the 89-tasks-zero-patterns failure.
**What failed:** When removing design-reviewer.md (impeccable swap), the 5-level rubric scoring it contained was lost — it wasn't migrated to the surviving validation agents. This required re-implementing rubrics across 4 agents. Lesson: when deleting an agent, audit what unique features it contained and redistribute them before deletion.
**Lesson:** Named rubric levels are more reliable than numeric scores for LLM-based validation — "pick the level first, then score within range" prevents reverse-engineering a number to justify a pre-decided pass. Root-cause routing prevents the escalation ladder from wasting compute on the wrong agent. State validation and idempotency guards are cheap insurance against session interruption — add them to any persistent state file. When deleting an agent file, always check what unique features it contributed to the pipeline and migrate them first.
