#!/usr/bin/env python3
"""
Capture REAL Day 1 Lab 1.2 / 1.3 execution evidence using Ollama.

Produces:
  evidence/day1-evidence.json
  evidence/day1-evidence.md
  evidence/raw/*.txt

This script does NOT fabricate or replay model output. It calls the local
Ollama server through the course-provided OllamaAnthropic adapter.

Usage (from repository root):
  python tools/capture_day1_evidence.py

Optional:
  OLLAMA_MODEL=qwen2.5:14b python tools/capture_day1_evidence.py
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ollama_shim import OllamaAnthropic  # noqa: E402
import agent_loop as course  # noqa: E402


MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EVIDENCE_DIR = ROOT / "evidence"
RAW_DIR = EVIDENCE_DIR / "raw"
EVIDENCE_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)


def make_client(temperature: float):
    return OllamaAnthropic(model=MODEL, host=HOST, temperature=temperature)


def tool_result_to_dict(output: Any) -> dict:
    if isinstance(output, dict):
        return output
    return {"value": output}


def run_agent(
    goal: str,
    *,
    temperature: float = 0.5,
    max_steps: int = 8,
    tool_specs=None,
    frozen_today: str | None = None,
) -> dict:
    """Instrumented copy of the course loop preserving its semantics."""
    client = make_client(temperature)
    messages = [{"role": "user", "content": goal}]
    specs = copy.deepcopy(tool_specs if tool_specs is not None else course.TOOL_SPECS)

    tool_functions = dict(course.TOOL_FUNCTIONS)
    if frozen_today:
        def fixed_today():
            return {"today": frozen_today}
        tool_functions["get_today"] = fixed_today

    trace = []
    total_input = 0
    total_output = 0
    final = None
    stopped_by = None

    for step in range(1, max_steps + 1):
        response = client.messages.create(
            model=course.MODEL,
            max_tokens=4096,
            tools=specs,
            messages=messages,
        )
        total_input += getattr(response.usage, "input_tokens", 0) or 0
        total_output += getattr(response.usage, "output_tokens", 0) or 0

        model_text = "\n".join(
            b.text.strip()
            for b in response.content
            if getattr(b, "type", None) == "text" and getattr(b, "text", "").strip()
        )

        step_record = {
            "step": step,
            "stop_reason": response.stop_reason,
            "model_text": model_text,
            "tool_calls": [],
        }

        if response.stop_reason != "tool_use":
            final = "".join(
                b.text for b in response.content if getattr(b, "type", None) == "text"
            ).strip()
            trace.append(step_record)
            stopped_by = "model_final"
            break

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            fn = tool_functions.get(block.name)
            if fn is None:
                output = {"error": f"Unknown tool: {block.name}"}
            else:
                try:
                    output = fn(**block.input)
                except Exception as exc:
                    output = {"error": f"{type(exc).__name__}: {exc}"}

            output = tool_result_to_dict(output)
            step_record["tool_calls"].append(
                {
                    "name": block.name,
                    "args": block.input,
                    "result": output,
                }
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output),
                    "is_error": "error" in output,
                }
            )

        trace.append(step_record)
        messages.append({"role": "user", "content": results})
    else:
        stopped_by = "max_steps"
        final = "Stopped: step limit reached"

    return {
        "goal": goal,
        "temperature": temperature,
        "max_steps": max_steps,
        "frozen_today": frozen_today,
        "steps": len(trace),
        "tool_order": [
            call["name"] for s in trace for call in s["tool_calls"]
        ],
        "trace": trace,
        "final_answer": final,
        "stopped_by": stopped_by,
        "tokens": {
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output,
        },
    }


def run_plain(question: str, *, temperature: float = 0.0) -> dict:
    client = make_client(temperature)
    response = client.messages.create(
        model=course.MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": question}],
    )
    answer = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    ).strip()
    inp = getattr(response.usage, "input_tokens", 0) or 0
    out = getattr(response.usage, "output_tokens", 0) or 0
    return {
        "answer": answer,
        "stop_reason": response.stop_reason,
        "tokens": {"input": inp, "output": out, "total": inp + out},
    }


def weak_get_today_specs():
    specs = copy.deepcopy(course.TOOL_SPECS)
    for spec in specs:
        if spec["name"] == "get_today":
            spec["description"] = "Returns a date."
    return specs


def write_raw(name: str, record: dict):
    p = RAW_DIR / f"{name}.txt"
    lines = [
        f"SCENARIO: {name}",
        f"MODEL: {MODEL}",
        f"STEPS: {record.get('steps', '-')}",
        f"TOOL ORDER: {record.get('tool_order', '-')}",
        f"TOKENS: {record.get('tokens', '-')}",
        "",
        "TRACE",
        "=" * 70,
    ]
    for step in record.get("trace", []):
        lines.append(f"\nSTEP {step['step']} stop_reason={step['stop_reason']}")
        if step.get("model_text"):
            lines.append(f"MODEL: {step['model_text']}")
        for call in step.get("tool_calls", []):
            lines.append(f"ACTION: {call['name']}({json.dumps(call['args'])})")
            lines.append(f"RESULT: {json.dumps(call['result'])}")
    lines.extend(["", "FINAL", "=" * 70, str(record.get("final_answer", ""))])
    p.write_text("\n".join(lines), encoding="utf-8")


def summarize_behavior(record: dict) -> str:
    if record.get("stopped_by") == "max_steps":
        return "Hit the hard step ceiling before the model returned a final answer."
    if record.get("tool_order"):
        return (
            f"Used {len(record['tool_order'])} tool call(s): "
            + " → ".join(record["tool_order"])
            + "."
        )
    return "Returned a final answer without requesting any tool."


def md_for(data: dict) -> str:
    n1, n2 = data["normal_run_1"], data["normal_run_2"]
    weak = data["weak_description"]
    missing = data["missing_order"]
    starved = data["max_steps_2"]
    plain = data["plain_call"]
    frozen = data["frozen_date_reproduction"]

    return f"""# Day 1 — Real Execution Evidence

**Model:** `{MODEL}`  
**Ollama host:** `{HOST}`  
**Evidence generated:** {date.today().isoformat()}  

> These traces were generated by a real local model call through Ollama. They are not mocked or replayed.

## Lab 1.2 — Normal run 1

- **Steps:** {n1['steps']}
- **Tool order:** {' → '.join(n1['tool_order']) or '(none)'}
- **Stopped by:** {n1['stopped_by']}
- **Input tokens:** {n1['tokens']['input']}
- **Output tokens:** {n1['tokens']['output']}
- **Total tokens:** {n1['tokens']['total']}
- **Observed behavior:** {summarize_behavior(n1)}

## Lab 1.2 — Normal run 2

- **Steps:** {n2['steps']}
- **Tool order:** {' → '.join(n2['tool_order']) or '(none)'}
- **Stopped by:** {n2['stopped_by']}
- **Input tokens:** {n2['tokens']['input']}
- **Output tokens:** {n2['tokens']['output']}
- **Total tokens:** {n2['tokens']['total']}
- **Observed behavior:** {summarize_behavior(n2)}

### Non-determinism comparison

- Run 1 path: `{' → '.join(n1['tool_order']) or '(none)'}`
- Run 2 path: `{' → '.join(n2['tool_order']) or '(none)'}`
- Same path: **{'YES' if n1['tool_order'] == n2['tool_order'] and n1['steps'] == n2['steps'] else 'NO'}**

## Dependency evidence

`count_business_days(start, end)` cannot know its concrete arguments until earlier information is available:
- `start` comes from `get_today()`;
- `end` is derived from `lookup_order()` invoice date + terms.

The stronger agentic dependency is behavioral: if `lookup_order()` returns an error, the appropriate next action changes instead of blindly continuing the happy path.

## Who decides to stop?

The model expresses the semantic stop decision through `response.stop_reason`. The orchestration code reads it at:

```python
if response.stop_reason != "tool_use":
```

The hard `MAX_STEPS` ceiling is independently owned by the program.

## Modification A — weak `get_today` description

- **Steps:** {weak['steps']}
- **Tool order:** {' → '.join(weak['tool_order']) or '(none)'}
- **Input tokens:** {weak['tokens']['input']}
- **Output tokens:** {weak['tokens']['output']}
- **Observed behavior:** {summarize_behavior(weak)}

## Modification B — order #9999

- **Steps:** {missing['steps']}
- **Tool order:** {' → '.join(missing['tool_order']) or '(none)'}
- **Stopped by:** {missing['stopped_by']}
- **Input tokens:** {missing['tokens']['input']}
- **Output tokens:** {missing['tokens']['output']}
- **Observed behavior:** {summarize_behavior(missing)}
- **Final answer:** {missing['final_answer']}

## Modification C — `MAX_STEPS = 2`

- **Steps:** {starved['steps']}
- **Tool order:** {' → '.join(starved['tool_order']) or '(none)'}
- **Stopped by:** {starved['stopped_by']}
- **Input tokens:** {starved['tokens']['input']}
- **Output tokens:** {starved['tokens']['output']}
- **Observed behavior:** {summarize_behavior(starved)}

A production agent still needs this limit because a model can wander, repeat calls, or continue searching indefinitely. The ceiling bounds cost and latency even when it occasionally truncates a valid path.

## Lab 1.3 — Plain call

- **Stop reason:** {plain['stop_reason']}
- **Input tokens:** {plain['tokens']['input']}
- **Output tokens:** {plain['tokens']['output']}
- **Total tokens:** {plain['tokens']['total']}

### Plain-call output

> {plain['answer'].replace(chr(10), chr(10) + '> ')}

## Agent versus plain-call token comparison

| Run | Input | Output | Total |
|---|---:|---:|---:|
| Plain call | {plain['tokens']['input']} | {plain['tokens']['output']} | {plain['tokens']['total']} |
| Agent run 1 | {n1['tokens']['input']} | {n1['tokens']['output']} | {n1['tokens']['total']} |

The agent's additional spend buys tool access, iterative observation, and the possibility of recovery from missing or changing information.

## Temporal reproducibility run

The supplied fixture has order `4471` invoiced on `2026-03-03` with 30-day terms, while the script uses the machine's real current date. Because that scenario becomes stale after April 2026, I also ran a **separately labelled reproduction** with `get_today()` frozen to `2026-03-24`.

- **Frozen date:** {frozen['frozen_today']}
- **Steps:** {frozen['steps']}
- **Tool order:** {' → '.join(frozen['tool_order']) or '(none)'}
- **Input tokens:** {frozen['tokens']['input']}
- **Output tokens:** {frozen['tokens']['output']}
- **Final answer:** {frozen['final_answer']}

This frozen-date run is for reproducing the teaching scenario only; it is not represented as the current date.

## Raw trace files

See `evidence/raw/` for complete per-step action/result traces.
"""


def main():
    # Quick connectivity check through the same adapter.
    try:
        client = make_client(0.0)
        check = client.messages.create(
            model=course.MODEL,
            max_tokens=32,
            messages=[{"role": "user", "content": "Reply with exactly: evidence OK"}],
        )
    except Exception as exc:
        print("ERROR: Could not reach a working Ollama model.")
        print(f"Model: {MODEL}")
        print(f"Host: {HOST}")
        print(f"Details: {exc}")
        print("\nStart Ollama and ensure the model is installed:")
        print("  ollama serve")
        print(f"  ollama pull {MODEL}")
        return 2

    normal_goal = (
        "How many business days do we have left before the invoice for "
        "order #4471 goes overdue? Show your reasoning briefly."
    )

    data = {
        "meta": {
            "model": MODEL,
            "host": HOST,
            "generated_on": date.today().isoformat(),
        },
        "normal_run_1": run_agent(normal_goal, temperature=0.5),
        "normal_run_2": run_agent(normal_goal, temperature=0.5),
        "weak_description": run_agent(
            normal_goal,
            temperature=0.0,
            tool_specs=weak_get_today_specs(),
        ),
        "missing_order": run_agent(
            "How many business days do we have left before the invoice for "
            "order #9999 goes overdue? Show your reasoning briefly.",
            temperature=0.0,
        ),
        "max_steps_2": run_agent(
            normal_goal,
            temperature=0.0,
            max_steps=2,
        ),
        "plain_call": run_plain(normal_goal, temperature=0.0),
        "frozen_date_reproduction": run_agent(
            normal_goal,
            temperature=0.0,
            frozen_today="2026-03-24",
        ),
    }

    (EVIDENCE_DIR / "day1-evidence.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (EVIDENCE_DIR / "day1-evidence.md").write_text(md_for(data), encoding="utf-8")

    for name in (
        "normal_run_1",
        "normal_run_2",
        "weak_description",
        "missing_order",
        "max_steps_2",
        "frozen_date_reproduction",
    ):
        write_raw(name, data[name])

    plain_raw = RAW_DIR / "plain_call.txt"
    plain_raw.write_text(
        f"MODEL: {MODEL}\n"
        f"TOKENS: {data['plain_call']['tokens']}\n"
        f"STOP: {data['plain_call']['stop_reason']}\n\n"
        f"{data['plain_call']['answer']}\n",
        encoding="utf-8",
    )

    print("PASS: real Day 1 execution evidence captured.")
    print(f"Markdown: {EVIDENCE_DIR / 'day1-evidence.md'}")
    print(f"JSON:     {EVIDENCE_DIR / 'day1-evidence.json'}")
    print(f"Raw:      {RAW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
