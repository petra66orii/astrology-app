import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from locations.models import GeoNameAlternateName
from locations.search import normalize_search_text
from tests.conftest import make_location


@pytest.mark.django_db
def test_location_search_handles_duplicates_country_and_unknown(user, dataset):
    make_location(
        dataset,
        4250542,
        "Springfield",
        "US",
        114394,
        admin1="Illinois",
        country_name="United States",
    )
    make_location(
        dataset,
        4951788,
        "Springfield",
        "US",
        155929,
        admin1="Massachusetts",
        country_name="United States",
    )
    make_location(dataset, 999, "Springfield", "CA", 5000, admin1="Ontario", country_name="Canada")
    client = APIClient()
    client.force_authenticate(user)
    response = client.get(reverse("location-search"), {"q": "Springfield", "country": "US"})
    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [4951788, 4250542]
    assert "Massachusetts" in response.data["results"][0]["display_name"]
    assert client.get(reverse("location-search"), {"q": "Atlantis"}).data["results"] == []


@pytest.mark.django_db
def test_location_search_is_unicode_aware(user, dataset):
    iasi = make_location(
        dataset, 675810, "Iași", "RO", 290422, admin1="Iași", country_name="Romania"
    )
    sao = make_location(
        dataset, 3448439, "São Paulo", "BR", 12325232, admin1="São Paulo", country_name="Brazil"
    )
    GeoNameAlternateName.objects.create(
        alternate_name_id=1,
        location=iasi,
        iso_language="ro",
        name="Iaşi",
        search_name=normalize_search_text("Iaşi"),
        is_preferred=True,
    )
    client = APIClient()
    client.force_authenticate(user)
    assert (
        client.get(reverse("location-search"), {"q": "Iasi"}).data["results"][0]["id"]
        == iasi.geonames_id
    )
    assert (
        client.get(reverse("location-search"), {"q": "Sao Paulo"}).data["results"][0]["id"]
        == sao.geonames_id
    )


@pytest.mark.django_db
def test_resolved_location_snapshot_is_immutable(resolved_location):
    resolved_location.locality = "Changed"
    with pytest.raises(ValidationError):
        resolved_location.save()
