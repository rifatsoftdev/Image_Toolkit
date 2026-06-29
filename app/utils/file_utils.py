import os
import uuid
import time
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

def validate_image_bytes(content: bytes) -> tuple[bool, str]:
    """
    Validate the image using magic bytes.
    Returns (is_valid, mime_type)
    """
    if len(content) < 12:
        return False, "File is too small to be a valid image."
        
    # Check JPEG: FF D8 FF
    if content[:3] == b"\xff\xd8\xff":
        return True, "image/jpeg"
        
    # Check PNG: 89 50 4E 47 0D 0A 1A 0A
    if content[:8] == b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a":
        return True, "image/png"
        
    # Check WEBP: RIFF (4 bytes) ... WEBP (4 bytes starting at index 8)
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True, "image/webp"
        
    return False, "Unsupported image format. Only PNG, JPG, JPEG, and WEBP are allowed."

async def validate_and_read_upload(file: UploadFile) -> tuple[bytes, str, str]:
    """
    Validates file size, extension, and magic bytes MIME type.
    Returns (content_bytes, mime_type, file_extension)
    """
    # 1. Validate file extension
    filename = file.filename or ""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension .{ext}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
        
    # Normalize extension (jpeg -> jpg)
    if ext == "jpeg":
        ext = "jpg"

    # 2. Validate file size (chunked check to avoid memory bloat before checking)
    # We read up to limit + 1 to see if it exceeds
    content = await file.read(settings.MAX_UPLOAD_SIZE + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB."
        )
        
    # 3. Validate MIME type using magic bytes
    is_valid, mime_type = validate_image_bytes(content)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=mime_type
        )
        
    return content, mime_type, ext

def generate_secure_filename(ext: str) -> str:
    """
    Generate a secure random UUID-based filename.
    """
    normalized_ext = ext.lower()
    if normalized_ext not in settings.ALLOWED_EXTENSIONS:
        normalized_ext = "png"
    return f"{uuid.uuid4().hex}.{normalized_ext}"

def purge_old_files(max_age_seconds: int = 900):
    """
    Clean up files older than max_age_seconds from uploads and downloads directories.
    """
    now = time.time()
    for folder in [settings.UPLOAD_DIR, settings.DOWNLOAD_DIR]:
        if not folder.exists():
            continue
        for filename in os.listdir(folder):
            file_path = folder / filename
            if file_path.is_file():
                try:
                    # check modification time
                    if now - file_path.stat().st_mtime > max_age_seconds:
                        file_path.unlink()
                except Exception:
                    # Ignore deletion errors (e.g. file locked/already deleted)
                    pass
