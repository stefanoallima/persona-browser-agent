"""Prompt templates for persona browser testing."""


def build_task_prompt(
    persona_text: str,
    url: str,
    objectives: str,
    scope: str = "task",
    form_data: str = "",
) -> str:
    """Build the natural-language task for the browser-use agent.

    Args:
        persona_text: Full persona markdown content
        url: Application URL to test
        objectives: Comma-separated objectives
        scope: "task" (narrow, specific pages) or "gate" (full app walkthrough)
        form_data: Optional realistic data for form filling
    """
    scope_block = _SCOPE_TASK if scope == "task" else _SCOPE_GATE

    form_block = ""
    if form_data:
        form_block = f"""
## Realistic Form Data
Use this data when filling forms (matches the persona's profile):
{form_data}
"""

    return f"""You are a simulated user persona testing a web application.
Your job is to navigate the app naturally — as a REAL person would — and report what you experience.

## Your Identity
{persona_text}

## Your Mission
Navigate to {url} and attempt these objectives AS THIS PERSONA:
{objectives}

{scope_block}
{form_block}
## How to Navigate

1. **FIRST IMPRESSION**: Go to the URL. What do you see? Is it immediately clear what this app does?
   - Note: load time, visual clarity, whether you feel welcome or confused

2. **DISCOVERABILITY**: For each objective, try to find the relevant feature:
   - Look at the navigation, headings, buttons — what stands out?
   - Do NOT use developer tools or inspect elements — a real user wouldn't
   - If you can't find something within 30 seconds of looking, report it as NOT DISCOVERABLE

3. **FORM FILLING**: When you encounter forms:
   - Fill with REALISTIC data matching the persona (real-looking names, emails, phone numbers)
   - Test with EMPTY required fields first — does the app show helpful errors?
   - Test with INVALID data (wrong email format, too-short password) — are error messages clear?
   - Submit with VALID data — does the app confirm success clearly?
   - Report the EXACT error messages you see

4. **INTERACTION**: Click buttons, follow links, use dropdowns naturally:
   - Does the UI respond immediately? Any lag?
   - Do hover states / active states give feedback?
   - Are loading states shown for async operations?

5. **FLOW COMPLETION**: For each objective:
   - Could you complete it end-to-end? YES/NO
   - How many clicks/steps did it take?
   - Were there any dead ends?
   - Did you ever feel lost or unsure what to do next?

6. **ERROR RECOVERY**: Deliberately make mistakes:
   - Click the wrong button — can you go back?
   - Submit bad data — can you correct it without re-entering everything?
   - Navigate away mid-flow — can you resume?

## Reporting Instructions

After completing ALL objectives, provide a structured summary:

For EACH objective:
- OBJECTIVE: [the objective]
- FOUND: YES/NO (how long to find it)
- COMPLETED: YES/NO (what happened)
- FORMS: [list any forms encountered and whether they worked]
- FRICTION: [any moments of confusion or frustration]
- SCREENSHOTS: [describe what you captured]

OVERALL:
- FIRST_IMPRESSION: [1 sentence gut reaction]
- USABILITY_SCORE: 1-10 (1=unusable, 10=delightful)
- TOP_ISSUES: [numbered list of problems, most severe first]
- WOULD_RECOMMEND: YES/NO/MAYBE
- HONEST_REACTION: [1 sentence raw honest opinion as this persona]
"""


_SCOPE_TASK = """
## Scope: TASK-LEVEL
You are testing a SPECIFIC feature or page that was just built/modified.
Focus NARROWLY on the pages and routes related to the objectives above.
Do NOT explore the entire application — stay focused on this task's UI changes."""

_SCOPE_GATE = """
## Scope: FULL APPLICATION
You are doing a COMPLETE walkthrough of the application as the persona.
Explore ALL main routes and navigation paths.
Try to accomplish ALL objectives end-to-end.
Also explore areas BEYOND the objectives — what else would this persona try?
Report on the OVERALL experience, not just individual features."""
