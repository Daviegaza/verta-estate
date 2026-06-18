# VESTRA Full System Startup
# Usage: .\start-all.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VESTRA Full System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- PostgreSQL check ---
$pg = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pg.Status -eq "Running") {
    Write-Host "  PostgreSQL:  running" -ForegroundColor Green
} else {
    Write-Host "  PostgreSQL:  NOT RUNNING" -ForegroundColor Red
}

# --- Kill old instances ---
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force 2>$null
Start-Sleep -Milliseconds 300

# --- Start Backend in new window ---
Write-Host "  Backend:     http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-NoProfile",
    "-Command", "Set-Location '$ScriptDir\backend'; Write-Host 'VESTRA Backend starting...' -ForegroundColor Cyan; Write-Host 'Docs: http://localhost:8000/docs' -ForegroundColor Yellow; .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"
) -WindowStyle Minimized

Start-Sleep -Milliseconds 500

# --- Start Frontend in new window ---
Write-Host "  Frontend:    http://localhost:3000" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-NoProfile",
    "-Command", "Set-Location '$ScriptDir\frontend-build'; Write-Host 'VESTRA Frontend starting...' -ForegroundColor Cyan; npm run dev"
) -WindowStyle Minimized

Write-Host ""
Write-Host "  Login:  demo@vestra.co.ke / demo1234" -ForegroundColor Magenta
Write-Host "  Stop:   .\stop-all.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "Both servers starting in separate windows..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
