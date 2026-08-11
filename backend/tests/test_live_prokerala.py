import os
from datetime import UTC, datetime

import pytest

from charts.engines.prokerala import ProkeralaEngine

LIVE_ENABLED = os.getenv("RUN_LIVE_PROKERALA_TESTS") == "1"
HAS_CREDENTIALS = bool(os.getenv("PROKERALA_CLIENT_ID") and os.getenv("PROKERALA_CLIENT_SECRET"))


@pytest.mark.skipif(
    not (LIVE_ENABLED and HAS_CREDENTIALS),
    reason="BLOCKED_BY_CREDENTIALS or RUN_LIVE_PROKERALA_TESTS is not enabled",
)
def test_small_budgeted_live_exact_chart():
    engine = ProkeralaEngine(
        os.environ["PROKERALA_CLIENT_ID"], os.environ["PROKERALA_CLIENT_SECRET"]
    )
    result = engine.calculate_exact_chart(
        utc_datetime=datetime(2000, 1, 1, 12, tzinfo=UTC),
        latitude=53.33306,
        longitude=-6.24889,
    )
    assert len(result.planets) >= 10
    assert len(result.houses) == 12
