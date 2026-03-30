# Phase 0 PoC Findings

**Date**: 2026-03-30
**browser-use version**: 0.12.5
**LLM**: google/gemini-2.5-flash via OpenRouter (using ChatLiteLLM)

---

## PoC-1: AgentHistoryList Structure

**Verdict: OUTCOME A — Deterministic parser feasible**

### What AgentHistoryList provides per step:

| Field | Available | Source |
|-------|-----------|--------|
| URL | YES | `step.state.url` |
| Page title | YES | `step.state.title` |
| Screenshot path | YES | `step.state.screenshot_path` (PNG files on disk) |
| Action taken | YES | `step.model_output.action[]` — structured dict with full params |
| Action result | YES | `step.result[].extracted_content` — human-readable summary |
| LLM reasoning | YES | `step.model_output.current_state.thinking` |
| LLM memory | YES | `step.model_output.current_state.memory` |
| LLM next goal | YES | `step.model_output.current_state.next_goal` |
| DOM element interacted | YES | `step.state.interacted_element` with tag, attrs, bounds |
| Per-step timing | YES | `step.metadata.duration_seconds` |
| Errors | YES | `step.result[].error` |
| Done/success flags | YES | `step.result[].is_done`, `step.result[].success` |

### V3 Schema Mapping

| v3 Field | Derivable | How |
|----------|-----------|-----|
| `pages[].url_visited` | YES | Group steps by `state.url` |
| `pages[].screenshot` | YES | `state.screenshot_path` per step |
| `pages[].observations.actions[]` | YES | `model_output.action[]` with params |
| `pages[].observations.description` | YES | From `current_state.thinking` + `next_goal` |
| `experience{}` | YES | From `final_result()` + `extracted_content()` |
| `elapsed_seconds` | YES | `total_duration_seconds()` |
| `manifest_coverage{}` | YES | Compare visited URLs against manifest |
| `network_log` | NO | Needs HAR file (PoC-2) |

### Environment Issues Found
- `langchain_openai` broken in this environment (torch/c10.dll). Used `ChatLiteLLM` instead.
- OpenRouter model ID is `google/gemini-2.5-flash` (not `gemini-2.5-flash-preview`).
- Python segfault during interpreter shutdown (Chromium cleanup) — cosmetic only.

---

## PoC-2: HAR Network Capture

**Verdict: FULLY FUNCTIONAL (with known CDP cookie limitation)**

### What HAR captures:

| Data | Captured | Notes |
|------|----------|-------|
| HTTP method | YES | GET, POST, etc. |
| URL | YES | Full URL with path |
| Status code | YES | 200, 201, 400, 401, 409, etc. |
| Timing (ms) | YES | Per-request duration |
| Request headers | YES | Content-Type, non-httpOnly cookies |
| Request body (POST) | YES | Full JSON body |
| Response headers | YES | Content-Type, but NOT Set-Cookie for httpOnly |
| Response body | MOSTLY | Captured for most requests; 201 POST may miss body due to navigation race |

### V3 network_log Mapping

| Check | Result |
|-------|--------|
| HAR file created | PASS |
| Contains entries | PASS |
| API calls captured | PASS |
| Method captured | PASS |
| URL captured | PASS |
| Status captured | PASS |
| Timing captured | PASS |
| Request body (POST) | PASS |
| Response body | PASS |
| Set-Cookie (httpOnly) | FAIL — CDP security boundary |
| Cookie header (httpOnly) | FAIL — CDP security boundary |

### Known Limitations

1. **httpOnly cookies**: Chrome CDP does not expose httpOnly cookies in Network.requestWillBeSent or Network.responseReceived events. **Workaround**: Use `CDP Network.getAllCookies()` after navigation to capture cookie state separately.

2. **HTTP-only filter**: The HAR watchdog silently drops HTTP (non-HTTPS) requests. For localhost testing, a monkey-patch is needed. Production HTTPS sites are unaffected.

3. **POST 201 response body race**: When a POST triggers page navigation (redirect to /dashboard), the async `getResponseBody` CDP call may not complete before the page unloads. Error responses (4xx) are captured fine since they don't trigger navigation.

### Implications for v3 Architecture

- `har_parser.py` can extract method, URL, status, timing, request body, response body from HAR
- Auth cookie verification needs a supplementary `CDP Network.getAllCookies()` call — add to `network_verifier.py`
- The HTTP filter is only relevant for local development; document in README

---

## Decision

**Phase 1 is cleared to proceed as designed.** Both critical assumptions are empirically validated:

1. AgentHistoryList → v3 JSON: deterministic `output_parser.py` is feasible (Outcome A)
2. HAR → network_log: `har_parser.py` is feasible; auth cookies need CDP supplementary call

### Adjustments to v3 architecture:

1. Add `CDP Network.getAllCookies()` call after each page navigation for httpOnly cookie capture
2. Use `ChatLiteLLM` (browser-use native) instead of `langchain_openai` for LLM creation
3. Model ID on OpenRouter: `google/gemini-2.5-flash` (not `-preview`)
4. For local dev/testing: document the HTTP HAR filter and monkey-patch
