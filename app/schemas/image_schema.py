from pydantic import BaseModel, Field
from typing import Optional

class ImageDetails(BaseModel):
    filename: str
    format: str
    width: int
    height: int
    size: int  # size in bytes

class ApiResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None
    image: Optional[ImageDetails] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
