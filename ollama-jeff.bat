@echo off
REM ollama-jeff.bat — Drop this in your PATH
REM Mimics 'ollama launch jeff' locally
REM Put in: C:\Users\slows\AppData\Local\Microsoft\WindowsApps\
REM Or add A:\AI\jeff-release to PATH

REM Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
)

REM Check model
ollama list 2>nul | findstr "hermes3:8b" >nul 2>&1
if %errorlevel% neq 0 (
    echo Pulling hermes3:8b...
    ollama pull hermes3:8b
)

REM Launch Jeff
jeff %*
