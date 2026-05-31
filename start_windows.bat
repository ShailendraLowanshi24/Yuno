@echo off
REM Start Yuno AI on Windows

call .venv\Scripts\activate.bat

echo Starting Backend on http://localhost:8000 ...
start "Yuno Backend" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Frontend on http://localhost:5173 ...
start "Yuno Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo  Yuno AI is starting!
echo  Frontend:  http://localhost:5173
echo  Backend:   http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo.
pause
