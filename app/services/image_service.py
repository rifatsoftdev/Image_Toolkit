from io import BytesIO
from PIL import Image, ImageOps
from typing import Tuple

class ImageService:
    @staticmethod
    def load_image(content: bytes) -> Image.Image:
        """
        Load an image from bytes.
        """
        return Image.open(BytesIO(content))

    @staticmethod
    def save_image_to_bytes(img: Image.Image, img_format: str, quality: int = 90) -> bytes:
        """
        Save a PIL Image to bytes with the specified format and quality.
        Handles transparency conversion for JPEGs.
        """
        out = BytesIO()
        pil_format = img_format.upper()
        if pil_format == "JPG":
            pil_format = "JPEG"
        
        # Safe copy to avoid modifying original in-memory object
        working_img = img.copy()

        # Handle JPEG transparency by pasting onto a white background
        if pil_format == "JPEG" and working_img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", working_img.size, (255, 255, 255))
            if working_img.mode == "RGBA":
                background.paste(working_img, mask=working_img.split()[3])
            elif working_img.mode == "LA":
                background.paste(working_img, mask=working_img.split()[1])
            else:
                background.paste(working_img.convert("RGBA"), mask=working_img.convert("RGBA").split()[3])
            working_img = background
        elif working_img.mode == "LA" and pil_format != "JPEG":
            working_img = working_img.convert("RGBA")

        # Set up save parameters
        save_kwargs = {}
        if pil_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
        elif pil_format == "PNG":
            save_kwargs["optimize"] = True
            save_kwargs["compress_level"] = 9
            if quality < 80:
                # Reduce colors for PNG if lower quality/compression is selected to save bandwidth
                working_img = working_img.convert("P", palette=Image.Palette.ADAPTIVE, colors=max(16, int(256 * (quality / 100))))
        
        working_img.save(out, format=pil_format, **save_kwargs)
        return out.getvalue()

    @classmethod
    def compress(cls, content: bytes, format: str, quality: int) -> Tuple[bytes, int, int, str]:
        """
        Compress an image while keeping the original format.
        """
        img = cls.load_image(content)
        compressed_bytes = cls.save_image_to_bytes(img, format, quality=quality)
        # Load compressed image to check new dimensions/metadata if needed, or return original sizes
        return compressed_bytes, img.width, img.height, format

    @classmethod
    def convert(cls, content: bytes, target_format: str) -> Tuple[bytes, int, int, str]:
        """
        Convert an image to a target format.
        """
        img = cls.load_image(content)
        converted_bytes = cls.save_image_to_bytes(img, target_format, quality=90)
        return converted_bytes, img.width, img.height, target_format

    @classmethod
    def resize(cls, content: bytes, format: str, width: int, height: int, maintain_aspect_ratio: bool) -> Tuple[bytes, int, int, str]:
        """
        Resize an image with optional aspect ratio maintenance.
        """
        img = cls.load_image(content)
        orig_width, orig_height = img.size
        
        if maintain_aspect_ratio:
            if width and height:
                # Scale to fit inside width and height boundaries
                ratio = min(width / orig_width, height / orig_height)
                new_width = max(1, int(orig_width * ratio))
                new_height = max(1, int(orig_height * ratio))
            elif width:
                # Base scaling on width
                ratio = width / orig_width
                new_width = width
                new_height = max(1, int(orig_height * ratio))
            elif height:
                # Base scaling on height
                ratio = height / orig_height
                new_width = max(1, int(orig_width * ratio))
                new_height = height
            else:
                new_width, new_height = orig_width, orig_height
        else:
            new_width = width if width else orig_width
            new_height = height if height else orig_height

        # Perform resizing using High Quality resampling (Lanczos)
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized_bytes = cls.save_image_to_bytes(resized_img, format)
        return resized_bytes, new_width, new_height, format

    @classmethod
    def crop(cls, content: bytes, format: str, x: int, y: int, width: int, height: int) -> Tuple[bytes, int, int, str]:
        """
        Crop an image to the designated box coordinates.
        """
        img = cls.load_image(content)
        orig_width, orig_height = img.size
        
        left = max(0, min(x, orig_width))
        top = max(0, min(y, orig_height))
        right = max(left + 1, min(left + width, orig_width))
        bottom = max(top + 1, min(top + height, orig_height))
        
        cropped_img = img.crop((left, top, right, bottom))
        cropped_bytes = cls.save_image_to_bytes(cropped_img, format)
        return cropped_bytes, cropped_img.width, cropped_img.height, format

    @classmethod
    def rotate_flip(cls, content: bytes, format: str, rotate_angle: int, flip_h: bool, flip_v: bool) -> Tuple[bytes, int, int, str]:
        """
        Rotate (90, 180, 270) and/or flip (horizontal, vertical) an image.
        """
        img = cls.load_image(content)
        
        # Apply rotation (clockwise mapping)
        if rotate_angle == 90:
            img = img.transpose(Image.Transpose.ROTATE_270)
        elif rotate_angle == 180:
            img = img.transpose(Image.Transpose.ROTATE_180)
        elif rotate_angle == 270:
            img = img.transpose(Image.Transpose.ROTATE_90)
            
        # Apply flips
        if flip_h:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flip_v:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            
        processed_bytes = cls.save_image_to_bytes(img, format)
        return processed_bytes, img.width, img.height, format

    @classmethod
    def remove_metadata(cls, content: bytes, format: str) -> Tuple[bytes, int, int, str]:
        """
        Strip all EXIF/metadata.
        """
        img = cls.load_image(content)
        # Create a copy and clear info metadata dict
        cleaned_img = img.copy()
        cleaned_img.info = {}
        
        # When we write, we omit any exif parameter which strips metadata
        cleaned_bytes = cls.save_image_to_bytes(cleaned_img, format)
        return cleaned_bytes, cleaned_img.width, cleaned_img.height, format
