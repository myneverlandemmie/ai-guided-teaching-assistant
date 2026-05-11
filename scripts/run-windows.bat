@echo off
REM Windows local demo starter / Windows 单机体验启动脚本占位
REM This script will be completed after the FastAPI app is implemented.
REM 正式 FastAPI 应用完成后再补充完整启动逻辑。

cd /d %~dp0\..\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
