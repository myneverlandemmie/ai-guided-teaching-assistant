@echo off
setlocal

set "REPO_WIN=%~dp0"

for /f "usebackq delims=" %%i in (`wsl wslpath -a "%REPO_WIN%"`) do set "REPO_WSL=%%i"

if "%REPO_WSL%"=="" (
    echo Failed to convert project path with wslpath.
    pause
    exit /b 1
)

echo Starting 智学导评 V0.2 from:
echo %REPO_WSL%
echo.
echo The browser will open:
echo http://127.0.0.1:8000/ui-v2/courses
echo.

start "" cmd /c "timeout /t 5 /nobreak >nul & start http://127.0.0.1:8000/ui-v2/courses"

wsl bash -lc "sleep 3; cd ""%REPO_WSL%/backend"" && AI_PROVIDER=deepseek PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

pause
