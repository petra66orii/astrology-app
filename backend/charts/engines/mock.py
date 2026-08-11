"""Deterministic local engine for the runnable development slice and tests."""

import hashlib
from datetime import UTC, datetime

from charts.domain import (
    Aspect,
    BirthTimePrecision,
    CalculationMetadata,
    ChartAngles,
    HousePosition,
    NormalizedNatalChart,
    PlanetPosition,
)

from .prokerala import ProkeralaEngine


class MockAstrologyEngine(ProkeralaEngine):
    planet_names = (
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
    )
    zodiac = (
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    )

    def __init__(self):
        super().__init__("development-mock", "development-mock")

    def _metadata(
        self, source_hash: str, request_count: int = 1, capped: bool = False
    ) -> CalculationMetadata:
        return CalculationMetadata(
            provider="development-mock",
            provider_api_version="fixture-v1",
            adapter_version="mock-engine-1",
            contract_version=self.contract_version,
            calculation_version="mock-tropical-placidus-v1",
            zodiac_system="tropical",
            house_system="placidus",
            aspect_profile="major-default-v1",
            calculated_at=datetime.now(UTC),
            source_response_sha256=source_hash,
            provider_request_count=request_count,
            sampling_capped=capped,
        )

    def calculate_exact_chart(
        self, *, utc_datetime: datetime, latitude: float, longitude: float
    ) -> NormalizedNatalChart:
        epoch_hours = utc_datetime.timestamp() / 3600
        positions = []
        for index, name in enumerate(self.planet_names):
            speed = 0.55 if name == "Moon" else 0.04 / (index + 1)
            degrees = (index * 32.7 + epoch_hours * speed) % 360
            positions.append(
                PlanetPosition(
                    name=name,
                    longitude=degrees,
                    zodiac_sign=self.zodiac[int(degrees // 30)],
                    is_retrograde=name in {"Mercury", "Saturn"},
                    house_number=int((degrees - longitude) % 360 // 30) + 1,
                )
            )
        ascendant = (epoch_hours * 15 + longitude) % 360
        houses = tuple(
            HousePosition(
                number=index + 1,
                start_cusp=(ascendant + index * 30) % 360,
                end_cusp=(ascendant + (index + 1) * 30) % 360,
            )
            for index in range(12)
        )
        aspects = (
            Aspect("Sun", "Moon", "Trine", 1.25),
            Aspect("Venus", "Mars", "Sextile", 2.1),
        )
        source_hash = hashlib.sha256(
            f"{utc_datetime.isoformat()}:{latitude:.6f}:{longitude:.6f}".encode()
        ).hexdigest()
        return NormalizedNatalChart(
            BirthTimePrecision.EXACT,
            tuple(positions),
            ChartAngles(
                ascendant=ascendant,
                midheaven=(ascendant + 270) % 360,
                descendant=(ascendant + 180) % 360,
                imum_coeli=(ascendant + 90) % 360,
            ),
            houses,
            aspects,
            (),
            self._metadata(source_hash),
        )
