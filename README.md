# Persona Browser Agent

AI-driven browser testing as simulated personas. The AI navigates your web app like a real user — finding features, filling forms, and reporting friction — so you catch UX issues before humans do.

**Companion to [SUDD](https://github.com/stefanoallima/sudd2)** — SUDD's gate validation calls persona-test to run real browser testing for each persona.

## Architecture

```
                          persona-browser-agent
  ┌───────────────────────────────────────────────────────────┐
  │                                                           │
  │  Navigator          Scorers (parallel)      Reconciler    │
  │  ┌──────────┐       ┌──────────────┐       ┌──────────┐  │
  │  │ browser- │       │ Text Scorer  │       │  Score    │  │
  │  │ use +    │──────▶│ (GLM 5-turbo)│──────▶│Reconciler│  │
  │  │ Gemini   │  │    └──────────────┘  │    │ (Sonnet) │  │
  │  │ Flash    │  │    ┌──────────────┐  │    └──────────┘  │
  │  │          │  │    │Visual Scorer │  │         │        │
  │  └────┬─────┘  └───▶│(Gemini Flash)│──┘         │        │
  │       │         │   └──────────────┘            ▼        │
  │       │         │   ┌──────────────┐       JSON Report   │
  │  Playwright     └───│  Network     │       on stdout     │
  │  (local          ───│  Verifier    │──────────────       │
  │   Chromium)         │(deterministic)│                     │
  │                     └──────────────┘                      │
  └───────────────────────────────────────────────────────────┘
```

- **Navigator**: browser-use + Gemini Flash — navigates your app as the persona
- **Text Scorer**: GLM 5-turbo — evaluates criteria from text observations + network log
- **Visual Scorer**: Gemini Flash — evaluates criteria from screenshots (no network data)
- **Network Verifier**: Deterministic Python — cross-references API calls against codeintel contracts
- **Score Reconciler**: Claude Sonnet — reconciles text/visual scorer disagreements

## Quick Start

### 1. Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| **Python** | 3.11+ | Runtime |
| **pip** | Latest | Package install |
| **OpenRouter API key** | — | For Gemini Flash LLM (~$0.01/test) |

### 2. Install

```bash
git clone https://github.com/stefanoallima/persona-browser-agent.git
cd persona-browser-agent
pip install -e .
playwright install chromium
```

### 3. Set API key

```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc):
export OPENROUTER_API_KEY="sk-or-v1-..."

# Windows (PowerShell):
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
# Windows (permanent):
setx OPENROUTER_API_KEY "sk-or-v1-..."
```

Get a key at [openrouter.ai](https://openrouter.ai/).

### 4. Verify

```bash
persona-test --help
# Should show: "Persona Browser Agent — AI-driven browser testing as simulated personas"
```

### 5. Run a test

```bash
persona-test \
  --persona examples/persona-ecommerce-shopper.md \
  --url http://localhost:3000 \
  --objectives "find signup form, fill with realistic data, submit"
```

## Usage

### CLI (navigator only)
```bash
persona-test \
  --persona path/to/persona.md \
  --url http://localhost:3000 \
  --objectives "find signup, fill form, submit" \
  --scope task \
  --output report.json \
  --screenshots-dir ./screenshots/
```

### CLI (full pipeline — with scorers + reconciler)
```bash
persona-test \
  --persona path/to/persona.md \
  --url http://localhost:3000 \
  --objectives "register, login, view dashboard" \
  --scope gate \
  --codeintel path/to/codeintel.json \
  --rubric path/to/rubric.md \
  --manifest path/to/manifest.json \
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
print(report["status"])        # DONE, ERROR, SKIP, or PARTIAL
print(report["agent_result"])  # What the persona experienced
```

### Full pipeline (Python)
```python
from persona_browser.pipeline import run_pipeline_sync

report = run_pipeline_sync(
    persona_path="persona.md",
    url="http://localhost:3000",
    objectives="register, login, dashboard",
    codeintel_path="codeintel.json",
    rubric_path="rubric.md",
    scope="gate",
)
# report contains: pages, summary, network_verification, verification_tasks
```

## SUDD Integration

This tool is called by [SUDD v3.6](https://github.com/stefanoallima/sudd2) during gate validation:

```
/sudd:gate
  Step 2a: Code intelligence extraction (codeintel.json, manifest.json, rubric.md)
  Step 2b: persona-test runs for EACH persona  <-- this tool
  Step 2c: Persona validator reads the browser reports
  Step 2d: UX tester spot-checks against screenshots
  Step 2e: Unified scoring formula
```

**Setup for SUDD**: Both repos should be siblings:
```
projects/
  sudd2/                      <-- SUDD framework
  persona-browser-agent/      <-- this repo
  your-app/                   <-- your project (sudd init here)
```

When you run `sudd init` in your project, it auto-detects and installs persona-browser-agent from the sibling directory.

**SUDD config** (`sudd/sudd.yaml`):
```yaml
browser_use:
  enabled: true
  command: persona-test        # installed via pip install -e ../persona-browser-agent
  provider: openrouter
  model: google/gemini-2.5-flash
  api_key_env: OPENROUTER_API_KEY
  run_on:
    per_task: true
    gate: true
```

## Configuration

Edit `config.yaml` (or pass `--config path/to/config.yaml`):

```yaml
llm:
  provider: openrouter              # openrouter | zai | openai | custom
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY
  temperature: 0.1

scoring:
  text_scorer:
    model: zhipuai/glm-5-turbo      # fast, text-only
  visual_scorer:
    model: google/gemini-3-flash     # multimodal vision
  reconciler:
    model: anthropic/claude-sonnet-4-6

browser:
  headless: true
  width: 1280
  height: 720
  max_steps: 50                      # max browser actions per test
  timeout_seconds: 120               # hard timeout
  capture_network: true              # HAR recording for network verifier

reporting:
  screenshots: true
  screenshots_dir: "./screenshots"
  format: json
```

### Alternative LLM Providers

**Z.AI GLM (free, text-only):**
```yaml
llm:
  provider: zai
  model: glm-5.1
  endpoint: "https://api.z.ai/api/coding/paas/v4"
  api_key_env: ZAI_API_KEY
```

**OpenAI:**
```yaml
llm:
  provider: openai
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
```

## Output Format

### Navigator-only report
```json
{
  "status": "DONE",
  "elapsed_seconds": 45.2,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "scope": "task",
  "objectives": "find signup, fill form, submit",
  "agent_result": "... detailed persona findings ...",
  "navigator_output": {
    "pages": [...],
    "experience": {...},
    "manifest_coverage": {...}
  }
}
```

### Full pipeline report (with scorers)
```json
{
  "version": "1.1",
  "status": "DONE",
  "pages": [
    {
      "id": "register",
      "pb_criteria": [
        {"criterion": "...", "text_result": "PASS", "visual_result": "PASS", "reconciled": "PASS"}
      ],
      "consumer_criteria": [...]
    }
  ],
  "summary": {
    "pb_criteria_passed": 12,
    "pb_criteria_failed": 1,
    "consumer_criteria_passed": 8,
    "deal_breakers_triggered": []
  },
  "network_verification": {
    "api_calls_total": 15,
    "api_calls_matched_codeintel": 14,
    "deal_breakers": []
  }
}
```

### Status values

| Status | Meaning | Exit code |
|--------|---------|-----------|
| `DONE` | Test completed successfully | 0 |
| `PARTIAL` | Navigator hit max_steps before completing | 0 |
| `SKIP` | Cannot run (missing dependency, API key, or file) | 0 (CLI: 1 for missing files) |
| `ERROR` | Test started but failed (timeout, crash) | 0 |

## Persona File Format

```markdown
# Persona: Sarah Chen

## Identity
- Marketing manager, 34, moderate tech comfort
- Uses laptop, Chrome, office WiFi

## Objectives
### Objective 1: Register for the platform
**Steps:**
1. Find the signup page
2. Fill in name, email, password
3. Submit the form
**Success criteria:**
- Registration completes without errors
- Redirected to dashboard

## Deal-Breakers
- Form loses data on validation error
- No confirmation after signup

## Form Data
first_name: Sarah
last_name: Chen
email: sarah.chen@example.com
password: SecurePass123!
```

## Cost

| Component | Cost |
|-----------|------|
| Browser (Playwright, local) | $0 |
| Navigator LLM (Gemini Flash via OpenRouter) | ~$0.01/test |
| Scorer LLMs (text + visual + reconciler) | ~$0.02/test |
| **Total per test** | **~$0.03** |
| **Typical monthly** | **< $5** |

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=persona_browser -v

# Integration tests (require live browser + running app)
INTEGRATION_TEST=1 python -m pytest tests/test_integration.py -v
```

## Related

- **[SUDD](https://github.com/stefanoallima/sudd2)** — Autonomous AI coding framework that uses this tool for persona validation
- **[INTEGRATION.md](INTEGRATION.md)** — Full service contract for consuming agents
