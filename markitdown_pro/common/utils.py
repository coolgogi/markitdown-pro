import re
from pathlib import Path


def detect_extension(file_path: str) -> str:
    """Return the file extension in lowercase."""
    return Path(file_path).suffix.lower()


def is_pdf(file_path: str) -> bool:
    """Check if the file is a PDF."""
    return detect_extension(file_path) == ".pdf"


def is_image(file_path: str) -> bool:
    """Check if the file is an image based on its extension."""
    return detect_extension(file_path) in (
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tiff",
        ".gif",
        ".heic",
        ".webp",
    )


def is_audio(file_path: str) -> bool:
    """Check if the file is an audio file based on its extension."""
    return detect_extension(file_path) in (".mp3", ".wav", ".m4a", ".ogg", ".flac")


def is_zip(file_path: str) -> bool:
    """Check if the file is a ZIP archive."""
    return detect_extension(file_path) == ".zip"


def is_eml(file_path: str) -> bool:
    """Check if the file is an EML email file."""
    return detect_extension(file_path) == ".eml"


def clean_markdown(md_text: str) -> str:
    """
    Clean up Markdown text by removing trailing spaces and reducing excess newlines.
    """
    md_text = re.sub(r"[ \t]+(\r?\n)", r"\1", md_text)
    md_text = re.sub(r"\n{3,}", "\n\n", md_text)
    return md_text.strip()


def ensure_minimum_content(md_text: str) -> bool:
    """
    Check if the Markdown text has non-trivial content.
    """
    if not md_text:
        return False
    return bool(md_text and len(md_text.strip()) > 30)
