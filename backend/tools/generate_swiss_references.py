"""Generate numerical-only golden references with Swiss Ephemeris.

This is certification tooling, not a runtime calculation fallback. Swiss Ephemeris
licensing must be reviewed before its code is ever incorporated into the product.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}
SIGNS = (
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
ASPECT_ANGLES = {
    "Conjunction": 0.0,
    "Sextile": 60.0,
    "Square": 90.0,
    "Trine": 120.0,
    "Opposition": 180.0,
}

FIXTURES = (
    {
        "fixture_id": "A_DUBLIN_EXACT",
        "display_name": "Dublin exact time",
        "local_date": "1990-06-20",
        "local_time": "14:30:00",
        "fold": 0,
        "geonames_id": 2964574,
        "latitude": 53.333060,
        "longitude": -6.248890,
        "timezone": "Europe/Dublin",
    },
    {
        "fixture_id": "B_BUCHAREST_EXACT",
        "display_name": "Bucharest exact time",
        "local_date": "1990-06-20",
        "local_time": "14:30:00",
        "fold": 0,
        "geonames_id": 683506,
        "latitude": 44.432250,
        "longitude": 26.106260,
        "timezone": "Europe/Bucharest",
    },
    {
        "fixture_id": "C_SYDNEY_EXACT",
        "display_name": "Sydney exact time",
        "local_date": "1990-06-20",
        "local_time": "14:30:00",
        "fold": 0,
        "geonames_id": 2147714,
        "latitude": -33.867850,
        "longitude": 151.207320,
        "timezone": "Australia/Sydney",
    },
    {
        "fixture_id": "D_DUBLIN_DST_FOLD_1",
        "display_name": "Dublin ambiguous DST time, second occurrence",
        "local_date": "2026-10-25",
        "local_time": "01:30:00",
        "fold": 1,
        "geonames_id": 2964574,
        "latitude": 53.333060,
        "longitude": -6.248890,
        "timezone": "Europe/Dublin",
    },
    {
        "fixture_id": "E_DUBLIN_UNKNOWN",
        "display_name": "Dublin unknown birth time",
        "local_date": "1990-06-20",
        "local_time": None,
        "fold": None,
        "geonames_id": 2964574,
        "latitude": 53.333060,
        "longitude": -6.248890,
        "timezone": "Europe/Dublin",
    },
)


def julian_day(value: datetime) -> float:
    value = value.astimezone(UTC)
    hour = value.hour + value.minute / 60 + value.second / 3600 + value.microsecond / 3.6e9
    return swe.julday(value.year, value.month, value.day, hour, swe.GREG_CAL)


def circular_separation(one: float, two: float) -> float:
    return abs((one - two + 180.0) % 360.0 - 180.0)


def house_number(longitude: float, cusps: list[float]) -> int:
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        if (longitude - start) % 360.0 < (end - start) % 360.0:
            return index + 1
    raise RuntimeError("Could not place longitude in a house")


def positions(instant: datetime) -> dict[str, dict]:
    result = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for name, planet_id in PLANETS.items():
        values, returned_flags, warning = swe.calc_ut(julian_day(instant), planet_id, flags)
        if warning or not returned_flags & swe.FLG_SWIEPH:
            raise RuntimeError(f"Swiss Ephemeris fallback for {name}: {warning!r}")
        longitude = values[0] % 360.0
        result[name] = {
            "longitude": longitude,
            "sign": SIGNS[int(longitude // 30)],
            "is_retrograde": values[3] < 0,
        }
    return result


def aspects(planets: dict[str, dict]) -> list[dict]:
    result = []
    names = list(planets)
    for index, one in enumerate(names):
        for two in names[index + 1 :]:
            separation = circular_separation(planets[one]["longitude"], planets[two]["longitude"])
            for aspect_name, angle in ASPECT_ANGLES.items():
                orb = abs(separation - angle)
                if orb <= 8.0:
                    result.append(
                        {"body_one": one, "body_two": two, "name": aspect_name, "orb_degrees": orb}
                    )
                    break
    return result


def exact_reference(fixture: dict, instant: datetime) -> dict:
    cusps_raw, ascmc = swe.houses_ex(
        julian_day(instant), fixture["latitude"], fixture["longitude"], b"P", 0
    )
    cusps = list(cusps_raw[1:13])
    planets = positions(instant)
    for value in planets.values():
        value["house_number"] = house_number(value["longitude"], cusps)
    return {
        "planets": planets,
        "angles": {"ascendant": ascmc[0], "midheaven": ascmc[1]},
        "house_cusps": cusps,
        "aspects": aspects(planets),
    }


def unknown_reference(fixture: dict) -> tuple[dict, str]:
    zone = ZoneInfo(fixture["timezone"])
    local_date = date.fromisoformat(fixture["local_date"])
    start = datetime.combine(local_date, time.min, zone).astimezone(UTC)
    end = datetime.combine(local_date + timedelta(days=1), time.min, zone).astimezone(UTC)
    instants = [start + timedelta(hours=index) for index in range(25)]
    instants[-1] = end
    samples = [positions(instant) for instant in instants]
    ranges = {}
    for name in PLANETS:
        anchor = samples[0][name]["longitude"]
        unwrapped = [
            anchor + ((item[name]["longitude"] - anchor + 180) % 360 - 180) for item in samples
        ]
        signs = {item[name]["sign"] for item in samples}
        retrogrades = {item[name]["is_retrograde"] for item in samples}
        ranges[name] = {
            "start_degrees": min(unwrapped) % 360,
            "end_degrees": max(unwrapped) % 360,
            "wraps_zero": min(unwrapped) < 0 or max(unwrapped) >= 360,
            "sign": next(iter(signs)) if len(signs) == 1 else None,
            "is_retrograde": next(iter(retrogrades)) if len(retrogrades) == 1 else None,
        }
    return {
        "angles": None,
        "houses": [],
        "house_placements": None,
        "planet_ranges": ranges,
        "sampling": "25 hourly Swiss Ephemeris samples including both local-day boundaries",
    }, f"{start.isoformat().replace('+00:00', 'Z')}/{end.isoformat().replace('+00:00', 'Z')}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ephemeris-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    swe.set_ephe_path(str(args.ephemeris_dir.resolve()))
    output_fixtures = []
    for fixture in FIXTURES:
        item = dict(fixture)
        if fixture["local_time"] is None:
            reference, utc_interval = unknown_reference(fixture)
            item["birth_time_precision"] = "UNKNOWN"
            item["utc_interval"] = utc_interval
            item["utc_instant"] = None
        else:
            local = datetime.combine(
                date.fromisoformat(fixture["local_date"]),
                time.fromisoformat(fixture["local_time"]),
                ZoneInfo(fixture["timezone"]),
            ).replace(fold=fixture["fold"])
            instant = local.astimezone(UTC)
            reference = exact_reference(fixture, instant)
            item["birth_time_precision"] = "EXACT"
            item["utc_instant"] = instant.isoformat().replace("+00:00", "Z")
            item["utc_interval"] = None
        item.update(
            {
                "zodiac_system": "tropical",
                "house_system": "placidus",
                "aspect_profile": "major aspects, 8 degree maximum orb",
                "prokerala_endpoint": "/v2/astrology/natal-planet-position",
                "prokerala_api_version": "v2 (OpenAPI retrieved 2026-08-11)",
                "calculation_timestamp": "2026-08-11",
                "independent_reference_sources": [
                    {
                        "name": "Swiss Ephemeris 2.10.03 with official DE441-derived .se1 files",
                        "url": "https://github.com/aloistr/swisseph",
                        "role": "planetary longitudes, speeds, Placidus houses, angles, and derived major aspects",
                    },
                    {
                        "name": "GeoNames and IANA tzdata human verification",
                        "url": "https://download.geonames.org/export/dump/",
                        "role": "coordinates, timezone ID, UTC conversion, and DST fold/gap checks",
                    },
                ],
                "reference_retrieval_date": "2026-08-11",
                "reviewer_notes": "Numerical reference generated independently of Prokerala; shared Swiss Ephemeris ancestry remains possible and unverified.",
                "reference_result": reference,
                "provider_result": None,
                "tolerance_result": "BLOCKED_BY_CREDENTIALS",
                "status": "BLOCKED",
            }
        )
        output_fixtures.append(item)
    document = {
        "schema_version": "1.0.0",
        "dataset_id": "gate-b-certification-2026-08-11",
        "reference_engine": {
            "name": "Swiss Ephemeris",
            "library_version": swe.version,
            "binding": "pysweph 2.10.3.6 (certification-only, not a runtime dependency)",
            "planet_file_sha256": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
            "moon_file_sha256": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
            "license_note": "Swiss Ephemeris licensing must be reviewed before any product integration.",
        },
        "fixtures": output_fixtures,
        "timezone_validation": {
            "dublin_nonexistent": {
                "local": "2026-03-29T01:30:00",
                "timezone": "Europe/Dublin",
                "expected": "NONEXISTENT",
            },
            "dublin_ambiguous": {
                "local": "2026-10-25T01:30:00",
                "timezone": "Europe/Dublin",
                "fold_0_utc": "2026-10-25T00:30:00Z",
                "fold_1_utc": "2026-10-25T01:30:00Z",
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
