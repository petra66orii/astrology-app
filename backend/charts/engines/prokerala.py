from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, date, datetime, timedelta
from datetime import time as datetime_time
from decimal import Decimal
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from django.conf import settings

from charts.domain import (
    Aspect,
    BirthTimePrecision,
    CalculationMetadata,
    ChartAngles,
    HousePosition,
    NormalizedNatalChart,
    PlanetPosition,
    UnavailableCalculation,
)
from charts.models import ProviderCreditEvent
from charts.provider_usage import reserve_provider_credits

from .base import ProviderError
from .sampling import SampleFrame, SamplePosition, adaptive_sample


class ProkeralaEngine:
    base_url = "https://api.prokerala.com/v2"
    token_url = "https://api.prokerala.com/token"
    adapter_version = "prokerala-v2-production-1"
    contract_version = "1.0.0"
    calculation_version = "tropical-placidus-major-v1"
    endpoint = "/astrology/natal-planet-position"
    credits_per_request = 500
    main_planets = {
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    }
    major_aspects = {"conjunction", "sextile", "square", "trine", "opposition"}

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        max_unknown_samples: int | None = None,
        credit_budget: int | None = None,
    ):
        if not client_id or not client_secret:
            raise ProviderError(
                "provider_not_configured", "Astrology calculation is not configured."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, min(max_retries, 3))
        self.max_unknown_samples = max_unknown_samples or settings.UNKNOWN_TIME_MAX_SAMPLES
        self.credit_budget = credit_budget
        self._reserved_credits = 0
        self._budget_lock = Lock()
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._last_http_status: int | None = None
        self.last_response_observation: dict[str, Any] | None = None

    def _read_json(self, request: Request, *, retry: bool) -> dict[str, Any]:
        attempts = self.max_retries + 1 if retry else 1
        for attempt in range(attempts):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    self._last_http_status = getattr(response, "status", 200)
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                is_retryable = exc.code == 429 or exc.code >= 500
                if is_retryable and attempt + 1 < attempts:
                    time.sleep(0.25 * (2**attempt))
                    continue
                raise ProviderError(
                    f"provider_http_{exc.code}",
                    "The astrology provider could not complete the request.",
                    is_retryable,
                    exc.code,
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt + 1 < attempts:
                    time.sleep(0.25 * (2**attempt))
                    continue
                raise ProviderError(
                    "provider_unavailable",
                    "The astrology provider is temporarily unavailable.",
                    True,
                ) from exc
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    "provider_invalid_response",
                    "The astrology provider returned an invalid response.",
                ) from exc
        raise AssertionError("unreachable")

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("ascii")
        payload = self._read_json(
            Request(
                self.token_url,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ),
            retry=True,
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise ProviderError(
                "provider_auth_invalid", "The astrology provider could not authenticate."
            )
        self._token = token
        self._token_expires_at = time.monotonic() + max(
            30, int(payload.get("expires_in", 3600)) - 30
        )
        return token

    def _reserve_budget(self, credits: int) -> None:
        if self.credit_budget is None:
            return
        with self._budget_lock:
            if self._reserved_credits + credits > self.credit_budget:
                raise ProviderError(
                    "provider_credit_budget_exceeded",
                    "The configured live-provider credit budget would be exceeded.",
                )
            self._reserved_credits += credits

    def _ensure_budget_available(self, credits: int) -> None:
        if self.credit_budget is not None and self._reserved_credits + credits > self.credit_budget:
            raise ProviderError(
                "provider_credit_budget_exceeded",
                "The configured live-provider credit budget is too small for this calculation.",
            )

    @staticmethod
    def _maximum_decimal_places(value: Any) -> int:
        observed: list[int] = []

        def visit(item: Any) -> None:
            if isinstance(item, float):
                observed.append(max(0, -Decimal(str(item)).as_tuple().exponent))
            elif isinstance(item, dict):
                for nested in item.values():
                    visit(nested)
            elif isinstance(item, list):
                for nested in item:
                    visit(nested)

        visit(value)
        return max(observed, default=0)

    def calculate_exact_chart(
        self,
        *,
        utc_datetime: datetime,
        latitude: float,
        longitude: float,
        chart_id: UUID | None = None,
        flow: str = ProviderCreditEvent.Flow.EXACT,
        sample_number: int | None = None,
    ) -> NormalizedNatalChart:
        if utc_datetime.tzinfo is None:
            raise ValueError("utc_datetime must be timezone-aware")
        if type(self) is ProkeralaEngine and not settings.RUN_LIVE_PROKERALA_TESTS:
            raise ProviderError(
                "live_provider_not_enabled",
                "Live provider calls require the explicit RUN_LIVE_PROKERALA_TESTS flag.",
            )
        chart_id = chart_id or uuid4()
        self._reserve_budget(self.credits_per_request)
        try:
            usage = reserve_provider_credits(
                provider="prokerala",
                endpoint=self.endpoint,
                estimated_credits=self.credits_per_request,
                chart_id=chart_id,
                flow=flow,
                sample_number=sample_number,
            )
        except Exception as exc:
            raise ProviderError(
                "provider_observability_unavailable",
                "Provider usage could not be recorded, so the paid call was refused.",
            ) from exc
        query = urlencode(
            {
                "datetime": utc_datetime.astimezone(UTC).isoformat(timespec="seconds"),
                "coordinates": f"{latitude:.6f},{longitude:.6f}",
                "house_system": "placidus",
                "orb": "default",
                "ayanamsa": 0,
                "la": "en",
            }
        )
        started = time.monotonic()
        try:
            payload = self._read_json(
                Request(
                    f"{self.base_url}{self.endpoint}?{query}",
                    headers={
                        "Authorization": f"Bearer {self._access_token()}",
                        "Accept": "application/json",
                    },
                ),
                # Calculation calls consume credits. Never retry automatically.
                retry=False,
            )
            data = payload.get("data") if isinstance(payload, dict) else None
            self.last_response_observation = {
                "http_status": self._last_http_status or 200,
                "provider_api_version": "v2",
                "top_level_keys": sorted(payload) if isinstance(payload, dict) else [],
                "data_keys": sorted(data) if isinstance(data, dict) else [],
                "raw_payload_persisted": False,
                "provider_credit_usage_exposed": False,
                "maximum_decimal_places_observed": self._maximum_decimal_places(payload),
            }
            result = self._normalize_exact(payload)
        except ProviderError as exc:
            usage.complete(
                succeeded=False,
                latency_ms=round((time.monotonic() - started) * 1000),
                failure_code=exc.code,
                response_http_status=exc.http_status,
            )
            raise
        usage.complete(
            succeeded=True,
            latency_ms=round((time.monotonic() - started) * 1000),
            response_http_status=self._last_http_status or 200,
        )
        return result

    def calculate_unknown_time_chart(
        self,
        *,
        birth_date: date,
        timezone_id: str,
        latitude: float,
        longitude: float,
        chart_id: UUID | None = None,
    ) -> NormalizedNatalChart:
        if not settings.ENABLE_LIVE_UNKNOWN_TIME and type(self) is ProkeralaEngine:
            raise ProviderError(
                "unknown_time_live_disabled",
                f"Unknown-time live calculation is disabled pending approval of its {self.max_unknown_samples * 500:,}-credit maximum cost.",
            )
        chart_id = chart_id or uuid4()
        self._ensure_budget_available(self.max_unknown_samples * self.credits_per_request)
        zone = ZoneInfo(timezone_id)
        start = datetime.combine(birth_date, datetime_time.min, zone).astimezone(UTC)
        end = datetime.combine(birth_date + timedelta(days=1), datetime_time.min, zone).astimezone(
            UTC
        ) - timedelta(microseconds=1)
        source_hashes: list[str] = []

        def calculate(instant: datetime) -> SampleFrame:
            chart = self.calculate_exact_chart(
                utc_datetime=instant,
                latitude=latitude,
                longitude=longitude,
                chart_id=chart_id,
                flow=ProviderCreditEvent.Flow.UNKNOWN,
                sample_number=len(source_hashes) + 1,
            )
            source_hashes.append(chart.metadata.source_response_sha256)
            positions = {
                item.name: SamplePosition(item.longitude or 0.0, bool(item.is_retrograde))
                for item in chart.planets
            }
            aspects = {
                (
                    min(item.body_one, item.body_two),
                    max(item.body_one, item.body_two),
                    item.name,
                ): item
                for item in chart.aspects
            }
            return SampleFrame(instant, positions, aspects)

        summary = adaptive_sample(start, end, calculate, max_samples=self.max_unknown_samples)
        combined_hash = hashlib.sha256("".join(sorted(source_hashes)).encode("ascii")).hexdigest()
        metadata = self._metadata(combined_hash, len(summary.samples), summary.capped)
        unavailable = (
            UnavailableCalculation("angles", "Birth time is unknown."),
            UnavailableCalculation("houses", "Birth time is unknown."),
            UnavailableCalculation("house_placements", "Birth time is unknown."),
        )
        return NormalizedNatalChart(
            BirthTimePrecision.UNKNOWN,
            summary.planets,
            None,
            (),
            summary.stable_aspects,
            unavailable,
            metadata,
        )

    @staticmethod
    def _longitude(value: Any, field: str) -> float:
        if not isinstance(value, (int, float)):
            raise ProviderError(
                "provider_schema_mismatch", f"Provider returned an invalid {field}."
            )
        return float(value) % 360.0

    def _metadata(
        self, source_hash: str, request_count: int = 1, capped: bool = False
    ) -> CalculationMetadata:
        return CalculationMetadata(
            provider="prokerala",
            provider_api_version="v2",
            adapter_version=self.adapter_version,
            contract_version=self.contract_version,
            calculation_version=self.calculation_version,
            zodiac_system="tropical",
            house_system="placidus",
            aspect_profile="major-default-v1",
            calculated_at=datetime.now(UTC),
            source_response_sha256=source_hash,
            provider_request_count=request_count,
            sampling_capped=capped,
        )

    def _normalize_exact(self, payload: dict[str, Any]) -> NormalizedNatalChart:
        try:
            if payload.get("status") != "ok":
                raise ProviderError(
                    "provider_rejected", "The astrology provider rejected the calculation."
                )
            data = payload["data"]
            planets = tuple(
                PlanetPosition(
                    name=item["name"],
                    longitude=self._longitude(item["longitude"], "planet longitude"),
                    zodiac_sign=item["zodiac"]["name"],
                    is_retrograde=bool(item["is_retrograde"]),
                    house_number=int(item["house_number"]),
                )
                for item in data["planet_positions"]
                if item["name"] in self.main_planets
            )
            houses = tuple(
                HousePosition(
                    number=int(item["number"]),
                    start_cusp=self._longitude(item["start_cusp"]["longitude"], "house cusp"),
                    end_cusp=self._longitude(item["end_cusp"]["longitude"], "house cusp"),
                )
                for item in data["houses"]
            )
            angle_values = {
                item["name"].casefold(): self._longitude(item["longitude"], "angle")
                for item in data["angles"]
            }
            angles = ChartAngles(
                angle_values.get("ascendant"),
                angle_values.get("midheaven", angle_values.get("mid heaven")),
                angle_values.get("descendant"),
                angle_values.get("imum coeli", angle_values.get("nadir")),
            )
            aspects = tuple(
                Aspect(
                    item["planet_one"]["name"],
                    item["planet_two"]["name"],
                    item["aspect"]["name"],
                    float(item["orb"]),
                )
                for item in data["aspects"]
                if item["planet_one"]["name"] in self.main_planets
                and item["planet_two"]["name"] in self.main_planets
                and item["aspect"]["name"].casefold() in self.major_aspects
            )
            if {item.name for item in planets} != self.main_planets:
                raise ProviderError(
                    "provider_schema_mismatch",
                    "Provider response did not contain the required ten planets.",
                )
            if {item.number for item in houses} != set(range(1, 13)):
                raise ProviderError(
                    "provider_schema_mismatch",
                    "Provider response did not contain all twelve houses.",
                )
            if angles.ascendant is None or angles.midheaven is None:
                raise ProviderError(
                    "provider_schema_mismatch",
                    "Provider response did not contain the required chart angles.",
                )
        except ProviderError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                "provider_schema_mismatch", "The astrology provider response was incomplete."
            ) from exc
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return NormalizedNatalChart(
            BirthTimePrecision.EXACT,
            planets,
            angles,
            houses,
            aspects,
            (),
            self._metadata(hashlib.sha256(canonical).hexdigest()),
        )
