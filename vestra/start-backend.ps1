# VESTRA Backend Startup
# Double-click start-backend.bat or run: .\start-backend.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VESTRA Backend API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Health:    http://localhost:8000/health" -ForegroundColor Yellow
Write-Host ""

Set-Location "$ScriptDir\backend"
& .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
