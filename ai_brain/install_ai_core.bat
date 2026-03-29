@echo off
setlocal enabledelayedexpansion
title Smart Categorizer - AI Core Setup

echo ========================================================
echo   Installing Smart Categorizer AI Core (Ollama + Qwen)
echo ========================================================
echo.
echo [1/3] Downloading AI Engine (Ollama)...
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"

echo [2/3] Installing AI Engine silently...
start /wait OllamaSetup.exe /SILENT

echo [3/3] Downloading Arabic/English Qwen Brain (This may take a while depending on internet speed)...
REM Give the Ollama service a few seconds to start up in the background
timeout /t 5 /nobreak >nul
ollama pull qwen2.5:7b

echo.
echo Cleaning up temporary files...
del OllamaSetup.exe

echo ========================================================
echo   ✅ AI Core Installation Complete! 
echo   The AI Brain is now running in the background.
echo   You can now install and run the Smart Categorizer App.
echo ========================================================
pause