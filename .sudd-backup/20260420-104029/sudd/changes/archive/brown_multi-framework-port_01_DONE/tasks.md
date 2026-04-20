# Tasks: brown_multi-framework-port_01

## Implementation Tasks

- [x] T01: Rewrite port.md frontmatter and detection section
  - Files: sudd/commands/macro/port.md
  - Effort: S
  - Dependencies: none
  - Details: Update frontmatter description to mention all 4 frameworks. Rewrite DETECTION section with 4 framework checks, confidence levels, edge case handling (BMAD+PRD dedup), and multi-framework user prompt.

- [x] T02: Write OpenSpec mapper section (enhanced)
  - Files: sudd/commands/macro/port.md
  - Effort: M
  - Dependencies: T01
  - Details: Enhance existing OpenSpec section with delta spec flattening instructions (ADDED/MODIFIED/REMOVED → requirement list), AGENTS.md convention extraction, and source tagging on all artifacts.

- [x] T03: Write BMAD mapper section (new)
  - Files: sudd/commands/macro/port.md
  - Effort: L
  - Dependencies: T01
  - Details: New section covering: PRD decomposition (vision, personas, specs, design from section headers), epic→change mapping, story→task mapping with acceptance criteria, technical-preferences extraction, fallback when no epics/ dir exists (use stories/ or single change). Handle real portfolio structure (no docs/epics/ found — stories may be flat).

- [x] T04: Write Generic/PRD mapper section (new)
  - Files: sudd/commands/macro/port.md
  - Effort: M
  - Dependencies: T01
  - Details: New section covering: keyword-based section detection for decomposing monolithic PRD, tasklist.md mapping, architecture_diagrams.md mapping, CLAUDE.md convention extraction. Case-insensitive PRD detection. Ambiguous sections default to vision.md.

- [x] T05: Write Superpowers mapper section (enhanced)
  - Files: sudd/commands/macro/port.md
  - Effort: S
  - Dependencies: T01
  - Details: Enhance existing section with plan file extraction from .claude/ and brainstorming result extraction into proposals.

- [x] T06: Write merge strategy section
  - Files: sudd/commands/macro/port.md
  - Effort: M
  - Dependencies: T02, T03, T04, T05
  - Details: New section for multi-framework merge: vision concatenation, spec appending with source tags, task deduplication by similarity, persona merge by role name. Source tag format: `<!-- ported from: {framework} [{file}] -->`.

- [x] T07: Write persona extraction section
  - Files: sudd/commands/macro/port.md
  - Effort: M
  - Dependencies: T01
  - Details: Cross-framework persona extraction with per-framework lookup locations. Persona file template with role, goals, pain points, context. Merge logic for overlapping personas across frameworks.

- [x] T08: Write validation and output sections
  - Files: sudd/commands/macro/port.md
  - Effort: S
  - Dependencies: T06, T07
  - Details: Rewrite VALIDATION section to cover all 4 frameworks. Update output template with per-framework summary. Update GUARDRAILS with new rules (BMAD dedup, source tagging, persona extraction).

## Test Tasks

- [x] T09: Verify port.md is internally consistent
  - Files: sudd/commands/macro/port.md
  - Effort: S
  - Dependencies: T08
  - Details: Read final port.md end-to-end. Check: all 4 frameworks referenced in detection AND mapper sections, source tag format consistent, persona template consistent, no stale references to old 2-framework version.

## Documentation Tasks

- [x] T10: Update vision.md agent/command descriptions if needed
  - Files: sudd/vision.md
  - Effort: S
  - Dependencies: T08
  - Details: Check if port command description in vision.md needs updating for 4-framework support. Update if stale.

---
Total: 10 tasks | Est. effort: 1S+3M+1L (T01-T08 implementation) + 2S (verification/docs)
