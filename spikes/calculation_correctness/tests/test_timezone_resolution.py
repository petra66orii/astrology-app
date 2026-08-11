from datetime import datetime, timezone
import unittest

from spikes.calculation_correctness.timezone_resolution import LocalTimeStatus, require_utc, resolve_local_time


class TimezoneTests(unittest.TestCase):
    def test_normal_dublin_time(self) -> None:
        result = resolve_local_time(datetime(2026, 6, 15, 12, 0), "Europe/Dublin")
        self.assertEqual(result.status, LocalTimeStatus.RESOLVED)
        self.assertEqual(result.candidates[0].utc_datetime, datetime(2026, 6, 15, 11, 0, tzinfo=timezone.utc))

    def test_nonexistent_dublin_time(self) -> None:
        result = resolve_local_time(datetime(2026, 3, 29, 1, 30), "Europe/Dublin")
        self.assertEqual(result.status, LocalTimeStatus.NONEXISTENT)
        self.assertEqual(result.candidates, ())
        with self.assertRaisesRegex(ValueError, "does not exist"):
            require_utc(datetime(2026, 3, 29, 1, 30), "Europe/Dublin")

    def test_ambiguous_dublin_time_requires_fold(self) -> None:
        local = datetime(2026, 10, 25, 1, 30)
        result = resolve_local_time(local, "Europe/Dublin")
        self.assertEqual(result.status, LocalTimeStatus.AMBIGUOUS)
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(require_utc(local, "Europe/Dublin", 0), datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc))
        self.assertEqual(require_utc(local, "Europe/Dublin", 1), datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            require_utc(local, "Europe/Dublin")


if __name__ == "__main__":
    unittest.main()
