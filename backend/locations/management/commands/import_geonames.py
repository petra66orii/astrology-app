from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from locations.models import GeoNameAlternateName, GeoNameLocation, GeoNamesDataset
from locations.search import normalize_search_text


class Command(BaseCommand):
    help = "Import an explicitly downloaded GeoNames cities500 TSV and useful alternate names."

    def add_arguments(self, parser):
        parser.add_argument("cities_file", type=Path)
        parser.add_argument("--alternate-names", type=Path)
        parser.add_argument("--country-info", type=Path)
        parser.add_argument("--admin1-codes", type=Path)
        parser.add_argument("--admin2-codes", type=Path)
        parser.add_argument("--dataset-version", required=True)
        parser.add_argument("--batch-size", type=int, default=5000)
        parser.add_argument("--replace", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        cities_file: Path = options["cities_file"]
        if not cities_file.is_file():
            raise CommandError(f"Cities file does not exist: {cities_file}")
        dataset, created = GeoNamesDataset.objects.get_or_create(version=options["dataset_version"])
        if not created and not options["replace"]:
            raise CommandError("Dataset version already exists; use a new version or --replace")

        batch_size = max(100, options["batch_size"])
        countries = self._load_country_info(options.get("country_info"))
        admin1_names = self._load_admin_names(options.get("admin1_codes"))
        admin2_names = self._load_admin_names(options.get("admin2_codes"))
        imported_ids: set[int] = set()
        batch: list[GeoNameLocation] = []
        row_count = 0
        GeoNameLocation.objects.filter(retired_at__isnull=True).update(retired_at=timezone.now())
        with cities_file.open("r", encoding="utf-8", newline="") as source:
            for line_number, row in enumerate(csv.reader(source, delimiter="\t"), start=1):
                if len(row) < 19:
                    raise CommandError(f"Invalid cities row {line_number}: expected 19 fields")
                try:
                    geonames_id = int(row[0])
                    latitude, longitude = float(row[4]), float(row[5])
                    population = max(0, int(row[14] or 0))
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        raise ValueError("coordinate range")
                    modified = date.fromisoformat(row[18])
                except ValueError as exc:
                    raise CommandError(f"Invalid cities row {line_number}") from exc
                if not row[17] or row[6] != "P":
                    continue
                batch.append(
                    GeoNameLocation(
                        geonames_id=geonames_id,
                        canonical_name=row[1],
                        ascii_name=row[2],
                        search_name=normalize_search_text(f"{row[1]} {row[2]}"),
                        country_code=row[8],
                        country_name=countries.get(row[8], row[8]),
                        admin1_code=row[10],
                        admin1_name=admin1_names.get(f"{row[8]}.{row[10]}", ""),
                        admin2_code=row[11],
                        admin2_name=admin2_names.get(f"{row[8]}.{row[10]}.{row[11]}", ""),
                        latitude=latitude,
                        longitude=longitude,
                        population=population,
                        feature_class=row[6],
                        feature_code=row[7],
                        timezone_id=row[17],
                        source_modified_on=modified,
                        dataset=dataset,
                        retired_at=None,
                    )
                )
                imported_ids.add(geonames_id)
                if len(batch) >= batch_size:
                    self._upsert_locations(batch)
                    row_count += len(batch)
                    batch.clear()
        if batch:
            self._upsert_locations(batch)
            row_count += len(batch)

        alternates_file = options.get("alternate_names")
        if alternates_file:
            self._import_alternates(alternates_file, imported_ids, batch_size)
        dataset.row_count = row_count
        dataset.save(update_fields=["row_count"])
        self.stdout.write(
            self.style.SUCCESS(f"Imported {row_count} GeoNames locations as {dataset.version}")
        )

    @staticmethod
    def _upsert_locations(batch):
        fields = [
            "canonical_name",
            "ascii_name",
            "search_name",
            "country_code",
            "country_name",
            "admin1_code",
            "admin1_name",
            "admin2_code",
            "admin2_name",
            "latitude",
            "longitude",
            "population",
            "feature_class",
            "feature_code",
            "timezone_id",
            "source_modified_on",
            "dataset",
            "retired_at",
        ]
        GeoNameLocation.objects.bulk_create(
            batch,
            batch_size=len(batch),
            update_conflicts=True,
            update_fields=fields,
            unique_fields=["geonames_id"],
        )

    @staticmethod
    def _load_country_info(source_path: Path | None) -> dict[str, str]:
        if source_path is None:
            return {}
        if not source_path.is_file():
            raise CommandError(f"Country info file does not exist: {source_path}")
        countries = {}
        with source_path.open("r", encoding="utf-8", newline="") as source:
            for row in csv.reader(
                (line for line in source if not line.startswith("#")), delimiter="\t"
            ):
                if len(row) > 4:
                    countries[row[0]] = row[4]
        return countries

    @staticmethod
    def _load_admin_names(source_path: Path | None) -> dict[str, str]:
        if source_path is None:
            return {}
        if not source_path.is_file():
            raise CommandError(f"Admin code file does not exist: {source_path}")
        names = {}
        with source_path.open("r", encoding="utf-8", newline="") as source:
            for row in csv.reader(source, delimiter="\t"):
                if len(row) >= 2:
                    names[row[0]] = row[1]
        return names

    def _import_alternates(self, source_path: Path, imported_ids: set[int], batch_size: int):
        if not source_path.is_file():
            raise CommandError(f"Alternate names file does not exist: {source_path}")
        GeoNameAlternateName.objects.filter(location_id__in=imported_ids).delete()
        useful_languages = {"", "en", "de", "es", "fr", "pt", "ro"}
        batch: list[GeoNameAlternateName] = []
        with source_path.open("r", encoding="utf-8", newline="") as source:
            for row in csv.reader(source, delimiter="\t"):
                if len(row) < 8:
                    continue
                try:
                    alternate_id, location_id = int(row[0]), int(row[1])
                except ValueError:
                    continue
                if location_id not in imported_ids or row[2] not in useful_languages or not row[3]:
                    continue
                batch.append(
                    GeoNameAlternateName(
                        alternate_name_id=alternate_id,
                        location_id=location_id,
                        iso_language=row[2],
                        name=row[3],
                        search_name=normalize_search_text(row[3]),
                        is_preferred=row[4] == "1",
                        is_short=row[5] == "1",
                        is_colloquial=row[6] == "1",
                        is_historic=row[7] == "1",
                    )
                )
                if len(batch) >= batch_size:
                    GeoNameAlternateName.objects.bulk_create(
                        batch, batch_size=batch_size, ignore_conflicts=True
                    )
                    batch.clear()
        if batch:
            GeoNameAlternateName.objects.bulk_create(
                batch, batch_size=batch_size, ignore_conflicts=True
            )
