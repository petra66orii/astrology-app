from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from locations.models import GeoNameLocation, ResolvedLocation
from locations.timezones import timezone_at

from .domain import BirthTimePrecision
from .models import BirthProfile, NatalChart


class ResolvedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResolvedLocation
        fields = (
            "id",
            "source",
            "source_id",
            "selected_display_name",
            "locality",
            "admin_region",
            "country_name",
            "country_code",
            "latitude",
            "longitude",
            "timezone_id",
            "source_data_version",
            "resolved_at",
        )


class BirthProfileSerializer(serializers.ModelSerializer):
    geonames_location_id = serializers.IntegerField(write_only=True, required=False)
    resolved_location = ResolvedLocationSerializer(read_only=True)

    class Meta:
        model = BirthProfile
        fields = (
            "id",
            "display_label",
            "local_birth_date",
            "local_birth_time",
            "birth_time_precision",
            "geonames_location_id",
            "resolved_location",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        precision = attrs.get(
            "birth_time_precision", getattr(self.instance, "birth_time_precision", None)
        )
        birth_time = attrs.get("local_birth_time", getattr(self.instance, "local_birth_time", None))
        if precision == BirthTimePrecision.EXACT and birth_time is None:
            raise serializers.ValidationError(
                {"local_birth_time": "Birth time is required for an exact-time profile."}
            )
        if precision == BirthTimePrecision.UNKNOWN:
            attrs["local_birth_time"] = None
        if self.instance is None and "geonames_location_id" not in attrs:
            raise serializers.ValidationError({"geonames_location_id": "Select a location."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        location_id = validated_data.pop("geonames_location_id")
        source = (
            GeoNameLocation.objects.select_related("dataset")
            .filter(geonames_id=location_id, retired_at__isnull=True)
            .first()
        )
        if source is None:
            raise serializers.ValidationError(
                {"geonames_location_id": "The selected location is unavailable."}
            )
        timezone_id = timezone_at(float(source.latitude), float(source.longitude))
        region = source.admin1_name or source.admin1_code
        country = source.country_name or source.country_code
        display = ", ".join(item for item in (source.canonical_name, region, country) if item)
        values = {
            "source": "geonames",
            "source_id": str(source.geonames_id),
            "selected_display_name": display,
            "locality": source.canonical_name,
            "admin_region": region,
            "country_name": country,
            "country_code": source.country_code,
            "latitude": source.latitude,
            "longitude": source.longitude,
            "timezone_id": timezone_id,
            "source_data_version": source.dataset.version,
        }
        identity_hash = ResolvedLocation.build_identity_hash(
            {
                "source": values["source"],
                "source_id": values["source_id"],
                "display": display,
                "locality": values["locality"],
                "admin_region": region,
                "country_name": country,
                "country_code": source.country_code,
                "latitude": str(source.latitude),
                "longitude": str(source.longitude),
                "timezone_id": timezone_id,
                "source_data_version": source.dataset.version,
            }
        )
        snapshot, _ = ResolvedLocation.objects.get_or_create(
            identity_hash=identity_hash, defaults=values
        )
        return BirthProfile.objects.create(
            owner=self.context["request"].user, resolved_location=snapshot, **validated_data
        )


class ChartCreateSerializer(serializers.Serializer):
    birth_profile_id = serializers.UUIDField()
    fold = serializers.IntegerField(required=False, min_value=0, max_value=1)


class NatalChartSerializer(serializers.ModelSerializer):
    birth_profile_label = serializers.CharField(
        source="birth_profile.display_label", read_only=True
    )
    location = ResolvedLocationSerializer(source="resolved_location", read_only=True)
    calculation_version = serializers.SerializerMethodField()

    class Meta:
        model = NatalChart
        fields = (
            "id",
            "birth_profile",
            "birth_profile_label",
            "location",
            "status",
            "normalized_result",
            "failure_code",
            "failure_message",
            "calculated_at",
            "created_at",
            "calculation_version",
        )

    def get_calculation_version(self, obj):
        version = obj.calculation_version
        return {
            "id": version.id,
            "contract_version": version.contract_version,
            "adapter_version": version.adapter_version,
            "provider": version.provider,
            "provider_api_version": version.provider_api_version,
            "timezone_data_version": version.timezone_data_version,
            "geonames_dataset_version": version.geonames_dataset_version,
            "zodiac_system": version.zodiac_system,
            "house_system": version.house_system,
            "aspect_profile_version": version.aspect_profile_version,
            "application_git_sha": version.application_git_sha,
        }
