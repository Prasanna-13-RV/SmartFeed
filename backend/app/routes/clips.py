"""clips.py — routes for YouTube → short-clips pipeline.

POST /clips/process   – download & split one or more YouTube videos
GET  /video/{id}/{n}  – stream a specific clip file
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from app.services.clip_service import CLIPS_DIR, process_youtube_url
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
