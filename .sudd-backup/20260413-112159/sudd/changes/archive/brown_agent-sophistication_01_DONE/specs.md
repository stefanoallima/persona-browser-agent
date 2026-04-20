# Specifications: brown_agent-sophistication_01

## Functional Requirements

### FR-1: Standardized Agent Activation Protocol
- Given: Any of the 20 agent files (18 existing + decomposer + solution-explorer)
- When: An agent is invoked by the orchestrator or chain
- Then: The agent has ACTIVATION, PREREQUISITES, OUTPUTS, PERMISSIONS sections in a standardized format. PREREQUISITES are checked before execution proceeds. If any blocking condition is true, agent halts with a report instead of producing garbage.

### FR-2: Solution Explorer Agent
- Given: specs.md + researcher output + persona research + antigravity back-plan exist
- When: Planning chain reaches solution-explorer step
- Then: Agent generates 3-5 candidate approaches, scores them on 6 weighted criteria (persona fit 25%, cost 20%, speed 15%, maintainability 20%, scalability 10%, risk 10%), selects winner with rationale, documents rejected alternatives with reasons, writes `changes/{id}/solutions.md`

### FR-3: Decomposer Agent
- Given: PRD/vision.md + design.md (architecture) exist
- When: Decomposer is invoked
- Then: Agent extracts feature groups into changes, breaks each into specs and tasks, orders by dependency, estimates effort (S/M/L), identifies parallelizable work. Output: proposal.md + specs.md + tasks.md per change.

### FR-4: Agent Permission Boundaries
- Given: Any agent is executing
- When: Agent attempts to modify a file
- Then: Agent's PERMISSIONS section defines CAN modify and CANNOT modify lists. Agents must not write to files outside their CAN list. Violations are logged.

### FR-5: Blocking Conditions
- Given: Any agent starts execution
- When: Agent checks PREREQUISITES
- Then: If any blocking condition is true (missing files, empty inputs, conflicting requirements, < 3 candidates for explorer), agent halts immediately with a structured BLOCKED report naming the condition, instead of proceeding.

### FR-6: Red Team Critique Loop — Architecture
- Given: Architect produces initial design.md
- When: Architecture critique phase runs
- Then: Critic finds exactly 10 weaknesses (numbered, with severity). Architect fixes and produces revised design. Second critic finds 10 NEW weaknesses (no repeats). Architect fixes and produces FINAL design. All 20 weaknesses logged with dispositions (FIXED/DEFERRED/ACKNOWLEDGED).

### FR-7: Red Team Critique Loop — Coding
- Given: Coder produces initial implementation
- When: Code critique phase runs
- Then: Same 3-iteration pattern as FR-6. Tests run after each revision. All 20 weaknesses logged.

### FR-8: Autonomous Agent Chaining
- Given: An agent completes its work
- When: Agent writes its OUTPUTS
- Then: OUTPUTS section names the NEXT agent. Orchestrator routes to that agent automatically. Four chains defined: Planning, Build, Validation, Error.

### FR-9: Coder Agent Enhancement
- Given: Coder receives a task
- When: Coder executes
- Then: Reads tests first (TDD), design second, specs third, lessons fourth. Implements incrementally (function → test → next). If design is flawed, produces DESIGN_ISSUE report instead of broken code, routing back to architect.

### FR-10: QA Agent Enhancement
- Given: QA receives a task
- When: QA writes tests
- Then: Produces risk profile (probability × impact), requirements trace (Given-When-Then from specs), coverage targets per risk level, NFR assessment.

### FR-11: Architect Agent Enhancement
- Given: Architect receives selected approach from solution-explorer
- When: Architect designs
- Then: Reads solutions.md for selected approach. Produces file-level design (files, functions, interfaces), explicit handoff contracts (input/output schemas), complexity estimates, parallelizable work identification, testable acceptance criteria.

### FR-12: Open Source First Technology Selection
- Given: Solution explorer, architect, or researcher selects technology
- When: Brief/PRD is silent on technology choice
- Then: Default to open-source. Free tier only if open-source insufficient. Paid only if ROI threshold met (free < 80% AND paid > 95%, or saves 100h+). If brief specifies paid service or "accuracy paramount", respect it and note expected costs.

### FR-13: Learning Engine Enhancement
- Given: An agent is about to execute
- When: Learning engine runs pre-task
- Then: Injects top-3 relevant lessons. Patterns seen 3+ times are promoted. Confidence decays over time unless reinforced. Cross-change learning within session.

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Constraint: All changes to agent files must preserve existing INPUT/OUTPUT/RULES content — only ADD new sections (ACTIVATION, PREREQUISITES, PERMISSIONS)
- Rationale: Existing agent behavior must not regress

### NFR-2: Context Window Efficiency
- Constraint: Activation headers should add < 20 lines per agent file. Context-manager strips non-relevant sections when building agent prompts.
- Rationale: Token budget is limited; every added line reduces available context for actual work

### NFR-3: No New Dependencies
- Constraint: No Python, no new CLI tools, no new npm packages. Everything remains markdown + existing Go CLI.
- Rationale: SUDD is markdown-first by design

## Consumer Handoffs

### Handoff 1: Solution Explorer → Architect
- Format: `changes/{id}/solutions.md` markdown file
- Schema: Candidates section with name/pattern/scores per candidate, Decision Matrix table, Selected candidate clearly marked, Trade-offs section
- Validation: Architect reads solutions.md and designs ONLY the selected approach

### Handoff 2: Architect → Decomposer
- Format: `changes/{id}/design.md` markdown file
- Schema: File-level design with components, interfaces, acceptance criteria
- Validation: Decomposer can extract task boundaries from design

### Handoff 3: Architect ↔ Critique Loop
- Format: design.md + critique report (in log.md)
- Schema: 10 numbered weaknesses with severity, dispositions for each
- Validation: Second critique produces 10 NEW weaknesses (no repeats from first)

### Handoff 4: Coder → DESIGN_ISSUE → Architect
- Format: DESIGN_ISSUE report in log.md
- Schema: Problem description, what was attempted, why design is flawed, suggested fix
- Validation: Architect receives and revises design.md

### Handoff 5: Learning Engine → All Agents
- Format: Top-3 lessons injected into agent context
- Schema: Lesson text + confidence level + relevance score
- Validation: Agent receives lessons before execution starts

### FR-14: Size-Aware Change Documentation
- Given: A new change is created (by task-discoverer, add-task, or decomposer)
- When: The change effort is estimated
- Then: Documentation depth scales with size:
  - S (< 1h): proposal.md (with persona reference + handoff line) + tasks.md (single checkbox)
  - M/L (1h+): Full suite — proposal.md + specs.md (with Consumer Handoffs) + design.md + tasks.md + log.md. Full planning chain including persona-detector, persona-researcher, antigravity.
- Then: tasks.md is always the single source of truth for completion tracking
- Then: Every change, regardless of size, must name its persona and what consumes its output. S-size references existing personas. M/L creates or updates persona files via the planning chain.

### FR-15: Task Discoverer v2 Integration
- Given: Task discoverer identifies work to be done
- When: It creates output
- Then: Creates `changes/active/{id}/proposal.md` (not `task-specs/{name}.md`). Estimates size (S/M/L). Creates documentation appropriate to size. Uses current paths (sudd/vision.md, sudd/changes/).

### FR-16: Completion Tracking for All Changes
- Given: Any change exists in `changes/active/{id}/`
- When: Work is completed on it
- Then: Tasks marked `[x]` in tasks.md (or in proposal.md for S-size changes). Archived to `changes/archive/{id}_DONE/`. Stats updated in state.json.

## Out of Scope
- New agents beyond decomposer and solution-explorer
- UI/TUI changes to the Go CLI
- Multi-agent concurrent execution
