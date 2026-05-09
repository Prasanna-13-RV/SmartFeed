from __future__ import annotations

from pathlib import Path
from typing import Optional
import cloudinary
import cloudinary.uploader
from app.config import settings

# Initialize Cloudinary
if settings.cloudinary_cloud_name:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )


def mock_upload_to_youtube(media_path: str, title: str) -> str:
    """Return the server file URL — no external upload."""
    _ = title
    return _media_path_to_url(media_path)


# ─────────────────────────────────────────────────
#  CLOUDINARY UPLOAD
# ─────────────────────────────────────────────────

def upload_clip_to_cloudinary(
    file_path: str, video_id: str, clip_number: int
) -> str:
    """
    Upload a clip to Cloudinary in folder: youtube/${video_id}/clips${clip_number}
    Returns the Cloudinary URL.
    """
    if not settings.cloudinary_cloud_name:
        raise RuntimeError("Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in .env")
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Clip file not found: {file_path}")
    
    # Upload to Cloudinary with folder structure: youtube/${video_id}/clips${clip_number}
    # Make videos PUBLIC so they can be accessed without authentication
    try:
        result = cloudinary.uploader.upload(
            file=str(file_path),
            resource_type="video",
            folder=f"youtube/{video_id}",
            public_id=f"clips{clip_number}",
            overwrite=True,
            type="upload",  # Public upload type
        )
        return result["secure_url"]
    except Exception as e:
        raise RuntimeError(f"Cloudinary upload failed: {str(e)}")


# ─────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────

def _media_path_to_url(media_path: str) -> str:
    """Convert a local file path to an accessible server URL.
    e.g. generated/images/abc.jpg → http://localhost:8000/generated/images/abc.jpg
    """
    from pathlib import Path as _Path
    posix = _Path(media_path).as_posix()
    # Find the 'generated/' segment and keep from there
    idx = posix.find("generated/")
    rel = posix[idx:] if idx >= 0 else _Path(media_path).name
    return f"{settings.base_url}/{rel}"


# ─────────────────────────────────────────────────
#  INSTAGRAM — placeholder (Graph API needs approval)
# ─────────────────────────────────────────────────

def mock_upload_to_instagram(media_path: str, title: str) -> str:
    _ = title
    # Return the real accessible URL of the generated image on our server
    return _media_path_to_url(media_path)
