from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    date: date
    title: str | None
    body: str
    visibility: str
    created_at: datetime


class DiaryEntryCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=20000)
    title: str | None = Field(default=None, max_length=120)
    visibility: str = Field(default="shared", pattern="^(private|shared)$")


class DiaryEntryUpdateRequest(BaseModel):
    body: str | None = Field(default=None, max_length=20000)
    title: str | None = Field(default=None, max_length=120)
    visibility: str | None = Field(default=None, pattern="^(private|shared)$")


class AttachMediaRequest(BaseModel):
    media_id: int
    caption: str | None = Field(default=None, max_length=255)
