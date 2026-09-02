#!/usr/bin/env python3
"""
Generate the FINAL Day 1 submission from REAL evidence produced by
tools/capture_day1_evidence.py.

Refuses to create the final file if evidence is missing or incomplete.

Usage:
    python tools/finalize_submission.py

Output:
    submission/Day1-Foundations-Lab-Submission-FINAL.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs" / "Day1-Foundations-Lab-Submission.md"
EVIDENCE = ROOT / "evidence" / "day1-evidence.json"
OUTDIR = ROOT / "submission"
FINAL = OUTDIR / "Day1-Foundations-Lab-Submission-FINAL.md"


def require(cond, message):
    if not cond:
        raise SystemExit(f"ERROR: {message}")


def tool_path(record):
    order = record.get("tool_order") or []
    return " → ".join(order) if order else "(none)"


def calls_by_step(record):
    rows = []
    for step in record.get("trace", []):
        calls = step.get("tool_calls", [])
        if not calls:
            rows.append(
                f"- Step {step['step']}: no tool call; "
                f"`stop_reason={step.get('stop_reason')}`"
            )
            continue
        for call in calls:
            rows.append(
                f"- Step {step['step']}: `{call['name']}("
                f"{json.dumps(call.get('args', {}), ensure_ascii=False)})` "
                f"→ `{json.dumps(call.get('result', {}), ensure_ascii=False)}`"
            )
    return "\n".join(rows)


def observed_behavior(record):
    if record.get("stopped_by") == "max_steps":
        return "The orchestration code stopped the run at the configured hard step ceiling."
    order = record.get("tool_order") or []
    if order:
        return (
            f"The model requested {len(order)} tool call(s) in the path "
            f"`{tool_path(record)}` before returning or stopping."
        )
    return "The model returned without requesting a tool."


def main():
    require(DRAFT.exists(), f"missing draft: {DRAFT}")
    require(EVIDENCE.exists(), (
        "real evidence has not been captured yet. Run "
        "`python tools/capture_day1_evidence.py` first."
    ))

    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    required_records = [
        "normal_run_1",
        "normal_run_2",
        "weak_description",
        "missing_order",
        "max_steps_2",
        "plain_call",
        "frozen_date_reproduction",
    ]
    for name in required_records:
        require(name in data, f"evidence record missing: {name}")

    for name in [
        "normal_run_1",
        "normal_run_2",
        "weak_description",
        "missing_order",
        "max_steps_2",
        "frozen_date_reproduction",
    ]:
        r = data[name]
        require(isinstance(r.get("steps"), int) and r["steps"] > 0,
                f"{name}: no real step count")
        require("tokens" in r, f"{name}: token usage missing")
        require(r["tokens"].get("input", 0) > 0,
                f"{name}: input token count is zero/missing")
        require(r["tokens"].get("output", 0) >= 0,
                f"{name}: output token count missing")
        require(r.get("stopped_by") in {"model_final", "max_steps"},
                f"{name}: stop evidence missing")

    plain = data["plain_call"]
    require(plain.get("tokens", {}).get("input", 0) > 0,
            "plain_call: input token count missing")
    require(isinstance(plain.get("answer"), str) and plain["answer"].strip(),
            "plain_call: output text missing")

    n1 = data["normal_run_1"]
    n2 = data["normal_run_2"]
    weak = data["weak_description"]
    missing = data["missing_order"]
    starved = data["max_steps_2"]
    frozen = data["frozen_date_reproduction"]
    meta = data.get("meta", {})

    same_path = (
        n1.get("tool_order") == n2.get("tool_order")
        and n1.get("steps") == n2.get("steps")
    )

    lab12_13 = f"""# Lab 1.2 — Build and run a real agent loop

## Execution environment

- **Real model runtime:** Ollama
- **Model:** `{meta.get('model', 'unknown')}`
- **Evidence date:** `{meta.get('generated_on', 'unknown')}`
- **Evidence source:** real execution through the course `ollama_shim.py`
- **Raw traces:** `evidence/raw/`

No run data in this section is mocked or inferred.

## 1. How many steps did it take, and which tools did it call?

### Normal run 1

- **Steps:** {n1['steps']}
- **Tool order:** `{tool_path(n1)}`
- **Stopped by:** `{n1['stopped_by']}`
- **Input tokens:** {n1['tokens']['input']}
- **Output tokens:** {n1['tokens']['output']}
- **Total tokens:** {n1['tokens']['total']}

Observed trace:

{calls_by_step(n1)}

### Normal run 2

- **Steps:** {n2['steps']}
- **Tool order:** `{tool_path(n2)}`
- **Stopped by:** `{n2['stopped_by']}`
- **Input tokens:** {n2['tokens']['input']}
- **Output tokens:** {n2['tokens']['output']}
- **Total tokens:** {n2['tokens']['total']}

Observed trace:

{calls_by_step(n2)}

## 2. Find the dependency

The concrete arguments for `count_business_days(start, end)` depend on earlier observations:

- `start` is supplied by `get_today()`;
- `end` is derived from the invoice date and payment terms returned by `lookup_order()`.

The stronger agentic dependency appears on the error path: if `lookup_order()` reports that the order does not exist, the correct next action is no longer the same happy-path calculation. The model must respond to the observation rather than blindly execute a predetermined continuation.

## 3. Who decided to stop?

The model communicates its semantic decision through `response.stop_reason`. The orchestration code reads it here:

```python
if response.stop_reason != "tool_use":
```

The model therefore chooses whether it needs another tool or is ready to answer. Separately, my code owns the hard safety ceiling through `MAX_STEPS`.

## 4. Run it twice — non-determinism

- Run 1: `{tool_path(n1)}` in **{n1['steps']}** step(s)
- Run 2: `{tool_path(n2)}` in **{n2['steps']}** step(s)
- Same path and step count: **{'YES' if same_path else 'NO'}**

The important observation is empirical rather than assumed: these are the two paths actually returned by the local model.

---

## Required modification (a) — weaken `get_today` description

I changed the description to:

```text
Returns a date.
```

### Actual run

- **Steps:** {weak['steps']}
- **Tool order:** `{tool_path(weak)}`
- **Stopped by:** `{weak['stopped_by']}`
- **Input tokens:** {weak['tokens']['input']}
- **Output tokens:** {weak['tokens']['output']}

Observed trace:

{calls_by_step(weak)}

**Result:** {observed_behavior(weak)}

This experiment isolates prompt/tool-description quality because the underlying Python implementation of `get_today()` is unchanged.

---

## Required modification (b) — order `#9999`

### Actual run

- **Steps:** {missing['steps']}
- **Tool order:** `{tool_path(missing)}`
- **Stopped by:** `{missing['stopped_by']}`
- **Input tokens:** {missing['tokens']['input']}
- **Output tokens:** {missing['tokens']['output']}

Observed trace:

{calls_by_step(missing)}

### Final model response

> {str(missing.get('final_answer', '')).replace(chr(10), chr(10) + '> ')}

The tool returns an informative error rather than crashing. This gives the model an observation it can use to stop, clarify, recover, or—if it behaves poorly—expose that failure in the trace.

---

## Required modification (c) — `MAX_STEPS = 2`

### Actual run

- **Steps:** {starved['steps']}
- **Tool order:** `{tool_path(starved)}`
- **Stopped by:** `{starved['stopped_by']}`
- **Input tokens:** {starved['tokens']['input']}
- **Output tokens:** {starved['tokens']['output']}

Observed trace:

{calls_by_step(starved)}

**Why the ceiling is still required:** even when a low ceiling truncates a legitimate path, a production agent needs a hard bound so a wandering model cannot make unlimited calls, accumulate cost and latency indefinitely, or repeat actions forever.

---

# Lab 1.3 — Compare a plain call against the agent

## 1. What did the plain call do?

- **Stop reason:** `{plain.get('stop_reason')}`
- **Input tokens:** {plain['tokens']['input']}
- **Output tokens:** {plain['tokens']['output']}
- **Total tokens:** {plain['tokens']['total']}

### Actual plain-call response

> {plain['answer'].replace(chr(10), chr(10) + '> ')}

The response above is the actual local-model output with **no tools available**.

## 2. If it produced numbers, are they real?

The fixture in `agent_loop.py` says:

- order `4471`
- invoiced `2026-03-03`
- payment terms `30 days`
- customer `Northwind Ltd`

Any order fact in the plain response that is not present in those supplied facts or in the user prompt is unsupported. I evaluate the output against that fixture rather than accepting fluent arithmetic as evidence.

## 3. Token-count comparison

| Run | Input tokens | Output tokens | Total |
|---|---:|---:|---:|
| Plain call | {plain['tokens']['input']} | {plain['tokens']['output']} | {plain['tokens']['total']} |
| Agent — normal run 1 | {n1['tokens']['input']} | {n1['tokens']['output']} | {n1['tokens']['total']} |
| Agent — normal run 2 | {n2['tokens']['input']} | {n2['tokens']['output']} | {n2['tokens']['total']} |

The extra spend bought iterative access to real tool outputs and the ability to choose subsequent actions based on observations. That cost is justified only when the missing/current facts and adaptive path are actually necessary.

## 4. One variant where a plain call is the correct design

> “Given the invoice date, due date, today's date, and holiday list below, explain the business-day calculation in two sentences.”

All facts are supplied in the prompt, so no runtime lookup or adaptive loop is needed.

---

## Reproducibility check for the course's March scenario

The original fixture becomes temporally stale because `get_today()` uses the machine's current date. I therefore kept the required real-current-date runs above and made one **separately labelled** reproduction with `get_today()` frozen to `2026-03-24`.

- **Frozen date:** `{frozen.get('frozen_today')}`
- **Steps:** {frozen['steps']}
- **Tool order:** `{tool_path(frozen)}`
- **Input tokens:** {frozen['tokens']['input']}
- **Output tokens:** {frozen['tokens']['output']}

### Final response from frozen-date reproduction

> {str(frozen.get('final_answer', '')).replace(chr(10), chr(10) + '> ')}

This run exists only to reproduce the teaching scenario. It is not represented as the current date.

---

"""

    draft = DRAFT.read_text(encoding="utf-8")

    # Replace status/integrity note.
    draft = re.sub(
        r"\*\*Submission status:\*\*.*?\n\n> \*\*Execution integrity note:\*\*.*?\n",
        "**Submission status:** Complete — written analysis plus real Lab 1.2/1.3 execution evidence.\n\n"
        "> **Execution integrity note:** The execution traces, paths, stop reasons, and token counts in Labs 1.2 and 1.3 were captured from real local-model runs through Ollama using the course adapter. Raw traces are retained under `evidence/raw/`.\n",
        draft,
        flags=re.S,
    )

    # Replace entire Lab 1.2 + Lab 1.3 section up to Lab 1.4.
    pattern = re.compile(
        r"# Lab 1\.2 — Build and run a real agent loop.*?(?=# Lab 1\.4 — Design with the patterns)",
        re.S,
    )
    draft, count = pattern.subn(lab12_13, draft)
    require(count == 1, f"expected one Lab 1.2/1.3 block to replace, found {count}")

    # Remove old remaining-run checklist if still present.
    draft = re.sub(
        r"\n# Remaining run evidence checklist.*\Z",
        "\n",
        draft,
        flags=re.S,
    )

    forbidden = [
        "TO CAPTURE",
        "TO MEASURE",
        "still require one real model run",
        "run evidence still to capture",
    ]
    for marker in forbidden:
        require(marker not in draft, f"final document still contains incomplete marker: {marker}")

    # Ensure evidence-bearing fields exist.
    require("Input tokens:" in draft, "final document lacks token evidence")
    require("Tool order:" in draft, "final document lacks tool-order evidence")
    require("Observed trace:" in draft, "final document lacks execution traces")
    require("Normal run 2" in draft, "final document lacks second-run evidence")
    require("order `#9999`" in draft, "final document lacks error-path experiment")
    require("`MAX_STEPS = 2`" in draft, "final document lacks max-step experiment")

    OUTDIR.mkdir(exist_ok=True)
    FINAL.write_text(draft, encoding="utf-8")

    print("PASS: FINAL submission generated from real execution evidence.")
    print(FINAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
