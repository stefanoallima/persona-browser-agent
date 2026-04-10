---
name: sudd:done
description: Archive completed (or stuck) change
phase: complete
micro: true
prereq: sudd:gate (passed or stuck)
creates: archive entry, lessons learned
---

Archive the change. Update memory. Clean up.

**Input**:
- `/sudd:done` — archive active change
- `/sudd:done {change-id}` — archive specific change

---

## ORCHESTRATOR CHECK

## PHASE GUARD
Read sudd/state.json
If gate_passed != true AND retry_count < 8: STOP. "Run /sudd:gate first."

```bash
cat sudd/state.json
```

Check if gate passed or stuck:
- Passed: archive as DONE
- Stuck (retry >= 8): archive as STUCK
- Neither: "Gate not passed. Run `/sudd:gate` first."

---

## STEP 1: DETERMINE OUTCOME

Read final state:
- `sudd/changes/active/{id}/log.md` — execution history
- `sudd/state.json` — retry count

Outcome:
- `DONE` — gate passed, all consumers satisfied
- `STUCK` — max retries, couldn't pass gate
- `BLOCKED` — external dependency missing

---

## STEP 2: EXTRACT LESSONS

```
Dispatch(agent=learning-engine):

Read: sudd/changes/active/{id}/log.md
Read: All feedback from retries

Extract:
1. What worked well?
2. What didn't work?
3. Patterns to remember
4. Patterns to avoid

Write: sudd/memory/lessons.md
  ## {date}: {change-id}
  - Lesson 1
  - Lesson 2

If pattern seen 3+ times:
  Promote to sudd/memory/patterns.md
```

---

## STEP 3: ARCHIVE

### If DONE
```bash
mv sudd/changes/active/{id} sudd/changes/archive/{id}_DONE
```

Create summary: `sudd/changes/archive/{id}_DONE/SUMMARY.md`
```markdown
# Archive: {change-id}

## Outcome: DONE

## Summary
{1-2 sentences}

## Consumers Validated
- Consumer 1: score
- Consumer 2: score

## Files Changed
- path/to/file.py — description

## Lessons Learned
- Lesson 1
- Lesson 2

## Completed: {timestamp}
```

### If STUCK
```bash
mv sudd/changes/active/{id} sudd/changes/archive/{id}_STUCK
```

Create: `sudd/changes/archive/{id}_STUCK/STUCK.md`
```markdown
# Stuck: {change-id}

## Why Stuck
{reason from final feedback}

## All Feedback History
{accumulated feedback from all retries}

## What Was Tried
- Attempt 1: ...
- Attempt 2: ...

## Suggested Human Actions
- Action 1
- Action 2

## Files Partially Complete
- path/to/file.py — X% complete
```

Copy to: `sudd/memory/stuck-history/{id}.md`

### Rollback Generation (STUCK changes only)

Read `## Files Modified` from log.md and generate a rollback script.

Add a "## Rollback Command" section to STUCK.md with the following format:

    ## Rollback Command
    # Rollback for {change-id} (STUCK at task {last_task})
    git checkout main -- {file1} {file2} {file3}

Where {file1}, {file2}, etc. are every file listed under "## Files Modified"
in log.md.

Include this rollback section in the STUCK.md archive file so humans can
quickly undo partial work.

### Cost Summary (ALL changes — DONE or STUCK)

**Phase transition: complete → inception — valid**

Read `## Cost Log` from log.md (if present) and display a summary:

```
Cost Summary:
  Total retries: {retry_count}
  Escalation tier reached: {tier}
  Tasks completed: {N}
  Tasks remaining: {M} (STUCK only)
```

Include this in the OUTPUT section and in the archive SUMMARY.md / STUCK.md.

### Rollback Instructions
1. List all files modified during this change (from log.md)
2. Include command: `git checkout main -- {list of modified files}`
3. Note: Branch sudd/{change-id} is preserved for human review

---

## STEP 4: UPDATE STATE

Update `sudd/state.json`:
```json
{
  "active_change": null,
  "phase": "inception",
  "retry_count": 0,
  "stats": {
    "tasks_completed": N+1 or N,
    "tasks_stuck": M or M+1
  },
  "tests_passed": false,
  "gate_score": 0,
  "gate_passed": false,
  "last_command": "sudd:done"
}
```

### Discovery + Audit Counter Increment (v3.4)

After updating state.json, increment both change counters:

```
Read state.json → discovery.changes_since_last (default 0 if missing)
Write state.json → discovery.changes_since_last = previous + 1

Read state.json → audit.changes_since_last_audit (default 0 if missing)
Write state.json → audit.changes_since_last_audit = previous + 1
```

These feed the staleness checks:
- `/sudd:discover` triggers after `discovery.run_every_n_changes` (default 3)
- `/sudd:audit` triggers after `audit.auto_after_n_changes` (default 5)

**NOTE**: When running inside `sudd auto`, the Go binary handles these
increments automatically. Only update manually when running `/sudd:done`
standalone outside of the auto pipeline.

---

## STEP 5: GIT CLEANUP

```bash
git add sudd/
git commit -m "chore: archive {change-id} as {DONE|STUCK}"
git checkout main
git merge sudd/{change-id}
```

---

## OUTPUT

### DONE
```
Archived: {change-id} ✓

  Outcome: DONE
  Consumers: all validated (min: 98/100 EXEMPLARY)
  Lessons: 3 captured
  
  sudd/changes/archive/{id}_DONE/

Session stats updated.
Ready for next change. Run /sudd:new
```

### STUCK
```
Archived: {change-id} ⚠

  Outcome: STUCK
  Retries: 8
  Reason: {final blocker}
  
  Stuck history saved to: sudd/memory/stuck-history/
  
  Human action needed. See archive for details.
```

---

## GUARDRAILS

- Always extract lessons before archiving
- Preserve full history for stuck changes
- Update stats accurately
- Clean git state after archive
- Clear active_change in state
