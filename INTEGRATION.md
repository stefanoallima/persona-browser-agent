# Persona Browser Agent — Service Contract

This document defines what persona-browser-agent receives, what it does, and what it returns. Build against this contract.

---

## 0. CONSUMER SETUP — How Another Repo Connects

Before using persona-browser-agent, the consuming repo needs to install it, set environment variables, and tell its AI agent the tool exists.

### Option A: Sibling directory (recommended for local dev)

The consuming repo and persona-browser-agent live next to each other:
```
projects/
├── my-app/                    ← consuming repo (AI agent runs here)
│   ├── CLAUDE.md              ← tell the agent this tool exists
│   └── sudd/
│       └── personas/
│           └── end-user.md
└── persona-browser-agent/     ← this repo
    └── persona_browser/
```

Install once:
```bash
cd ../persona-browser-agent && pip install -e .
playwright install chromium
export OPENROUTER_API_KEY="sk-or-..."
```

### Option B: pip install from Git
```bash
pip install git+https://github.com/your-org/persona-browser-agent.git
playwright install chromium
export OPENROUTER_API_KEY="sk-or-..."
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes (default provider) | API key for Gemini Flash via OpenRouter |
| `ZAI_API_KEY` | Only if provider=zai | API key for Z.AI GLM-5.1 |
| `OPENAI_API_KEY` | Only if provider=openai | API key for OpenAI models |

### Tell the Consuming Agent

Add to your repo's `CLAUDE.md` (or equivalent):

````markdown
## Persona Browser Testing
Run AI-driven UX tests as simulated personas using persona-browser-agent:

    persona-test \
      --persona <persona-file.md> \
      --url <app-url> \
      --objectives "<comma-separated objectives>"

Output is JSON on stdout: `{"status": "DONE|SKIP|ERROR", "agent_result": "..."}`.
Parse `agent_result` for the persona's natural-language findings.
Full contract: see persona-browser-agent/INTEGRATION.md
````

### Path Resolution

The consuming agent does NOT need to know where persona-browser-agent lives on disk. After `pip install -e .`, the `persona-test` CLI and `python -m persona_browser.cli` work from any directory. The `--config` flag points to wherever you keep config.yaml.

---

## 1. INTERFACE — How Consuming Agents Connect

### Primary (v1): CLI (subprocess via Bash)

The consuming agent (e.g., a SUDD ux-tester, a Claude Code session, or any AI agent with Bash access) invokes persona-browser-agent as a **CLI subprocess**. Just a Python CLI that reads files, runs a browser, and prints JSON to stdout.

```
┌──────────────────────┐         ┌──────────────────────────────────┐
│  Consuming Agent     │         │  persona-browser-agent           │
│  (any AI agent with  │  Bash   │  (separate Python process)       │
│   Bash tool access)  │────────▶│                                  │
│                      │         │  1. Read persona .md from disk   │
│  e.g., Claude Code,  │         │  2. Launch local Chromium        │
│  OpenCode, Crush,    │         │  3. Gemini Flash decides actions │
│  or custom agent     │         │  4. Navigate, click, fill forms  │
│                      │◀────────│  5. Print JSON to stdout         │
│  Parses stdout JSON  │  stdout │                                  │
└──────────────────────┘   JSON  └──────────────────────────────────┘
```

**Why CLI for v1:**
- No long-running server to manage — start, run, exit
- Works on any OS without extra setup
- Any AI agent with Bash/shell access can call it
- JSON on stdout is the simplest integration possible
- Each test is stateless — no session management needed

### Planned (v1.1): MCP Server

MCP is the natural evolution — it gives the consuming agent a native tool call instead of constructing shell commands and parsing stdout. Planned for v1.1.

Configure in consuming repo's `.mcp.json` (or equivalent):
```json
{
  "mcpServers": {
    "persona-browser": {
      "command": "python",
      "args": ["-m", "persona_browser.mcp_server"],
      "cwd": "/path/to/persona-browser-agent"
    }
  }
}
```

MCP tools to expose:
- `persona_test_run(persona_path, url, objectives, scope, task_id?)` → returns JSON report
- `persona_test_config()` → returns current LLM/browser config

CLI remains the primary interface. MCP is an enhancement for tighter integration.

---

## 2. INPUT — What You Receive

### 2a. CLI Arguments

```
python -m persona_browser.cli \
  --persona <path>           # REQUIRED: path to persona .md file
  --url <url>                # REQUIRED: URL of running application
  --objectives <string>      # REQUIRED: comma-separated objectives to test
  --scope <task|gate>        # OPTIONAL: default "task"
  --task-id <id>             # OPTIONAL: task ID (e.g., T03)
  --output <path>            # OPTIONAL: write JSON report to this file too
  --config <path>            # OPTIONAL: path to config.yaml
  --form-data <path>         # OPTIONAL: path to file with realistic form data
  --screenshots-dir <path>   # OPTIONAL: save screenshots here
  --record-video <path>      # OPTIONAL: save video recording here
```

**Form data precedence**: If both `--form-data` (external file) AND `## Form Data` (embedded in persona .md) are provided, both are injected into the prompt. The LLM sees both and uses the more specific one. To avoid confusion, prefer one source — embed form data in the persona file unless you need to override it per-run.

### 2b. Persona File (--persona)

A markdown file on disk. The agent reads the **ENTIRE file as raw text** and injects it into the browser-use prompt as the persona's identity. No section parsing is enforced in code — the LLM interprets the structure.

**Important**: persona-browser-agent does NOT validate the persona file against a schema. Any markdown file works. The format below is **recommended** for best results — the LLM understands these sections well.

**Recommended format:**

```markdown
# Persona: {Name}
or
# Micro-Persona: {Task-ID} — {Consumer Name}

## Identity
- Name, age, role, tech comfort, device, context

## Objectives
### Objective N: {title}
**Steps:**
1. Step one
2. Step two
**Success criteria:**
- Criterion one
- Criterion two

## Deal-Breakers
- Condition that causes instant failure

## Form Data                    ← fenced code block with key: value pairs
first_name: Sarah
email: sarah.chen@example.com
password: SecurePass123!
```

**Also valid** (micro-personas may use these instead of ## Objectives):

```markdown
## Contract
- What the code MUST provide

## Verification Rubric          ← for consuming agent's internal use, not parsed by browser-use
### CONTRACT (must ALL pass)
- [ ] Criterion
```

**How it works**: The entire persona text is injected into the prompt as-is. The browser-use LLM reads it, adopts the identity, and uses objectives/steps as its test plan. Better-structured personas → better test results, but any readable markdown works.

### 2c. Config File (--config)

YAML file with LLM and browser settings:

```yaml
llm:
  provider: openrouter        # openrouter | zai | openai | custom
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY
  temperature: 0.1
  max_tokens: 20000

browser:
  headless: true
  width: 1280
  height: 720
  timeout: 300                 # max seconds for the entire test
  record_video: false
  record_video_dir: "./recordings"

reporting:
  screenshots: true
  screenshots_dir: "./screenshots"
  format: json
```

If `--config` is not provided, use defaults or look for `config.yaml` in the working directory.

### 2d. Scope

| Scope | Meaning | What you do |
|-------|---------|-------------|
| `task` | Testing ONE specific feature/page | Navigate ONLY the routes related to the objectives. Stay focused. Don't explore the whole app. |
| `gate` | Testing the ENTIRE application | Navigate ALL main routes. Try ALL objectives. Explore beyond objectives. Report on overall experience. |

---

## 3. PROCESS — What You Do

This is what persona-browser-agent must execute internally:

### Step 1: Parse inputs
```
1. Read and parse the persona .md file
2. Extract: identity, objectives, deal-breakers, form data
3. Load config (LLM provider, browser settings)
4. Validate: API key exists, persona file found, URL provided
   → If validation fails: print JSON with status=SKIP, exit 0
```

### Step 2: Build the prompt
```
1. Construct a natural-language task for browser-use:
   - Inject persona identity ("You are Sarah Chen, 34, marketing manager...")
   - Inject objectives ("Find signup form, fill it, submit")
   - Inject scope instructions (narrow for task, broad for gate)
   - Inject form data if available ("Use this data when filling forms: ...")
   - Inject testing instructions (check discoverability, fill forms, test errors)
```

### Step 3: Launch browser and run
```
1. Initialize browser-use Agent with:
   - The constructed prompt
   - The configured LLM (Gemini Flash via OpenRouter, or whatever config says)
   - A local Chromium browser instance
2. The AI agent autonomously:
   - Navigates to the URL
   - Looks at the page (via vision/accessibility tree)
   - Decides what to click, type, or navigate
   - Fills forms with persona-appropriate data
   - Takes screenshots at key moments
   - Reports findings in natural language
3. Enforce timeout (config.browser.timeout seconds)
   → If timeout: return what was collected so far with status=ERROR
```

### Step 4: Collect results
```
1. Capture the agent's natural-language report
2. Collect screenshots (if enabled)
3. Record video path (if enabled)
4. Measure elapsed time
5. Close the browser
```

### Step 5: Output results
```
1. Build JSON report (see Output section below)
2. Print JSON to stdout
3. If --output flag: also write to that file path
4. Exit with code 0
```

---

## 4. OUTPUT — What You Return

### 4a. JSON to stdout (ALWAYS)

Every run prints exactly ONE JSON object to stdout. Nothing else on stdout.

**stderr**: May contain progress messages (e.g., "Report written to /path/report.json") and browser-use internal logs. Consuming agents should capture **stdout only** for the JSON report. stderr can be logged for debugging but should not be parsed.

```json
{
  "status": "DONE",
  "elapsed_seconds": 45.2,
  "persona": "sudd/changes/active/green_auth_01/tasks/T03/micro-persona.md",
  "url": "http://localhost:3000",
  "scope": "task",
  "task_id": "T03",
  "objectives": "fill signup form, submit, verify confirmation",
  "agent_result": "## Persona Test Report\n\n### First Impression\nThe page loaded in under 2 seconds...\n\n### Objective 1: Fill signup form\nFOUND: YES (3 seconds, signup button in top-right)\nCOMPLETED: YES\nFORMS: Filled name, email, password. Validation showed 'Password too weak' when I used '123' — good error message.\n\n### Overall\nUSABILITY_SCORE: 8/10\nWOULD_RECOMMEND: YES\nHONEST_REACTION: Clean signup flow, minor issue with password requirements not shown upfront."
}
```

### 4b. Status Values

| Status | When | Exit code | Consumer action |
|--------|------|-----------|-------------|
| `DONE` | Test ran to completion | 0 | Parse `agent_result`, use as evidence in verdict |
| `SKIP` | Can't run (missing dep, key, file) | 0 | Log warning, continue without browser-use |
| `ERROR` | Test started but failed (timeout, crash) | 0 | Log error, apply -5 score penalty, continue |

**Exit code is ALWAYS 0** unless there's a truly fatal Python error (import failure, syntax error). The `status` field in the JSON tells the consuming agent what happened.

### 4c. Error/Skip JSON

When status is SKIP or ERROR, include `error` and `reason` fields:

```json
{
  "status": "SKIP",
  "elapsed_seconds": 0,
  "persona": "path/to/persona.md",
  "url": "http://localhost:3000",
  "error": "Missing API key: set the OPENROUTER_API_KEY environment variable",
  "reason": "missing_api_key"
}
```

| reason | Meaning |
|--------|---------|
| `missing_dependency` | `browser-use` package not installed |
| `missing_api_key` | Environment variable for API key is empty |
| `missing_persona` | Persona .md file not found at given path |
| `timeout` | Agent exceeded `browser.timeout` seconds |
| `connection_failed` | Can't reach the URL (dev server not running?) |
| `unknown` | Unexpected error |

### 4d. agent_result Format

The `agent_result` string is a **natural-language report** from the AI persona. It is NOT structured JSON — it's the raw output from the browser-use agent describing what it experienced.

Consuming agents read this as text and incorporate the findings into their own structured reports. The format varies per run, but the prompt instructs the browser-use agent to include:

```
For EACH objective:
- OBJECTIVE: [the objective]
- FOUND: YES/NO (how long to find it)
- COMPLETED: YES/NO (what happened)
- FORMS: [list any forms encountered and whether they worked]
- FRICTION: [any moments of confusion or frustration]

OVERALL:
- FIRST_IMPRESSION: [1 sentence]
- USABILITY_SCORE: 1-10
- TOP_ISSUES: [numbered list]
- WOULD_RECOMMEND: YES/NO/MAYBE
- HONEST_REACTION: [1 sentence]
```

### 4e. Files on Disk (optional)

| File | When | Path |
|------|------|------|
| JSON report | `--output` flag provided | The path specified |
| Screenshots | `--screenshots-dir` provided | `{dir}/01-initial-load.png`, `02-{action}.png`, etc. |
| Video | `--record-video` provided | `{dir}/session.webm` |

---

## 5. CONFIGURATION — What Can Be Changed

All configuration is in `config.yaml`. The caller passes `--config path/to/config.yaml`.

### LLM Provider (swap without code changes)

```yaml
# Gemini Flash via OpenRouter (default — multimodal vision, low cost)
llm:
  provider: openrouter
  model: google/gemini-2.5-flash-preview
  endpoint: "https://openrouter.ai/api/v1"
  api_key_env: OPENROUTER_API_KEY

# Z.AI GLM-5.1 (free via coding plan — text-only, good for text-heavy UIs)
llm:
  provider: zai
  model: glm-5.1
  endpoint: "https://api.z.ai/api/coding/paas/v4"
  api_key_env: ZAI_API_KEY

# Any OpenAI-compatible endpoint
llm:
  provider: custom
  model: your-model-name
  endpoint: "https://your-api.com/v1"
  api_key_env: YOUR_API_KEY
```

### Consuming project config

The consuming project may mirror browser-use settings in its own config (e.g., SUDD stores a copy in `sudd.yaml → browser_use`). When invoking persona-browser-agent, pass `--config persona-browser-agent/config.yaml`. The persona-browser-agent config.yaml is the source of truth for LLM/browser settings.

---

## 6. SETUP — Prerequisites

```bash
# 1. Install the package
cd persona-browser-agent
pip install -e .

# 2. Install Chromium for Playwright (first time only)
playwright install chromium

# 3. Set API key
export OPENROUTER_API_KEY="sk-or-..."

# 4. Verify it works
persona-test \
  --persona examples/persona-ecommerce-shopper.md \
  --url "https://example.com" \
  --objectives "find the main heading"
```

---

## 7. EXAMPLE — Complete Round-Trip

### Input
```bash
python -m persona_browser.cli \
  --persona examples/micro-persona-signup-form.md \
  --url http://localhost:3000/register \
  --objectives "fill signup form with name and email, submit, see confirmation" \
  --scope task \
  --task-id T03 \
  --output /tmp/report.json
```

### What happens inside
1. Reads `examples/micro-persona-signup-form.md` → extracts identity ("first-time visitor"), objectives, form data (Jordan Rivera, jordan.rivera@example.com, SecurePass123!)
2. Builds prompt: "You are a first-time visitor... Navigate to http://localhost:3000/register... Fill the signup form..."
3. Launches headless Chromium
4. Gemini Flash sees the page, finds the form, fills name/email/password with the persona's data
5. Submits the form
6. Reports what happened

### Output (stdout)
```json
{
  "status": "DONE",
  "elapsed_seconds": 32.7,
  "persona": "examples/micro-persona-signup-form.md",
  "url": "http://localhost:3000/register",
  "scope": "task",
  "task_id": "T03",
  "objectives": "fill signup form with name and email, submit, see confirmation",
  "agent_result": "## Test Report\n\n### First Impression\nClean registration page. Form fields are clearly labeled.\n\n### Objective: Fill signup form\nFOUND: YES (immediate — form is the main content)\nCOMPLETED: YES\nFORMS: Filled name='Jordan Rivera', email='jordan.rivera@example.com', password='SecurePass123!', confirm='SecurePass123!'. All fields accepted.\n\nSubmitted form → redirected to dashboard with 'Welcome, Jordan!' message.\n\n### Error Testing\nEmpty email → 'Email is required' (clear)\nShort password '123' → 'Password must be at least 8 characters' (helpful)\nMismatched confirm → 'Passwords do not match' (clear)\n\n### Overall\nFIRST_IMPRESSION: Professional and straightforward\nUSABILITY_SCORE: 9/10\nTOP_ISSUES: 1. Password requirements not shown before typing\nWOULD_RECOMMEND: YES\nHONEST_REACTION: Simple, clean signup — exactly what I expected."
}
```

### What the consuming agent does with it
The consuming agent parses this JSON, reads `agent_result`, and incorporates:
- "COMPLETED: YES" → evidence for PASS on this objective
- "Password requirements not shown" → minor issue, feed to developer as improvement
- "USABILITY_SCORE: 9/10" → factor into intuitiveness assessment
- "WOULD_RECOMMEND: YES" → strong positive signal for the verdict
