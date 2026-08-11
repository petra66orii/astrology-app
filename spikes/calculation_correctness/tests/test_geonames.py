import unittest

from spikes.calculation_correctness.geonames import PlaceRecord, normalize_search_text, search_places


PLACES = (
    PlaceRecord(4250542, "Springfield", "Springfield", (), "US", "IL", "167", 39.80, -89.64, 114394),
    PlaceRecord(4951788, "Springfield", "Springfield", (), "US", "MA", "013", 42.10, -72.59, 155929),
    PlaceRecord(675810, "Iași", "Iasi", ("Iaşi", "Jassy"), "RO", "23", None, 47.16, 27.58, 290422),
    PlaceRecord(3448439, "São Paulo", "Sao Paulo", (), "BR", "27", None, -23.55, -46.63, 12325232),
)


class GeoNamesSearchTests(unittest.TestCase):
    def test_duplicate_cities_are_distinct_and_ranked(self) -> None:
        results = search_places(PLACES, "Springfield", "US")
        self.assertEqual([item.geoname_id for item in results], [4951788, 4250542])
        self.assertNotEqual(results[0].admin1_code, results[1].admin1_code)

    def test_unicode_and_ascii_names_match(self) -> None:
        self.assertEqual(search_places(PLACES, "Iasi")[0].canonical_name, "Iași")
        self.assertEqual(search_places(PLACES, "São")[0].geoname_id, 3448439)
        self.assertEqual(normalize_search_text("Iași"), "iasi")

    def test_country_filter(self) -> None:
        self.assertEqual(search_places(PLACES, "Springfield", "RO"), ())

    def test_unknown_location(self) -> None:
        self.assertEqual(search_places(PLACES, "Atlantis"), ())


if __name__ == "__main__":
    unittest.main()
