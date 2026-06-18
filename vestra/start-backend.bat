@echo off
REM VESTRA Backend Startup (double-click to run)
cd /d "%~dp0backend"

echo ========================================
echo   VESTRA Backend API
echo ========================================
echo.
echo Starting FastAPI server...
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo.

venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
pause
