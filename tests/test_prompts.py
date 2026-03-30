"""TDD tests for persona_browser/prompts.py — observation-only, manifest-aware."""

import pytest
from persona_browser.prompts import build_task_prompt


PERSONA = "You are Alex, a 32-year-old product manager who uses web apps daily."
URL = "https://example.com"
OBJECTIVES = "Sign up for an account, explore the dashboard"


# ── Basics ──────────────────────────────────────────────────────────────────

def test_prompt_contains_persona():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert PERSONA in prompt


def test_prompt_contains_url():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert URL in prompt


def test_prompt_contains_objectives():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert OBJECTIVES in prompt


# ── Scoring language MUST NOT appear ────────────────────────────────────────

def test_prompt_no_usability_score():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert "USABILITY_SCORE" not in prompt


def test_prompt_no_top_issues():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert "TOP_ISSUES" not in prompt


def test_prompt_no_would_recommend():
    """WOULD_RECOMMEND as an instruction must not appear."""
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    assert "WOULD_RECOMMEND" not in prompt


def test_prompt_no_scoring_language():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    forbidden = ["rubric", "grade against", "score against criteria", "rate the quality"]
    for term in forbidden:
        assert term.lower() not in prompt.lower(), f"Forbidden term found: {term!r}"


# ── Observation language MUST appear ────────────────────────────────────────

def test_prompt_has_observation_instructions():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    lower = prompt.lower()
    assert "observe" in lower or "describe what you see" in lower


def test_prompt_has_no_score_instruction():
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES)
    lower = prompt.lower()
    assert "do not score" in lower or "do not judge quality" in lower


# ── Manifest: pages ─────────────────────────────────────────────────────────

def test_prompt_manifest_pages_included():
    manifest = {
        "pages": [
            {"path": "/dashboard", "purpose": "Main overview", "how_to_reach": "Click Dashboard link"},
            {"path": "/settings", "purpose": "Account configuration", "how_to_reach": "Top-right menu"},
        ]
    }
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES, manifest=manifest)
    assert "Main overview" in prompt
    assert "Account configuration" in prompt


# ── Manifest: auth_flow ──────────────────────────────────────────────────────

def test_prompt_auth_flow_included():
    manifest = {
        "auth_flow": {
            "pre_auth": "Visit /login",
            "auth_action": "Submit credentials",
            "post_auth": "Redirected to /dashboard",
            "verify_persistence": "Refresh page, still logged in",
            "verify_logout": "Click logout, redirected to /login",
        }
    }
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES, manifest=manifest)
    lower = prompt.lower()
    assert "auth" in lower or "login" in lower or "log in" in lower


# ── Manifest: verification_tasks ────────────────────────────────────────────

def test_prompt_verification_tasks_included():
    manifest = {
        "verification_tasks": [
            "Refresh the page and confirm data persists",
            "Check that the user profile shows correct information",
        ]
    }
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES, manifest=manifest)
    assert "Refresh the page and confirm data persists" in prompt


# ── Form data ────────────────────────────────────────────────────────────────

def test_prompt_form_data_included():
    form_data = "Name: Alex Johnson\nEmail: alex@example.com\nPassword: S3cur3Pass!"
    prompt = build_task_prompt(PERSONA, URL, OBJECTIVES, form_data=form_data)
    assert form_data in prompt
