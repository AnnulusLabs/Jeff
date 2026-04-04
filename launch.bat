@echo off
REM Jeff Launcher — Steve's Rig
REM 9950X3D + RTX 3090 (24GB) + Ollama
REM A:\AI\jeff\launch.bat

echo.
echo     ┌──────────┐
echo     │  ·    ·  │   My name Jeff.
echo     │    ──    │   I handle it.
echo     └────┬─────┘
echo     ┌────┴─────┐
echo     │  [JEFF]  │   24GB VRAM · Solar Powered
echo     └──────────┘
echo.

REM Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama not running. Starting...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
)

REM Check if jeff is installed
where jeff >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Jeff not installed. Installing...
    pip install -e "A:\AI\jeff-release[workplay]"
)

REM Launch
jeff %*
