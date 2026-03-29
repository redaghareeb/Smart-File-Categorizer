@echo off
setlocal enabledelayedexpansion
echo.
echo ════════════════════════════════════════════════
echo   Smart Document Categorizer — Portable Build
echo ════════════════════════════════════════════════
echo.
echo   For a proper setup.exe: run build_installer.bat
echo.

pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

REM ffmpeg
if not exist "ffmpeg_bin\ffmpeg.exe" (
    echo Downloading ffmpeg...
    python setup_ffmpeg.py
)

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."

echo Building...
python -m PyInstaller --onedir ^
    --windowed ^
    --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    %FFMPEG_DATA% ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module pip ^
    --exclude-module setuptools ^
    --noupx ^
    app.py

if exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    python cleanup_dist.py 2>nul
    echo.
    echo ═══════════════════════════════════════════
    echo   ✅ Portable build ready!
    echo   📂 dist\SmartDocCategorizer\
    echo ═══════════════════════════════════════════
) else (
    echo   ❌ BUILD FAILED
)
pause
