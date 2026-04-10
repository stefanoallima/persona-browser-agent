# Specifications: brown_mechanical-enforcement_01

## Functional Requirements

### FR-1: Named Rubric Levels in Scoring
- Given: A validation agent (persona-validator, contract-verifier, peer-reviewer, handoff-validator) evaluates output
- When: The agent produces a verdict
- Then: The agent selects ONE of 5 named levels (EXEMPLARY/STRONG/ACCEPTABLE/WEAK/BROKEN) with evidence, and the level deterministically maps to a score range

### FR-2: Gate Passes Only EXEMPLARY
- Given: Gate.md aggregates scores from all consumers
- When: Determining PASS/FAIL
- Then: PASS requires ALL consumers at EXEMPLARY level. Any consumer at STRONG or below = FAIL. No numeric threshold ambiguity.

### FR-3: Lesson Injection Before Coder
- Given: A coder task is about to execute (first attempt or retry)
- When: Orchestrator prepares coder context
- Then: Top-3 matching lessons from memory/lessons.md are included in coder prompt, matched by task technology/domain tags. Logged to log.md.

### FR-4: Pattern Promotion
- Given: Learning-engine runs after task completion
- When: A lesson tag combination appears 3+ times across different changes in lessons.md
- Then: The lesson is promoted to patterns.md with ESTABLISHED status, occurrence count, and evidence

### FR-5: Root-Cause Routing
- Given: Blocker-detector classifies a failure with root cause
- When: Root cause is SPEC_ERROR or DESIGN_FLAW
- Then: Retry routes to architect (not coder). Architect revises specs/design, then coder retries. Escalation ladder resets for the re-routed task.

### FR-6: Root-Cause Routing — CONTEXT_DRIFT
- Given: Blocker-detector classifies root cause as CONTEXT_DRIFT
- When: Orchestrator processes the classification
- Then: Context is reset — coder re-reads vision.md and specs.md from scratch. Previous partial context discarded.

### FR-7: State Validation on Read
- Given: Any command reads sudd/state.json
- When: JSON is parsed
- Then: Phase is validated against allowed values (inception/planning/build/validate/complete). Active_change directory existence is verified. On invalid JSON, auto-restore from `git show HEAD:sudd/state.json`.

### FR-8: Idempotency Guard
- Given: Apply.md is about to execute a task
- When: Task is marked [x] in tasks.md
- Then: Task is skipped. Log: "Task {id} already completed." No re-invocation of coder.

### FR-9: Feedback Compression at Retry 3+
- Given: Coder retry_count >= 3
- When: Orchestrator prepares RETRY BRIEFING
- Then: All accumulated feedback entries are compressed into STILL OPEN / RESOLVED / PATTERN format. Total coder context capped at 6000 tokens (task + design + compressed feedback + lessons).

## Non-Functional Requirements

### NFR-1: Zero New Dependencies
- Constraint: All fixes are markdown instruction changes. No Python, no JSON schema libraries, no external tools.
- Rationale: Preserves SUDD's "zero-Python" principle.

### NFR-2: Backward Compatibility
- Constraint: Existing state.json files, lessons.md entries, and archived changes must remain valid after changes.
- Rationale: Don't break existing installations.

### NFR-3: Token Budget
- Constraint: Changes to agent files must not increase per-agent token cost by more than 200 tokens.
- Rationale: Context window pressure (W4) was identified as a weakness. Fixes must not worsen it.

## Consumer Handoffs

### Handoff 1: standards.md → All Agents
- Format: Markdown reference section
- Content: Rubric level definitions, state validation protocol
- Validation: All 4 validation agents reference the canonical rubric table

### Handoff 2: blocker-detector → apply.md/run.md Orchestrator
- Format: Root cause classification in output markdown
- Content: `Root Cause: LOGIC_ERROR | SPEC_ERROR | DESIGN_FLAW | CONTEXT_DRIFT | EXTERNAL_DEPENDENCY`
- Validation: Orchestrator reads root cause and routes accordingly (not just action)

### Handoff 3: learning-engine → memory/patterns.md
- Format: Pattern entry with ESTABLISHED status
- Content: Pattern name, occurrences, rule, evidence, status
- Validation: patterns.md has entries after running learning-engine on current lessons.md (which has 10+ lessons with overlapping tags)
