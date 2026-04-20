# Design: brown_multi-framework-port_01

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  /sudd:port                      │
│                  (port.md)                        │
├─────────────────────────────────────────────────┤
│  STEP 1: DETECTION                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐ │
│  │ OpenSpec  │ │  BMAD    │ │ Generic  │ │Super│ │
│  │ Detector  │ │ Detector │ │ Detector │ │power│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬──┘ │
│       └─────────┬───┴───────────┴───────────┘    │
│                 ▼                                 │
│  STEP 2: USER CHOICE (if multiple)               │
│       ┌─────────────────────┐                    │
│       │ Pick one / Merge all│                    │
│       └─────────┬───────────┘                    │
│                 ▼                                 │
│  STEP 3: FRAMEWORK-SPECIFIC MAPPER               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐ │
│  │ OpenSpec  │ │  BMAD    │ │ Generic  │ │Super│ │
│  │ Mapper   │ │ Mapper   │ │ Mapper   │ │power│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬──┘ │
│       └─────────┬───┴───────────┴───────────┘    │
│                 ▼                                 │
│  STEP 4: MERGE (if multiple frameworks)          │
│       ┌─────────────────────┐                    │
│       │ Deduplicate & Tag   │                    │
│       └─────────┬───────────┘                    │
│                 ▼                                 │
│  STEP 5: PERSONA EXTRACTION                      │
│       ┌─────────────────────┐                    │
│       │ Extract from all    │                    │
│       │ sources → personas/ │                    │
│       └─────────┬───────────┘                    │
│                 ▼                                 │
│  STEP 6: FINALIZE                                │
│       ┌─────────────────────┐                    │
│       │ state.json + sync   │                    │
│       └─────────────────────┘                    │
└─────────────────────────────────────────────────┘
```

## Component: Detection Engine

### Responsibility
Scan the project root for signature files/directories that indicate which frameworks are present.

### Interface
Input: project root path (cwd)
Output: list of `{ framework: string, confidence: "definite" | "probable", evidence: string[] }`

### Detection Rules (ordered by specificity)
```
1. openspec/project.md exists           → OpenSpec (definite)
2. .bmad-core/ directory exists          → BMAD (definite)
3. .claude/skills/superpowers/ exists    → Superpowers (definite)
4. AGENTS.md + reference/ both exist     → Superpowers (probable)
5. PRD.md exists (case-insensitive)      → Generic/PRD (definite)
6. docs/prd.md exists                    → Generic/PRD (definite)
   BUT if .bmad-core/ also exists        → already counted as BMAD, skip Generic
```

### Edge Cases
- BMAD projects often have `docs/prd.md` — don't double-count as both BMAD and Generic
- Projects with BMAD + OpenSpec: both are valid, offer merge
- No framework detected: offer manual selection or abort

## Component: OpenSpec Mapper

### Responsibility
Transform OpenSpec artifacts into SUDD structure.

### Implementation Notes
- **Delta spec flattening**: OpenSpec uses `### ADDED`, `### MODIFIED`, `### REMOVED` sections in change specs. Flatten by:
  1. Start with current main spec content
  2. Apply ADDED items as new requirements
  3. Apply MODIFIED items as updated requirements
  4. Note REMOVED items as "out of scope"
- **Change ID preservation**: Keep original OpenSpec change IDs (e.g., `blue_api-v2_03`)
- **Task state preservation**: `[x]` tasks stay checked, `[ ]` tasks stay unchecked

## Component: BMAD Mapper

### Responsibility
Transform BMAD epic/story hierarchy into SUDD change/task structure.

### Implementation Notes
- **Epic → Change mapping**:
  - Each `docs/epics/{name}/` or `docs/stories/{epic}/` directory becomes one SUDD change
  - Change ID: `brown_port-{epic-name}_01`
  - Epic description → proposal.md
- **Story → Task mapping**:
  - Each story.md within an epic → one task entry in tasks.md
  - `ACCEPTANCE_CRITERIA.md` → success criteria bullets under task
  - Story status (if tracked) → task checkbox state
- **PRD decomposition**:
  - Scan `docs/prd.md` for section headers
  - `## Purpose` / `## Overview` / `## Goals` → vision.md
  - `## User Personas` / `## Target Users` / `## ICP` → personas/
  - `## Requirements` / `## Features` → specs.md
  - `## Architecture` / `## Technical` → design.md
- **Fallback**: If `docs/epics/` doesn't exist, create a single change from the PRD

### Edge Case: No epics directory
Portfolio scan confirmed: no `docs/epics/` directories exist in any BMAD project. Stories may exist at `docs/stories/` level. Handle:
1. If `docs/stories/` exists with subdirs → each subdir = one change
2. If `docs/stories/` exists flat → all stories = tasks in one change
3. If neither exists → single change from PRD content

## Component: Generic/PRD Mapper

### Responsibility
Decompose a monolithic PRD into SUDD's separation of concerns.

### Implementation Notes
- **Section detection**: Parse markdown headers (##, ###) and match keywords:
  ```
  vision_keywords = [overview, purpose, vision, goals, objectives, mission]
  persona_keywords = [persona, user, target, icp, audience, customer]
  spec_keywords = [requirement, feature, scope, functionality, capability]
  design_keywords = [architecture, technical, system, infrastructure, stack]
  task_keywords = [task, milestone, timeline, roadmap, phase, sprint]
  ```
- **Ambiguous sections**: If a section doesn't match any keyword, append to vision.md (safe default)
- **Case handling**: Both `PRD.md` and `prd.md` must be detected (case-insensitive glob)

## Component: Merge Engine

### Responsibility
Combine artifacts from multiple frameworks into unified SUDD structure.

### Implementation Notes
- **Vision merge**: Concatenate with framework headers, deduplicate identical sentences
- **Spec merge**: Append with source tags, no deduplication (specs are additive)
- **Task merge**: Check for similar task descriptions (>80% word overlap) and merge
- **Persona merge**: Match by role name (case-insensitive), merge attributes
- **Source tagging**: Every section gets `<!-- ported from: {framework} [{file}] -->`

## Component: Persona Extractor

### Responsibility
Extract persona information from any framework's documents and create SUDD persona files.

### Implementation Notes
- **BMAD**: Look for `## User Personas` or `## Ideal Customer Profile` in prd.md
- **Generic/PRD**: Look for `## Target Users` or `## Personas` in PRD.md
- **OpenSpec**: Infer from project.md context (less explicit)
- **Persona file template**:
  ```markdown
  # Persona: {Name}
  <!-- ported from: {framework} [{file}] -->

  ## Role
  {extracted role}

  ## Goals
  - {extracted goals}

  ## Pain Points
  - {extracted pain points}

  ## Context
  {additional context from source}
  ```

## Data Flow

```
Source Files ──read──▶ Detection ──list──▶ User Choice
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              Single Framework    Multiple Frameworks
                                    │                   │
                                    ▼                   ▼
                              Run Mapper          Run Each Mapper
                                    │                   │
                                    │              Merge Engine
                                    │                   │
                                    └─────────┬─────────┘
                                              ▼
                                      Persona Extractor
                                              │
                                              ▼
                                    Write SUDD Artifacts
                                              │
                                              ▼
                                    state.json + sync
```

## File Changes

### Modified Files
- `sudd/commands/macro/port.md` — complete rewrite with 4 framework support, merge strategy, persona extraction

### Files NOT Changed
- All other SUDD files remain unchanged
- This is a self-contained change to one command file

## Configuration
- No new config needed
- Existing `sudd/sudd.yaml` not affected
- Detection is fully automatic from file system
