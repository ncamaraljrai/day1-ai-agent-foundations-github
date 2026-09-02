# Completeness Feedback — Fix Plan

The grader feedback is correct: the current written submission contains strong analysis but is not complete because several Lab 1.2 / 1.3 observations are placeholders rather than measured results.

## To move Completeness toward full credit

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-evidence-windows.ps1
```

or on macOS/Linux:

```bash
./run-evidence.sh
```

Then use `evidence/day1-evidence.md` to replace every:

- `TO CAPTURE LOCALLY`
- `TO MEASURE`

in `docs/Day1-Foundations-Lab-Submission.md`.

Do not invent those values. The course explicitly grades actual execution behavior.

## Evidence generated automatically

- model name
- run date
- steps per run
- tool-call order
- stop reason
- input tokens
- output tokens
- full raw action/result traces
- normal run ×2
- weak tool-description experiment
- missing-order error-path experiment
- `MAX_STEPS=2` experiment
- plain-call comparison
- separately labelled frozen-date reproduction
