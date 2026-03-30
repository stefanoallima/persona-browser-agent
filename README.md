# Persona Browser Agent

AI-driven browser testing as simulated personas. The AI navigates your web app like a real user — finding features, filling forms, and reporting friction — so you catch UX issues before humans do.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Persona Browser Agent (self-hosted)        │
│                                             │
│  ┌──────────┐    ┌────────────────────┐    │
│  │ browser- │    │ Playwright         │    │
│  │ use      │───▶│ (local browser)    │    │
│  │ (agent)  │    └────────────────────┘    │
│  └────┬─────┘                              │
│       │ LLM API calls                      │
│       ▼                                    │
│  ┌──────────────────────────────┐           │
│  │ Gemini Flash via OpenRouter  │  ◄── low  │
│  │ (multimodal vision LLM)     │     cost   │
│  └──────────────────────────────┘           │
└─────────────────────────────────────────────┘
```

- **Browser**: Runs locally via Playwright (zero cost)
- **LLM Brain**: Gemini Flash via OpenRouter (multimodal vision — understands UI layouts, screenshots, visual elements)
- **Configurable**: Swap to Z.AI GLM, OpenAI, or any OpenAI-compatible endpoint

## Setup

```bash
# Install
cd persona-browser-agent
pip install -e .

# Set your OpenRouter API key
export OPENROUTER_API_KEY="your-key-here"

# Install Playwright browsers (first time only)
playwright install chromium
```

## Usage

### CLI
```bash
# Basic test
persona-test \
  --persona path/to/persona.md \
  --url http://localhost:3000 \
  --objectives "find signup form, fill with realistic data, submit"

# Full gate-level walkthrough with output file
persona-test \
  --persona path/to/persona.md \
  --url http://localhost:3000 \
  --objectives "register account, create project, invite team member" \
  --scope gate \
  --output report.json \
  --screenshots-dir ./screenshots/
```

### Python API
```python
from persona_browser.agent import run_sync

report = run_sync(
    persona_path="persona.md",
    url="http://localhost:3000",
    objectives="find signup, fill form, submit",
    scope="task",
)
print(report["status"])  # DONE, ERROR, or SKIP
print(report["agent_result"])  # What the persona experienced
```

### From SUDD
```bash
# Per-task (step 3i)
python -m persona_browser.cli \
  --persona tasks/T01/micro-persona.md \
  --url http://localhost:3000 \
  --objectives "create new item, edit item, delete item" \
  --scope task --task-id T01 \
  --config sudd/sudd.yaml \
  --output tasks/T01/browser-use-report.json

# Gate-level (step 6c)
python -m persona_browser.cli \
  --persona changes/active/green_auth_01/personas/end-user.md \
  --url http://localhost:3000 \
  --objectives "register, login, view dashboard, update profile" \
  --scope gate \
  --output changes/active/green_auth_01/browser-use-gate-report.json
```

## Configuration

Edit `config.yaml`:

```yaml
llm:
  provider: openrouter             # openrouter | zai | openai | custom
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY

browser:
  headless: true
  timeout: 300

reporting:
  screenshots: true
  format: json
```

### Switch to Z.AI GLM (free, text-only)
```yaml
llm:
  provider: zai
  model: glm-5.1
  endpoint: "https://api.z.ai/api/coding/paas/v4"
  api_key_env: ZAI_API_KEY
```

## SUDD Integration

This tool is called by SUDD v3.2 agents:
- **ux-tester** (step 3i): Per-task persona simulation
- **persona-validator** (step 6c): Gate-level full walkthrough

Configure in `sudd/sudd.yaml`:
```yaml
browser_use:
  enabled: true
  provider: openrouter
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY
  run_on:
    per_task: true
    gate: true
  script: persona-browser-agent/persona_browser/cli.py
```

## Output Format

```json
{
  "status": "DONE",
  "elapsed_seconds": 45.2,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "scope": "task",
  "task_id": "T01",
  "objectives": "find signup, fill form, submit",
  "agent_result": "... detailed agent findings ..."
}
```

Status values:
- `DONE` — test completed, check agent_result
- `SKIP` — test skipped (missing dependency, API key, or persona file)
- `ERROR` — test failed (timeout, connection error, etc.)

## Cost

| Component | Cost |
|-----------|------|
| Browser (Playwright, local) | $0 |
| LLM (Gemini Flash, OpenRouter) | ~$0.01/test (vision model, very low cost) |
| This tool | $0 |
| **Total** | **< $1/month** (typical usage) |
