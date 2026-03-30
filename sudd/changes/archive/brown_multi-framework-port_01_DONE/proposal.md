# Change: brown_multi-framework-port_01

## Status
proposed

## Summary
Rebuild `/sudd:port` to auto-detect and consume documentation from any of the 4 major development frameworks (OpenSpec, BMAD, Superpowers, Generic/PRD) found across the project portfolio, transforming their artifacts into SUDD's templating structure.

## Motivation
Real projects across the portfolio use 4 different documentation frameworks, each with distinct directory structures, spec formats, and workflow artifacts:

| Framework | Found In | Key Artifacts |
|-----------|----------|---------------|
| **OpenSpec** | 14+ projects | `openspec/project.md`, `openspec/specs/`, `openspec/changes/` |
| **BMAD** | 12+ projects | `.bmad-core/`, `docs/prd.md`, `docs/stories/`, `docs/epics/` |
| **Superpowers** | via skills | `.claude/skills/superpowers*/`, brainstorming, plans |
| **Generic/PRD** | 3+ projects | `PRD.md`, `tasklist.md`, `architecture_diagrams.md`, `CLAUDE.md` |

The current `/sudd:port` only handles OpenSpec and Superpowers with hardcoded mappings. It cannot handle BMAD at all, and doesn't detect generic PRD-style projects. When a developer runs `/sudd:port` in a BMAD project, nothing happens.

**The goal**: Run `/sudd:port` in ANY project and get a working SUDD setup with vision, specs, design, tasks, and personas — regardless of which framework produced the original documentation.

## Scope

### What's included:

#### 1. Framework Detection Engine
Auto-detect which framework(s) a project uses by checking for signature files/directories:

```
openspec/project.md          → OpenSpec
.bmad-core/                  → BMAD
.claude/skills/superpowers/  → Superpowers
PRD.md OR docs/prd.md        → Generic/PRD
AGENTS.md + reference/       → Superpowers (alt)
```

Projects may use MULTIPLE frameworks (e.g., consumer_insights_ai has both OpenSpec AND BMAD). Detection must list all found and let the user choose or merge.

#### 2. OpenSpec → SUDD Mapping (Enhanced)
```
openspec/project.md                → sudd/vision.md
openspec/specs/{domain}/spec.md    → sudd/specs/{domain}.md
openspec/changes/{id}/proposal.md  → sudd/changes/active/{id}/proposal.md
openspec/changes/{id}/tasks.md     → sudd/changes/active/{id}/tasks.md
openspec/changes/{id}/design.md    → sudd/changes/active/{id}/design.md
openspec/changes/{id}/specs/       → merged into sudd/changes/active/{id}/specs.md
openspec/AGENTS.md                 → sudd/memory/lessons.md (extract conventions)
```

Key transformation: OpenSpec delta specs (ADDED/MODIFIED/REMOVED format) need to be flattened into SUDD's requirement-list format.

#### 3. BMAD → SUDD Mapping (NEW)
```
docs/prd.md                        → sudd/vision.md (extract purpose, goals, personas)
                                   → sudd/personas/{persona}.md (extract user personas/ICP)
docs/architecture.md               → sudd/changes/active/{id}/design.md
docs/epics/{name}/epic.md          → sudd/changes/active/{epic}/proposal.md
docs/stories/{epic}/{story}/       → sudd/changes/active/{epic}/tasks.md (one task per story)
  story.md                         → task description
  ACCEPTANCE_CRITERIA.md           → success criteria in tasks.md
.bmad-core/data/technical-preferences.md → sudd/memory/lessons.md (coding preferences)
.bmad-core/checklists/             → sudd/agents/ (inform validation agents)
docs/qa/gates/                     → inform gate.md scoring criteria
```

Key transformation: BMAD's epic/story hierarchy needs to be flattened into SUDD's change/task structure. Each epic becomes a SUDD change, each story becomes a task.

#### 4. Generic/PRD → SUDD Mapping (NEW)
```
PRD.md                             → sudd/vision.md (extract purpose + goals)
                                   → sudd/personas/{persona}.md (extract user personas)
                                   → sudd/changes/active/{id}/specs.md (extract requirements)
architecture_diagrams.md           → sudd/changes/active/{id}/design.md
tasklist.md                        → sudd/changes/active/{id}/tasks.md
CLAUDE.md                         → sudd/memory/lessons.md (extract coding conventions)
```

Key transformation: Monolithic PRD needs to be decomposed into SUDD's separation of concerns (vision vs specs vs design vs tasks).

#### 5. Superpowers → SUDD Mapping (Enhanced)
Current mapping is adequate. Minor improvements:
- Extract plan files from `.claude/` into change proposals
- Extract brainstorming results into proposals

#### 6. Merge Strategy
When multiple frameworks are detected:
- Show what was found
- Ask: "Merge all into SUDD?" or "Pick one framework?"
- If merge: combine vision sections, concatenate specs, deduplicate tasks
- Track source in each artifact: `<!-- ported from: openspec -->` or `<!-- ported from: bmad -->`

#### 7. Persona Extraction
All frameworks contain persona/user information in different places:
- **BMAD**: `docs/prd.md` has User Personas/ICP sections
- **Generic**: `PRD.md` has Target Users section
- **OpenSpec**: Less explicit, inferred from project.md
- **SUDD's own**: `sudd/personas/default.md`

The port must extract real personas and create `sudd/personas/{name}.md` for each — not just use the generic Stefano fallback.

### What's NOT included:
- Reverse porting (SUDD → other frameworks)
- Live sync (one-time port only)
- Framework-specific validation (BMAD QA gates, OpenSpec strict mode)
- Automated conflict resolution on merge

## Success Criteria
- [ ] `/sudd:port` auto-detects OpenSpec, BMAD, Generic/PRD, and Superpowers
- [ ] `/sudd:port` works on a project with ONLY a PRD.md (no framework)
- [ ] `/sudd:port` works on a BMAD project (epic/story → change/task mapping)
- [ ] `/sudd:port` handles projects with MULTIPLE frameworks (merge or choose)
- [ ] Personas are extracted from source docs (not just fallback)
- [ ] OpenSpec delta specs (ADDED/MODIFIED/REMOVED) are flattened
- [ ] BMAD stories with acceptance criteria become SUDD tasks with success criteria
- [ ] Source framework is tagged in ported artifacts (`<!-- ported from: ... -->`)
- [ ] Original files are NEVER deleted (port creates copies)
- [ ] State.json is set to brown mode with imported_from field
- [ ] All ported artifacts score >= 95 on persona validation

## Dependencies
- Depends on `brown_framework-hardening_01` (completed — threshold/state changes)

## Risks
- **Lossy transformation**: Some framework-specific concepts don't map cleanly to SUDD. Mitigation: always note unmapped artifacts in log.md.
- **PRD decomposition is subjective**: Splitting a monolithic PRD into vision/specs/design requires interpretation. Mitigation: use explicit section headers as boundaries (## Goals → vision, ## Requirements → specs, ## Architecture → design).
- **BMAD epic/story nesting**: Deep hierarchies may not flatten cleanly. Mitigation: one epic = one change, stories = tasks within that change.
- **Persona extraction quality**: Personas in PRDs are often vague. Mitigation: extract what exists, flag for persona-researcher agent to enrich later.
