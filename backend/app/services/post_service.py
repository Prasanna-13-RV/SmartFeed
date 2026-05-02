from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.media_service import generate_instagram_image, generate_youtube_short
from app.services.rss_service import fetch_all_rss
from app.services.upload_service import mock_upload_to_instagram, mock_upload_to_youtube
from app.utils.db import get_store, save_store

POST_NOT_FOUND = "Post not found"


def process_rss_items() -> Dict[str, int]:
    store = get_store()
    items = fetch_all_rss()
    inserted = 0
    skipped = 0

    for item in items:
        item["created_at"] = datetime.now(timezone.utc)
        if item["rss_id"] in store:
            skipped += 1
        else:
            store[item["rss_id"]] = item
            inserted += 1

    save_store()
    return {
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "total_seen": len(items),
    }


def list_posts() -> List[Dict[str, Any]]:
    store = get_store()
    return sorted(store.values(), key=lambda p: p.get("created_at", ""), reverse=True)


def generate_for_post(
    rss_id: str,
    audio_path: Optional[str] = None,
    platform_override: Optional[str] = None,
    template: int = 1,
) -> Dict[str, Any]:
    store = get_store()
    post = store.get(rss_id)
    if not post:
        raise ValueError(POST_NOT_FOUND)

    target_platform = platform_override or post["assigned_platform"]
    if target_platform not in {"instagram", "youtube"}:
        raise ValueError("Invalid platform")

    post = dict(post)
    post["assigned_platform"] = target_platform

    media_path = ""

    try:
        if target_platform == "youtube":
            media_path = generate_youtube_short(post, template=template, audio_path=audio_path)
            published_link = mock_upload_to_youtube(media_path, post["title"])
        else:
            media_path = generate_instagram_image(post, template=template)
            published_link = mock_upload_to_instagram(media_path, post["title"])

        store[rss_id].update({
            "assigned_platform": target_platform,
            "generated_media_link": media_path,
            "published_link": published_link,
            "post_status": "uploaded",
            "error_message": None,
            "updated_at": datetime.now(timezone.utc),
        })
        save_store()

        post["generated_media_link"] = media_path
        post["published_link"] = published_link
        post["post_status"] = "uploaded"
        post["error_message"] = None
        return post

    except Exception as exc:
        error_text = str(exc)
        store[rss_id].update({
            "assigned_platform": target_platform,
            "generated_media_link": media_path,
            "post_status": "failed",
            "error_message": error_text,
            "updated_at": datetime.now(timezone.utc),
        })
        save_store()
        raise RuntimeError(error_text) from exc


def generate_for_queued(limit: int = 10, audio_path: Optional[str] = None) -> Dict[str, Any]:
    store = get_store()
    queued = [p for p in store.values() if p.get("post_status") == "queued"][:limit]
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
    store = get_store()
    if rss_id not in store:
        raise ValueError(POST_NOT_FOUND)
    store[rss_id].update({"post_status": "queued", "error_message": None})
    save_store()
    return generate_for_post(rss_id, audio_path=audio_path)


def get_random_headlines(limit: int = 5) -> List[Dict[str, Any]]:
    store = get_store()
    safe_limit = max(5, min(limit, 10))
    eligible = [
        {
            "rss_id": p["rss_id"],
            "title": p["title"],
            "description": p.get("description", ""),
            "image_url": p.get("image_url", ""),
            "category": p["category"],
            "assigned_platform": p["assigned_platform"],
            "post_status": p["post_status"],
            "source_link": p.get("source_link"),
        }
        for p in store.values()
        if p.get("post_status") in {"queued", "failed"}
    ]
    return random.sample(eligible, min(safe_limit, len(eligible)))


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
        store = get_store()
        post = store.get(rss_id)
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
            results.append({
                "rss_id": rss_id,
                "status": "uploaded",
                "platform": platform,
                "published_link": generated.get("published_link"),
            })
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


def generate_latest(
    platform: str,
    template: int = 1,
    audio_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    One-shot endpoint for n8n:
    1. Fetch fresh RSS headlines
    2. Pick the best unseen headline (not yet uploaded for this platform)
    3. Generate the image (instagram) or video (youtube)
    4. Upload and return the result
    """
    if platform not in {"instagram", "youtube"}:
        raise ValueError("platform must be 'instagram' or 'youtube'")

    # ── Step 1: refresh RSS into store ──
    items = fetch_all_rss()
    store = get_store()
    now = datetime.now(timezone.utc)
    for item in items:
        if item["rss_id"] not in store:
            item["created_at"] = now
            store[item["rss_id"]] = item
    save_store()

    # ── Step 2: pick best headline not yet uploaded on this platform ──
    # Priority: never uploaded for this platform, prefer recent items
    candidates = [
        p for p in store.values()
        if p.get("post_status") != "uploaded"
        or p.get("assigned_platform") != platform
    ]

    # Exclude already uploaded for this exact platform
    candidates = [
        p for p in store.values()
        if not (p.get("post_status") == "uploaded" and p.get("assigned_platform") == platform)
    ]

    if not candidates:
        raise RuntimeError("No new headlines available — all posts have been uploaded")

    # Sort by created_at descending → pick freshest
    candidates.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)
    # Take top 10 freshest, then pick randomly to avoid duplicate runs getting same item
    top = candidates[:10]
    chosen = random.choice(top)
    rss_id = chosen["rss_id"]

    # ── Step 3 & 4: generate + upload ──
    # Template defaults:
    #   Instagram → always template 1 (Dark Bold orange)
    #   YouTube   → always template 2 (photo overlay)
    if template and template != 1:
        chosen_template = template
    elif platform == "youtube":
        chosen_template = 2
    else:
        chosen_template = 1

    return generate_for_post(
        rss_id,
        audio_path=audio_path,
        platform_override=platform,
        template=chosen_template,
    )
