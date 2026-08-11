from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .domain import BirthTimePrecision


class ImmutableModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(f"{type(self).__name__} records are immutable")
        return super().save(*args, **kwargs)


class BirthProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="birth_profiles"
    )
    display_label = models.CharField(max_length=120)
    local_birth_date = models.DateField()
    local_birth_time = models.TimeField(null=True, blank=True)
    birth_time_precision = models.CharField(
        max_length=10, choices=[(item.value, item.value) for item in BirthTimePrecision]
    )
    resolved_location = models.ForeignKey(
        "locations.ResolvedLocation", on_delete=models.PROTECT, related_name="birth_profiles"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)


class ChartCalculationVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_version = models.CharField(max_length=32)
    adapter_version = models.CharField(max_length=64)
    provider = models.CharField(max_length=32)
    provider_api_version = models.CharField(max_length=32)
    timezone_data_version = models.CharField(max_length=32)
    geonames_dataset_version = models.CharField(max_length=64)
    zodiac_system = models.CharField(max_length=32)
    house_system = models.CharField(max_length=32)
    aspect_profile_version = models.CharField(max_length=64)
    application_git_sha = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NatalChart(ImmutableModel):
    class Status(models.TextChoices):
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="natal_charts"
    )
    birth_profile = models.ForeignKey(BirthProfile, on_delete=models.PROTECT, related_name="charts")
    resolved_location = models.ForeignKey(
        "locations.ResolvedLocation", on_delete=models.PROTECT, related_name="charts"
    )
    calculation_version = models.ForeignKey(
        ChartCalculationVersion, on_delete=models.PROTECT, related_name="charts"
    )
    input_snapshot = models.JSONField()
    input_fingerprint = models.CharField(max_length=64, db_index=True)
    normalized_result = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=240, blank=True)
    provider_response_hash = models.CharField(max_length=64, blank=True)
    calculated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["owner", "-created_at"], name="chart_owner_created")]


class ProviderCreditEvent(models.Model):
    """Privacy-minimal operational record for a potentially billable provider call."""

    class Flow(models.TextChoices):
        EXACT = "EXACT", "Exact"
        UNKNOWN = "UNKNOWN", "Unknown time"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32)
    endpoint = models.CharField(max_length=120)
    estimated_credits = models.PositiveIntegerField()
    chart_id = models.UUIDField(db_index=True)
    flow = models.CharField(max_length=16, choices=Flow.choices)
    sample_number = models.PositiveSmallIntegerField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    failure_code = models.CharField(max_length=64, blank=True)
    response_http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["provider", "-occurred_at"], name="credit_provider_date"),
            models.Index(fields=["flow", "-occurred_at"], name="credit_flow_date"),
        ]
