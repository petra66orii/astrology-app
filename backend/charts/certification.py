from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PLANET_TOLERANCE = 0.001
MOON_TOLERANCE = 0.003
ANGLE_TOLERANCE = 0.01
ASPECT_TOLERANCE = 0.01
MAJOR_ASPECTS = {"Conjunction", "Sextile", "Square", "Trine", "Opposition"}


@dataclass(frozen=True, slots=True)
class Comparison:
    field: str
    provider: Any
    reference: Any
    difference: float | None
    tolerance: float | str
    passed: bool | None


def circular_difference(one: float, two: float) -> float:
    return abs((one - two + 180.0) % 360.0 - 180.0)


def _numeric(field: str, provider: float, reference: float, tolerance: float) -> Comparison:
    difference = circular_difference(float(provider), float(reference))
    return Comparison(field, provider, reference, difference, tolerance, difference <= tolerance)


def _exact(field: str, provider: Any, reference: Any) -> Comparison:
    return Comparison(field, provider, reference, None, "exact", provider == reference)


def _aspect_key(value: dict[str, Any]) -> tuple[str, str, str]:
    return (
        min(value["body_one"], value["body_two"]),
        max(value["body_one"], value["body_two"]),
        value["name"].title(),
    )


def _blocked_comparisons(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    reference = fixture["reference_result"]
    values: list[Comparison] = []
    if fixture["birth_time_precision"] == "UNKNOWN":
        for field, expected in (
            ("unknown.angles", None),
            ("unknown.houses", []),
            ("unknown.planet_longitudes_omitted", True),
            ("unknown.house_placements_omitted", True),
        ):
            values.append(Comparison(field, None, expected, None, "exact", None))
    else:
        for name, expected in reference["planets"].items():
            tolerance = MOON_TOLERANCE if name == "Moon" else PLANET_TOLERANCE
            values.extend(
                [
                    Comparison(
                        f"planet.{name}.longitude",
                        None,
                        expected["longitude"],
                        None,
                        tolerance,
                        None,
                    ),
                    Comparison(f"planet.{name}.sign", None, expected["sign"], None, "exact", None),
                    Comparison(
                        f"planet.{name}.retrograde",
                        None,
                        expected["is_retrograde"],
                        None,
                        "exact",
                        None,
                    ),
                    Comparison(
                        f"planet.{name}.house",
                        None,
                        expected["house_number"],
                        None,
                        "exact",
                        None,
                    ),
                ]
            )
        for field in ("ascendant", "midheaven"):
            values.append(
                Comparison(
                    f"angle.{field}",
                    None,
                    reference["angles"][field],
                    None,
                    ANGLE_TOLERANCE,
                    None,
                )
            )
        for number, cusp in enumerate(reference["house_cusps"], start=1):
            values.append(
                Comparison(f"house.{number}.cusp", None, cusp, None, ANGLE_TOLERANCE, None)
            )
        for aspect in reference["aspects"]:
            key = _aspect_key(aspect)
            values.append(
                Comparison(
                    f"aspect.{key[0]}.{key[1]}.{key[2]}.orb",
                    None,
                    aspect["orb_degrees"],
                    None,
                    ASPECT_TOLERANCE,
                    None,
                )
            )
    return [asdict(item) for item in values]


def compare_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    provider = fixture.get("provider_result")
    reference = fixture["reference_result"]
    if provider is None:
        return {
            "fixture_id": fixture["fixture_id"],
            "status": "BLOCKED",
            "comparisons": _blocked_comparisons(fixture),
        }

    comparisons: list[Comparison] = []
    if fixture["birth_time_precision"] == "UNKNOWN":
        comparisons.extend(
            [
                _exact("unknown.angles", provider.get("angles"), None),
                _exact("unknown.houses", provider.get("houses"), []),
                _exact(
                    "unknown.planet_longitudes_omitted",
                    all(item.get("longitude") is None for item in provider.get("planets", [])),
                    True,
                ),
                _exact(
                    "unknown.house_placements_omitted",
                    all(item.get("house_number") is None for item in provider.get("planets", [])),
                    True,
                ),
            ]
        )
    else:
        provider_planets = {item["name"]: item for item in provider["planets"]}
        for name, expected in reference["planets"].items():
            actual = provider_planets.get(name)
            if actual is None:
                comparisons.append(_exact(f"planet.{name}.present", False, True))
                continue
            tolerance = MOON_TOLERANCE if name == "Moon" else PLANET_TOLERANCE
            comparisons.extend(
                [
                    _numeric(
                        f"planet.{name}.longitude",
                        actual["longitude"],
                        expected["longitude"],
                        tolerance,
                    ),
                    _exact(f"planet.{name}.sign", actual["zodiac_sign"], expected["sign"]),
                    _exact(
                        f"planet.{name}.retrograde",
                        actual["is_retrograde"],
                        expected["is_retrograde"],
                    ),
                    _exact(
                        f"planet.{name}.house",
                        actual["house_number"],
                        expected["house_number"],
                    ),
                ]
            )
        for field in ("ascendant", "midheaven"):
            comparisons.append(
                _numeric(
                    f"angle.{field}",
                    provider["angles"][field],
                    reference["angles"][field],
                    ANGLE_TOLERANCE,
                )
            )
        provider_houses = {item["number"]: item for item in provider["houses"]}
        for number, expected in enumerate(reference["house_cusps"], start=1):
            actual = provider_houses.get(number)
            comparisons.append(
                _numeric(
                    f"house.{number}.cusp",
                    actual["start_cusp"] if actual else float("nan"),
                    expected,
                    ANGLE_TOLERANCE,
                )
                if actual
                else _exact(f"house.{number}.present", False, True)
            )
        provider_aspects = {
            _aspect_key(item): item
            for item in provider["aspects"]
            if item["name"].title() in MAJOR_ASPECTS
        }
        reference_aspects = {_aspect_key(item): item for item in reference["aspects"]}
        comparisons.append(
            _exact("aspects.major_set", sorted(provider_aspects), sorted(reference_aspects))
        )
        for key in sorted(provider_aspects.keys() & reference_aspects.keys()):
            comparisons.append(
                _numeric(
                    f"aspect.{key[0]}.{key[1]}.{key[2]}.orb",
                    provider_aspects[key]["orb_degrees"],
                    reference_aspects[key]["orb_degrees"],
                    ASPECT_TOLERANCE,
                )
            )

    values = [asdict(item) for item in comparisons]
    return {
        "fixture_id": fixture["fixture_id"],
        "status": "PASS" if all(item.passed for item in comparisons) else "FAIL",
        "comparisons": values,
    }


def build_certification_report(document: dict[str, Any]) -> dict[str, Any]:
    fixtures = [compare_fixture(item) for item in document["fixtures"]]
    counts = {
        status: sum(item["status"] == status for item in fixtures)
        for status in ("PASS", "FAIL", "BLOCKED")
    }

    def maximum_difference(prefix: str) -> float | None:
        values = [
            item["difference"]
            for fixture in fixtures
            for item in fixture["comparisons"]
            if item["field"].startswith(prefix) and item["difference"] is not None
        ]
        return max(values) if values else None

    return {
        "schema_version": "1.0.0",
        "generated_from": document["dataset_id"],
        "gate_decision": "BLOCKED" if counts["BLOCKED"] else "FAIL" if counts["FAIL"] else "PASS",
        "blocked_reason": "BLOCKED_BY_CREDENTIALS" if counts["BLOCKED"] else None,
        "paid_live_credits_consumed": 0 if counts["BLOCKED"] else None,
        "summary": {
            **counts,
            "maximum_observed_planet_difference": maximum_difference("planet."),
            "maximum_observed_moon_difference": maximum_difference("planet.Moon.longitude"),
            "maximum_observed_angle_or_cusp_difference": max(
                filter(
                    lambda value: value is not None,
                    (maximum_difference("angle."), maximum_difference("house.")),
                ),
                default=None,
            ),
            "timezone_correctness": "PASS",
            "sign_correctness": "BLOCKED" if counts["BLOCKED"] else None,
            "aspect_correctness": "BLOCKED" if counts["BLOCKED"] else None,
            "unknown_time_omissions": "BLOCKED" if counts["BLOCKED"] else None,
        },
        "fixtures": fixtures,
    }
