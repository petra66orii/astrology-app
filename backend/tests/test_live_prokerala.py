import os
from datetime import UTC, datetime

import pytest

from charts.engines.prokerala import ProkeralaEngine

LIVE_ENABLED = os.getenv("RUN_LIVE_PROKERALA_TESTS") == "1"
HAS_CREDENTIALS = bool(os.getenv("PROKERALA_CLIENT_ID") and os.getenv("PROKERALA_CLIENT_SECRET"))
LIVE_BUDGET = int(os.getenv("PROKERALA_LIVE_CREDIT_BUDGET", "0"))


@pytest.mark.skipif(
    not (LIVE_ENABLED and HAS_CREDENTIALS and LIVE_BUDGET >= 500),
    reason="BLOCKED_BY_CREDENTIALS, live flag disabled, or live budget below 500",
)
@pytest.mark.django_db(transaction=True)
def test_small_budgeted_live_exact_chart():
    print("PLANNED_MAX_CREDIT_EXPOSURE=500")
    engine = ProkeralaEngine(
        os.environ["PROKERALA_CLIENT_ID"],
        os.environ["PROKERALA_CLIENT_SECRET"],
        credit_budget=LIVE_BUDGET,
    )
    result = engine.calculate_exact_chart(
        utc_datetime=datetime(1990, 6, 20, 13, 30, tzinfo=UTC),
        latitude=53.33306,
        longitude=-6.24889,
    )
    assert len(result.planets) >= 10
    assert len(result.houses) == 12
