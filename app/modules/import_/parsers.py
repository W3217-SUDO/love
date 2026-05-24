from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from defusedxml import ElementTree


class ImportParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedPeriod:
    start_date: date


@dataclass(frozen=True)
class ParsedTag:
    date: date
    tag_key: str
    value: str | None = None


@dataclass(frozen=True)
class ParsedBbt:
    date: date
    temp_c: Decimal
    method: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ParsedHealthMetric:
    date: date
    metric_type: str
    value: Decimal
    unit: str
    source: str = "apple_health"
    meta_json: dict | None = None


@dataclass
class ParsedImport:
    periods: list[ParsedPeriod] = field(default_factory=list)
    tags: list[ParsedTag] = field(default_factory=list)
    bbt_readings: list[ParsedBbt] = field(default_factory=list)
    health_metrics: list[ParsedHealthMetric] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    unmapped: list[dict] = field(default_factory=list)


FLO_TAG_MAP = {
    ("symptom", "cramps"): "sym_cramps",
    ("ovulation", "positive"): "ovu_positive",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _apple_date(attrs: dict[str, str]) -> date | None:
    return _parse_date(attrs.get("startDate") or attrs.get("creationDate"))


def parse_flo_csv(raw: bytes) -> ParsedImport:
    parsed = ParsedImport()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    required = {"date", "type", "value"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ImportParseError("missing required columns: date,type,value")

    for index, row in enumerate(reader, start=2):
        row_date = _parse_date(row.get("date"))
        row_type = (row.get("type") or "").strip().lower()
        value = (row.get("value") or "").strip().lower()
        if row_date is None or not row_type or not value:
            parsed.skipped.append(f"row {index}: incomplete")
            continue

        if row_type == "period" and value == "start":
            parsed.periods.append(ParsedPeriod(start_date=row_date))
            continue

        tag_key = FLO_TAG_MAP.get((row_type, value))
        if tag_key is not None:
            parsed.tags.append(ParsedTag(date=row_date, tag_key=tag_key))
            continue

        parsed.unmapped.append({"row": index, "type": row_type, "value": value})

    return parsed


def parse_apple_health_xml(raw: bytes) -> ParsedImport:
    parsed = ParsedImport()
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise ImportParseError(f"invalid xml: {exc}") from exc
    if root.tag != "HealthData":
        raise ImportParseError("invalid Apple Health export: missing HealthData root")

    sleep_seconds_by_date: dict[date, float] = defaultdict(float)
    for record in root.iter("Record"):
        attrs = dict(record.attrib)
        record_type = attrs.get("type", "")
        record_date = _apple_date(attrs)
        if record_date is None:
            parsed.skipped.append(f"record without date: {record_type}")
            continue

        if record_type == "HKCategoryTypeIdentifierMenstrualFlow":
            parsed.periods.append(ParsedPeriod(start_date=record_date))
        elif record_type == "HKCategoryTypeIdentifierSexualActivity":
            parsed.tags.append(_parse_sexual_activity(record_date, record))
        elif record_type == "HKQuantityTypeIdentifierBasalBodyTemperature":
            value = _parse_decimal(attrs.get("value"))
            if value is None:
                parsed.skipped.append("basal body temperature without numeric value")
                continue
            unit = attrs.get("unit", "degC")
            if unit in {"degF", "fahrenheit"}:
                value = (value - Decimal("32")) * Decimal("5") / Decimal("9")
            parsed.bbt_readings.append(
                ParsedBbt(date=record_date, temp_c=value.quantize(Decimal("0.01"))),
            )
        elif record_type == "HKQuantityTypeIdentifierRestingHeartRate":
            _append_metric(parsed, record_date, "resting_heart_rate", attrs, "bpm")
        elif record_type in {
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
            "HKQuantityTypeIdentifierHRV",
        }:
            _append_metric(parsed, record_date, "hrv", attrs, "ms")
        elif record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            seconds = _duration_seconds(attrs.get("startDate"), attrs.get("endDate"))
            if seconds > 0:
                sleep_seconds_by_date[record_date] += seconds
            else:
                parsed.skipped.append("sleep analysis without duration")
        else:
            parsed.unmapped.append({"type": record_type, "date": record_date.isoformat()})

    for metric_date, seconds in sleep_seconds_by_date.items():
        hours = Decimal(str(seconds / 3600)).quantize(Decimal("0.01"))
        parsed.health_metrics.append(
            ParsedHealthMetric(
                date=metric_date,
                metric_type="sleep_duration",
                value=hours,
                unit="h",
            ),
        )

    return parsed


def _append_metric(
    parsed: ParsedImport,
    metric_date: date,
    metric_type: str,
    attrs: dict[str, str],
    default_unit: str,
) -> None:
    value = _parse_decimal(attrs.get("value"))
    if value is None:
        parsed.skipped.append(f"{metric_type} without numeric value")
        return
    parsed.health_metrics.append(
        ParsedHealthMetric(
            date=metric_date,
            metric_type=metric_type,
            value=value,
            unit=attrs.get("unit") or default_unit,
        ),
    )


def _parse_sexual_activity(record_date: date, record: ElementTree.Element) -> ParsedTag:
    value = (record.attrib.get("value") or "").lower()
    metadata_text = " ".join(
        child.attrib.get("value", "")
        for child in record.iter("MetadataEntry")
    ).lower()
    combined = f"{value} {metadata_text}"
    if "unprotected" in combined or "false" in combined:
        return ParsedTag(date=record_date, tag_key="unprotected_sex")
    return ParsedTag(date=record_date, tag_key="protected_sex")


def _duration_seconds(start: str | None, end: str | None) -> float:
    if not start or not end:
        return 0
    try:
        start_dt = datetime.strptime(start[:25], "%Y-%m-%d %H:%M:%S %z")
        end_dt = datetime.strptime(end[:25], "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return 0
    return max((end_dt - start_dt).total_seconds(), 0)
