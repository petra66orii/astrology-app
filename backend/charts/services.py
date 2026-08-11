from __future__ import annotations

import hashlib
import json
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from locations.timezones import LocalTimeError, require_utc

from .domain import BirthTimePrecision
from .engines import ProkeralaEngine
from .engines.base import ProviderError
from .models import BirthProfile, ChartCalculationVersion, NatalChart


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def get_chart_engine():
    if settings.ASTROLOGY_ENGINE == "mock":
        from .engines.mock import MockAstrologyEngine

        return MockAstrologyEngine()
    budget = settings.PROKERALA_LIVE_CREDIT_BUDGET or None
    return ProkeralaEngine(
        settings.PROKERALA_CLIENT_ID,
        settings.PROKERALA_CLIENT_SECRET,
        credit_budget=budget,
    )


class ChartCreationError(RuntimeError):
    def __init__(
        self,
        code: str,
        detail: str,
        *,
        candidates: list[dict] | None = None,
        status_code: int = 400,
    ):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.candidates = candidates or []
        self.status_code = status_code


def _input_snapshot(profile: BirthProfile, fold: int | None) -> dict:
    location = profile.resolved_location
    return {
        "display_label": profile.display_label,
        "local_birth_date": profile.local_birth_date.isoformat(),
        "local_birth_time": profile.local_birth_time.isoformat()
        if profile.local_birth_time
        else None,
        "birth_time_precision": profile.birth_time_precision,
        "fold": fold,
        "location": {
            "source": location.source,
            "source_id": location.source_id,
            "display_name": location.selected_display_name,
            "latitude": str(location.latitude),
            "longitude": str(location.longitude),
            "timezone_id": location.timezone_id,
            "source_data_version": location.source_data_version,
            "identity_hash": location.identity_hash,
        },
    }


def create_natal_chart(*, profile: BirthProfile, fold: int | None = None) -> NatalChart:
    today = timezone.localdate()
    if NatalChart.objects.filter(owner=profile.owner, created_at__date=today).count() >= (
        settings.USER_DAILY_CHART_CREATION_LIMIT
    ):
        raise ChartCreationError(
            "daily_chart_limit_reached",
            "The daily chart-creation limit has been reached.",
            status_code=429,
        )
    chart_id = uuid4()
    location = profile.resolved_location
    snapshot = _input_snapshot(profile, fold)
    fingerprint = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    try:
        engine = get_chart_engine()
        if profile.birth_time_precision == BirthTimePrecision.EXACT:
            if profile.local_birth_time is None:
                raise ChartCreationError(
                    "missing_birth_time", "An exact-time profile requires a birth time."
                )
            local_datetime = datetime.combine(profile.local_birth_date, profile.local_birth_time)
            try:
                utc_datetime = require_utc(local_datetime, location.timezone_id, fold)
            except LocalTimeError as exc:
                if exc.code == "nonexistent_local_time":
                    raise ChartCreationError(
                        exc.code,
                        "That local time did not occur because clocks changed. Correct the time or choose unknown birth time.",
                        status_code=409,
                    ) from exc
                if exc.code == "ambiguous_local_time":
                    raise ChartCreationError(
                        exc.code,
                        "That local time occurred twice because clocks changed. Select the correct offset.",
                        candidates=[item.as_dict() for item in exc.resolution.candidates],
                        status_code=409,
                    ) from exc
                raise
            result = engine.calculate_exact_chart(
                utc_datetime=utc_datetime,
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                chart_id=chart_id,
            )
            snapshot["utc_datetime"] = utc_datetime.isoformat().replace("+00:00", "Z")
        else:
            result = engine.calculate_unknown_time_chart(
                birth_date=profile.local_birth_date,
                timezone_id=location.timezone_id,
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                chart_id=chart_id,
            )
    except ChartCreationError:
        raise
    except ProviderError as exc:
        raise ChartCreationError(
            exc.code,
            exc.safe_message,
            status_code=503 if exc.retryable or exc.code.endswith("disabled") else 502,
        ) from exc

    metadata = result.metadata
    with transaction.atomic():
        calculation_version = ChartCalculationVersion.objects.create(
            contract_version=metadata.contract_version,
            adapter_version=metadata.adapter_version,
            provider=metadata.provider,
            provider_api_version=metadata.provider_api_version,
            timezone_data_version=package_version("tzdata"),
            geonames_dataset_version=location.source_data_version,
            zodiac_system=metadata.zodiac_system,
            house_system=metadata.house_system,
            aspect_profile_version=metadata.aspect_profile,
            application_git_sha=settings.APP_GIT_SHA,
        )
        return NatalChart.objects.create(
            id=chart_id,
            owner=profile.owner,
            birth_profile=profile,
            resolved_location=location,
            calculation_version=calculation_version,
            input_snapshot=snapshot,
            input_fingerprint=fingerprint,
            normalized_result=result.as_dict(),
            status=NatalChart.Status.SUCCEEDED,
            provider_response_hash=metadata.source_response_sha256,
            calculated_at=metadata.calculated_at,
        )
