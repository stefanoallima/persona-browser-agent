# Vision: SUDD — Simulated User-Driven Development

## Purpose

SUDD ensures code is only "Done" when validated from the **actual user's perspective** — not just "does it compile" but "does it deliver value."

## How It Works

```
SUDD = Planning + Persona Validation + Agent Orchestration + Learning

Planning:          proposals, specs, design, tasks
Persona Validation: impersonate real users, score value
Agent Orchestration: 20 specialized agents, handoff validation
Learning:          lessons, patterns, stuck-history
```

### The Loop

```
1. Pick or create task
2. Route to agents via markdown instructions
3. Agents read context, produce output
4. Handoff validation at EVERY boundary
5. Persona validates: "Does this serve the actual user?"
6. If NO → retry with feedback, escalate model tier
7. If YES → commit, archive, learn, next task
```

### What Makes SUDD Different

Other frameworks ask: "Does it work?"
SUDD asks: "Does it create VALUE for who will use it?"

Example:
- API endpoints work, tests pass → BUT API returns empty data → Frontend useless
- Dashboard renders, UI loads → BUT no insights → Executive can't decide

SUDD catches this by impersonating the actual user before declaring "done."

## Modes

| Mode | Input | Behavior |
|------|-------|----------|
| **green** | Vision/idea only | Extensive research, create everything from scratch |
| **brown** | Existing specs/code | Continue where left off, light discovery |

## Architecture: Markdown-First

**No Python orchestrators.** Everything is markdown + CLI agent.

| Concern | Location |
|---------|----------|
| Vision | `sudd/vision.md` |
| State | `sudd/state.json` |
| Agent instructions | `sudd/agents/*.md` |
| Change proposals | `sudd/changes/active/{id}/` |
| Personas | `sudd/personas/*.md` |
| Memory/Learning | `sudd/memory/` |
| Commands | `sudd/commands/` (synced to CLI folders) |

## Agent Roles

| Role | Purpose | Phase |
|------|---------|-------|
| researcher | Investigate technologies, patterns | Planning |
| persona-detector | Discover WHO consumes output | Planning |
| persona-researcher | Deep-research each consumer | Planning |
| antigravity | Back-plan from outcome | Planning |
| solution-explorer | Explore solution approaches | Planning |
| decomposer | Break work into tasks | Planning |
| deep-think | Vision alignment | Planning |
| architect | Design solutions | Planning |
| qa | Write tests (TDD) | Build |
| coder | Write implementation | Build |
| contract-verifier | Verify code matches specs | Build |
| handoff-validator | Validate every handoff | Build |
| peer-reviewer | Independent code review | Build |
| persona-validator | THE gate — impersonate user | Validate |
| ux-tester | Browser-based UI testing | Validate |
| blocker-detector | Classify errors | System |
| task-discoverer | Generate new tasks | System |
| learning-engine | Capture lessons | System |
| monitor | Session health | System |
| context-manager | Context window management | System |

## Escalation Ladder

When a task fails persona validation:

```
Retry 0-1: Free/Cheap (GLM, opencode)  — handles 70%
Retry 2-3: + Sonnet for validation
Retry 4-5: Sonnet for all
Retry 6-7: Opus for all
After 8:   STUCK → log for human, move on
```

## Conventions

- All agent communication via markdown
- Change proposals define WHAT to build
- Personas define WHO we're building for
- Handoff contracts define HOW outputs connect
- Memory compounds across tasks
- Autonomous by default, ask only for scope changes
