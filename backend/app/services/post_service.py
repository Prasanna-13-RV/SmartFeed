from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo.errors import DuplicateKeyError

from app.services.media_service import generate_instagram_image, generate_youtube_short
from app.services.rss_service import fetch_all_rss
from app.services.telegram_service import send_telegram_message
from app.services.upload_service import mock_upload_to_instagram, mock_upload_to_youtube
from app.utils.db import posts_collection

POST_NOT_FOUND = "Post not found"


def process_rss_items() -> Dict[str, int]:
    items = fetch_all_rss()
    inserted = 0
    skipped = 0

    for item in items:
        item["created_at"] = datetime.now(timezone.utc)
        try:
            posts_collection.insert_one(item)
            inserted += 1
        except DuplicateKeyError:
            skipped += 1

    return {
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "total_seen": len(items),
    }


def list_posts() -> List[Dict[str, Any]]:
    cursor = posts_collection.find({}, {"_id": 0}).sort("created_at", -1)
    return list(cursor)


def generate_for_post(
    rss_id: str,
    audio_path: Optional[str] = None,
    platform_override: Optional[str] = None,
) -> Dict[str, Any]:
    post = posts_collection.find_one({"rss_id": rss_id})
    if not post:
        raise ValueError(POST_NOT_FOUND)

    target_platform = platform_override or post["assigned_platform"]
    if target_platform not in {"instagram", "youtube"}:
        raise ValueError("Invalid platform")

    post["assigned_platform"] = target_platform

    image_path = generate_instagram_image(post)
    media_path = image_path

    try:
        if target_platform == "youtube":
            media_path = generate_youtube_short(post, image_path, audio_path=audio_path)
            published_link = mock_upload_to_youtube(media_path, post["title"])
        else:
            published_link = mock_upload_to_instagram(media_path, post["title"])

        posts_collection.update_one(
            {"rss_id": rss_id},
            {
                "$set": {
                    "assigned_platform": target_platform,
                    "generated_media_link": media_path,
                    "published_link": published_link,
                    "post_status": "uploaded",
                    "error_message": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        send_telegram_message(
            f"Posted successfully\nPlatform: {target_platform}\nTitle: {post['title']}\nLink: {published_link}"
        )

        post["assigned_platform"] = target_platform
        post["generated_media_link"] = media_path
        post["published_link"] = published_link
        post["post_status"] = "uploaded"
        post["error_message"] = None
        return post
    except Exception as exc:
        error_text = str(exc)
        posts_collection.update_one(
            {"rss_id": rss_id},
            {
                "$set": {
                    "assigned_platform": target_platform,
                    "generated_media_link": media_path,
                    "post_status": "failed",
                    "error_message": error_text,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise RuntimeError(error_text) from exc


def generate_for_queued(limit: int = 10, audio_path: Optional[str] = None) -> Dict[str, Any]:
    queued = list(posts_collection.find({"post_status": "queued"}).limit(limit))
    success = 0
    failed = 0
    errors: List[Dict[str, str]] = []

    for post in queued:
        try:
            generate_for_post(post["rss_id"], audio_path=audio_path)
            success += 1
        except Exception as exc:
            failed += 1
            errors.append({"rss_id": post["rss_id"], "error": str(exc)})

    return {
        "attempted": len(queued),
        "success": success,
        "failed": failed,
        "errors": errors,
    }


def retry_failed(rss_id: str, audio_path: Optional[str] = None) -> Dict[str, Any]:
    post = posts_collection.find_one({"rss_id": rss_id}, {"_id": 0})
    if not post:
        raise ValueError(POST_NOT_FOUND)

    posts_collection.update_one(
        {"rss_id": rss_id},
        {"$set": {"post_status": "queued", "error_message": None}},
    )
    return generate_for_post(rss_id, audio_path=audio_path)


def get_random_headlines(limit: int = 5) -> List[Dict[str, Any]]:
    safe_limit = max(5, min(limit, 10))
    pipeline = [
        {"$match": {"post_status": {"$in": ["queued", "failed"]}}},
        {"$sample": {"size": safe_limit}},
        {
            "$project": {
                "_id": 0,
                "rss_id": 1,
                "title": 1,
                "category": 1,
                "assigned_platform": 1,
                "post_status": 1,
                "source_link": 1,
            }
        },
    ]
    return list(posts_collection.aggregate(pipeline))


def upload_selected_posts(
    rss_ids: List[str],
    platform: str,
    audio_path: Optional[str] = None,
) -> Dict[str, Any]:
    if platform not in {"instagram", "youtube"}:
        raise ValueError("Invalid platform")

    uploaded = 0
    failed = 0
    skipped = 0
    results: List[Dict[str, Any]] = []

    for rss_id in rss_ids:
        post = posts_collection.find_one({"rss_id": rss_id}, {"_id": 0})
        if not post:
            failed += 1
            results.append({"rss_id": rss_id, "status": "failed", "error": POST_NOT_FOUND})
            continue

        if post.get("post_status") == "uploaded":
            skipped += 1
            results.append({"rss_id": rss_id, "status": "skipped", "reason": "Already uploaded"})
            continue

        try:
            generated = generate_for_post(
                rss_id,
                audio_path=audio_path,
                platform_override=platform,
            )
            uploaded += 1
            results.append(
                {
                    "rss_id": rss_id,
                    "status": "uploaded",
                    "platform": platform,
                    "published_link": generated.get("published_link"),
                }
            )
        except Exception as exc:
            failed += 1
            results.append({"rss_id": rss_id, "status": "failed", "error": str(exc)})

    return {
        "requested": len(rss_ids),
        "uploaded": uploaded,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }
