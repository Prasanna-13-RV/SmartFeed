from pydantic import BaseModel, Field
from typing import Optional, Literal


class NewsPost(BaseModel):
    rss_id: str
    title: str
    category: str
    assigned_platform: Literal["instagram", "youtube"]
    post_status: Literal["queued", "generated", "uploaded", "failed"] = "queued"
    source_link: str
    generated_media_link: Optional[str] = None
    published_link: Optional[str] = None
    error_message: Optional[str] = None


class ProcessRssResponse(BaseModel):
    inserted: int = Field(default=0)
    skipped_duplicates: int = Field(default=0)
    total_seen: int = Field(default=0)
