# Specifications: brown_multi-framework-port_01

## Functional Requirements

### FR-1: Framework Detection Engine
- Given: A project directory with unknown documentation structure
- When: `/sudd:port` is invoked (no args or with `auto`)
- Then: Scan for signature files/dirs and report all detected frameworks:
  - `openspec/project.md` → OpenSpec
  - `.bmad-core/` → BMAD
  - `.claude/skills/superpowers/` OR (`AGENTS.md` + `reference/`) → Superpowers
  - `PRD.md` OR `docs/prd.md` (case-insensitive) → Generic/PRD
- Detection must find ALL frameworks present (projects may use multiple)

### FR-2: OpenSpec → SUDD Mapping (Enhanced)
- Given: A project with `openspec/` directory
- When: OpenSpec framework is selected for porting
- Then:
  - `openspec/project.md` → `sudd/vision.md`
  - `openspec/specs/{domain}/spec.md` → `sudd/specs/{domain}.md`
  - `openspec/changes/{id}/proposal.md` → `sudd/changes/active/{id}/proposal.md`
  - `openspec/changes/{id}/tasks.md` → `sudd/changes/active/{id}/tasks.md`
  - `openspec/changes/{id}/design.md` → `sudd/changes/active/{id}/design.md`
  - `openspec/changes/{id}/specs/` → merged into `sudd/changes/active/{id}/specs.md`
  - `openspec/AGENTS.md` → extract conventions into `sudd/memory/lessons.md`
  - Delta specs (ADDED/MODIFIED/REMOVED format) flattened into requirement-list format

### FR-3: BMAD → SUDD Mapping
- Given: A project with `.bmad-core/` directory
- When: BMAD framework is selected for porting
- Then:
  - `docs/prd.md` → `sudd/vision.md` (extract purpose, goals)
  - `docs/prd.md` → `sudd/personas/{persona}.md` (extract user personas/ICP sections)
  - `docs/architecture.md` → `sudd/changes/active/{epic}/design.md`
  - Each epic becomes a SUDD change: `docs/epics/{name}/` → `sudd/changes/active/{epic}/proposal.md`
  - Each story becomes a task: story.md → task entry, ACCEPTANCE_CRITERIA.md → success criteria
  - `.bmad-core/data/technical-preferences.md` → `sudd/memory/lessons.md`
  - `.bmad-core/checklists/` → inform validation agents (noted in lessons.md)
- If `docs/epics/` doesn't exist, scan `docs/stories/` directly and create a single change

### FR-4: Generic/PRD → SUDD Mapping
- Given: A project with `PRD.md` or `docs/prd.md` (no `.bmad-core/`)
- When: Generic/PRD framework is selected for porting
- Then:
  - PRD sections mapped by header keywords:
    - Goals/Vision/Overview → `sudd/vision.md`
    - Users/Personas/ICP → `sudd/personas/{persona}.md`
    - Requirements/Features → `sudd/changes/active/{id}/specs.md`
    - Architecture/Technical → `sudd/changes/active/{id}/design.md`
  - `tasklist.md` (if exists) → `sudd/changes/active/{id}/tasks.md`
  - `architecture_diagrams.md` (if exists) → append to design.md
  - `CLAUDE.md` → extract coding conventions into `sudd/memory/lessons.md`
  - If PRD has no clear section headers, treat entire document as vision.md

### FR-5: Superpowers → SUDD Mapping (Enhanced)
- Given: A project with Superpowers artifacts
- When: Superpowers framework is selected for porting
- Then:
  - Existing mapping preserved (AGENTS.md → vision, reference/ → lessons)
  - NEW: `.claude/` plan files → extract into change proposals
  - NEW: Brainstorming results → extract into proposals

### FR-6: Multi-Framework Merge
- Given: A project with 2+ detected frameworks
- When: User chooses "merge all"
- Then:
  - Vision sections combined (deduplicated)
  - Specs concatenated with source tags
  - Tasks deduplicated by similarity
  - Each artifact tagged: `<!-- ported from: {framework} -->`
  - Personas merged by name similarity (don't duplicate "Admin" from two sources)

### FR-7: Persona Extraction
- Given: Any framework with user/persona information
- When: Porting is performed
- Then:
  - Extract real personas from source docs
  - Create `sudd/personas/{name}.md` for each distinct persona
  - Use actual names/roles from source (not generic fallbacks)
  - If no personas found, create one from project context

## Non-Functional Requirements

### NFR-1: Non-Destructive
- Constraint: Original framework files are NEVER deleted or modified
- Rationale: Port creates copies only; user must be able to revert

### NFR-2: Idempotent
- Constraint: Running `/sudd:port` twice produces same result (overwrites SUDD artifacts, doesn't duplicate)
- Rationale: Users may need to re-port after updating source docs

### NFR-3: Source Traceability
- Constraint: Every ported artifact includes `<!-- ported from: {framework} [{source_file}] -->` comment
- Rationale: Enables debugging and manual review of transformation quality

### NFR-4: Graceful Degradation
- Constraint: Missing optional files (tasklist.md, architecture.md) produce warnings, not errors
- Rationale: Not all projects have complete documentation

## Consumer Handoffs

### Handoff 1: port.md → state.json
- Format: JSON
- Schema: `{ mode: "brown", imported_from: "{framework}", phase: "build" | "inception" }`
- Validation: Valid JSON, mode always "brown"

### Handoff 2: port.md → vision.md
- Format: Markdown
- Schema: Standard SUDD vision.md with `# Vision`, `## Purpose`, `## Goals` sections
- Validation: Non-empty, has at least `# Vision` header

### Handoff 3: port.md → personas/{name}.md
- Format: Markdown
- Schema: Standard SUDD persona with `# Persona: {Name}`, `## Role`, `## Goals`, `## Pain Points`
- Validation: At least one persona created

### Handoff 4: port.md → changes/active/{id}/
- Format: Markdown files (proposal.md, specs.md, design.md, tasks.md)
- Schema: Standard SUDD change artifacts
- Validation: At least proposal.md is non-empty

### Handoff 5: port.md → memory/lessons.md
- Format: Markdown
- Schema: Appended entries with `### [PORTED] {source}` header
- Validation: Source conventions preserved

## Out of Scope
- Reverse porting (SUDD → other frameworks)
- Live sync (one-time port only)
- Framework-specific validation (BMAD QA gates, OpenSpec strict mode)
- Automated conflict resolution on merge
- Porting from frameworks not in the 4 supported types
