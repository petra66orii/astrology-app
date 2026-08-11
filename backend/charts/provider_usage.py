from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import ProviderCreditEvent

logger = logging.getLogger("charts.provider_usage")


@dataclass(frozen=True, slots=True)
class ProviderUsageReservation:
    event_id: UUID

    def complete(
        self,
        *,
        succeeded: bool,
        latency_ms: int,
        failure_code: str = "",
        response_http_status: int | None = None,
    ) -> None:
        ProviderCreditEvent.objects.filter(pk=self.event_id).update(
            succeeded=succeeded,
            failure_code=failure_code,
            response_http_status=response_http_status,
            latency_ms=max(0, latency_ms),
        )


def reserve_provider_credits(
    *,
    provider: str,
    endpoint: str,
    estimated_credits: int,
    chart_id: UUID,
    flow: str,
    sample_number: int | None,
) -> ProviderUsageReservation:
    """Persist intent before spending; failure to observe must prevent the paid call."""
    event = ProviderCreditEvent.objects.create(
        provider=provider,
        endpoint=endpoint,
        estimated_credits=estimated_credits,
        chart_id=chart_id,
        flow=flow,
        sample_number=sample_number,
    )
    today = timezone.localdate()
    daily_total = (
        ProviderCreditEvent.objects.filter(occurred_at__date=today).aggregate(
            total=Sum("estimated_credits")
        )["total"]
        or 0
    )
    threshold = settings.PROVIDER_DAILY_CREDIT_WARNING_THRESHOLD
    if threshold and daily_total >= threshold:
        logger.warning(
            "provider_credit_threshold_reached provider=%s estimated_daily_credits=%s threshold=%s",
            provider,
            daily_total,
            threshold,
        )
    return ProviderUsageReservation(event.pk)
