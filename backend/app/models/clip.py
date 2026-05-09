from pydantic import BaseModel, field_validator, Field
from typing import Union, Optional
from datetime import datetime


class ClipMetadata(BaseModel):
    """Metadata for uploaded clips"""
    video_id: str
    clip_number: int
    cloudinary_url: str
    title: str
    duration: int  # clip duration in seconds
    uploaded_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @field_validator('uploaded_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        if v is None:
            return datetime.utcnow()
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Parse ISO format string
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except:
                return datetime.utcnow()
        return datetime.utcnow()
