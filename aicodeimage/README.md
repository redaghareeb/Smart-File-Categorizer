# Smart Document Categorizer v4.0

**Organize, classify, and discover your files — powered by AI**

Arabic-first desktop application that automatically categorizes documents, images, audio, and video files into organized folders using keyword-based content analysis with OCR and speech-to-text.

## Project Files

```
SmartDocCategorizer/
├── app.py              ← Main GUI application (CustomTkinter)
├── engine.py           ← Classification engine (keyword matching, NLP)
├── categories.py       ← Category definitions, 21 role presets, 72 file types
├── i18n.py             ← Bilingual strings (Arabic / English)
├── transcribe.py       ← Audio/Video transcription (Whisper)
├── setup_ffmpeg.py     ← Auto-download ffmpeg for Windows
├── cleanup_dist.py     ← Post-build size optimizer
├── build.bat           ← Portable build (PyInstaller --onedir)
├── build_installer.bat ← Full installer build (PyInstaller + Inno Setup)
├── installer.iss       ← Inno Setup script
├── requirements.txt    ← Python dependencies
├── BUILD_GUIDE.md      ← Developer build instructions
└── USER_MANUAL.md      ← End-user guide
```

## Quick Start (Development)

```bash
pip install -r requirements.txt
python app.py
```

## Build Windows Installer

See BUILD_GUIDE.md for complete instructions.

## Features

- 23 default categories with Arabic + English keywords
- 21 job role presets (CTO, PM, BA, Developer, PhD, AV Manager, etc.)
- 72 file types across 11 groups (dynamically configurable)
- Multi-source folders — scan multiple locations at once
- OCR for images and scanned PDFs (EasyOCR)
- Audio/Video transcription via Whisper (Arabic optimized)
- 4-layer duplicate detection (size → partial hash → full hash → metadata)
- Bilingual UI (Arabic default, English available)
- RTL support for Arabic interface
- GPU acceleration for OCR and transcription
- Move or Copy mode with resume support
- Professional Windows installer with Inno Setup

## Author

Reda Ghareeb
- PayPal: paypal.me/redaghareeb
- Patreon: patreon.com/redaghareeb
- GitHub: github.com/redaghareeb
