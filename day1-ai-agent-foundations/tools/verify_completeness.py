#!/usr/bin/env python3
"""Fail if the final Day 1 submission is not grader-ready."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "submission" / "Day1-Foundations-Lab-Submission-FINAL.md"

if not FINAL.exists():
    print("FAIL: final submission does not exist.")
    print("Run the evidence capture + finalizer first.")
    sys.exit(1)

text = FINAL.read_text(encoding="utf-8")
problems = []

for marker in ("TO CAPTURE", "TO MEASURE", "evidence still to capture"):
    if marker.lower() in text.lower():
        problems.append(f"incomplete marker remains: {marker}")

required_phrases = [
    "Normal run 1",
    "Normal run 2",
    "Tool order:",
    "Input tokens:",
    "Output tokens:",
    "Observed trace:",
    "Required modification (a)",
    "Required modification (b)",
    "Required modification (c)",
    "order `#9999`",
    "`MAX_STEPS = 2`",
    "Actual plain-call response",
    "Token-count comparison",
]
for phrase in required_phrases:
    if phrase not in text:
        problems.append(f"missing required evidence section: {phrase}")

# Check there are nonzero numeric input token values.
values = [int(x) for x in re.findall(r"\*\*Input tokens:\*\*\s*(\d+)", text)]
if not values or not all(v > 0 for v in values):
    problems.append("real non-zero input token counts were not found")

if problems:
    print("FAIL: submission is not complete.")
    for p in problems:
        print(" -", p)
    sys.exit(1)

print("PASS: submission is completeness-ready.")
print(f"File: {FINAL}")
print(f"Non-zero input-token measurements found: {len(values)}")
