from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo.errors import PyMongoError
from typing import List, Literal, Optional

from app.services.post_service import (
    get_random_headlines,
    generate_for_post,
    generate_for_queued,
    list_posts,
    process_rss_items,
    retry_failed,
    upload_selected_posts,
)

router = APIRouter()


class GenerateRequest(BaseModel):
    rss_id: Optional[str] = None
    limit: int = 10
    audio_path: Optional[str] = None


class RetryRequest(BaseModel):
    rss_id: str
    audio_path: Optional[str] = None


class UploadSelectedRequest(BaseModel):
    rss_ids: List[str]
    platform: Literal["instagram", "youtube"]
    audio_path: Optional[str] = None


@router.get("/posts", responses={503: {"description": "Database unavailable"}})
def get_posts():
    try:
        return {"items": list_posts()}
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/headlines/random", responses={503: {"description": "Database unavailable"}})
def get_random(limit: int = 5):
    try:
        return {"items": get_random_headlines(limit=limit)}
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.post("/process-rss", responses={503: {"description": "Database unavailable"}})
def process_rss():
    try:
        return process_rss_items()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


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
            return {"item": generate_for_post(payload.rss_id, audio_path=payload.audio_path)}
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
