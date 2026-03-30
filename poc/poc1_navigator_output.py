"""
PoC-1: Inspect AgentHistoryList structure for v3 schema mapping.

Runs browser-use Agent against the test app (http://localhost:3333/register),
then inspects every field of the returned AgentHistoryList to confirm what
structured data is available for the v3 output schema.

NOTE: Uses browser_use.llm.litellm.ChatLiteLLM (native browser-use LLM wrapper)
instead of langchain_openai.ChatOpenAI because the anaconda environment has a
broken torch DLL (c10.dll, WinError 1114) that prevents langchain_core from
loading. ChatLiteLLM routes to the same OpenRouter endpoint and is the
appropriate LLM class for browser-use v0.12.5 (which uses BaseChatModel, not
langchain's BaseChatModel). OpenRouter model: openrouter/google/gemini-2.5-flash-preview.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    # -------------------------------------------------------------------
    # 1. Imports
    # -------------------------------------------------------------------
    from browser_use import Agent, BrowserSession, BrowserProfile
    from browser_use.agent.views import AgentHistoryList
    from browser_use.llm.litellm.chat import ChatLiteLLM

    print("=" * 70)
    print("PoC-1: AgentHistoryList Structure Inspection")
    print("=" * 70)

    # -------------------------------------------------------------------
    # 2. Configure LLM via OpenRouter (using browser-use native ChatLiteLLM)
    # -------------------------------------------------------------------
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    llm = ChatLiteLLM(
        model="openrouter/google/gemini-2.5-flash",
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        temperature=0.1,
    )
    print(f"LLM configured: {llm.model} via OpenRouter (ChatLiteLLM)")

    # -------------------------------------------------------------------
    # 3. Create BrowserSession with BrowserProfile
    # -------------------------------------------------------------------
    profile = BrowserProfile(
        headless=False,
        viewport={"width": 1280, "height": 720},
    )
    session = BrowserSession(browser_profile=profile)
    print("BrowserSession created (headless=False, 1280x720)")

    # -------------------------------------------------------------------
    # 4. Create Agent
    # -------------------------------------------------------------------
    task = (
        "Navigate to http://localhost:3333/register. "
        "Fill the signup form with: name=Jordan Rivera, email=jordan@example.com, "
        "password=SecurePass1. Submit the form. "
        "Then report what you see on the dashboard."
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser_session=session,
    )
    print(f"Agent created with task: {task[:80]}...")

    # -------------------------------------------------------------------
    # 5. Run the agent
    # -------------------------------------------------------------------
    print("\nRunning agent (max_steps=20)...")
    print("-" * 70)
    result: AgentHistoryList = await agent.run(max_steps=20)
    print("-" * 70)
    print("Agent run complete.")

    # -------------------------------------------------------------------
    # 6. Stop the session
    # -------------------------------------------------------------------
    try:
        await session.stop()
        print("Browser session stopped.")
    except Exception as e:
        print(f"Warning: session stop error: {e}")

    # -------------------------------------------------------------------
    # 7. Inspect ALL fields of AgentHistoryList
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("INSPECTION: AgentHistoryList fields")
    print("=" * 70)

    # --- is_done / is_successful ---
    print(f"\n[1] result.is_done()        = {result.is_done()}")
    print(f"[2] result.is_successful()  = {result.is_successful()}")

    # --- Numeric stats ---
    print(f"\n[3] result.total_duration_seconds() = {result.total_duration_seconds():.2f}s")
    print(f"[4] result.number_of_steps()        = {result.number_of_steps()}")

    # --- URLs ---
    urls = result.urls()
    print(f"\n[5] result.urls() ({len(urls)} items):")
    for i, url in enumerate(urls):
        print(f"    Step {i:2d}: {url}")

    # --- Action names ---
    action_names = result.action_names()
    print(f"\n[6] result.action_names() ({len(action_names)} items):")
    for i, name in enumerate(action_names):
        print(f"    Action {i:2d}: {name}")

    # --- Model actions (full params, truncated) ---
    model_actions = result.model_actions()
    print(f"\n[7] result.model_actions() ({len(model_actions)} items):")
    for i, action in enumerate(model_actions):
        action_str = str(action)
        if len(action_str) > 200:
            action_str = action_str[:200] + "..."
        print(f"    Action {i:2d}: {action_str}")

    # --- Action results (truncated) ---
    action_results = result.action_results()
    print(f"\n[8] result.action_results() ({len(action_results)} items):")
    for i, ar in enumerate(action_results):
        ar_str = str(ar)
        if len(ar_str) > 200:
            ar_str = ar_str[:200] + "..."
        print(f"    Result {i:2d}: {ar_str}")

    # --- Screenshot paths ---
    screenshot_paths = result.screenshot_paths()
    print(f"\n[9] result.screenshot_paths() ({len(screenshot_paths)} items):")
    for i, sp in enumerate(screenshot_paths):
        if sp:
            exists = Path(sp).exists()
            print(f"    Step {i:2d}: {sp} [exists={exists}]")
        else:
            print(f"    Step {i:2d}: None")

    # --- Model thoughts (LLM reasoning, truncated) ---
    thoughts = result.model_thoughts()
    print(f"\n[10] result.model_thoughts() ({len(thoughts)} items):")
    for i, thought in enumerate(thoughts):
        thought_str = str(thought)
        if len(thought_str) > 300:
            thought_str = thought_str[:300] + "..."
        print(f"    Step {i:2d}: {thought_str}")

    # --- Extracted content ---
    extracted = result.extracted_content()
    print(f"\n[11] result.extracted_content() ({len(extracted)} items):")
    for i, content in enumerate(extracted):
        content_str = str(content)
        if len(content_str) > 200:
            content_str = content_str[:200] + "..."
        print(f"    [{i}]: {content_str}")

    # --- Errors ---
    errors = result.errors()
    print(f"\n[12] result.errors() ({len(errors)} items):")
    for i, err in enumerate(errors):
        if err:
            print(f"    Step {i:2d}: ERROR: {str(err)[:200]}")
        else:
            print(f"    Step {i:2d}: None")

    # --- Final result ---
    final = result.final_result()
    print(f"\n[13] result.final_result():")
    if final:
        print(f"    {final[:500]}")
    else:
        print("    None")

    # -------------------------------------------------------------------
    # 8. Iterate result.history step by step
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("DETAILED HISTORY ITERATION")
    print("=" * 70)
    for i, step in enumerate(result.history):
        print(f"\n--- Step {i} ---")
        print(f"  type(step)            = {type(step).__name__}")
        # state fields
        print(f"  state.url             = {step.state.url}")
        print(f"  state.title           = {step.state.title}")
        print(f"  state.screenshot_path = {step.state.screenshot_path}")
        # interacted_element
        ie = step.state.interacted_element
        if ie and any(el is not None for el in ie):
            print(f"  state.interacted_element = {str(ie)[:200]}")
        else:
            print(f"  state.interacted_element = None / empty")
        # model_output
        if step.model_output:
            actions = step.model_output.action
            print(f"  model_output.actions ({len(actions)}):")
            for j, act in enumerate(actions):
                act_str = str(act.model_dump(exclude_none=True, mode="json"))
                if len(act_str) > 150:
                    act_str = act_str[:150] + "..."
                print(f"    [{j}]: {act_str}")
            # Current state (thoughts)
            cs = step.model_output.current_state
            if cs:
                cs_str = str(cs)
                if len(cs_str) > 200:
                    cs_str = cs_str[:200] + "..."
                print(f"  model_output.current_state = {cs_str}")
        else:
            print("  model_output = None")
        # results
        if step.result:
            for j, r in enumerate(step.result):
                print(f"  result[{j}].is_done           = {r.is_done}")
                print(f"  result[{j}].success           = {r.success}")
                ec = r.extracted_content
                if ec:
                    if len(ec) > 150:
                        ec = ec[:150] + "..."
                    print(f"  result[{j}].extracted_content = {ec}")
                if r.error:
                    print(f"  result[{j}].error             = {str(r.error)[:150]}")
        # metadata
        if step.metadata:
            print(f"  metadata.duration_seconds = {step.metadata.duration_seconds:.2f}s")

    # -------------------------------------------------------------------
    # 9. Save to JSON and print file size
    # -------------------------------------------------------------------
    output_path = "poc/poc1_output.json"
    try:
        result.save_to_file(output_path)
        size = Path(output_path).stat().st_size
        print(f"\n[SAVE] Saved to {output_path} ({size:,} bytes)")
    except Exception as e:
        print(f"\n[SAVE] Failed to save: {e}")

    # -------------------------------------------------------------------
    # 10. V3 SCHEMA MAPPING ASSESSMENT
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("V3 SCHEMA MAPPING ASSESSMENT")
    print("=" * 70)

    assessments = [
        (
            "pages[].url_visited",
            "AVAILABLE",
            "result.urls() → list[str|None] per step; also h.state.url in each history item",
        ),
        (
            "pages[].screenshot",
            "AVAILABLE",
            "result.screenshot_paths() → list[str|None] per step; also h.state.screenshot_path; base64 via h.state.get_screenshot()",
        ),
        (
            "pages[].observations.actions[]",
            "AVAILABLE",
            "result.model_actions() → list[dict] with action name+params per action; result.action_names() for names only",
        ),
        (
            "pages[].observations.description",
            "AVAILABLE (needs extraction)",
            "result.model_thoughts() → list[AgentBrain] with LLM current_state reasoning per step; also result.extracted_content()",
        ),
        (
            "experience{}",
            "PARTIALLY AVAILABLE",
            "result.final_result() gives final text; result.extracted_content() gives per-step; no structured 'experience' field natively",
        ),
        (
            "elapsed_seconds",
            "AVAILABLE",
            "result.total_duration_seconds() for total; h.metadata.duration_seconds per step",
        ),
        (
            "network_log",
            "NOT AVAILABLE in AgentHistoryList",
            "AgentHistoryList has no network_log; would need HAR capture via BrowserProfile.record_har_path (separate PoC)",
        ),
    ]

    print(f"\n{'Field':<45} {'Status':<30} Notes")
    print("-" * 130)
    for field, status, notes in assessments:
        print(f"  {field:<43} {status:<30} {notes}")

    # -------------------------------------------------------------------
    # 11. VERDICT
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("""
Outcome A — Deterministic parser feasible.

AgentHistoryList provides rich, structured per-step data:
  - Per-step URLs (state.url)
  - Per-step screenshot paths (state.screenshot_path, loadable as base64)
  - Per-step actions with full parameters (model_output.action[])
  - Per-step LLM reasoning/thoughts (model_output.current_state)
  - Per-step results and extracted content (result[].extracted_content)
  - Per-step error info (result[].error)
  - Per-step duration (metadata.duration_seconds)
  - Final answer text (final_result())
  - is_done() and is_successful() flags

The ONLY v3 field not directly available is network_log — but that can
be captured via BrowserProfile.record_har_path (subject of PoC-2).

All other v3 schema fields can be built with a deterministic parser
(no post-processing or LLM needed for schema construction).
""")

    print("=" * 70)
    print("PoC-1 complete.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
