"""Minimal Prokerala v2 adapter with a provider-neutral output boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import socket
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import ADAPTER_VERSION, CALCULATION_VERSION, CONTRACT_VERSION
from .contracts import (
    Aspect, BirthTimePrecision, ChartAngles, ChartMetadata, HousePosition,
    NatalChartResult, PlanetPosition, UnavailableCalculation,
)


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class JsonTransport(Protocol):
    def post_form(self, url: str, data: dict[str, str], timeout: float) -> dict[str, Any]: ...
    def get_json(self, url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]: ...


class UrlLibTransport:
    def _read(self, request: Request, timeout: float) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            retryable = exc.code == 429 or exc.code >= 500
            raise ProviderError(f"PROVIDER_HTTP_{exc.code}", "astrology provider rejected the request", retryable) from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE", "astrology provider is unavailable", True) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("PROVIDER_INVALID_RESPONSE", "astrology provider returned invalid JSON") from exc

    def post_form(self, url: str, data: dict[str, str], timeout: float) -> dict[str, Any]:
        body = urlencode(data).encode("ascii")
        return self._read(Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout)

    def get_json(self, url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
        return self._read(Request(url, headers=headers), timeout)


@dataclass(slots=True)
class ProkeralaAdapter:
    client_id: str
    client_secret: str
    transport: JsonTransport
    timeout_seconds: float = 10.0
    base_url: str = "https://api.prokerala.com/v2"
    token_url: str = "https://api.prokerala.com/token"

    def calculate_exact(
        self, *, utc_datetime: datetime, latitude: float, longitude: float,
        house_system: str = "placidus", aspect_profile: str = "major",
        timezone_database_version: str = "unknown",
    ) -> NatalChartResult:
        if utc_datetime.tzinfo is None or utc_datetime.utcoffset() is None:
            raise ValueError("utc_datetime must be timezone-aware")
        token_data = self.transport.post_form(self.token_url, {
            "grant_type": "client_credentials", "client_id": self.client_id,
            "client_secret": self.client_secret,
        }, self.timeout_seconds)
        token = token_data.get("access_token")
        if not isinstance(token, str) or not token:
            raise ProviderError("PROVIDER_AUTH_INVALID", "provider token response had no access token")
        query = urlencode({
            "datetime": utc_datetime.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "coordinates": f"{latitude:.6f},{longitude:.6f}",
            "house_system": house_system,
            "orb": "default",
            "ayanamsa": 0,
            "la": "en",
        })
        payload = self.transport.get_json(
            f"{self.base_url}/astrology/natal-planet-position?{query}",
            {"Authorization": f"Bearer {token}", "Accept": "application/json"},
            self.timeout_seconds,
        )
        return normalize_exact_response(payload, house_system, aspect_profile, timezone_database_version)


def _longitude(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)):
        raise ProviderError("PROVIDER_SCHEMA_MISMATCH", f"invalid {field}")
    return float(value) % 360.0


def normalize_exact_response(
    payload: dict[str, Any], house_system: str = "placidus",
    aspect_profile: str = "major", timezone_database_version: str = "unknown",
) -> NatalChartResult:
    try:
        if payload.get("status") != "ok":
            raise ProviderError("PROVIDER_REJECTED", "provider returned a non-success status")
        data = payload["data"]
        planets = tuple(PlanetPosition(
            name=item["name"], longitude=_longitude(item["longitude"], "planet longitude"),
            zodiac_sign=item["zodiac"]["name"], is_retrograde=bool(item["is_retrograde"]),
            house_number=int(item["house_number"]),
        ) for item in data["planet_positions"])
        houses = tuple(HousePosition(
            number=int(item["number"]),
            start_cusp=_longitude(item["start_cusp"]["longitude"], "house start cusp"),
            end_cusp=_longitude(item["end_cusp"]["longitude"], "house end cusp"),
        ) for item in data["houses"])
        angle_values = {item["name"].casefold(): _longitude(item["longitude"], "angle longitude") for item in data["angles"]}
        angles = ChartAngles(
            ascendant=angle_values.get("ascendant"), midheaven=angle_values.get("midheaven"),
            descendant=angle_values.get("descendant"), imum_coeli=angle_values.get("imum coeli"),
        )
        aspects = tuple(Aspect(
            body_one=item["planet_one"]["name"], body_two=item["planet_two"]["name"],
            name=item["aspect"]["name"], orb_degrees=float(item["orb"]),
        ) for item in data["aspects"])
    except ProviderError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError("PROVIDER_SCHEMA_MISMATCH", "provider response did not match the documented schema") from exc

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    metadata = ChartMetadata(
        provider="prokerala", provider_api_version="v2", adapter_version=ADAPTER_VERSION,
        contract_version=CONTRACT_VERSION, calculation_version=CALCULATION_VERSION,
        zodiac_system="tropical", house_system=house_system, aspect_profile=aspect_profile,
        timezone_database_version=timezone_database_version,
        calculated_at=datetime.now(timezone.utc), source_response_sha256=hashlib.sha256(canonical).hexdigest(),
    )
    return NatalChartResult(BirthTimePrecision.EXACT, planets, angles, houses, aspects, (), metadata)


def suppress_time_dependent_fields(result: NatalChartResult) -> NatalChartResult:
    planets = tuple(PlanetPosition(
        name=p.name, longitude=None, zodiac_sign=None,
        is_retrograde=None, house_number=None,
    ) for p in result.planets)
    unavailable = (
        UnavailableCalculation("angles", "birth time is unknown"),
        UnavailableCalculation("houses", "birth time is unknown"),
        UnavailableCalculation("house_placements", "birth time is unknown"),
    )
    return NatalChartResult(BirthTimePrecision.UNKNOWN, planets, None, (), (), unavailable, result.metadata)
