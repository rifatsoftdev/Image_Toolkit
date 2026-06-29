from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from app.schemas.image_schema import ApiResponse, ImageDetails
from app.middlewares.rate_limiter import check_rate_limit
from app.services.image_service import ImageService
from app.utils.file_utils import (
    validate_and_read_upload,
    generate_secure_filename,
    settings
)

router = APIRouter(prefix="/api/image", tags=["image"])
logger = logging.getLogger("dting_toolkit.router")

def save_processed_image(content: bytes, ext: str) -> Path:
    """
    Helper to save processed image bytes to the static downloads directory.
    """
    filename = generate_secure_filename(ext)
    file_path = settings.DOWNLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path

@router.post("/compress", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def compress_image(
    file: UploadFile = File(...),
    quality: int = Form(80, ge=10, le=100)
):
    try:
        content, mime, ext = await validate_and_read_upload(file)
        
        # Keep original format
        processed_bytes, width, height, out_fmt = ImageService.compress(
            content=content,
            format=ext,
            quality=quality
        )
        
        saved_path = save_processed_image(processed_bytes, ext)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message="Image compressed successfully.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=width,
                height=height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Compression error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during compression: {str(e)}"
        )

@router.post("/convert", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def convert_image(
    file: UploadFile = File(...),
    target_format: str = Form(...)
):
    try:
        # Validate target format
        target_format = target_format.lower()
        if target_format not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported target format: {target_format}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        content, mime, ext = await validate_and_read_upload(file)
        
        processed_bytes, width, height, out_fmt = ImageService.convert(
            content=content,
            target_format=target_format
        )
        
        saved_path = save_processed_image(processed_bytes, target_format)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message=f"Image successfully converted from {ext.upper()} to {target_format.upper()}.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=width,
                height=height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Conversion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during conversion: {str(e)}"
        )

@router.post("/resize", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(None, ge=1),
    height: int = Form(None, ge=1),
    maintain_aspect_ratio: bool = Form(True)
):
    try:
        if not width and not height:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least width or height must be specified."
            )

        content, mime, ext = await validate_and_read_upload(file)
        
        processed_bytes, out_width, out_height, out_fmt = ImageService.resize(
            content=content,
            format=ext,
            width=width,
            height=height,
            maintain_aspect_ratio=maintain_aspect_ratio
        )
        
        saved_path = save_processed_image(processed_bytes, ext)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message="Image resized successfully.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=out_width,
                height=out_height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Resizing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during resizing: {str(e)}"
        )

@router.post("/crop", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def crop_image(
    file: UploadFile = File(...),
    x: int = Form(..., ge=0),
    y: int = Form(..., ge=0),
    width: int = Form(..., ge=1),
    height: int = Form(..., ge=1)
):
    try:
        content, mime, ext = await validate_and_read_upload(file)
        
        processed_bytes, out_width, out_height, out_fmt = ImageService.crop(
            content=content,
            format=ext,
            x=x,
            y=y,
            width=width,
            height=height
        )
        
        saved_path = save_processed_image(processed_bytes, ext)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message="Image cropped successfully.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=out_width,
                height=out_height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Cropping error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during cropping: {str(e)}"
        )

@router.post("/rotate", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def rotate_image(
    file: UploadFile = File(...),
    rotate: int = Form(0),
    flip_h: bool = Form(False),
    flip_v: bool = Form(False)
):
    try:
        if rotate not in (0, 90, 180, 270):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rotation angle must be 0, 90, 180, or 270 degrees."
            )
            
        content, mime, ext = await validate_and_read_upload(file)
        
        processed_bytes, out_width, out_height, out_fmt = ImageService.rotate_flip(
            content=content,
            format=ext,
            rotate_angle=rotate,
            flip_h=flip_h,
            flip_v=flip_v
        )
        
        saved_path = save_processed_image(processed_bytes, ext)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message="Image rotated/flipped successfully.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=out_width,
                height=out_height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Rotation/Flip error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during rotation/flip: {str(e)}"
        )

@router.post("/remove-metadata", response_model=ApiResponse, dependencies=[Depends(check_rate_limit)])
async def remove_metadata(
    file: UploadFile = File(...)
):
    try:
        content, mime, ext = await validate_and_read_upload(file)
        
        processed_bytes, out_width, out_height, out_fmt = ImageService.remove_metadata(
            content=content,
            format=ext
        )
        
        saved_path = save_processed_image(processed_bytes, ext)
        size = len(processed_bytes)
        
        return ApiResponse(
            success=True,
            message="All EXIF and metadata successfully removed.",
            download_url=f"/api/image/download/{saved_path.name}",
            image=ImageDetails(
                filename=saved_path.name,
                format=out_fmt.upper(),
                width=out_width,
                height=out_height,
                size=size
            )
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Metadata removal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while removing metadata: {str(e)}"
        )

@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download endpoint to serve processed images.
    """
    # Prevent path traversal attacks
    safe_filename = Path(filename).name
    file_path = settings.DOWNLOAD_DIR / safe_filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or has expired."
        )
        
    ext = safe_filename.split(".")[-1].lower()
    media_type = f"image/{ext}"
    if ext == "jpg":
        media_type = "image/jpeg"
        
    # Return FileResponse. Browser can view or download.
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename
    )
