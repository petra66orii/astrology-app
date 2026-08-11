from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from charts.domain import NormalizedNatalChart


class AstrologyEngine(Protocol):
    def calculate_exact_chart(
        self,
        *,
        utc_datetime: datetime,
        latitude: float,
        longitude: float,
        chart_id: UUID | None = None,
    ) -> NormalizedNatalChart: ...
    def calculate_unknown_time_chart(
        self, *, birth_date: date, timezone_id: str, latitude: float, longitude: float
    ) -> NormalizedNatalChart: ...


class ProviderError(RuntimeError):
    def __init__(
        self,
        code: str,
        safe_message: str,
        retryable: bool = False,
        http_status: int | None = None,
    ):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable
        self.http_status = http_status
