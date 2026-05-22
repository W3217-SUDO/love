"""Pydantic schemas for daily log endpoints."""
from datetime import date

from pydantic import BaseModel, ConfigDict


class DailyTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    tag_key: str
    value: str | None


class DailyEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    notes: str | None
    tags: list[DailyTagOut] = []


class ToggleResponse(BaseModel):
    tag_key: str
    active: bool


class NotesRequest(BaseModel):
    notes: str
