#!/usr/bin/env bash
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Install it from https://ollama.com/download" >&2
  exit 1
fi

if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Start Ollama in another terminal: ollama serve" >&2
  exit 1
fi

ollama pull "$MODEL"
python3 tools/capture_day1_evidence.py
echo "Evidence written to evidence/day1-evidence.md"
