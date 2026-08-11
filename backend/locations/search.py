from __future__ import annotations

import unicodedata

from django.contrib.postgres.search import TrigramSimilarity
from django.db import connection
from django.db.models import Exists, OuterRef, Q

from .models import GeoNameAlternateName, GeoNameLocation


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", value).casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char)).strip()


def search_locations(query: str, country_code: str | None = None, limit: int = 10):
    needle = normalize_search_text(query)
    if len(needle) < 2:
        return GeoNameLocation.objects.none()
    alternate_match = GeoNameAlternateName.objects.filter(
        location_id=OuterRef("pk"), search_name__icontains=needle
    )
    locations = (
        GeoNameLocation.objects.filter(retired_at__isnull=True)
        .annotate(alternate_match=Exists(alternate_match))
        .filter(Q(search_name__icontains=needle) | Q(alternate_match=True))
    )
    if country_code:
        locations = locations.filter(country_code=country_code.upper())
    if connection.vendor == "postgresql":
        locations = locations.annotate(
            similarity=TrigramSimilarity("search_name", needle)
        ).order_by("-similarity", "-population", "canonical_name", "geonames_id")
    else:
        locations = locations.order_by("-population", "canonical_name", "geonames_id")
    return locations[: max(1, min(limit, 20))]
