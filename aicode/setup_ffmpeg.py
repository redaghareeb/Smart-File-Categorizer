"""
setup_ffmpeg.py — Download and setup ffmpeg for Windows
Run once before building: python setup_ffmpeg.py

Downloads ffmpeg essentials build and extracts ffmpeg.exe
to be bundled with the application.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_DIR = Path("ffmpeg_bin")


def download_ffmpeg():
    """Download and extract ffmpeg.exe for Windows."""

    if FFMPEG_DIR.exists() and (FFMPEG_DIR / "ffmpeg.exe").exists():
        print(f"✅ ffmpeg already exists at {FFMPEG_DIR / 'ffmpeg.exe'}")
        return True

    FFMPEG_DIR.mkdir(exist_ok=True)
    zip_path = FFMPEG_DIR / "ffmpeg.zip"

    print("📥 Downloading ffmpeg (~90MB)...")
    print(f"   URL: {FFMPEG_URL}")
    print("   This is a one-time download.")
    print()

    try:
        # Download with progress
        def _progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                mb = downloaded / (1024*1024)
                total_mb = total_size / (1024*1024)
                sys.stdout.write(f"\r   {mb:.0f}/{total_mb:.0f} MB ({pct:.0f}%)")
                sys.stdout.flush()

        urllib.request.urlretrieve(FFMPEG_URL, str(zip_path), reporthook=_progress)
        print("\n   ✅ Download complete")

    except Exception as e:
        print(f"\n   ❌ Download failed: {e}")
        print()
        print("   Manual download:")
        print(f"   1. Go to: {FFMPEG_URL}")
        print(f"   2. Extract ffmpeg.exe to: {FFMPEG_DIR.absolute()}")
        return False

    # Extract only ffmpeg.exe (not the full package)
    print("📦 Extracting ffmpeg.exe...")
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            for member in zf.namelist():
                basename = os.path.basename(member)
                if basename in ("ffmpeg.exe", "ffprobe.exe"):
                    # Extract to ffmpeg_bin/
                    target = FFMPEG_DIR / basename
                    with zf.open(member) as src, open(str(target), 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"   ✅ {basename}")

        # Cleanup zip
        zip_path.unlink()

        if (FFMPEG_DIR / "ffmpeg.exe").exists():
            print()
            print(f"✅ ffmpeg ready at: {FFMPEG_DIR.absolute()}")
            print(f"   Size: {(FFMPEG_DIR / 'ffmpeg.exe').stat().st_size // (1024*1024)} MB")
            return True
        else:
            print("   ❌ ffmpeg.exe not found in archive")
            return False

    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return False


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is for Windows only.")
        print("On Linux/Mac: sudo apt install ffmpeg  /  brew install ffmpeg")
        sys.exit(1)

    success = download_ffmpeg()
    if success:
        print()
        print("Next steps:")
        print("  1. Run: build_installer.bat")
        print("  2. ffmpeg will be bundled automatically with the app")
    else:
        print()
        print("ffmpeg download failed. You can:")
        print("  1. Download manually from https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract ffmpeg.exe to the ffmpeg_bin/ folder")
        print("  3. Then run build_installer.bat")
