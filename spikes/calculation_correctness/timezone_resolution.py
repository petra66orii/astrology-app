"""Resolve local civil time without guessing across DST transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class LocalTimeStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NONEXISTENT = "NONEXISTENT"


@dataclass(frozen=True, slots=True)
class UtcCandidate:
    fold: int
    utc_datetime: datetime
    utc_offset_seconds: int


@dataclass(frozen=True, slots=True)
class LocalTimeResolution:
    status: LocalTimeStatus
    timezone_id: str
    candidates: tuple[UtcCandidate, ...]


def resolve_local_time(local_datetime: datetime, timezone_id: str) -> LocalTimeResolution:
    if local_datetime.tzinfo is not None:
        raise ValueError("local_datetime must be naive")
    try:
        zone = ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown IANA timezone: {timezone_id}") from exc

    candidates: list[UtcCandidate] = []
    seen_instants: set[datetime] = set()
    for fold in (0, 1):
        aware = local_datetime.replace(tzinfo=zone, fold=fold)
        utc_value = aware.astimezone(timezone.utc)
        round_trip = utc_value.astimezone(zone)
        if round_trip.replace(tzinfo=None) != local_datetime or utc_value in seen_instants:
            continue
        seen_instants.add(utc_value)
        offset = aware.utcoffset()
        assert offset is not None
        candidates.append(UtcCandidate(fold, utc_value, int(offset.total_seconds())))

    if not candidates:
        status = LocalTimeStatus.NONEXISTENT
    elif len(candidates) == 2:
        status = LocalTimeStatus.AMBIGUOUS
    else:
        status = LocalTimeStatus.RESOLVED
    return LocalTimeResolution(status, timezone_id, tuple(candidates))


def require_utc(local_datetime: datetime, timezone_id: str, fold: int | None = None) -> datetime:
    resolution = resolve_local_time(local_datetime, timezone_id)
    if resolution.status is LocalTimeStatus.NONEXISTENT:
        raise ValueError("local time does not exist because of a timezone transition")
    if resolution.status is LocalTimeStatus.AMBIGUOUS and fold is None:
        raise ValueError("local time is ambiguous; fold 0 or 1 must be selected")
    selected = resolution.candidates[0] if fold is None else next(
        (candidate for candidate in resolution.candidates if candidate.fold == fold), None
    )
    if selected is None:
        raise ValueError("the selected fold is not valid for this local time")
    return selected.utc_datetime
