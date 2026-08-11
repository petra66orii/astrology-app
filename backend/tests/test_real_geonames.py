import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command

from locations.models import GeoNameAlternateName, GeoNameLocation, GeoNamesDataset
from locations.search import normalize_search_text, search_locations
from locations.timezones import timezone_at

FIXTURE = Path(__file__).parent / "fixtures" / "geonames_certification_records.json"


@pytest.fixture
def real_geonames(db):
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    dataset = GeoNamesDataset.objects.create(
        version=source["dataset_version"], row_count=len(source["locations"])
    )
    for row in source["locations"]:
        values = dict(row)
        values["source_modified_on"] = date.fromisoformat(values["source_modified_on"])
        GeoNameLocation.objects.create(
            **values,
            search_name=normalize_search_text(f"{row['canonical_name']} {row['ascii_name']}"),
            feature_class="P",
            dataset=dataset,
        )
    for row in source["alternate_names"]:
        GeoNameAlternateName.objects.create(
            **row,
            search_name=normalize_search_text(row["name"]),
        )
    return source


@pytest.mark.django_db
def test_real_required_records_match_official_dump(real_geonames):
    expected = {item["geonames_id"]: item for item in real_geonames["locations"]}
    for geonames_id, source in expected.items():
        location = GeoNameLocation.objects.get(pk=geonames_id)
        assert location.country_code == source["country_code"]
        assert location.admin1_name == source["admin1_name"]
        assert location.latitude == Decimal(source["latitude"])
        assert location.longitude == Decimal(source["longitude"])
        assert location.timezone_id == source["timezone_id"]
        assert (
            timezone_at(float(location.latitude), float(location.longitude))
            == source["timezone_id"]
        )


@pytest.mark.django_db
def test_real_search_ranking_unicode_country_and_duplicates(real_geonames):
    expected_first = {
        ("Dublin", "IE"): 2964574,
        ("Bucharest", "RO"): 683506,
        ("Berlin", "DE"): 2950159,
        ("New York", "US"): 5128581,
        ("Sydney", "AU"): 2147714,
        ("Iasi", "RO"): 675810,
        ("Iași", "RO"): 675810,
        ("Sao Paulo", "BR"): 3448439,
        ("São Paulo", "BR"): 3448439,
    }
    for (query, country), expected_id in expected_first.items():
        assert search_locations(query, country, 10)[0].geonames_id == expected_id

    springfields = list(search_locations("Springfield", "US", 10))
    ids = {item.geonames_id for item in springfields}
    assert {4250542, 4951788} <= ids
    assert GeoNameLocation.objects.get(pk=4250542).admin1_name == "Illinois"
    assert GeoNameLocation.objects.get(pk=4951788).admin1_name == "Massachusetts"
    assert len(springfields) > 1


@pytest.mark.django_db
def test_import_records_reproducibility_metadata(tmp_path):
    cities = tmp_path / "cities500.txt"
    alternates = tmp_path / "alternateNamesV2.txt"
    countries = tmp_path / "countryInfo.txt"
    admin1 = tmp_path / "admin1CodesASCII.txt"
    admin2 = tmp_path / "admin2Codes.txt"
    cities.write_text(
        "\t".join(
            [
                "2964574",
                "Dublin",
                "Dublin",
                "",
                "53.33306",
                "-6.24889",
                "P",
                "PPLC",
                "IE",
                "",
                "L",
                "D",
                "",
                "",
                "1024027",
                "",
                "",
                "Europe/Dublin",
                "2022-03-09",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    alternates.write_text("1\t2964574\ten\tDublin\t1\t0\t0\t0\n", encoding="utf-8")
    countries.write_text("IE\tIRL\t372\tEI\tIreland\n", encoding="utf-8")
    admin1.write_text("IE.L\tLeinster\tLeinster\t1\n", encoding="utf-8")
    admin2.write_text("IE.L.D\tDublin City\tDublin City\t2\n", encoding="utf-8")

    call_command(
        "import_geonames",
        cities,
        alternate_names=alternates,
        country_info=countries,
        admin1_codes=admin1,
        admin2_codes=admin2,
        dataset_version="real-import-test",
    )
    dataset = GeoNamesDataset.objects.get(version="real-import-test")
    assert dataset.row_count == 1
    assert dataset.alternate_name_count == 1
    assert dataset.import_duration_ms >= 0
    assert len(dataset.source_manifest["cities500"]["sha256"]) == 64
    assert dataset.source_manifest["cities500"]["source_url"].endswith("cities500.zip")
