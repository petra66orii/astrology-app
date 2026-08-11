from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from spikes.calculation_correctness import CALCULATION_VERSION
from spikes.calculation_correctness.contracts import BirthTimePrecision
from spikes.calculation_correctness.prokerala import (
    ProviderError, UrlLibTransport, normalize_exact_response, suppress_time_dependent_fields,
)


FIXTURE = Path(__file__).parent / "fixtures" / "prokerala_natal_documented_shape.json"


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_exact_chart_normalization(self) -> None:
        result = normalize_exact_response(self.payload, timezone_database_version="2026a")
        self.assertEqual(result.time_precision, BirthTimePrecision.EXACT)
        self.assertEqual(result.planets[0].name, "Sun")
        self.assertEqual(result.planets[0].house_number, 7)
        self.assertEqual(result.angles.ascendant, 101.25)
        self.assertEqual(result.aspects[0].name, "Sextile")
        self.assertEqual(result.metadata.calculation_version, CALCULATION_VERSION)
        self.assertEqual(result.metadata.provider_api_version, "v2")
        self.assertEqual(len(result.metadata.source_response_sha256), 64)

    def test_unknown_time_suppression(self) -> None:
        result = suppress_time_dependent_fields(normalize_exact_response(self.payload))
        self.assertEqual(result.time_precision, BirthTimePrecision.UNKNOWN)
        self.assertIsNone(result.angles)
        self.assertEqual(result.houses, ())
        self.assertTrue(all(planet.house_number is None for planet in result.planets))
        self.assertTrue(all(planet.longitude is None for planet in result.planets))
        self.assertEqual(result.aspects, ())
        self.assertEqual({item.field for item in result.unavailable}, {"angles", "houses", "house_placements"})

    def test_schema_error_is_normalized(self) -> None:
        with self.assertRaises(ProviderError) as caught:
            normalize_exact_response({"status": "ok", "data": {}})
        self.assertEqual(caught.exception.code, "PROVIDER_SCHEMA_MISMATCH")

    def test_provider_non_success_is_normalized(self) -> None:
        with self.assertRaises(ProviderError) as caught:
            normalize_exact_response({"status": "error", "data": {}})
        self.assertEqual(caught.exception.code, "PROVIDER_REJECTED")


if __name__ == "__main__":
    unittest.main()
