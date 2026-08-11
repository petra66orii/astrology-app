from __future__ import annotations

import hashlib
import json
import uuid

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models


class GeoNamesDataset(models.Model):
    version = models.CharField(max_length=64, unique=True)
    source_name = models.CharField(max_length=64, default="GeoNames cities500")
    source_modified_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.version


class GeoNameLocation(models.Model):
    geonames_id = models.BigIntegerField(primary_key=True)
    canonical_name = models.CharField(max_length=200)
    ascii_name = models.CharField(max_length=200)
    search_name = models.TextField()
    country_code = models.CharField(max_length=2)
    country_name = models.CharField(max_length=200, blank=True)
    admin1_code = models.CharField(max_length=20, blank=True)
    admin1_name = models.CharField(max_length=200, blank=True)
    admin2_code = models.CharField(max_length=80, blank=True)
    admin2_name = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    population = models.BigIntegerField(default=0)
    feature_class = models.CharField(max_length=1)
    feature_code = models.CharField(max_length=10)
    timezone_id = models.CharField(max_length=64)
    source_modified_on = models.DateField(null=True, blank=True)
    dataset = models.ForeignKey(GeoNamesDataset, on_delete=models.PROTECT, related_name="locations")
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_name"], name="location_name_trgm", opclasses=["gin_trgm_ops"]),
            models.Index(fields=["country_code", "-population"], name="location_country_pop"),
            models.Index(fields=["country_code", "admin1_code"], name="location_country_admin"),
        ]

    def __str__(self) -> str:
        return f"{self.canonical_name}, {self.country_code}"


class GeoNameAlternateName(models.Model):
    alternate_name_id = models.BigIntegerField(primary_key=True)
    location = models.ForeignKey(
        GeoNameLocation, on_delete=models.CASCADE, related_name="alternate_names"
    )
    iso_language = models.CharField(max_length=16, blank=True)
    name = models.CharField(max_length=400)
    search_name = models.TextField()
    is_preferred = models.BooleanField(default=False)
    is_short = models.BooleanField(default=False)
    is_colloquial = models.BooleanField(default=False)
    is_historic = models.BooleanField(default=False)

    class Meta:
        indexes = [
            GinIndex(
                fields=["search_name"], name="alternate_name_trgm", opclasses=["gin_trgm_ops"]
            ),
            models.Index(fields=["location", "-is_preferred"], name="alternate_location_pref"),
        ]


class ResolvedLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=32)
    source_id = models.CharField(max_length=64)
    selected_display_name = models.CharField(max_length=400)
    locality = models.CharField(max_length=200)
    admin_region = models.CharField(max_length=200, blank=True)
    country_name = models.CharField(max_length=200)
    country_code = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timezone_id = models.CharField(max_length=64)
    source_data_version = models.CharField(max_length=64)
    resolved_at = models.DateTimeField(auto_now_add=True)
    identity_hash = models.CharField(max_length=64, unique=True, editable=False)

    class Meta:
        ordering = ("selected_display_name",)

    @staticmethod
    def build_identity_hash(values: dict) -> str:
        canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("ResolvedLocation snapshots are immutable")
        if not self.identity_hash:
            values = {
                "source": self.source,
                "source_id": self.source_id,
                "display": self.selected_display_name,
                "locality": self.locality,
                "admin_region": self.admin_region,
                "country_name": self.country_name,
                "country_code": self.country_code,
                "latitude": str(self.latitude),
                "longitude": str(self.longitude),
                "timezone_id": self.timezone_id,
                "source_data_version": self.source_data_version,
            }
            self.identity_hash = self.build_identity_hash(values)
        return super().save(*args, **kwargs)
