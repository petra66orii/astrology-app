from datetime import datetime, timedelta, timezone
import unittest

from spikes.calculation_correctness.unknown_time import SamplePosition, adaptive_sample


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class UnknownTimeTests(unittest.TestCase):
    def test_initial_five_points_and_invariants(self) -> None:
        def calculate(instant: datetime) -> dict[str, SamplePosition]:
            hours = (instant - START).total_seconds() / 3600
            return {
                "Sun": SamplePosition(10 + hours * 0.04, False),
                "Mars": SamplePosition(130 + hours * 0.02, False),
            }

        result = adaptive_sample(START, START + timedelta(hours=24), calculate)
        self.assertEqual(len(result.samples), 5)
        self.assertTrue(result.sign_invariant["Sun"])
        self.assertTrue(result.retrograde_invariant["Mars"])

    def test_adapts_near_sign_and_retrograde_boundaries(self) -> None:
        def calculate(instant: datetime) -> dict[str, SamplePosition]:
            hours = (instant - START).total_seconds() / 3600
            return {"Moon": SamplePosition(29.5 + hours * 0.08, hours >= 12)}

        result = adaptive_sample(START, START + timedelta(hours=24), calculate, min_step=timedelta(minutes=30))
        self.assertGreater(len(result.samples), 5)
        self.assertFalse(result.sign_invariant["Moon"])
        self.assertFalse(result.retrograde_invariant["Moon"])

    def test_suppresses_aspects_when_sample_cap_is_reached(self) -> None:
        def calculate(instant: datetime) -> dict[str, SamplePosition]:
            hours = (instant - START).total_seconds() / 3600
            return {"Sun": SamplePosition(10 + hours, False), "Moon": SamplePosition(10 + hours, False)}

        result = adaptive_sample(START, START + timedelta(hours=24), calculate, max_samples=5)
        self.assertTrue(result.capped)
        self.assertEqual(result.stable_aspects, ())


if __name__ == "__main__":
    unittest.main()
