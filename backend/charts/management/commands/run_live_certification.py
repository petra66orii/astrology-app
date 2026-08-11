from __future__ import annotations

import json
import os
from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from charts.engines.prokerala import ProkeralaEngine
from locations.models import GeoNameLocation
from locations.timezones import require_utc


class Command(BaseCommand):
    help = "Run exactly one guarded Dublin exact-time certification request."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, required=True)

    def handle(self, *args, **options):
        if not settings.RUN_LIVE_PROKERALA_TESTS:
            raise CommandError("RUN_LIVE_PROKERALA_TESTS=1 is required")
        if not settings.PROKERALA_CLIENT_ID or not settings.PROKERALA_CLIENT_SECRET:
            raise CommandError("BLOCKED_BY_CREDENTIALS")
        budget_text = os.getenv("PROKERALA_LIVE_CREDIT_BUDGET", "")
        if not budget_text or settings.PROKERALA_LIVE_CREDIT_BUDGET < 500:
            raise CommandError("PROKERALA_LIVE_CREDIT_BUDGET must be at least 500")

        location = GeoNameLocation.objects.get(geonames_id=2964574, retired_at__isnull=True)
        utc_datetime = require_utc(
            datetime.combine(date(1990, 6, 20), time(14, 30)), location.timezone_id, 0
        )
        self.stdout.write("PLANNED_MAX_CREDIT_EXPOSURE=500")
        engine = ProkeralaEngine(
            settings.PROKERALA_CLIENT_ID,
            settings.PROKERALA_CLIENT_SECRET,
            credit_budget=settings.PROKERALA_LIVE_CREDIT_BUDGET,
        )
        result = engine.calculate_exact_chart(
            utc_datetime=utc_datetime,
            latitude=float(location.latitude),
            longitude=float(location.longitude),
            chart_id=uuid4(),
        )
        document = {
            "fixture_id": "A_DUBLIN_EXACT",
            "observation": engine.last_response_observation,
            "normalized_result": result.as_dict(),
            "raw_provider_payload_persisted": False,
        }
        output: Path = options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Normalized result written to {output}"))
