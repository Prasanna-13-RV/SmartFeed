from __future__ import annotations

import random
from datetime import datetime, timezone


def mock_upload_to_instagram(media_path: str, title: str) -> str:
    _ = (media_path, title)
    # Simulate occasional API failures.
    if random.random() < 0.1:
        raise RuntimeError("Instagram upload failed: mock API timeout")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"https://instagram.mock/post/{stamp}"


def mock_upload_to_youtube(media_path: str, title: str) -> str:
    _ = (media_path, title)
    if random.random() < 0.1:
        raise RuntimeError("YouTube upload failed: mock API rejected payload")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"https://youtube.mock/shorts/{stamp}"
