"""
transcribe.py — Audio/Video transcription for document categorization
Uses official OpenAI Whisper (PyTorch) for ultimate stability.
"""

import os, sys, io, logging, subprocess, tempfile
from pathlib import Path

log = logging.getLogger("cto_v3")

# Audio/Video extensions
AUDIO_EXT = {".mp3",".wav",".m4a",".aac",".ogg",".flac",".wma",".opus"}
VIDEO_EXT = {".mp4",".mkv",".avi",".mov",".wmv",".flv",".webm",".mpg",".mpeg",".m4v",".3gp"}
MEDIA_EXT = AUDIO_EXT | VIDEO_EXT

_whisper_model = None
_whisper_available = None  # None = not checked, True/False = checked
_custom_ffmpeg_path = None # Store the user's custom path

def set_ffmpeg_path(path: str):
    """Allow the engine to inject a custom ffmpeg.exe path."""
    global _custom_ffmpeg_path
    if path and Path(path).is_file():
        _custom_ffmpeg_path = path

def is_available() -> bool:
    """Check if official openai-whisper is installed."""
    global _whisper_available
    if _whisper_available is None:
        try:
            import whisper
            _whisper_available = True
        except ImportError:
            _whisper_available = False
    return _whisper_available

_ffmpeg_path = None  # cached path to ffmpeg executable

def _find_ffmpeg() -> str | None:
    """Find ffmpeg: custom path first, then bundled, then system PATH."""
    global _ffmpeg_path, _custom_ffmpeg_path
    
    if _custom_ffmpeg_path and Path(_custom_ffmpeg_path).exists():
        return _custom_ffmpeg_path

    if _ffmpeg_path is not None:
        return _ffmpeg_path

    candidates = []
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
        candidates.append(app_dir / "ffmpeg.exe")
        candidates.append(app_dir / "ffmpeg_bin" / "ffmpeg.exe")
        candidates.append(app_dir / "_internal" / "ffmpeg.exe")
    
    script_dir = Path(__file__).parent
    candidates.append(script_dir / "ffmpeg_bin" / "ffmpeg.exe")
    candidates.append(script_dir / "ffmpeg.exe")

    for c in candidates:
        if c.exists():
            _ffmpeg_path = str(c)
            log.info("  ffmpeg: %s (bundled)", _ffmpeg_path)
            return _ffmpeg_path

    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        if result.returncode == 0:
            _ffmpeg_path = "ffmpeg"
            return _ffmpeg_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    log.warning("  ⚠ ffmpeg not found — video transcription disabled")
    return None

def _check_ffmpeg() -> bool:
    return _find_ffmpeg() is not None

def _get_model(model_size="medium", gpu=False):
    """Lazy-load Official Whisper model."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        import whisper
        import torch

        # Use PyTorch device logic (same as your OCR, guaranteeing stability)
        device = "cuda" if gpu and torch.cuda.is_available() else "cpu"

        log.info("تحميل نموذج Whisper الرسمي (%s) على %s ...", model_size, device)
        log.info("  ⏳ يرجى الانتظار، جاري إعداد النموذج...")

        # Load the official model
        _whisper_model = whisper.load_model(model_size, device=device)
        
        log.info("  ✅ Whisper جاهز (%s, %s)", model_size, device)
        return _whisper_model

    except Exception as e:
        log.warning("فشل تحميل Whisper: %s", e)
        return None

def _extract_audio(video_path: str, max_duration: int = 300) -> str | None:
    """Extract audio from video using ffmpeg."""
    if not _check_ffmpeg():
        return None

    ffmpeg = _find_ffmpeg()
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        cmd = [
            ffmpeg, "-i", video_path,
            "-t", str(max_duration),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            tmp.name,
        ]

        result = subprocess.run(
            cmd, capture_output=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode == 0 and Path(tmp.name).stat().st_size > 1000:
            return tmp.name
        else:
            os.unlink(tmp.name)
            return None
    except Exception as e:
        try: os.unlink(tmp.name)
        except: pass
        return None

def transcribe_file(filepath: str, gpu=False, max_duration=300, model_size="medium") -> dict:
    """Transcribe using Official OpenAI Whisper."""
    empty = {"text": "", "language": "unknown", "duration": 0, "segments": 0}

    if not is_available():
        return empty

    ext = Path(filepath).suffix.lower()
    audio_path = filepath
    is_video = ext in VIDEO_EXT
    
    if is_video:
        audio_path = _extract_audio(filepath, max_duration)
        if not audio_path:
            return empty

    try:
        model = _get_model(model_size, gpu)
        if model is None:
            return empty

        # Official Whisper transcription call
        # FP16 is disabled on CPU to prevent PyTorch warnings/errors
        import torch
        fp16_enabled = True if gpu and torch.cuda.is_available() else False

        result = model.transcribe(
            audio_path,
            fp16=fp16_enabled,
            condition_on_previous_text=True,
            initial_prompt="هذا ملف صوتي يحتوي على محتوى باللغة العربية أو الإنجليزية"
        )

        # The official library returns the full text directly!
        full_text = result.get("text", "").strip()
        detected_lang = result.get("language", "unknown")
        
        # Simple safety cutoff for massive texts
        if len(full_text) > 15000:
            full_text = full_text[:15000]

        return {
            "text": full_text,
            "language": detected_lang,
            "duration": 0, # Official simple transcribe doesn't return easy duration
            "segments": len(result.get("segments", [])),
        }

    except Exception as e:
        log.debug("Transcription failed for %s: %s", filepath, e)
        return empty

    finally:
        if is_video and audio_path and audio_path != filepath:
            try: os.unlink(audio_path)
            except: pass

def transcribe_text_only(filepath: str, gpu=False, max_duration=300, model_size="medium") -> str:
    """Convenience: just return the text, or empty string."""
    result = transcribe_file(filepath, gpu, max_duration, model_size)
    return result.get("text", "")