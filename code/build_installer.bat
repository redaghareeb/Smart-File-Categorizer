@echo off
setlocal enabledelayedexpansion
echo.
echo ========================================================
echo   Smart Document Categorizer - Installer Builder
echo ========================================================
echo.

REM -- Check Python version --
python --version 2>nul | findstr "3.14" >nul
if %errorlevel% equ 0 (
    echo [WARNING] Python 3.14 detected - may have PyInstaller issues.
    echo Recommended: use Python 3.12 for building.
    echo.
    set /p "CONT=Continue with 3.14 anyway? (y/n): "
    if /i not "!CONT!"=="y" exit /b 1
)

REM -- Step 1: Install dependencies --
echo [1/5] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo        Done.
echo.

REM -- Step 2: Setup ffmpeg --
echo [2/5] Checking ffmpeg...
if exist "ffmpeg_bin\ffmpeg.exe" (
    echo        ffmpeg already present.
) else (
    echo        Downloading ffmpeg...
    python setup_ffmpeg.py
)
echo.

REM -- Step 3: Clean previous builds --
echo [3/5] Cleaning previous builds...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist\SmartDocCategorizer" rmdir /s /q "dist\SmartDocCategorizer" >nul 2>&1
echo        Done.
echo.

REM -- Step 4: Build with PyInstaller --
echo [4/5] Building application (this may take a few minutes)...
echo.

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" (
    set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."
)

REM The PyInstaller command must be on one single line (distutils removed!)
python -m PyInstaller --onedir --windowed --name "SmartDocCategorizer" --icon="icon.ico" --add-data "icon.ico;." --add-data "engine.py;." --add-data "i18n.py;." --add-data "categories.py;." --add-data "transcribe.py;." %FFMPEG_DATA% --hidden-import customtkinter --hidden-import CTkMessagebox --hidden-import docx --hidden-import pdfplumber --hidden-import openpyxl --hidden-import pptx --hidden-import PIL --hidden-import hashlib --collect-all customtkinter --exclude-module matplotlib --exclude-module scipy --exclude-module numpy.tests --exclude-module setuptools --exclude-module pip --exclude-module pytest --exclude-module unittest --exclude-module tkinter.test --noupx app.py

if not exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    echo.
    echo ===================================
    echo   BUILD FAILED - check errors above
    echo ===================================
    pause
    exit /b 1
)

echo.
echo        PyInstaller build complete.
echo        Cleaning dist folder...
python cleanup_dist.py 2>nul
echo.

REM -- Step 5: Create installer with Inno Setup --
echo [5/5] Creating installer...
echo.

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    echo    Inno Setup not found.
    echo    Your app is ready as portable in: dist\SmartDocCategorizer\
    pause
    exit /b 0
)

if not exist "installer_output" mkdir "installer_output"

if not exist "icon.ico" (
    powershell -Command "(Get-Content installer.iss) -replace 'SetupIconFile=icon.ico', '; SetupIconFile=icon.ico' | Set-Content installer_temp.iss"
    "!ISCC!" installer_temp.iss
    del installer_temp.iss >nul 2>&1
) else (
    "!ISCC!" installer.iss
)

echo.
echo ========================================================
if exist "installer_output\SmartDocCategorizer_Setup_v1.0.exe" (
    echo   SUCCESS: INSTALLER CREATED!
    echo   Location: installer_output\SmartDocCategorizer_Setup_v1.0.exe
) else (
    echo   Installer creation failed. Portable build is in: dist\SmartDocCategorizer\
)
echo ========================================================
pause