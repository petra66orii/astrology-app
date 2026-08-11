from datetime import UTC, datetime

import pytest

from locations.timezones import LocalTimeError, LocalTimeStatus, require_utc, resolve_local_time


def test_normal_exact_time():
    assert require_utc(datetime(2026, 6, 15, 12), "Europe/Dublin") == datetime(
        2026, 6, 15, 11, tzinfo=UTC
    )


def test_nonexistent_dublin_time():
    resolution = resolve_local_time(datetime(2026, 3, 29, 1, 30), "Europe/Dublin")
    assert resolution.status is LocalTimeStatus.NONEXISTENT
    with pytest.raises(LocalTimeError, match="nonexistent_local_time"):
        require_utc(datetime(2026, 3, 29, 1, 30), "Europe/Dublin")


def test_both_ambiguous_dublin_folds():
    local = datetime(2026, 10, 25, 1, 30)
    resolution = resolve_local_time(local, "Europe/Dublin")
    assert resolution.status is LocalTimeStatus.AMBIGUOUS
    assert require_utc(local, "Europe/Dublin", 0) == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    assert require_utc(local, "Europe/Dublin", 1) == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
