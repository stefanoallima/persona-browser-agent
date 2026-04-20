# Specifications: brown_validation-rubrics_01

## Functional Requirements

### FR-1: Anchored Scoring Rubrics for Design Reviewer
- Given: design-reviewer evaluates a frontend file
- When: scoring any of the 7 domains (Typography, Color & Contrast, Spatial Design, Motion Design, Interaction Design, Responsive Design, UX Writing)
- Then: each domain is scored using a 5-level anchored rubric with concrete descriptors per level, not subjective judgment

### FR-2: Rubric Level Definitions
- Given: a 5-level rubric scale per domain
- When: the reviewer assigns a score
- Then: the score must fall within a defined band (0-20, 21-40, 41-60, 61-80, 81-100) and the reviewer must cite which level descriptors match, producing reproducible scores across runs

### FR-3: Persona Objective Definitions
- Given: a persona definition in `sudd/personas/*.md`
- When: the persona is used for validation
- Then: the persona file contains an `## Objectives` section with 3-5 concrete task-based goals the persona would accomplish using the platform (action-verb format, measurable completion)

### FR-4: Objective-Based UX Testing
- Given: ux-tester receives a persona with defined objectives
- When: testing the UI
- Then: the tester executes each objective as a test scenario, scoring completion success per objective, not just following spec-derived flows

### FR-5: Objective-Based Persona Validation
- Given: persona-validator receives a persona with defined objectives
- When: validating the output
- Then: the validator walks through each objective, reports per-objective pass/fail with evidence, and the overall score reflects objective completion rate

### FR-6: Single Frontend Worktree Constraint
- Given: worktree mode is enabled and a batch contains multiple frontend tasks
- When: dispatching tasks to worktrees
- Then: at most 1 frontend-touching worktree is active at any time; remaining frontend tasks are queued and run sequentially after the first completes and merges

### FR-7: Step Reordering — Contract Before Design Review
- Given: a task produces frontend files
- When: the validation chain runs
- Then: the order is: 3a (code) → 3b (contract-verifier) → 3b.5 (design-reviewer) → 3c (peer-reviewer) → 3d (handoff-validator)

## Non-Functional Requirements

### NFR-1: Rubric Reproducibility
- Constraint: Two runs of design-reviewer on identical code should produce scores within the same rubric band (±1 band maximum variance)
- Rationale: Eliminates W8 (scoring subjectivity) — the primary motivation for this change

### NFR-2: Objective Discoverability
- Constraint: Persona objectives must be written in action-verb format that can be directly converted to test steps without interpretation
- Rationale: Eliminates the gap between "what persona wants" and "what ux-tester tests"

### NFR-3: No Performance Regression
- Constraint: Frontend worktree serialization must not add overhead in sequential mode (default)
- Rationale: Only worktree opt-in mode is affected by the constraint

## API Contracts

### Interface: Rubric Score Output (design-reviewer)
- Input: frontend file paths, sudd.yaml design context
- Output per domain:
  ```
  #### {Domain}: {N}/100 — Level {1-5}: {level_name}
  Evidence:
  - {checklist_item}: {PASS/FAIL} — `{file}:{line}`
  Level justification: {which descriptors from the rubric matched}
  ```
- Errors: if no frontend files, output skip message

### Interface: Persona Objectives (personas/*.md)
- Format:
  ```markdown
  ## Objectives
  1. {Action verb} {specific task} — {measurable outcome}
  2. {Action verb} {specific task} — {measurable outcome}
  3. {Action verb} {specific task} — {measurable outcome}
  ```
- Constraint: 3-5 objectives per persona, each must be independently testable

### Interface: Objective Test Results (ux-tester)
- Output:
  ```markdown
  ### Objective Test Results
  | # | Objective | Steps Taken | Result | Evidence |
  |---|-----------|-------------|--------|----------|
  | 1 | {objective} | {what was done} | PASS/FAIL | {screenshot/output} |
  ```

### Interface: Objective Validation Results (persona-validator)
- Output:
  ```markdown
  ### Objective Walkthrough
  | # | Objective | As Consumer I... | Result | Evidence |
  |---|-----------|-------------------|--------|----------|
  | 1 | {objective} | {first-person narrative} | PASS/FAIL | {file:line or output} |

  Objectives passed: {N}/{total}
  Objective completion rate: {percentage}
  ```
- Constraint: if < 100% objectives pass, score CANNOT exceed 90 regardless of other factors

## Data Models

### Rubric Level
- level: integer (1-5)
- name: string (e.g., "Broken", "Weak", "Acceptable", "Strong", "Exemplary")
- score_range: string (e.g., "0-20")
- descriptors: string[] (3-5 concrete criteria that define this level)

### Persona Objective
- id: integer (1-5)
- action: string (verb phrase, e.g., "Retrieve prospecting information")
- target: string (what is acted on, e.g., "for target companies")
- measurable_outcome: string (how to verify completion)

## Consumer Handoffs

### Handoff 1: design-reviewer → coder (feedback loop)
- Format: markdown with rubric level citations
- Schema: per-domain score with level name, evidence citations in `file:line` format, specific fix instructions
- Validation: each violation must reference a rubric descriptor that was violated

### Handoff 2: persona objectives → ux-tester
- Format: objectives from personas/*.md
- Schema: action + target + measurable outcome per objective
- Validation: each objective must appear as a test row in the objective test results table

### Handoff 3: persona objectives → persona-validator
- Format: objectives from personas/*.md
- Schema: action + target + measurable outcome per objective
- Validation: each objective must appear in the objective walkthrough table with first-person narrative

### Handoff 4: context-manager → orchestrator (frontend worktree constraint)
- Format: worktree status table in log.md
- Schema: includes `frontend: yes/no` column
- Validation: at most 1 row with `frontend: yes` and status `active` at any time

## Out of Scope
- Visual regression / screenshot diffing tooling
- Runtime rendering validation (design-reviewer remains static code analysis)
- Automated rubric calibration across projects
- Persona objective auto-generation from codebase analysis
- Changing the 95/100 gate threshold
