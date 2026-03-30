# Phase 0 Proof of Concept Scripts

## Prerequisites

1. Python 3.11+ with browser-use installed:
   ```bash
   pip install "browser-use>=0.2.0"
   ```

2. Node.js for the test app:
   ```bash
   cd poc/test_app && npm install
   ```

3. `OPENROUTER_API_KEY` environment variable set.

4. Note: `langchain_openai` may not work in all environments (torch/c10.dll issues). The PoC scripts use `browser_use.llm.litellm.ChatLiteLLM` as a workaround.

## Running

### 1. Start the test app

```bash
cd poc/test_app
node server.js
# Runs on http://localhost:3333
```

### 2. Run PoC-1 (AgentHistoryList inspection)

```bash
python poc/poc1_navigator_output.py
```

Outputs: per-step inspection + V3 SCHEMA MAPPING ASSESSMENT.
Saves full history to `poc/poc1_output.json`.

### 3. Run PoC-2 (HAR network capture)

```bash
python poc/poc2_network_capture.py
```

Outputs: HAR entry analysis + V3 NETWORK_LOG MAPPING ASSESSMENT.
Saves HAR file to `poc/session.har`.

## Results

See `FINDINGS.md` for empirical results.
