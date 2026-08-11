from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import lru_cache
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

    def as_dict(self) -> dict:
        return {
            "fold": self.fold,
            "utc_datetime": self.utc_datetime.isoformat().replace("+00:00", "Z"),
            "utc_offset_seconds": self.utc_offset_seconds,
        }


@dataclass(frozen=True, slots=True)
class LocalTimeResolution:
    status: LocalTimeStatus
    timezone_id: str
    candidates: tuple[UtcCandidate, ...]


@lru_cache(maxsize=1)
def timezone_finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder(in_memory=True)


def timezone_at(latitude: float, longitude: float) -> str:
    timezone_id = timezone_finder().timezone_at(lat=latitude, lng=longitude)
    if not timezone_id:
        raise ValueError("No IANA timezone could be resolved for these coordinates")
    return timezone_id


def resolve_local_time(local_datetime: datetime, timezone_id: str) -> LocalTimeResolution:
    if local_datetime.tzinfo is not None:
        raise ValueError("local_datetime must be naive")
    try:
        zone = ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("The saved location has an invalid timezone") from exc
    candidates: list[UtcCandidate] = []
    seen: set[datetime] = set()
    for fold in (0, 1):
        aware = local_datetime.replace(tzinfo=zone, fold=fold)
        utc_value = aware.astimezone(UTC)
        if utc_value.astimezone(zone).replace(tzinfo=None) != local_datetime or utc_value in seen:
            continue
        seen.add(utc_value)
        offset = aware.utcoffset()
        assert offset is not None
        candidates.append(UtcCandidate(fold, utc_value, int(offset.total_seconds())))
    status = (
        LocalTimeStatus.NONEXISTENT
        if not candidates
        else LocalTimeStatus.AMBIGUOUS
        if len(candidates) == 2
        else LocalTimeStatus.RESOLVED
    )
    return LocalTimeResolution(status, timezone_id, tuple(candidates))


def require_utc(local_datetime: datetime, timezone_id: str, fold: int | None = None) -> datetime:
    resolution = resolve_local_time(local_datetime, timezone_id)
    if resolution.status is LocalTimeStatus.NONEXISTENT:
        raise LocalTimeError("nonexistent_local_time", resolution)
    if resolution.status is LocalTimeStatus.AMBIGUOUS and fold is None:
        raise LocalTimeError("ambiguous_local_time", resolution)
    selected = (
        resolution.candidates[0]
        if fold is None
        else next(
            (candidate for candidate in resolution.candidates if candidate.fold == fold), None
        )
    )
    if selected is None:
        raise LocalTimeError("invalid_fold", resolution)
    return selected.utc_datetime


class LocalTimeError(ValueError):
    def __init__(self, code: str, resolution: LocalTimeResolution):
        super().__init__(code)
        self.code = code
        self.resolution = resolution
