"""Pydantic schemas for cycle HTTP endpoints."""
from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PeriodStartRequest(BaseModel):
    start_date: date
    notes: str | None = None


class PeriodEndRequest(BaseModel):
    start_date: date
    end_date: date


class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    start_date: date
    end_date: date | None
    notes: str | None


class BbtLogRequest(BaseModel):
    date: date
    temp_c: Decimal = Field(decimal_places=2, max_digits=4)
    measure_time: time | None = None
    method: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class BbtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    temp_c: Decimal
    measure_time: time | None
    method: str | None
    notes: str | None


class FertileWindowOut(BaseModel):
    start: date
    end: date


class SignalEvidenceOut(BaseModel):
    source: str
    active: bool
    confidence: float
    evidence: str
    predicted_ovulation: date | None = None
    predicted_next_period: date | None = None


class PredictionOut(BaseModel):
    target_date: date
    next_period: date | None
    ovulation: date | None
    fertile_window: FertileWindowOut | None
    phase: str
    confidence_level: str  # "low" | "medium" | "high"
    confidence_score: float
    evidence: list[SignalEvidenceOut]
