import copy
import json
from pathlib import Path

from charts.certification import build_certification_report, compare_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "certification" / "golden_fixtures.json"


def provider_from_reference(fixture):
    reference = fixture["reference_result"]
    cusps = reference["house_cusps"]
    return {
        "time_precision": "EXACT",
        "planets": [
            {
                "name": name,
                "longitude": value["longitude"],
                "zodiac_sign": value["sign"],
                "is_retrograde": value["is_retrograde"],
                "house_number": value["house_number"],
            }
            for name, value in reference["planets"].items()
        ],
        "angles": reference["angles"],
        "houses": [
            {"number": index + 1, "start_cusp": cusp, "end_cusp": cusps[(index + 1) % 12]}
            for index, cusp in enumerate(cusps)
        ],
        "aspects": reference["aspects"],
    }


def test_unrun_golden_suite_is_honestly_blocked():
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = build_certification_report(document)
    assert report["gate_decision"] == "BLOCKED"
    assert {key: report["summary"][key] for key in ("PASS", "FAIL", "BLOCKED")} == {
        "PASS": 0,
        "FAIL": 0,
        "BLOCKED": 5,
    }


def test_exact_tolerance_comparator_passes_equal_values_and_rejects_moon_error():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["fixtures"][0]
    fixture["provider_result"] = provider_from_reference(fixture)
    assert compare_fixture(fixture)["status"] == "PASS"
    failed = copy.deepcopy(fixture)
    next(item for item in failed["provider_result"]["planets"] if item["name"] == "Moon")[
        "longitude"
    ] += 0.0031
    result = compare_fixture(failed)
    assert result["status"] == "FAIL"
    assert any(
        item["field"] == "planet.Moon.longitude" and not item["passed"]
        for item in result["comparisons"]
    )


def test_unknown_time_omissions_are_exact():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["fixtures"][4]
    fixture["provider_result"] = {
        "angles": None,
        "houses": [],
        "planets": [{"name": "Sun", "longitude": None, "house_number": None}],
    }
    assert compare_fixture(fixture)["status"] == "PASS"
    fixture["provider_result"]["planets"][0]["house_number"] = 1
    assert compare_fixture(fixture)["status"] == "FAIL"
