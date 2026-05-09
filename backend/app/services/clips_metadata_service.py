"""clips_metadata_service.py - Manage clip metadata storage and retrieval"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import json
from app.config import settings
from app.models.clip import ClipMetadata


# Store metadata in a JSON file
METADATA_DIR = Path(settings.output_dir) / ".metadata"
CLIPS_METADATA_FILE = METADATA_DIR / "clips.json"


def _ensure_metadata_dir() -> None:
    """Ensure metadata directory exists"""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_metadata() -> Dict[str, List[Dict]]:
    """Load all clips metadata from disk"""
    if not CLIPS_METADATA_FILE.exists():
        return {}
    try:
        with open(CLIPS_METADATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_metadata(data: Dict[str, List[Dict]]) -> None:
    """Save clips metadata to disk"""
    _ensure_metadata_dir()
    with open(CLIPS_METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def save_clip_metadata(
    video_id: str,
    clip_number: int,
    cloudinary_url: str,
    title: str,
    duration: int,
) -> ClipMetadata:
    """Save clip metadata after successful upload"""
    _ensure_metadata_dir()
    metadata = _load_metadata()
    
    if video_id not in metadata:
        metadata[video_id] = []
    
    clip_info = {
        "video_id": video_id,
        "clip_number": clip_number,
        "cloudinary_url": cloudinary_url,
        "title": title,
        "duration": duration,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    
    # Remove old entry if exists and add new one
    metadata[video_id] = [
        c for c in metadata[video_id] if c["clip_number"] != clip_number
    ]
    metadata[video_id].append(clip_info)
    # Sort by clip number
    metadata[video_id].sort(key=lambda x: x["clip_number"])
    
    _save_metadata(metadata)
    return ClipMetadata(**clip_info)


def get_clip_metadata(video_id: str, clip_number: int) -> Optional[ClipMetadata]:
    """Get metadata for a specific clip"""
    metadata = _load_metadata()
    if video_id not in metadata:
        return None
    
    for clip in metadata[video_id]:
        if clip["clip_number"] == clip_number:
            return ClipMetadata(**clip)
    return None


def get_all_clips_for_video(video_id: str) -> List[ClipMetadata]:
    """Get all clips metadata for a video, sorted by clip number"""
    metadata = _load_metadata()
    if video_id not in metadata:
        return []
    
    clips = [ClipMetadata(**clip) for clip in metadata[video_id]]
    clips.sort(key=lambda x: x.clip_number)
    return clips


def get_oldest_video_with_clips() -> Optional[tuple[str, List[ClipMetadata]]]:
    """
    Get the oldest video (by first clip upload time) with its clips in ascending order
    Returns: (video_id, [clips]) or None if no clips exist
    """
    metadata = _load_metadata()
    
    if not metadata:
        return None
    
    # Find oldest video by comparing first upload time
    oldest_video_id = None
    oldest_time = None
    
    for video_id, clips in metadata.items():
        if not clips:
            continue
        # Get the earliest uploaded clip for this video
        first_clip = min(clips, key=lambda x: x["uploaded_at"])
        clip_time = datetime.fromisoformat(first_clip["uploaded_at"])
        
        if oldest_time is None or clip_time < oldest_time:
            oldest_time = clip_time
            oldest_video_id = video_id
    
    if oldest_video_id is None:
        return None
    
    # Return video_id with clips sorted in ascending order
    clips = [ClipMetadata(**clip) for clip in metadata[oldest_video_id]]
    clips.sort(key=lambda x: x.clip_number)
    return (oldest_video_id, clips)


def delete_clip_metadata(video_id: str, clip_number: int) -> bool:
    """Delete metadata for a specific clip"""
    metadata = _load_metadata()
    if video_id not in metadata:
        return False
    
    original_count = len(metadata[video_id])
    metadata[video_id] = [
        c for c in metadata[video_id] if c["clip_number"] != clip_number
    ]
    
    if len(metadata[video_id]) == 0:
        del metadata[video_id]
    
    _save_metadata(metadata)
    return len(metadata[video_id]) < original_count if video_id in metadata else True
