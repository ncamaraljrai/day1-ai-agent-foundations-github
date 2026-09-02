# Run Guide — Complete the remaining Day 1 evidence

## Current environment result

No reachable Ollama runtime was detected in the artifact execution environment used to prepare this submission. Therefore no model trace or token count was invented.

## Recommended local path

Use the course Ollama adapter with a tool-capable local model.

```bash
ollama serve
ollama pull qwen2.5:7b
```

Confirm:

```bash
curl http://localhost:11434/api/tags
```

Then in the lab scripts replace:

```python
client = anthropic.Anthropic()
```

with:

```python
from ollama_shim import OllamaAnthropic
client = OllamaAnthropic(model="qwen2.5:7b")
```

For the non-determinism comparison, run with `temperature=0.5` if the course adapter is configured to accept it.

## Temporal reproducibility warning

`agent_loop.py` uses `datetime.date.today()`. The fixture for order 4471 is due in April 2026. A run performed after that date will not reproduce the theory's March 24 scenario.

Record the as-is result first. If the purpose is to reproduce the original lesson, make a second clearly labelled experiment where `get_today()` returns `2026-03-24`.

Never report the frozen-date result as the real current date.
