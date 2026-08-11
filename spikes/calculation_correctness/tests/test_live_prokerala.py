"""Paid integration test: skipped unless credentials and an explicit flag exist."""

from datetime import datetime, timezone
import os
import unittest

from spikes.calculation_correctness.prokerala import ProkeralaAdapter, UrlLibTransport


LIVE = os.getenv("RUN_LIVE_PROKERALA_TESTS") == "1"
HAS_CREDENTIALS = bool(os.getenv("PROKERALA_CLIENT_ID") and os.getenv("PROKERALA_CLIENT_SECRET"))


@unittest.skipUnless(LIVE and HAS_CREDENTIALS, "BLOCKED_BY_CREDENTIALS or live flag not enabled")
class LiveProkeralaTests(unittest.TestCase):
    def test_documented_natal_endpoint(self) -> None:
        adapter = ProkeralaAdapter(os.environ["PROKERALA_CLIENT_ID"], os.environ["PROKERALA_CLIENT_SECRET"], UrlLibTransport())
        result = adapter.calculate_exact(
            utc_datetime=datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
            latitude=53.3498, longitude=-6.2603,
        )
        self.assertGreaterEqual(len(result.planets), 10)
        self.assertEqual(len(result.houses), 12)


if __name__ == "__main__":
    unittest.main()
