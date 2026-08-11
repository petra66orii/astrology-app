from rest_framework import serializers

from .models import GeoNameLocation


class LocationSearchResultSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="geonames_id")
    display_name = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    class Meta:
        model = GeoNameLocation
        fields = (
            "id",
            "display_name",
            "canonical_name",
            "region",
            "country_name",
            "country_code",
            "latitude",
            "longitude",
            "timezone_id",
        )

    def get_region(self, obj):
        return obj.admin1_name or obj.admin1_code

    def get_display_name(self, obj):
        parts = [
            obj.canonical_name,
            obj.admin1_name or obj.admin1_code,
            obj.country_name or obj.country_code,
        ]
        return ", ".join(part for part in parts if part)
