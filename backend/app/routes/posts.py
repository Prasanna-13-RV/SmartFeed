from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional
from pathlib import Path

from app.services.post_service import (
    get_random_headlines,
    generate_for_post,
    generate_for_queued,
    generate_latest,
    list_posts,
    process_rss_items,
    retry_failed,
    upload_selected_posts,
)
from app.utils.db import get_store

router = APIRouter()


class GenerateRequest(BaseModel):
    rss_id: Optional[str] = None
    limit: int = 10
    audio_path: Optional[str] = None
    platform: Optional[str] = None  # 'instagram' or 'youtube'
    template: int = 1  # 1=dark, 2=light/navy, 3=photo (instagram only)


class RetryRequest(BaseModel):
    rss_id: str
    audio_path: Optional[str] = None


class UploadSelectedRequest(BaseModel):
    rss_ids: List[str]
    platform: Literal["instagram", "youtube"]
    audio_path: Optional[str] = None


@router.get("/posts")
def get_posts():
    return {"items": list_posts()}


@router.get("/headlines/random")
def get_random(limit: int = 5):
    return {"items": get_random_headlines(limit=limit)}


@router.post("/process-rss")
def process_rss():
    return process_rss_items()


@router.post(
    "/generate/",
    responses={
        404: {"description": "Post not found"},
        500: {"description": "Generation or upload failed"},
    },
)
def generate(payload: GenerateRequest):
    try:
        if payload.rss_id:
            return {"item": generate_for_post(
                payload.rss_id,
                audio_path=payload.audio_path,
                platform_override=payload.platform,
                template=payload.template,
            )}
        return generate_for_queued(limit=payload.limit, audio_path=payload.audio_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/retry/",
    responses={
        404: {"description": "Post not found"},
        500: {"description": "Retry generation or upload failed"},
    },
)
def retry(payload: RetryRequest):
    try:
        return {"item": retry_failed(payload.rss_id, audio_path=payload.audio_path)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/upload-selected/",
    responses={
        400: {"description": "Invalid platform or empty selection"},
        500: {"description": "One or more uploads failed"},
    },
)
def upload_selected(payload: UploadSelectedRequest):
    if not payload.rss_ids:
        raise HTTPException(status_code=400, detail="Please select at least one headline")

    try:
        return upload_selected_posts(
            rss_ids=payload.rss_ids,
            platform=payload.platform,
            audio_path=payload.audio_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class GenerateLatestRequest(BaseModel):
    platform: Literal["instagram", "youtube"]
    template: int = 1
    audio_path: Optional[str] = None


@router.post(
    "/generate-latest",
    summary="One-shot: fetch RSS → pick best headline → generate → upload",
    responses={
        400: {"description": "Invalid platform"},
        500: {"description": "No headlines available or generation failed"},
    },
)
def generate_latest_endpoint(payload: GenerateLatestRequest):
    """
    Called by n8n with platform='instagram' or platform='youtube'.
    Automatically fetches fresh RSS, picks the most recent unposted headline,
    generates the media, and returns the result.
    """
    try:
        result = generate_latest(
            platform=payload.platform,
            template=payload.template,
            audio_path=payload.audio_path,
        )
        return {"item": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete(
    "/posts/{rss_id}",
    summary="Delete a post and its generated media files",
    responses={
        404: {"description": "Post not found"},
    },
)
def delete_post(rss_id: str):
    store = get_store()
    post = store.get(rss_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post '{rss_id}' not found")

    deleted_files = []
    for key in ("media_path", "ig_path", "yt_path"):
        path_str = post.get(key)
        if path_str:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                deleted_files.append(p.name)

    del store[rss_id]
    return {"deleted": rss_id, "files_removed": deleted_files}


@router.delete(
    "/files/{filename}",
    summary="Delete a generated file by its filename (without extension)",
)
def delete_file(filename: str):
    from app.config import settings as _settings
    output_root = Path(_settings.output_dir)
    search_dirs = [
        output_root / "images",
        output_root / "videos",
    ]
    deleted = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if f.stem == filename:
                f.unlink()
                deleted.append(str(f.name))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"No file found with name '{filename}'")

    return {"deleted": deleted}


def _delete_folder_contents(folder: Path) -> list[str]:
    deleted = []
    if folder.exists():
        for f in folder.iterdir():
            if f.is_file():
                f.unlink()
                deleted.append(f.name)
    return deleted


@router.delete("/files/images", summary="Delete all generated images")
def delete_all_images():
    from app.config import settings as _settings
    deleted = _delete_folder_contents(Path(_settings.output_dir) / "images")
    return {"deleted_count": len(deleted), "deleted": deleted}


@router.delete("/files/videos", summary="Delete all generated videos")
def delete_all_videos():
    from app.config import settings as _settings
    deleted = _delete_folder_contents(Path(_settings.output_dir) / "videos")
    return {"deleted_count": len(deleted), "deleted": deleted}


@router.delete("/files", summary="Delete all generated images and videos")
def delete_all_files():
    from app.config import settings as _settings
    output_root = Path(_settings.output_dir)
    deleted_images = _delete_folder_contents(output_root / "images")
    deleted_videos = _delete_folder_contents(output_root / "videos")
    return {
        "deleted_count": len(deleted_images) + len(deleted_videos),
        "images": deleted_images,
        "videos": deleted_videos,
    }
