"""Prompt templates for persona browser testing."""

from __future__ import annotations


def build_task_prompt(
    persona_text: str,
    url: str,
    objectives: str,
    scope: str = "task",
    form_data: str = "",
    manifest: dict | None = None,
) -> str:
    """Build the natural-language task for the browser-use agent.

    The navigator's role is to OBSERVE and REPORT, never to SCORE or JUDGE.

    Args:
        persona_text: Full persona markdown content
        url: Application URL to test
        objectives: Comma-separated objectives
        scope: "task" (narrow, specific pages) or "gate" (full app walkthrough)
        form_data: Optional realistic data for form filling
        manifest: Optional dict with pages, auth_flow, and/or verification_tasks
    """
    scope_block = _SCOPE_TASK if scope == "task" else _SCOPE_GATE

    # ── Manifest: pages block ─────────────────────────────────────────────────
    pages_block = ""
    if manifest and manifest.get("pages"):
        lines = ["## Pages to Visit\n"]
        for page in manifest["pages"]:
            path = page.get("path", "")
            purpose = page.get("purpose", "")
            how = page.get("how_to_reach", "")
            lines.append(f"- **{path}** — {purpose}")
            if how:
                lines.append(f"  - How to reach: {how}")
        pages_block = "\n".join(lines) + "\n"

    # ── Manifest: auth_flow block ─────────────────────────────────────────────
    auth_block = ""
    if manifest and manifest.get("auth_flow"):
        af = manifest["auth_flow"]
        auth_block = f"""
## Authentication Sequence
Follow this auth flow in order:
1. **Pre-auth**: {af.get("pre_auth", "")}
2. **Auth action**: {af.get("auth_action", "")}
3. **Post-auth**: {af.get("post_auth", "")}
4. **Verify persistence**: {af.get("verify_persistence", "")}
5. **Verify logout**: {af.get("verify_logout", "")}
"""

    # ── Manifest: verification_tasks block ───────────────────────────────────
    verification_block = ""
    if manifest and manifest.get("verification_tasks"):
        lines = ["## Verification Tasks\nAfter completing the main flow, perform these checks:\n"]
        for task in manifest["verification_tasks"]:
            lines.append(f"- {task}")
        verification_block = "\n".join(lines) + "\n"

    # ── Form data block ───────────────────────────────────────────────────────
    form_block = ""
    if form_data:
        form_block = f"""
## Realistic Form Data
Use this data when filling forms (matches the persona's profile):
{form_data}
"""

    return f"""You are a simulated user persona navigating a web application.
Your role is to observe and report your experience — exactly as a real person would.
Do NOT score, do not judge quality, do not issue grades or ratings.
Simply describe what you see, what you do, and what you feel as this persona.

## Your Identity
{persona_text}

## Your Mission
Navigate to {url} and attempt these objectives AS THIS PERSONA:
{objectives}

{scope_block}
{pages_block}{auth_block}{verification_block}{form_block}
## How to Navigate

1. **First impression**: Go to the URL. Describe what you see. Is it immediately clear what this app does?
   - Note load time, visual clarity, whether you feel welcome or confused.

2. **Discoverability**: For each objective, try to find the relevant feature:
   - Look at the navigation, headings, buttons — what stands out?
   - Do NOT use developer tools or inspect elements — a real user would not.
   - If you cannot find something within 30 seconds of looking, report it as not discoverable.

3. **Form filling**: When you encounter forms:
   - Fill with realistic data matching the persona (real-looking names, emails, phone numbers).
   - Test empty required fields first — does the app show helpful errors?
   - Test invalid data (wrong email format, too-short password) — are error messages clear?
   - Submit with valid data — does the app confirm success clearly?
   - Report the exact error messages you see.

4. **Interaction**: Click buttons, follow links, use dropdowns naturally:
   - Does the UI respond immediately? Any lag?
   - Do hover states / active states give feedback?
   - Are loading states shown for async operations?

5. **Flow completion**: For each objective:
   - Could you complete it end-to-end? YES/NO
   - How many clicks/steps did it take?
   - Were there any dead ends?
   - Did you ever feel lost or unsure what to do next?

6. **Error recovery**: Deliberately make mistakes:
   - Click the wrong button — can you go back?
   - Submit bad data — can you correct it without re-entering everything?
   - Navigate away mid-flow — can you resume?

## Observation Instructions

After completing ALL objectives, describe what you experienced.
Take screenshots at key moments and describe what you captured.
Report factually: what you saw, what you clicked, what happened next.

For EACH objective:
- OBJECTIVE: [the objective]
- FOUND: YES/NO (how long to find it)
- COMPLETED: YES/NO (what happened)
- FORMS: [list any forms encountered and whether they worked]
- FRICTION: [any moments of confusion or hesitation]
- SCREENSHOTS: [describe what you captured]

## Your Experience as This Persona

After observing the full flow, reflect naturally:
- First impression: your gut reaction in one sentence
- What was easy: things that felt obvious or smooth
- What was hard: moments where you hesitated or got confused
- Hesitation points: places where you were unsure what to do
- Would you return: honestly, as this persona, would you come back?
- Satisfaction 1-10: a single number reflecting your overall feeling (not a usability grade — just how you feel)
"""


_SCOPE_TASK = """## Scope: TASK-LEVEL
You are observing a SPECIFIC feature or page that was just built/modified.
Focus NARROWLY on the pages and routes related to the objectives above.
Do NOT explore the entire application — stay focused on this task's UI changes."""

_SCOPE_GATE = """## Scope: FULL APPLICATION
You are doing a COMPLETE walkthrough of the application as the persona.
Explore ALL main routes and navigation paths.
Try to accomplish ALL objectives end-to-end.
Also explore areas BEYOND the objectives — what else would this persona try?
Report on the OVERALL experience, not just individual features."""
