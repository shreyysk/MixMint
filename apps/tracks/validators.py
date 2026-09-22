import os
from django.core.exceptions import ValidationError

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",  # MP3
    "audio/aiff",
    "audio/x-aiff",
    "application/zip",
    "application/x-zip-compressed",  # Album ZIPs
}
MAX_TRACK_SIZE_MB = 500  # 500MB max per track


def validate_audio_file(file):
    """Validate file MIME type using magic bytes, falling back to header bytes and extension."""
    if file.size > MAX_TRACK_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File too large. Maximum {MAX_TRACK_SIZE_MB}MB.")

    mime = None
    try:
        import magic

        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
    except Exception:
        # Fallback to header inspection
        file.seek(0)
        header = file.read(2048)
        file.seek(0)

        # Check WAV (starts with RIFF and has WAVE)
        if header.startswith(b"RIFF") and b"WAVE" in header[:16]:
            mime = "audio/wav"
        # Check ZIP (starts with PK\x03\x04)
        elif header.startswith(b"PK\x03\x04"):
            mime = "application/zip"
        # Check MP3 (starts with ID3 or \xff\xfb or \xff\xf3)
        elif header.startswith(b"ID3") or header.startswith(b"\xff\xfb") or header.startswith(b"\xff\xf3"):
            mime = "audio/mpeg"
        # Check AIFF (starts with FORM and has AIFF)
        elif header.startswith(b"FORM") and b"AIFF" in header[:16]:
            mime = "audio/aiff"
        else:
            # Last resort fallback: check file extension
            ext = os.path.splitext(file.name)[1].lower()
            if ext == ".wav":
                mime = "audio/wav"
            elif ext == ".mp3":
                mime = "audio/mpeg"
            elif ext in (".zip", ".zipx"):
                mime = "application/zip"
            elif ext in (".aif", ".aiff"):
                mime = "audio/aiff"

    if not mime or mime not in ALLOWED_AUDIO_TYPES:
        raise ValidationError(f"Invalid file type: {mime or 'unknown'}. Only WAV, MP3, AIFF, ZIP allowed.")
