from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    location: str | None
    start_date: date
    end_date: date | None
    description: str | None
    cover_media_id: int | None
    created_by_id: int
    created_at: datetime


class AttachMediaRequest(BaseModel):
    media_id: int
    caption: str | None = Field(default=None, max_length=255)
