@echo off
setlocal

set "REPO_WIN=%~dp0"

for /f "usebackq delims=" %%i in (`wsl wslpath -a "%REPO_WIN%"`) do set "REPO_WSL=%%i"

if "%REPO_WSL%"=="" (
    echo Failed to convert project path with wslpath.
    pause
    exit /b 1
)

echo 此操作会删除本地运行数据库、上传文件和导出文件，但不会删除源码。
echo.
echo Project root:
echo %REPO_WSL%
echo.
pause

wsl bash -lc "cd ""%REPO_WSL%"" && rm -f backend/app.db && mkdir -p data/uploads data/exports && find data/uploads -mindepth 1 ! -name .gitkeep ! -name .gitignore -exec rm -rf {} + && find data/exports -mindepth 1 ! -name .gitkeep ! -name .gitignore -exec rm -rf {} + && mkdir -p data/uploads data/exports/chaoxing data/exports/guides && touch data/uploads/.gitkeep data/exports/chaoxing/.gitkeep data/exports/guides/.gitkeep && echo ""---- git status --short ----"" && git status --short && echo ""---- data/uploads ----"" && find data/uploads -maxdepth 2 -print && echo ""---- data/exports ----"" && find data/exports -maxdepth 3 -print"

echo.
echo Clean finished.
pause
