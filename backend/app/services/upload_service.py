from __future__ import annotations

from app.config import settings


def mock_upload_to_youtube(media_path: str, title: str) -> str:
    """Return the server file URL — no external upload."""
    _ = title
    return _media_path_to_url(media_path)


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
