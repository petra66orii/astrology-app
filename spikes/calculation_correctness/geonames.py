"""Small in-memory analogue of the planned PostgreSQL location search."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char)).strip()


@dataclass(frozen=True, slots=True)
class PlaceRecord:
    geoname_id: int
    canonical_name: str
    ascii_name: str
    alternate_names: tuple[str, ...]
    country_code: str
    admin1_code: str | None
    admin2_code: str | None
    latitude: float
    longitude: float
    population: int
    feature_class: str = "P"
    feature_code: str = "PPL"


def search_places(
    places: tuple[PlaceRecord, ...], query: str, country_code: str | None = None
) -> tuple[PlaceRecord, ...]:
    needle = normalize_search_text(query)
    if not needle:
        return ()
    matches: list[tuple[int, int, PlaceRecord]] = []
    for place in places:
        if country_code and place.country_code.casefold() != country_code.casefold():
            continue
        names = (place.canonical_name, place.ascii_name, *place.alternate_names)
        normalized_names = tuple(normalize_search_text(name) for name in names)
        exact = needle in normalized_names
        prefix = any(name.startswith(needle) for name in normalized_names)
        contains = any(needle in name for name in normalized_names)
        if contains:
            rank = 0 if exact else 1 if prefix else 2
            matches.append((rank, -place.population, place))
    matches.sort(key=lambda item: (item[0], item[1], item[2].country_code, item[2].geoname_id))
    return tuple(item[2] for item in matches)
