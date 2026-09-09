"""
Document storage service: filesystem operations for uploaded documents.
All file I/O is isolated here so it can be swapped for cloud storage later.
"""
import os
import uuid

from app.config import settings


def _ensure_storage_dir() -> str:
    """Create the document storage directory if it does not exist and return its absolute path."""
    storage_dir = os.path.abspath(settings.DOCUMENT_STORAGE_PATH)
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def generate_stored_filename(original_filename: str) -> str:
    """
    Generate a unique, safe filename using UUID4.
    Preserves the original extension for convenience but never trusts the stem.
    """
    ext = os.path.splitext(original_filename)[1].lower()  # e.g. ".pdf"
    return f"{uuid.uuid4().hex}{ext}"


def save_file(stored_filename: str, content: bytes) -> str:
    """
    Write file bytes to the storage directory.

    Returns:
        The full path to the stored file (for DB record).
    """
    storage_dir = _ensure_storage_dir()
    file_path = os.path.join(storage_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def delete_file(storage_path: str) -> None:
    """
    Remove a stored file from disk.
    Silently succeeds if the file is already missing.
    """
    try:
        if os.path.isfile(storage_path):
            os.remove(storage_path)
    except OSError:
        pass  # Best-effort deletion; logged upstream if needed


def get_file_path(storage_path: str) -> str | None:
    """
    Return the absolute file path if the file exists on disk, else None.
    """
    abs_path = os.path.abspath(storage_path)
    if os.path.isfile(abs_path):
        return abs_path
    return None
