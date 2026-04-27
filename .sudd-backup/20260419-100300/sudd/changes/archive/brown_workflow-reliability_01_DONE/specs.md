# Specifications: brown_workflow-reliability_01

## Functional Requirements

### FR-1: Agent Invocation Protocol
- Given: A command needs to invoke an agent (e.g., `Task(agent=coder)`)
- When: The orchestrator reaches an agent step
- Then: The command reads the agent's .md file and spawns a subagent via the CLI tool's native dispatch (Claude Code Agent tool, OpenCode agents, Crush commands). Independent agents spawn in parallel. Sequential agents wait for predecessor output files to exist on disk.

### FR-2: Centralized Configuration (sudd.yaml)
- Given: SUDD is initialized in a project
- When: Any command spawns an agent
- Then: The command reads `sudd/sudd.yaml` for that agent's tier (opus/sonnet/free), the escalation ladder, and the cost_mode. The user edits ONE file to control all model assignments.

### FR-3: Feedback Pipe Between Retries
- Given: Gate fails with score < 95
- When: Gate command runs
- Then: Gate APPENDS per-persona feedback to `## Accumulated Feedback` in log.md (never overwrites). On retry, coder's PREREQUISITES include reading this section. Context-manager compresses if > 3 retries.

### FR-4: Formal Phase Enum
- Given: A command updates phase in state.json
- When: Phase transition is attempted
- Then: Transition is validated against the enum (inception → planning → build → validate → complete, plus validate → build for retry). Invalid transitions are logged as warnings and rejected.

### FR-5: Handoff Contract Schema
- Given: specs.md defines Consumer Handoffs
- When: Handoff contracts are written
- Then: Each contract uses the standardized markdown format: `### Handoff: {Producer} → {Consumer}` with bullet points for Format, Location, Required fields, Validated by, Error case. Structured enough for validators to parse, readable as markdown.

### FR-6: QA Early Involvement
- Given: Architect produces FINAL design.md (after critique loop)
- When: Planning chain continues
- Then: QA agent runs a lightweight testability review before decomposer. Checks: are acceptance criteria testable? Any untestable components? Appropriate test framework? Output: `## Testability Notes` appended to design.md.

### FR-7: Brown Mode Research Gap Fix
- Given: Mode is brown and /sudd:plan runs
- When: Plan checks for research artifacts
- Then: Research agents run if `personas/*.md` has only default.md OR specs.md has no Consumer Handoffs section — regardless of mode. Brown mode with existing research skips it.

### FR-8: Test Framework Detection
- Given: /sudd:test runs
- When: No `test_command` is set in sudd.yaml
- Then: Auto-detect by checking for `*_test.go`, `*.test.ts`, `test_*.py`, Makefile test target, package.json scripts.test. Store detected command in sudd.yaml. If none found, QA agent creates test infrastructure first.

### FR-9: Retry Context Continuity
- Given: retry_count > 0 and /sudd:apply runs
- When: Coder is about to be invoked
- Then: Orchestrator prepares a RETRY BRIEFING: previous gate_score, accumulated feedback, latest critique dispositions, top-3 lessons. Passed to coder as part of agent prompt. Instruction: "FIX THESE SPECIFIC ISSUES. Do not rewrite from scratch."

### FR-10: Stuck Change Rollback
- Given: /sudd:apply completes a task
- When: Code files are modified
- Then: Apply command appends file paths to `## Files Modified` section in log.md. When /sudd:done archives as STUCK, it reads this section to generate a `git checkout main -- {files}` rollback command.

### FR-11: Traceability Report
- Given: Persona-validator scores a criterion as "pass"
- When: Validation completes
- Then: For each passing criterion, validator identifies WHICH code/output satisfies it. If no traceable implementation maps to the criterion, it is flagged UNMAPPED and score is capped at 80. Logged as "UNMAPPED SUCCESS" in log.md.

### FR-12: Root Cause Classification
- Given: A task fails and blocker-detector runs
- When: Blocker-detector classifies the error
- Then: Output includes both Action (RETRY/BLOCKED/STUCK) AND Root Cause (LOGIC_ERROR/SPEC_ERROR/EXTERNAL_DEPENDENCY/CONTEXT_DRIFT/DESIGN_FLAW). Root cause is logged in log.md and consumed by learning engine for pattern detection.

### FR-13: Structured Postmortems
- Given: A task fails or gets stuck
- When: Learning engine captures the outcome
- Then: Uses extended template with Root Cause, Agent, Error, Hypothesis, Resolution, Prevention fields. Hypothesis forces the agent to theorize, not just log.

### FR-14: Contract Revision on Escalation
- Given: Coder fails 2+ times on the SAME handoff contract violation
- When: Coder raises CONTRACT_REVISION
- Then: Architect receives the report and can modify ONLY the specific flagged handoff contract in specs.md. Original contract preserved in log.md. Retry count resets to 0 for that task after revision.

### FR-15: Per-Change Cost Awareness
- Given: An agent completes its work
- When: Agent finishes execution
- Then: A row is appended to `## Cost Log` table in log.md with step, agent name, tier used, estimated tokens. Monitor agent flags if total exceeds ~100K tokens.

## Non-Functional Requirements

### NFR-1: No Python, No Inter-Process JSON
- Constraint: All agent communication is via markdown files on disk. No JSON payloads between processes. No Python orchestrator.
- Rationale: V1's 30+ Python modules with JSON handoffs broke constantly. Markdown-first is the core architecture decision.

### NFR-2: Single Configuration Source
- Constraint: All model/tier/escalation configuration lives in sudd.yaml. Agent .md files contain behavior only, not model config.
- Rationale: Users should not need to search 20+ files to change model assignments.

### NFR-3: Backward Compatibility
- Constraint: Changes to command files must not break existing workflows. New sections (Accumulated Feedback, Files Modified, Cost Log) are additive — they appear when needed, don't require pre-creation.
- Rationale: Existing changes in progress should not be disrupted.

## Consumer Handoffs

### Handoff: Gate → Coder (on retry)
- **Format**: markdown section in log.md
- **Location**: `## Accumulated Feedback` in `changes/{id}/log.md`
- **Required fields**: retry number, gate score, per-persona feedback
- **Validated by**: coder PREREQUISITES check that section exists on retry
- **Error case**: if section missing on retry, coder proceeds without feedback (degraded but not blocked)

### Handoff: Apply → Done (file tracking)
- **Format**: markdown section in log.md
- **Location**: `## Files Modified` in `changes/{id}/log.md`
- **Required fields**: file path, task ID, description
- **Validated by**: done command reads section to generate rollback
- **Error case**: if section missing, done.md warns "no file tracking available, manual rollback needed"

### Handoff: Blocker-Detector → Learning Engine (root cause)
- **Format**: classification in log.md
- **Location**: blocker-detector output in `changes/{id}/log.md`
- **Required fields**: Action, Root Cause
- **Validated by**: learning engine parses Root Cause for pattern detection
- **Error case**: if Root Cause missing, learning engine logs without classification

### Handoff: sudd.yaml → Commands (agent config)
- **Format**: YAML file
- **Location**: `sudd/sudd.yaml`
- **Required fields**: agents section with tier per agent, escalation.ladder, cost_mode
- **Validated by**: commands read sudd.yaml; if missing or malformed, fall back to `free` tier for all
- **Error case**: missing sudd.yaml → warn user, default all agents to free

## Out of Scope
- Auto-rollback on deployment (v1 sentinel-ops)
- Smart CI skipping (v1 sentinel-ops)
- mem0 or external memory dependency
- Per-task cost enforcement/budget gates
- Changes to Go CLI (sudd-go/)
