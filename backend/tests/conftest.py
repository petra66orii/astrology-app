from __future__ import annotations

from decimal import Decimal

import pytest

from accounts.models import User
from locations.models import GeoNameLocation, GeoNamesDataset, ResolvedLocation
from locations.search import normalize_search_text


@pytest.fixture
def user(db):
    return User.objects.create_user("person@example.com", "Strong-passphrase-123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user("other@example.com", "Strong-passphrase-456")


@pytest.fixture
def dataset(db):
    return GeoNamesDataset.objects.create(version="cities500-2026-08-11")


def make_location(
    dataset, geonames_id, name, country_code, population, *, admin1="", country_name=""
):
    return GeoNameLocation.objects.create(
        geonames_id=geonames_id,
        canonical_name=name,
        ascii_name=normalize_search_text(name),
        search_name=normalize_search_text(name),
        country_code=country_code,
        country_name=country_name or country_code,
        admin1_code=admin1,
        admin1_name=admin1,
        latitude=Decimal("53.333060"),
        longitude=Decimal("-6.248890"),
        population=population,
        feature_class="P",
        feature_code="PPL",
        timezone_id="Europe/Dublin",
        dataset=dataset,
    )


@pytest.fixture
def dublin(dataset):
    return make_location(dataset, 2964574, "Dublin", "IE", 1_024_027, country_name="Ireland")


@pytest.fixture
def resolved_location(db):
    return ResolvedLocation.objects.create(
        source="geonames",
        source_id="2964574",
        selected_display_name="Dublin, Ireland",
        locality="Dublin",
        admin_region="Leinster",
        country_name="Ireland",
        country_code="IE",
        latitude=Decimal("53.333060"),
        longitude=Decimal("-6.248890"),
        timezone_id="Europe/Dublin",
        source_data_version="cities500-test",
    )
