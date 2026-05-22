"""Cycle HTTP endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError, NotFound, ValidationFailed
from app.modules.auth.models import User
from app.modules.cycle.predictor import CombinedPredictor
from app.modules.cycle.schemas import (
    BbtLogRequest,
    BbtOut,
    FertileWindowOut,
    PeriodEndRequest,
    PeriodOut,
    PeriodStartRequest,
    PredictionOut,
    SignalEvidenceOut,
)
from app.modules.cycle.service import (
    InvalidBbtReading,
    PeriodNotFound,
    PeriodOverlapError,
    list_bbt,
    list_periods,
    log_bbt,
    log_period_end,
    log_period_start,
)


class PeriodOverlapHTTPError(AppError):
    http_status = status.HTTP_409_CONFLICT
    code = "period_overlap"


router = APIRouter(tags=["cycle"])


@router.post("/cycle/log/start", response_model=PeriodOut)
def post_period_start(
    payload: PeriodStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PeriodOut:
    try:
        period = log_period_start(
            db, user_id=user.id,
            start_date=payload.start_date, notes=payload.notes,
        )
        db.commit()
    except PeriodOverlapError as exc:
        raise PeriodOverlapHTTPError(str(exc)) from exc
    return PeriodOut.model_validate(period)


@router.post("/cycle/log/end", response_model=PeriodOut)
def post_period_end(
    payload: PeriodEndRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PeriodOut:
    try:
        period = log_period_end(
            db, user_id=user.id,
            start_date=payload.start_date, end_date=payload.end_date,
        )
        db.commit()
    except PeriodNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc
    return PeriodOut.model_validate(period)


@router.get("/cycle/periods", response_model=list[PeriodOut])
def get_cycle_periods(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PeriodOut]:
    rows = list_periods(db, user_id=user.id)
    return [PeriodOut.model_validate(r) for r in rows]


@router.get("/cycle/prediction", response_model=PredictionOut)
def get_cycle_prediction(
    date_: date = Query(alias="date", default_factory=date.today),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PredictionOut:
    pred = CombinedPredictor().predict(db, user_id=user.id, target_date=date_)
    return PredictionOut(
        target_date=pred.target_date,
        next_period=pred.next_period,
        ovulation=pred.ovulation,
        fertile_window=(
            FertileWindowOut(start=pred.fertile_window[0], end=pred.fertile_window[1])
            if pred.fertile_window else None
        ),
        phase=pred.phase,
        confidence_level=pred.confidence_level,
        confidence_score=pred.confidence_score,
        evidence=[
            SignalEvidenceOut(
                source=e.source,
                active=e.active,
                confidence=e.confidence,
                evidence=e.evidence,
                predicted_ovulation=e.predicted_ovulation,
                predicted_next_period=e.predicted_next_period,
            )
            for e in pred.evidence
        ],
    )


@router.post("/bbt/log", response_model=BbtOut)
def post_bbt_log(
    payload: BbtLogRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BbtOut:
    try:
        row = log_bbt(
            db,
            user_id=user.id,
            date=payload.date,
            temp_c=payload.temp_c,
            measure_time=payload.measure_time,
            method=payload.method,
            notes=payload.notes,
        )
        db.commit()
    except InvalidBbtReading as exc:
        raise ValidationFailed(str(exc)) from exc
    return BbtOut.model_validate(row)


@router.get("/bbt", response_model=list[BbtOut])
def get_bbt_list(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BbtOut]:
    rows = list_bbt(db, user_id=user.id, start_date=start, end_date=end)
    return [BbtOut.model_validate(r) for r in rows]
