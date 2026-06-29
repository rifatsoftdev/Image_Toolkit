import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "DTing Image Toolkit"
    API_V1_STR: str = "/api"
    
    # Ensure directories exist
    UPLOAD_DIR: Path = BASE_DIR / "app" / "static" / "uploads"
    DOWNLOAD_DIR: Path = BASE_DIR / "app" / "static" / "downloads"
    
    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Rate Limit settings
    RATE_LIMIT_DAILY: int = 20  # 20 images per day
    
    # File limits
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB in bytes
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_MIME_TYPES: set[str] = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp"
    }

settings = Settings()
