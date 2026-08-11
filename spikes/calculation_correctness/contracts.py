"""Provider-neutral calculation contracts.

Provider payloads must be normalized into these immutable values before any
frontend or persistence layer can consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class BirthTimePrecision(StrEnum):
    EXACT = "EXACT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class LocationIdentity:
    geoname_id: int
    canonical_name: str
    country_code: str
    admin1_code: str | None
    admin2_code: str | None
    latitude: float
    longitude: float
    timezone_id: str


@dataclass(frozen=True, slots=True)
class BirthInput:
    local_datetime: datetime
    location: LocationIdentity
    time_precision: BirthTimePrecision
    fold: int | None = None


@dataclass(frozen=True, slots=True)
class LongitudeRange:
    start_degrees: float
    end_degrees: float
    wraps_zero: bool = False


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
    ascendant: float | None = None
    midheaven: float | None = None
    descendant: float | None = None
    imum_coeli: float | None = None


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
class ChartMetadata:
    provider: str
    provider_api_version: str
    adapter_version: str
    contract_version: str
    calculation_version: str
    zodiac_system: str
    house_system: str
    aspect_profile: str
    timezone_database_version: str
    calculated_at: datetime
    source_response_sha256: str


@dataclass(frozen=True, slots=True)
class NatalChartResult:
    time_precision: BirthTimePrecision
    planets: tuple[PlanetPosition, ...]
    angles: ChartAngles | None
    houses: tuple[HousePosition, ...]
    aspects: tuple[Aspect, ...]
    unavailable: tuple[UnavailableCalculation, ...]
    metadata: ChartMetadata

    def __post_init__(self) -> None:
        if self.time_precision is BirthTimePrecision.UNKNOWN:
            if self.angles is not None or self.houses:
                raise ValueError("unknown-time results cannot contain angles or houses")
            if any(planet.house_number is not None for planet in self.planets):
                raise ValueError("unknown-time results cannot contain house placements")
