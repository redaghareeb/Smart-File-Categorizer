"""
cleanup_dist.py — Reduce PyInstaller dist size by removing unnecessary files
Run after PyInstaller build: python cleanup_dist.py

Typically saves 30-50% of the dist folder size.
"""

import os
import shutil
from pathlib import Path

DIST_DIR = Path("dist/SmartDocCategorizer")

# Patterns to delete (case-insensitive)
DELETE_PATTERNS = [
    # Test files
    "**/test_*", "**/tests/**", "**/*_test.py",
    # Documentation
    "**/*.md", "**/*.txt", "**/*.rst",
    # Unnecessary locales (keep English + Arabic)
    "**/locales/**",
    # Debug symbols
    "**/*.pdb",
    # Duplicate DLLs / large unnecessary libs
    "**/msvcp140_1.dll",  # already in system
    "**/ucrtbase.dll",     # already in system
]

# Folders to delete entirely
DELETE_FOLDERS = [
    "tcl/tzdata",          # timezone data (not needed)
    "tcl/msgs",            # tcl messages (not needed)
    "tk/msgs",             # tk messages
    "numpy/tests",
    "numpy/f2py",
    "numpy/distutils",
    "PIL/tests",
    "docx/tests",
    "pptx/tests",
    "openpyxl/tests",
    "pdfminer/tests",
    "share/jupyter",
    "share/man",
    "include",
    "Scripts",
]

# File extensions to delete
DELETE_EXTENSIONS = {
    ".pyc",   # compiled python (already bundled)
    ".pyo",
    ".pyi",   # type stubs
    ".c",     # C source files
    ".h",     # C headers
    ".html",  # documentation
    ".map",   # source maps
}

def cleanup():
    if not DIST_DIR.exists():
        print(f"Dist directory not found: {DIST_DIR}")
        return

    before_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    deleted_count = 0
    freed = 0

    # Delete folders
    for folder_pattern in DELETE_FOLDERS:
        for folder in DIST_DIR.glob(f"**/{folder_pattern}"):
            if folder.is_dir():
                size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                shutil.rmtree(folder, ignore_errors=True)
                freed += size
                deleted_count += 1
                print(f"  🗑️ {folder.relative_to(DIST_DIR)} ({size//1024:,} KB)")

    # Delete by extension
    for f in list(DIST_DIR.rglob("*")):
        if f.is_file() and f.suffix.lower() in DELETE_EXTENSIONS:
            size = f.stat().st_size
            f.unlink()
            freed += size
            deleted_count += 1

    after_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())

    print(f"\n{'═'*50}")
    print(f"  Before: {before_size // (1024*1024):,} MB")
    print(f"  After:  {after_size // (1024*1024):,} MB")
    print(f"  Saved:  {freed // (1024*1024):,} MB ({deleted_count} items)")
    print(f"{'═'*50}")


if __name__ == "__main__":
    cleanup()
