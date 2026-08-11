from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class BirthTimePrecision(StrEnum):
    EXACT = "EXACT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class LongitudeRange:
    start_degrees: float
    end_degrees: float
    wraps_zero: bool


@dataclass(frozen=True, slots=True)
class PlanetPosition:
    name: str
    longitude: float | None
    zodiac_sign: str | None
    is_retrograde: bool | None
    house_number: int | None
    longitude_range: LongitudeRange | None = None
    sign_is_invariant: bool | None = None
    retrograde_is_invariant: bool | None = None


@dataclass(frozen=True, slots=True)
class ChartAngles:
    ascendant: float | None
    midheaven: float | None
    descendant: float | None
    imum_coeli: float | None


@dataclass(frozen=True, slots=True)
class HousePosition:
    number: int
    start_cusp: float
    end_cusp: float


@dataclass(frozen=True, slots=True)
class Aspect:
    body_one: str
    body_two: str
    name: str
    orb_degrees: float
    stable_for_interval: bool = True


@dataclass(frozen=True, slots=True)
class UnavailableCalculation:
    field: str
    reason: str


@dataclass(frozen=True, slots=True)
class CalculationMetadata:
    provider: str
    provider_api_version: str
    adapter_version: str
    contract_version: str
    calculation_version: str
    zodiac_system: str
    house_system: str
    aspect_profile: str
    calculated_at: datetime
    source_response_sha256: str
    provider_request_count: int = 1
    sampling_capped: bool = False


@dataclass(frozen=True, slots=True)
class NormalizedNatalChart:
    time_precision: BirthTimePrecision
    planets: tuple[PlanetPosition, ...]
    angles: ChartAngles | None
    houses: tuple[HousePosition, ...]
    aspects: tuple[Aspect, ...]
    unavailable: tuple[UnavailableCalculation, ...]
    metadata: CalculationMetadata

    def __post_init__(self):
        if self.time_precision is BirthTimePrecision.UNKNOWN:
            if self.angles is not None or self.houses:
                raise ValueError("Unknown-time charts cannot contain angles or houses")
            if any(planet.house_number is not None for planet in self.planets):
                raise ValueError("Unknown-time charts cannot contain house placements")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["time_precision"] = self.time_precision.value
        value["metadata"]["calculated_at"] = self.metadata.calculated_at.isoformat()
        return json.loads(json.dumps(value))
