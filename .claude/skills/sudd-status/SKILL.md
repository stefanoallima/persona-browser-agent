---
name: "sudd-status"
description: "Show SUDD state and progress. Use when the user wants to check status."
license: MIT
metadata:
  author: sudd
  version: "3.3"
---

Show current SUDD state, active work, and session statistics.

**Input**:
- `/sudd:status` — full status report
- `/sudd:status brief` — one-line summary

---

## DISPLAY

```
═══════════════════════════════════════════════════════════
  SUDD STATUS
═══════════════════════════════════════════════════════════

  Mode: green | brown
  Autonomy: full | interactive
  Phase: inception | planning | build | validate | complete

  ───────────────────────────────────────────────────────
  ACTIVE CHANGE
  ───────────────────────────────────────────────────────

  ID: green_auth_01
  Phase: build
  Retry: 2/8

  Progress:
    ✓ proposal.md
    ✓ specs.md
    ✓ design.md
    ✓ tasks.md (4/7 complete)
    ○ log.md

  Tasks:
    ✓ T1: Setup schema
    ✓ T2: Create models
    ✓ T3: Implement API
    ✓ T4: Add validation
    ○ T5: Write tests
    ○ T6: Integration
    ○ T7: Documentation

  ───────────────────────────────────────────────────────
  SESSION STATS
  ───────────────────────────────────────────────────────

  Completed: 5
  Stuck: 1
  Blocked: 0
  Total retries: 12

  ───────────────────────────────────────────────────────
  AVAILABLE CHANGES
  ───────────────────────────────────────────────────────

  Active:
    • green_auth_01 (current)

  Archive:
    • green_dashboard_01_DONE
    • brown_api-v2_01_DONE
    • fix_login_01_STUCK

═══════════════════════════════════════════════════════════
```

---

## BRIEF FORMAT

```
SUDD: green | build | green_auth_01 (4/7 tasks) | retries: 2/8
```

---

## LOGIC

1. Read `sudd/state.json`
2. If active_change, read its files
3. Count task completion
4. List archive directory
5. Format output
