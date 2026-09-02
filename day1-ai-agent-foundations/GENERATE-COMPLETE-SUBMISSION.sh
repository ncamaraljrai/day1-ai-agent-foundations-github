#!/usr/bin/env bash
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"

command -v python3 >/dev/null || { echo "Python 3 is required." >&2; exit 1; }
command -v ollama >/dev/null || { echo "Ollama is required." >&2; exit 1; }

if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Start Ollama in another terminal with: ollama serve" >&2
  exit 1
fi

ollama pull "$MODEL"
python3 tools/capture_day1_evidence.py
python3 tools/finalize_submission.py
python3 tools/verify_completeness.py

echo
echo "COMPLETE. Submit:"
echo "submission/Day1-Foundations-Lab-Submission-FINAL.md"
