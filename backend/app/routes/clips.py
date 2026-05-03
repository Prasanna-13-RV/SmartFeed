"""clips.py — routes for YouTube → short-clips pipeline.

POST /clips/process   – download & split one or more YouTube videos
GET  /video/{id}/{n}  – stream a specific clip file
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from app.services.clip_service import CLIPS_DIR, process_youtube_url, save_cookies_from_b64, save_cookies_from_file
import shutil

# ── Input model ──────────────────────────────────────────────────────────────

_YT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


class ClipRequest(BaseModel):
    urls: List[str]
    clip_duration: Optional[int] = None  # None = auto-detect from video duration

    @field_validator("clip_duration", mode="before")
    @classmethod
    def clip_duration_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 5 or v > 3600):
            raise ValueError("clip_duration must be between 5 and 3600 seconds")
        return v

    @field_validator("urls")
    @classmethod
    def urls_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("urls list must not be empty")
        return v


# ── Routers ───────────────────────────────────────────────────────────────────

clips_router = APIRouter(prefix="/clips", tags=["clips"])
video_router = APIRouter(prefix="/video", tags=["clips"])


class CookiesUpdateRequest(BaseModel):
    cookies_b64: str  # base64-encoded Netscape cookies.txt


# POST /clips/upload-cookies  — upload cookies.txt directly as a file
@clips_router.post(
    "/upload-cookies",
    summary="Upload cookies.txt file directly",
)
async def upload_cookies(file: UploadFile = File(...)) -> dict:
    """
    Upload your cookies.txt directly — no base64 needed.

    How to get cookies:
    1. Install 'Get cookies.txt LOCALLY' Chrome extension
    2. Visit youtube.com while logged in → click extension → Export
    3. POST the file here
    """
    try:
        contents = await file.read()
        path = save_cookies_from_file(contents)
        return {"updated": True, "cookies_file": path}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# POST /clips/update-cookies  — base64 variant (kept for API/n8n use)
@clips_router.post(
    "/update-cookies",
    summary="Update YouTube cookies without redeploying",
)
def update_cookies(request: CookiesUpdateRequest) -> dict:
    """
    Accepts a base64-encoded Netscape cookies.txt and saves it to disk.
    Call this whenever YouTube bot-detection starts blocking downloads.

    How to get cookies:
    1. Install 'Get cookies.txt LOCALLY' Chrome extension
    2. Visit youtube.com while logged in, click extension → Export
    3. base64-encode the file:  base64 -w 0 cookies.txt
    4. POST that value here
    """
    try:
        path = save_cookies_from_b64(request.cookies_b64)
        return {"updated": True, "cookies_file": path}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# POST /clips/process
@clips_router.post(
    "/process",
    summary="Download YouTube video(s) and split into short clips",
    responses={
        200: {"description": "List of clip links per video"},
        422: {"description": "Validation error"},
        500: {"description": "Download or split failed"},
    },
)
def process_clips(request: ClipRequest) -> dict:
    """
    Accepts a list of YouTube URLs, downloads each video, splits it into
    clips of `clip_duration` seconds, deletes the original, and returns
    the streaming links.

    Example response::

        {
          "clips": [
            {
              "video_id": "dQw4w9WgXcQ",
              "links": [
                "http://localhost:8000/video/dQw4w9WgXcQ/1",
                "http://localhost:8000/video/dQw4w9WgXcQ/2"
              ]
            }
          ]
        }
    """
    results = []
    errors = []

    for url in request.urls:
        try:
            result = process_youtube_url(url, request.clip_duration)
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": url, "error": str(exc)})

    response: dict = {"clips": results}
    if errors:
        response["errors"] = errors

    return response


# GET /video/{video_id}/{clip_index}
@video_router.get(
    "/{video_id}/{clip_index}",
    summary="Stream a generated clip",
    responses={
        200: {"content": {"video/mp4": {}}, "description": "MP4 video stream"},
        400: {"description": "Invalid video_id or clip_index"},
        404: {"description": "Clip not found"},
    },
)
def serve_clip(video_id: str, clip_index: int) -> FileResponse:
    """Return the mp4 file for the requested clip."""
    # Guard against path traversal
    if not _YT_ID_RE.match(video_id):
        raise HTTPException(status_code=400, detail="Invalid video_id")
    if clip_index < 1:
        raise HTTPException(status_code=400, detail="clip_index must be ≥ 1")

    clip_path: Path = CLIPS_DIR / video_id / f"clip_{clip_index}.mp4"
    if not clip_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Clip {clip_index} for video '{video_id}' not found",
        )

    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=f"{video_id}_clip_{clip_index}.mp4",
    )


# GET /clips  — list ALL videos and their clips
@clips_router.get(
    "",
    summary="List all generated videos and their clips",
)
def list_all_clips() -> dict:
    """Return every video folder and its clip links, grouped by video ID.

    Example response::

        {
          "videos": [
            {
              "video_id": "dQw4w9WgXcQ",
              "total": 3,
              "links": [
                "http://localhost:8000/video/dQw4w9WgXcQ/1",
                "http://localhost:8000/video/dQw4w9WgXcQ/2",
                "http://localhost:8000/video/dQw4w9WgXcQ/3"
              ]
            }
          ],
          "total_videos": 1,
          "total_clips": 3
        }
    """
    from app.config import settings as _s
    base = _s.base_url.rstrip("/")

    videos = []
    if CLIPS_DIR.exists():
        for video_dir in sorted(CLIPS_DIR.iterdir()):
            if not video_dir.is_dir():
                continue
            clips = sorted(
                video_dir.glob("clip_*.mp4"),
                key=lambda p: int(p.stem.split("_")[1]),
            )
            if not clips:
                continue
            vid = video_dir.name
            links = [f"{base}/video/{vid}/{i}" for i in range(1, len(clips) + 1)]
            videos.append({"video_id": vid, "total": len(clips), "links": links})

    return {
        "videos": videos,
        "total_videos": len(videos),
        "total_clips": sum(v["total"] for v in videos),
    }


# GET /clips/{video_id}  — list existing clips for a video
@clips_router.get(
    "/{video_id}",
    summary="List generated clips for a video",
    responses={
        200: {"description": "Clip links"},
        400: {"description": "Invalid video_id"},
        404: {"description": "No clips found for this video"},
    },
)
def list_clips(video_id: str) -> dict:
    """Return the streaming links for all clips of a processed video."""
    if not _YT_ID_RE.match(video_id):
        raise HTTPException(status_code=400, detail="Invalid video_id")

    clip_dir: Path = CLIPS_DIR / video_id
    if not clip_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No clips found for video '{video_id}'",
        )

    clips = sorted(
        clip_dir.glob("clip_*.mp4"),
        key=lambda p: int(p.stem.split("_")[1]),
    )
    if not clips:
        raise HTTPException(
            status_code=404,
            detail=f"No clips found for video '{video_id}'",
        )

    from app.config import settings
    base = settings.base_url.rstrip("/")
    links = [f"{base}/video/{video_id}/{i}" for i in range(1, len(clips) + 1)]
    return {"video_id": video_id, "total": len(clips), "links": links}


# DELETE /clips/{video_id}
@clips_router.delete(
    "/{video_id}",
    summary="Delete all clips for a video",
    responses={
        200: {"description": "Clips deleted"},
        400: {"description": "Invalid video_id"},
        404: {"description": "No clips found for this video"},
    },
)
def delete_clips(video_id: str) -> dict:
    """Delete all generated clips (and the clip folder) for the given video ID."""
    if not _YT_ID_RE.match(video_id):
        raise HTTPException(status_code=400, detail="Invalid video_id")

    clip_dir: Path = CLIPS_DIR / video_id
    if not clip_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No clips found for video '{video_id}'",
        )

    shutil.rmtree(clip_dir)
    return {"deleted": True, "video_id": video_id}
