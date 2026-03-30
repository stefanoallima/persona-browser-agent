# INTEGRATION.md — Review & Gap Analysis

Reviewed: 2026-03-29

---

## Overall Assessment

**Score: 90% — strong service contract, missing the bootstrapping story.**

The document clearly defines what persona-browser-agent receives, does, and returns. A developer or AI agent reading this would understand the CLI interface, input format, and output contract. The gap is operational: it doesn't explain how a consuming repo actually wires this up.

---

## Accurate Against Codebase

| Claim | Code Location | Verified |
|-------|---------------|----------|
| CLI args (--persona, --url, --objectives, etc.) | `cli.py:25-64` | Yes |
| Config loading with defaults | `config.py:41-55` | Yes |
| LLM factory supports openrouter/zai/openai/custom | `llm.py:6-40` | Yes |
| Prompt injects persona text, objectives, scope | `prompts.py:4-93` | Yes |
| browser-use Agent with LLM + Browser | `agent.py:109-115` | Yes |
| JSON report with DONE/SKIP/ERROR status | `report.py:13-46` | Yes |
| Error classification (missing_api_key, timeout, etc.) | `report.py:51-65` | Yes |
| Exit code always 0 | `cli.py` (no sys.exit) | Yes |
| stdout is JSON only, stderr for messages | `cli.py:95-98` | Yes |

---

## Issues Found

### HIGH — Missing: Consumer Setup Section

The doc never explains how another repo actually wires this up. A Claude Code session in a consuming repo needs:

1. **Where to install** — `pip install -e ../persona-browser-agent`? Git submodule? pip from GitHub URL?
2. **Path resolution** — how does the consuming agent know where persona-browser-agent lives on disk?
3. **Environment variables** — which API key env vars must be set in the consuming shell?
4. **CLAUDE.md snippet** — what should the consuming repo's CLAUDE.md say so Claude knows this tool exists?

**Suggested addition — new Section 0:**

```markdown
## 0. CONSUMER SETUP — How Another Repo Connects

### Option A: Sibling directory (monorepo or co-located)
The consuming repo and persona-browser-agent live next to each other:
```
projects/
├── my-app/                    ← consuming repo (Claude Code runs here)
│   ├── CLAUDE.md
│   └── personas/
│       └── end-user.md
└── persona-browser-agent/     ← this repo
    └── persona_browser/
```

Install once:
```bash
cd persona-browser-agent && pip install -e .
playwright install chromium
export OPENROUTER_API_KEY="sk-or-..."
```

Add to consuming repo's CLAUDE.md:
```markdown
## Persona Browser Testing
Run UX tests with simulated personas:
```bash
persona-test \
  --persona personas/<file>.md \
  --url <target-url> \
  --objectives "<comma-separated objectives>"
```
Output is JSON on stdout with status DONE/SKIP/ERROR.
```

### Option B: pip install from Git
```bash
pip install git+https://github.com/org/persona-browser-agent.git
```

### Option C: MCP server (future)
Configure in consuming repo's .mcp.json:
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
```

---

### MEDIUM — MCP Dismissed Prematurely

**Section 1** says "No MCP" and frames it as future-maybe. But the actual use case — one Claude Code session calling this from another repo — is exactly what MCP was designed for.

**Current text:**
> No library import, no MCP, no HTTP server. Just a Python CLI.

**Problem:** CLI via Bash works but requires the consuming Claude to:
- Construct shell commands with proper quoting
- Parse stdout JSON manually
- Handle subprocess edge cases (hanging, buffering)

MCP gives the consuming Claude a native tool — no parsing, no shell escaping, structured input/output.

**Recommendation:** Keep CLI as v1 primary interface, but reframe MCP as a planned v1.1 enhancement rather than a distant future option.

---

### MEDIUM — SUDD Agent Roles Are Fictional

References throughout:
- "ux-tester (step 3i)" — does not exist
- "persona-validator (step 6c)" — does not exist
- "SUDD v3.2 agents" — no such version exists in this project

These read as if a working SUDD system already consumes this tool. It doesn't yet.

**Recommendation:** Replace specific agent role names with generic language:

| Current | Suggested |
|---------|-----------|
| "SUDD agents invoke persona-browser-agent" | "The consuming agent invokes persona-browser-agent" |
| "The ux-tester agent parses this JSON" | "The consuming agent parses this JSON" |
| "SUDD keeps its own copy in sudd.yaml" | "The consuming project may mirror config in its own settings" |

---

### LOW — Persona Format "Guaranteed Sections" Don't Match Examples

**Section 2b** says `## Objectives` with `### Objective N` is guaranteed in every persona file.

But `micro-persona-signup-form.md` has:
- `## Contract` (not `## Objectives`)
- `## Verification Rubric` (not mentioned as guaranteed)
- `## Deal-Breakers` (listed as "sometimes present")

**Reality:** The agent doesn't parse sections at all. `prompts.py:30` injects the entire persona text raw:
```python
## Your Identity
{persona_text}
```

The "guaranteed sections" contract is aspirational documentation for persona authors, not enforced code. This should be clarified — otherwise a consuming agent might try to validate persona files against this schema before sending them.

**Recommendation:** Reframe as "recommended format" rather than "guaranteed sections."

---

### LOW — Duplicate Form Data Mechanism

Two ways to provide form data:
1. `--form-data <path>` CLI flag → reads a separate file
2. `## Form Data` section embedded in the persona .md file

Both end up in the prompt. If both are provided, both are injected — potentially conflicting.

`prompts.py:23-28` injects `--form-data` content:
```python
if form_data:
    form_block = f"## Realistic Form Data\nUse this data...\n{form_data}"
```

And the persona text (which may contain its own `## Form Data`) is injected separately at line 35.

**Recommendation:** Document precedence. Suggest: `--form-data` overrides embedded form data, or clarify that both are injected and the LLM will use whichever appears more specific.

---

### LOW — stderr Output Not Documented

Section 4a says "nothing else on stdout" and mentions stderr, but doesn't document what stderr contains.

`cli.py:95`:
```python
print(f"Report written to {args.output}", file=sys.stderr)
```

A consuming agent parsing subprocess output should know to ignore stderr or what to expect there.

**Recommendation:** Add one line: "stderr may contain progress messages (e.g., 'Report written to /path'). Consuming agents should capture stdout only."

---

## Summary of Recommended Changes

| Priority | Change | Effort |
|----------|--------|--------|
| **HIGH** | Add Section 0: Consumer Setup (install, path, env vars, CLAUDE.md snippet) | 30 min |
| **MEDIUM** | Reframe MCP as planned v1.1, not distant future | 5 min |
| **MEDIUM** | Replace fictional SUDD agent names with generic "consuming agent" | 10 min |
| **LOW** | Reframe persona format as "recommended" not "guaranteed" | 5 min |
| **LOW** | Document form-data precedence | 5 min |
| **LOW** | Document stderr content | 2 min |
