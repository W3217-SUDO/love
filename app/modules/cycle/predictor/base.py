"""Shared types for the cycle predictor package.

`SignalResult` is what each Signal returns; `CyclePrediction` is the fused
output from `CombinedPredictor`. `Signal` is a Protocol so any class with
`source: str` and `evaluate(db, *, user_id, target_date) -> SignalResult`
can plug into `CombinedPredictor`.
"""
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

from sqlalchemy.orm import Session

ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class SignalResult:
    """One signal's contribution to the cycle prediction.

    `predicted_ovulation` -- date the signal thinks ovulation occurred / will occur.
    `confidence` -- 0.0 to 1.0; relative weight in the merge.
    `evidence` -- short human-readable explanation ("LH+ 26h ago", "BBT 3-step at D14->D16").
    `source` -- short tag ("calendar", "bbt", "lh") for UI grouping.
    `active` -- False means "this signal has no opinion right now" (CombinedPredictor skips it).
    """
    source: str
    active: bool
    confidence: float  # 0.0..1.0
    evidence: str
    predicted_ovulation: date | None = None
    predicted_next_period: date | None = None
    fertile_window: tuple[date, date] | None = None
    phase: str | None = None  # "menstrual" | "follicular" | "fertile" | "ovulation" | "luteal"


class Signal(Protocol):
    source: str

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        ...


@dataclass(frozen=True)
class CyclePrediction:
    """Final fused prediction from CombinedPredictor."""
    target_date: date
    next_period: date | None
    ovulation: date | None
    fertile_window: tuple[date, date] | None
    phase: str
    confidence_level: ConfidenceLevel
    confidence_score: float
    evidence: list[SignalResult]
