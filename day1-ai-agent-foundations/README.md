# Day 1 — AI Agent Foundations

GitHub-ready repository for the **Day 1 — Foundations** theory/lab work.

## What this repo contains

- `src/check_setup.py` — verifies Anthropic SDK compatibility and API access.
- `src/agent_loop.py` — minimal Reason → Act → Observe agent loop.
- `src/plain_vs_agent.py` — compares a plain LLM call with the agent version.
- `src/ollama_shim.py` — local Ollama adapter compatible with the lab interface.
- `docs/Day1-Foundations-Lab-Submission.md` — written lab submission.
- `docs/RUN-GUIDE.md` — instructions for collecting the remaining real-run evidence.

## Learning goals

This lab demonstrates:

- the difference between a plain model call, a fixed workflow, and an agent;
- the four core agent components: **model, tools, memory, loop**;
- the **Reason → Act → Observe** pattern;
- why tool descriptions matter;
- why agents need a hard iteration limit;
- how error paths affect agent behavior;
- why real execution traces and token counts should be measured rather than invented.

## Option A — Anthropic API

### Requirements

- Python 3.9+
- Anthropic API key

### Setup

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install:

```bash
pip install -r requirements.txt
```

Set your key.

macOS/Linux:

```bash
export ANTHROPIC_API_KEY="your-key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your-key"
```

Verify:

```bash
python src/check_setup.py
```

Run the agent:

```bash
python src/agent_loop.py
```

Compare with a plain call:

```bash
python src/plain_vs_agent.py
```

## Option B — Run locally with Ollama

Install Ollama and start it:

```bash
ollama serve
```

Pull a tool-capable model:

```bash
ollama pull qwen2.5:7b
```

Confirm Ollama is responding:

```bash
curl http://localhost:11434/api/tags
```

Then change the client creation in a lab script from:

```python
client = anthropic.Anthropic()
```

to:

```python
from ollama_shim import OllamaAnthropic
client = OllamaAnthropic(model="qwen2.5:7b")
```

If running from the repository root, either run scripts from `src/` or ensure `src` is on `PYTHONPATH`.

## Important reproducibility note

`agent_loop.py` uses:

```python
datetime.date.today()
```

The course fixture for order `4471` was designed around March 2026 and has a due date in April 2026. A run performed later will naturally produce a different result.

For honest lab evidence:

1. run the script **as-is** and record what really happens;
2. if you want to reproduce the original teaching scenario, make a separate clearly labelled experiment with a frozen date.

Do not report the frozen-date run as the real current date.

## Required Lab 1.2 experiments

After the normal run:

1. Change the `get_today` description to:
   ```text
   Returns a date.
   ```
2. Ask for order `#9999`.
3. Set:
   ```python
   MAX_STEPS = 2
   ```

Record what actually happened.

## Repository hygiene

Do **not** commit API keys, virtual environments, caches, or local model data.

See `.gitignore`.

## Submission integrity

The included written submission intentionally leaves real execution evidence marked for capture where the course requires measured traces or token counts. This avoids presenting expected behavior as if it had been observed.

## Suggested GitHub repository name

`day1-ai-agent-foundations`


## ⚠️ Required before graded submission: capture real evidence

The written analysis is **not sufficient by itself** for full completeness.  
Labs 1.2 and 1.3 explicitly require **actual execution evidence**, including:

- tool-call path / step count;
- two-run comparison;
- behavior after weakening the tool description;
- behavior for missing order `#9999`;
- behavior with `MAX_STEPS = 2`;
- plain-call behavior;
- real input/output token counts.

### Windows — one command

Open PowerShell in the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-evidence-windows.ps1
```

The script will ensure `qwen2.5:7b` is pulled and then execute the real local-model experiments.

### macOS / Linux

Start Ollama in one terminal:

```bash
ollama serve
```

Then:

```bash
./run-evidence.sh
```

### Output

The run creates:

```text
evidence/day1-evidence.md
evidence/day1-evidence.json
evidence/raw/*.txt
```

**Do not submit while the lab document still contains `TO CAPTURE` or `TO MEASURE`.**
Replace those placeholders using `evidence/day1-evidence.md`, or submit the evidence file alongside the written document if the learning platform accepts multiple files.

The capture script uses the course-provided `ollama_shim.py` and a real local model. It does not create mocked traces.
