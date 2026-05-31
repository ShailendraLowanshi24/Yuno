@echo off
REM ============================================================
REM Yuno AI Agent Orchestration Platform — Windows Setup
REM ============================================================

echo.
echo   Yuno AI Agent Orchestration Platform
echo   ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 is required. Install from https://python.org
    pause & exit /b 1
)
echo [OK] Python found

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js 18+ required. Install from https://nodejs.org
    pause & exit /b 1
)
echo [OK] Node.js found

REM .env
if not exist .env (
    copy .env.example .env
    echo [OK] Created .env - EDIT IT and add your OPENAI_API_KEY
) else (
    echo [OK] .env already exists
)

REM Python venv
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [OK] Virtual environment activated

pip install --quiet --upgrade pip
pip install --quiet -r backend\requirements.txt
echo [OK] Backend dependencies installed

cd frontend
npm install --silent
cd ..
echo [OK] Frontend dependencies installed

echo.
echo ================================================
echo  Setup complete!
echo  1. Edit .env and add your API keys
echo  2. Run: start_windows.bat
echo ================================================
pause
