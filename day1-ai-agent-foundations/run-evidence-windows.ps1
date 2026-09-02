$ErrorActionPreference = "Stop"

Write-Host "Day 1 evidence capture - Ollama" -ForegroundColor Cyan

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "Ollama is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install it from: https://ollama.com/download"
    exit 1
}

$model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:7b" }

Write-Host "Using model: $model"

# Check whether Ollama API responds; start it if needed.
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
}
catch {
    Write-Host "Starting Ollama server..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 4
}

Write-Host "Ensuring model is available..."
ollama pull $model

Write-Host ""
Write-Host "Capturing REAL traces and token counts..." -ForegroundColor Yellow
python tools/capture_day1_evidence.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Open: evidence/day1-evidence.md"
