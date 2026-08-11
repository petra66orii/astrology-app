from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from charts.domain import (
    Aspect,
    BirthTimePrecision,
    CalculationMetadata,
    ChartAngles,
    HousePosition,
    LongitudeRange,
    NormalizedNatalChart,
    PlanetPosition,
    UnavailableCalculation,
)
from charts.engines.base import ProviderError
from charts.engines.prokerala import ProkeralaEngine
from charts.models import BirthProfile, NatalChart
from charts.services import ChartCreationError, create_natal_chart

FIXTURE = Path(__file__).parent / "fixtures" / "prokerala_natal.json"


def metadata(request_count=1):
    return CalculationMetadata(
        provider="mock-prokerala",
        provider_api_version="v2",
        adapter_version="test-1",
        contract_version="1.0.0",
        calculation_version="test-calc",
        zodiac_system="tropical",
        house_system="placidus",
        aspect_profile="major-default-v1",
        calculated_at=datetime.now(UTC),
        source_response_sha256="a" * 64,
        provider_request_count=request_count,
    )


class MockEngine:
    def calculate_exact_chart(self, **kwargs):
        return NormalizedNatalChart(
            BirthTimePrecision.EXACT,
            (PlanetPosition("Sun", 100.0, "Cancer", False, 1),),
            ChartAngles(10.0, 20.0, 190.0, 200.0),
            (HousePosition(1, 10.0, 40.0),),
            (Aspect("Sun", "Moon", "Trine", 1.0),),
            (),
            metadata(),
        )

    def calculate_unknown_time_chart(self, **kwargs):
        return NormalizedNatalChart(
            BirthTimePrecision.UNKNOWN,
            (
                PlanetPosition(
                    "Sun",
                    None,
                    "Cancer",
                    False,
                    None,
                    LongitudeRange(99.5, 100.5, False),
                    True,
                    True,
                ),
            ),
            None,
            (),
            (),
            (UnavailableCalculation("angles", "Birth time is unknown."),),
            metadata(5),
        )


@pytest.mark.django_db
def test_exact_and_unknown_chart_persistence_and_suppression(user, resolved_location):
    exact = BirthProfile.objects.create(
        owner=user,
        display_label="Exact",
        local_birth_date=date(2026, 6, 15),
        local_birth_time=time(12),
        birth_time_precision="EXACT",
        resolved_location=resolved_location,
    )
    unknown = BirthProfile.objects.create(
        owner=user,
        display_label="Unknown",
        local_birth_date=date(2026, 6, 15),
        birth_time_precision="UNKNOWN",
        resolved_location=resolved_location,
    )
    with patch("charts.services.get_chart_engine", return_value=MockEngine()):
        exact_chart = create_natal_chart(profile=exact)
        unknown_chart = create_natal_chart(profile=unknown)
    assert exact_chart.normalized_result["angles"]["ascendant"] == 10.0
    assert unknown_chart.normalized_result["angles"] is None
    assert unknown_chart.normalized_result["houses"] == []
    assert unknown_chart.normalized_result["planets"][0]["house_number"] is None


@pytest.mark.django_db
def test_chart_and_calculation_version_are_immutable(user, resolved_location):
    profile = BirthProfile.objects.create(
        owner=user,
        display_label="Exact",
        local_birth_date=date(2026, 6, 15),
        local_birth_time=time(12),
        birth_time_precision="EXACT",
        resolved_location=resolved_location,
    )
    with patch("charts.services.get_chart_engine", return_value=MockEngine()):
        chart = create_natal_chart(profile=profile)
    chart.status = NatalChart.Status.FAILED
    with pytest.raises(ValidationError):
        chart.save()
    chart.calculation_version.provider = "changed"
    with pytest.raises(ValidationError):
        chart.calculation_version.save()


@pytest.mark.django_db
def test_chart_api_enforces_ownership(user, other_user, resolved_location):
    profile = BirthProfile.objects.create(
        owner=other_user,
        display_label="Private",
        local_birth_date=date(2026, 6, 15),
        birth_time_precision="UNKNOWN",
        resolved_location=resolved_location,
    )
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1/charts/create/", {"birth_profile_id": str(profile.id)}, format="json"
    )
    assert response.status_code == 404


def test_exact_prokerala_normalization_and_error_translation(settings):
    engine = ProkeralaEngine("id", "secret")
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = engine._normalize_exact(payload)
    assert result.planets[0].zodiac_sign == "Capricorn"
    assert result.angles.ascendant == 101.25
    with pytest.raises(ProviderError) as caught:
        engine._normalize_exact({"status": "ok", "data": {}})
    assert caught.value.code == "provider_schema_mismatch"


def test_unknown_sampler_never_exposes_time_dependent_fields(settings):
    settings.ENABLE_LIVE_UNKNOWN_TIME = True

    class SamplingEngine(ProkeralaEngine):
        def calculate_exact_chart(self, *, utc_datetime, latitude, longitude):
            hours = utc_datetime.hour + utc_datetime.minute / 60
            return NormalizedNatalChart(
                BirthTimePrecision.EXACT,
                (
                    PlanetPosition("Sun", 100 + hours * 0.01, "Cancer", False, 1),
                    PlanetPosition("Moon", 220 + hours * 0.2, "Scorpio", False, 5),
                ),
                ChartAngles(10, 20, 190, 200),
                (HousePosition(1, 10, 40),),
                (),
                (),
                metadata(),
            )

    result = SamplingEngine("id", "secret", max_unknown_samples=9).calculate_unknown_time_chart(
        birth_date=date(2026, 6, 15),
        timezone_id="Europe/Dublin",
        latitude=53.33,
        longitude=-6.24,
    )
    assert result.time_precision is BirthTimePrecision.UNKNOWN
    assert result.angles is None and result.houses == ()
    assert all(item.house_number is None and item.longitude is None for item in result.planets)
    assert result.metadata.provider_request_count <= 9


@pytest.mark.django_db
def test_ambiguous_and_nonexistent_errors_are_safe(user, resolved_location):
    ambiguous = BirthProfile.objects.create(
        owner=user,
        display_label="Ambiguous",
        local_birth_date=date(2026, 10, 25),
        local_birth_time=time(1, 30),
        birth_time_precision="EXACT",
        resolved_location=resolved_location,
    )
    nonexistent = BirthProfile.objects.create(
        owner=user,
        display_label="Gap",
        local_birth_date=date(2026, 3, 29),
        local_birth_time=time(1, 30),
        birth_time_precision="EXACT",
        resolved_location=resolved_location,
    )
    with patch("charts.services.get_chart_engine", return_value=MockEngine()):
        with pytest.raises(ChartCreationError) as ambiguous_error:
            create_natal_chart(profile=ambiguous)
        with pytest.raises(ChartCreationError) as gap_error:
            create_natal_chart(profile=nonexistent)
    assert ambiguous_error.value.code == "ambiguous_local_time"
    assert len(ambiguous_error.value.candidates) == 2
    assert gap_error.value.code == "nonexistent_local_time"


@pytest.mark.django_db
def test_complete_mocked_exact_and_unknown_api_flow(settings, user, dublin):
    settings.ASTROLOGY_ENGINE = "mock"
    client = APIClient()
    client.force_authenticate(user)

    exact_profile = client.post(
        "/api/v1/birth-profiles/",
        {
            "display_label": "Exact API chart",
            "local_birth_date": "2026-06-15",
            "local_birth_time": "12:00:00",
            "birth_time_precision": "EXACT",
            "geonames_location_id": dublin.geonames_id,
        },
        format="json",
    )
    assert exact_profile.status_code == 201
    exact_chart = client.post(
        "/api/v1/charts/create/",
        {"birth_profile_id": exact_profile.data["id"]},
        format="json",
    )
    assert exact_chart.status_code == 201
    assert exact_chart.data["normalized_result"]["angles"] is not None
    assert client.get(f"/api/v1/charts/{exact_chart.data['id']}/").status_code == 200

    unknown_profile = client.post(
        "/api/v1/birth-profiles/",
        {
            "display_label": "Unknown API chart",
            "local_birth_date": "2026-06-15",
            "birth_time_precision": "UNKNOWN",
            "geonames_location_id": dublin.geonames_id,
        },
        format="json",
    )
    assert unknown_profile.status_code == 201
    unknown_chart = client.post(
        "/api/v1/charts/create/",
        {"birth_profile_id": unknown_profile.data["id"]},
        format="json",
    )
    assert unknown_chart.status_code == 201
    result = unknown_chart.data["normalized_result"]
    assert result["angles"] is None and result["houses"] == []
    assert all(item["house_number"] is None for item in result["planets"])
