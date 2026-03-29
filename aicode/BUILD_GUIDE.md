# BUILD GUIDE — Smart Document Categorizer

Complete instructions for building the Windows installer (.exe).

## Prerequisites

### 1. Python 3.12 (Recommended)

Python 3.14 has compatibility issues with PyInstaller. Use Python 3.12:

- Download: https://www.python.org/downloads/release/python-31211/
- Choose: "Windows installer (64-bit)"
- During install, check:
  - ✅ Add Python to PATH
  - ✅ Install for all users

If you have multiple Python versions, use `py -3.12` to target 3.12 specifically.

### 2. Inno Setup 6 (For installer — free)

- Download: https://jrsoftware.org/isinfo.php
- Install with default settings
- This creates the professional setup.exe installer

### 3. ffmpeg (For audio/video transcription)

Either:
- Run `python setup_ffmpeg.py` (auto-downloads ~90MB)
- Or download manually from https://www.gyan.dev/ffmpeg/builds/

## Build Options

### Option A: Full Installer (Recommended)

Creates a professional setup.exe with Start Menu shortcuts and uninstaller.

```cmd
cd SmartDocCategorizer
build_installer.bat
```

This automatically:
1. Installs Python dependencies
2. Downloads ffmpeg (if not present)
3. Cleans previous builds
4. Builds with PyInstaller (--onedir)
5. Removes unnecessary files (saves ~30-50%)
6. Creates installer with Inno Setup

Output: `installer_output/SmartDocCategorizer_Setup_v4.0.exe` (~80-120 MB)

### Option B: Portable Build

Creates a folder you can copy to any PC — no installation needed.

```cmd
cd SmartDocCategorizer
build.bat
```

Output: `dist/SmartDocCategorizer/SmartDocCategorizer.exe`

### Option C: Manual Build

If the batch files don't work:

```cmd
cd SmartDocCategorizer

REM 1. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM 2. Download ffmpeg
python setup_ffmpeg.py

REM 3. Build
python -m PyInstaller --onedir --windowed --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    --add-data "ffmpeg_bin\ffmpeg.exe;." ^
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
    --noupx ^
    app.py

REM 4. Clean (optional)
python cleanup_dist.py

REM 5. Create installer (optional — requires Inno Setup)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Custom App Icon

To add your own icon:
1. Create a 256x256 PNG image
2. Convert to .ico format (use https://convertio.co/png-ico/)
3. Save as `icon.ico` in the project folder
4. Rebuild — the installer will use it automatically

## Expected File Sizes

| Build Type | Size | Startup Time |
|---|---|---|
| PyInstaller --onefile (old) | ~432 MB | 15-30 seconds |
| PyInstaller --onedir (portable) | ~200 MB folder | 2-3 seconds |
| Inno Setup installer | ~80-120 MB | 2-3 seconds (after install) |

## Troubleshooting

### "failed to start embedded python interpreter"
- Cause: Python 3.14 incompatibility with PyInstaller
- Fix: Install and use Python 3.12

### "pyinstaller is not recognized"
- Fix: Use `python -m PyInstaller` instead of `pyinstaller`

### "NoneType object has no attribute write"
- Cause: PyInstaller --windowed sets sys.stderr=None
- Fix: Already handled in engine.py (_suppress_stderr)

### Blank screen when changing language
- Fix: Already handled in app.py (_rebuild_ui with column reset)

### Build is too large
- Run `python cleanup_dist.py` after PyInstaller
- Use `--exclude-module` for unused packages
- The cleanup script removes test files, docs, and type stubs

### ffmpeg not working
- Run `python setup_ffmpeg.py` to download
- Or manually place ffmpeg.exe in the `ffmpeg_bin/` folder
- The app auto-detects ffmpeg from bundled path, then system PATH

## GPU Support

For GPU acceleration (OCR + Whisper 5-10x faster):

```cmd
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

The app auto-detects GPU. If GPU fails, it falls back to CPU automatically.
