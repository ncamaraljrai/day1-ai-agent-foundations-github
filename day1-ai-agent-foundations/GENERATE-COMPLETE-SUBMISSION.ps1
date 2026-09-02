$ErrorActionPreference = "Stop"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Day 1 - Generate COMPLETE graded submission" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found on PATH." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install Ollama, then run this script again."
    exit 1
}

$model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:7b" }
Write-Host "Model: $model"

try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
}
catch {
    Write-Host "Starting Ollama server..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "[1/4] Pull/check model..." -ForegroundColor Yellow
ollama pull $model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[2/4] Run REAL Labs 1.2 and 1.3..." -ForegroundColor Yellow
python tools/capture_day1_evidence.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[3/4] Build final submission from measured evidence..." -ForegroundColor Yellow
python tools/finalize_submission.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[4/4] Verify completeness..." -ForegroundColor Yellow
python tools/verify_completeness.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host " COMPLETE - submit this file:" -ForegroundColor Green
Write-Host " submission/Day1-Foundations-Lab-Submission-FINAL.md" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
