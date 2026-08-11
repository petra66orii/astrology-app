# Commercial backend

This is the new Django 5.2/DRF application. The repository-root terminal application remains historical reference only.

## Local setup

Requirements: Python 3.13, PostgreSQL 17+, and the PostgreSQL `pg_trgm` extension. The committed runtime and dependency locks are `.python-version`, `pyproject.toml`, and `requirements.lock`.

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
```

Load `.env` variables through your shell or IDE. Django does not parse `.env` files itself, which avoids an implicit production configuration mechanism. Never commit `.env`.

For local PostgreSQL using the included Compose file:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Production uses `DJANGO_SETTINGS_MODULE=config.settings.production`. Development uses `config.settings.development`.

## GeoNames import

The application does not call the free GeoNames API at runtime. Download the official source files explicitly so licensing, provenance, and refresh timing remain operational decisions:

```powershell
New-Item -ItemType Directory -Force data\geonames
Invoke-WebRequest https://download.geonames.org/export/dump/cities500.zip -OutFile data\geonames\cities500.zip
Invoke-WebRequest https://download.geonames.org/export/dump/alternateNamesV2.zip -OutFile data\geonames\alternateNamesV2.zip
Invoke-WebRequest https://download.geonames.org/export/dump/countryInfo.txt -OutFile data\geonames\countryInfo.txt
Invoke-WebRequest https://download.geonames.org/export/dump/admin1CodesASCII.txt -OutFile data\geonames\admin1CodesASCII.txt
Invoke-WebRequest https://download.geonames.org/export/dump/admin2Codes.txt -OutFile data\geonames\admin2Codes.txt
Expand-Archive data\geonames\cities500.zip data\geonames\cities500
Expand-Archive data\geonames\alternateNamesV2.zip data\geonames\alternateNamesV2
```

Import a versioned dataset:

```powershell
.\.venv\Scripts\python.exe manage.py import_geonames data\geonames\cities500\cities500.txt `
  --alternate-names data\geonames\alternateNamesV2\alternateNamesV2.txt `
  --country-info data\geonames\countryInfo.txt `
  --admin1-codes data\geonames\admin1CodesASCII.txt `
  --admin2-codes data\geonames\admin2Codes.txt `
  --dataset-version cities500-YYYY-MM-DD
```

The command streams UTF-8 TSV rows, validates coordinates and required fields, uses batched PostgreSQL upserts, retires records missing from a refresh, and filters alternate names to useful autocomplete languages. The operation is transactional. Existing charts retain immutable `ResolvedLocation` snapshots.

GeoNames data is CC BY 4.0. Product/legal surfaces must include “Contains data from GeoNames” with a link to `https://www.geonames.org/`.

## Tests and checks

Normal PostgreSQL suite:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check accounts charts config core locations tests manage.py
.\.venv\Scripts\ruff.exe format --check accounts charts config core locations tests manage.py
.\.venv\Scripts\python.exe manage.py check
```

An explicit SQLite-only developer fallback is available with `USE_SQLITE_FOR_TESTS=1`; CI always exercises PostgreSQL.

Live Prokerala testing is off by default. Set `PROKERALA_CLIENT_ID`, `PROKERALA_CLIENT_SECRET`, and `RUN_LIVE_PROKERALA_TESTS=1` to run the single 500-credit exact-chart smoke test. Never place credentials in source.

## Architecture boundaries

- `accounts`: UUID email users and Django session authentication.
- `locations`: GeoNames search data, immutable resolved snapshots, and timezone conversion.
- `charts`: birth profiles, immutable calculations, normalized domain contracts, and provider engines.
- `charts/engines`: the only layer allowed to know Prokerala response shapes.
- Browser responses never contain raw provider JSON.

Unknown-time calculation begins with five samples and adaptively subdivides to a hard maximum of 17 calculation requests. At 500 credits per request, the strict maximum is **8,500 credits**. Calculation requests are never automatically retried, preserving that ceiling. Live unknown-time execution remains disabled unless `ENABLE_LIVE_UNKNOWN_TIME=1` is deliberately configured.
