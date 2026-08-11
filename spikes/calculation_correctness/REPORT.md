# Calculation-correctness spike report

Report date: 2026-08-11. Scope: focused audit/test infrastructure only.

## 1. Executive result

Gate B is **CONDITIONAL PASS**. The provider-neutral boundary, Prokerala v2 request/normalization prototype, DST behavior, GeoNames search design, preliminary 14-case catalogue, unknown-time adaptive sampler, and 15 offline/live-gated tests exist. Fourteen tests pass and the paid live test is skipped. A full PASS is prohibited because Prokerala credentials are absent and five fixtures do not yet have independent numerical evidence.

## 2. Credential remediation action

`.vscode/uptime.sh` contains a committed `x-api-key` used against an AWS API Gateway endpoint in `eu-west-1` for the old Code Institute/Gitpod workspace-usage telemetry. The value was not printed. The owner must disable/delete that API key in AWS API Gateway, inspect API Gateway/CloudWatch usage for abuse, and remove the telemetry script from the rebuilt application. Rotation means creating a replacement only if that legacy telemetry is genuinely retained; never commit it. Git history was not rewritten.

## 3. Prokerala endpoint assessment

Official OpenAPI source: `https://api.prokerala.com/spec/astrology.v2.yaml`; server `https://api.prokerala.com/v2`; OAuth2 client-credentials token URL `https://api.prokerala.com/token`. Credentials are sent in the token request body and API requests use a bearer token.

The calculation endpoint is `GET /astrology/natal-planet-position` (operation `get-natal-planet-position`, 500 credits). Its documented JSON contains `houses`, `planet_positions`, `angles`, `aspects`, and `declinations`, so it covers natal Sun/Moon/planets, angles, cusps/house placements, and aspects in one call. Required query inputs are an ISO-8601 offset-bearing `datetime`, `latitude,longitude` coordinates, `house_system`, and `orb`. The API has no separate timezone-ID parameter: resolve the user's local civil time internally and send an unambiguous UTC ISO-8601 instant. `birth_time_unknown` is documented, but product unknown-time stability still requires our bounded interval policy rather than trusting a hidden provider time.

House systems: `placidus`, `koch`, `whole-sign`, `equal-house`, `m-house`, `porphyrius`, `regiomontanus`, `campanus`. `ayanamsa=0` is tropical; documented sidereal options include 1 Lahiri, 3 Raman, and 5 KP. Orb is `default` or `exact`; language is `en`, `de`, or `es`. The schema declares JSON numeric fields as float but gives no decimal precision guarantee, so precision must be measured from live responses.

Optional SVG endpoints are `GET /astrology/natal-chart` (500 credits) and `GET /astrology/natal-aspect-chart` (500 credits). They are presentation artifacts, not calculation truth, and are not needed for this gate. The public OpenAPI documents only the 200 response and does not publish a stable error schema or rate limits. The adapter therefore maps HTTP 429/5xx conservatively; contractual rate limits must be confirmed from the purchased plan/dashboard before production.

## 4. Normalized astrology contract

`contracts.py` defines immutable `BirthInput`, `LocationIdentity`, `BirthTimePrecision`, `NatalChartResult`, `PlanetPosition`, `ChartAngles`, `HousePosition`, `Aspect`, `UnavailableCalculation`, `ChartMetadata`, and `LongitudeRange`. Prokerala JSON terminates at the adapter. Exact results can contain angles, houses, placements, and aspects. Unknown results structurally reject angles, houses, and house placements. Metadata versions the provider API, adapter, domain contract, calculation policy, timezone data, options, timestamp, and source-response hash.

## 5. Unknown-time algorithm

Start with the beginning, 25%, 50%, 75%, and end of the possible UTC interval. Recursively bisect intervals when midpoint angular motion is non-linear beyond tolerance, a zodiac sign changes, retrograde state changes, or a major aspect approaches/crosses its configured orb boundary. Stop at a configured minimum step or maximum sample count. Derive circular longitude ranges plus sign/retrograde invariance from every sample. Publish a major aspect only when every sample is safely inside the orb with a boundary margin and the sampler did not hit its cap; otherwise suppress it.

This is a bounded astrology product behavior contract, not a proof of mathematical continuity. The more reliable inexpensive evolution is provider-supported batch ephemeris data or a licensed local ephemeris used solely to locate ingresses, stations, and orb roots, followed by Prokerala verification at those event times. With a 500-credit call per instant, adaptive live calls require cost caps and caching.

## 6. GeoNames import/search design

Use official `cities500.zip` (roughly 185k populated places/admin seats), `alternateNamesV2.zip` filtered to imported GeoName IDs and useful human-language names, `admin1CodesASCII.txt`, `admin2Codes.txt`, `countryInfo.txt`, and feature codes. The main city row already includes an IANA timezone, but coordinate-based verification remains necessary at borders. Do not use `allCountries.zip` or pandas at process startup.

A Django management command downloads to a staging area, verifies recorded size/checksum, streams tab-delimited UTF-8 through PostgreSQL `COPY`, filters alternate names, validates counts/coordinates/foreign keys, then transactionally upserts or swaps staging tables. Retire deleted IDs rather than silently repointing charts. Run a full monthly refresh for MVP; daily modification/deletion feeds can follow if freshness needs it.

The SQL artifact uses canonical Unicode display values, separate accent-folded/case-folded search values, `pg_trgm` GIN indexes, country/admin indexes, and population ranking. Search ranking is exact name, prefix, trigram similarity, preferred/canonical name, feature importance, then population. Country is an explicit filter. Duplicate cities remain separate GeoNames IDs and display admin1/admin2/country. Use NFKC for display ingestion and NFKD + casefold + combining-mark removal for search only. Preserve original Unicode. GeoNames is CC BY 4.0: show “Contains data from GeoNames” with a link in product/legal attribution and retain source/import metadata.

## 7. Timezone/DST design

Use `timezonefinder` 8.x for offline WGS84 coordinate-to-IANA lookup (Python 3.13 compatible), pin its version and boundary-data provenance, and reuse an in-memory finder per process. Persist the resolved IANA ID in an immutable chart location snapshot. Use `zoneinfo` plus pinned `tzdata` for historical offset conversion, storing tzdata version.

Validate both PEP 495 folds by UTC round-trip. Zero valid instants means NONEXISTENT: reject the exact time, explain the DST gap, and let the user correct it or switch to unknown. Two distinct instants means AMBIGUOUS: present both offsets/folds; if the user cannot select, treat time-dependent output as unavailable. Never choose silently.

## 8. Golden fixture catalogue

`fixtures/golden_catalogue.json` contains all 14 requested cases: Dublin, Bucharest, Berlin, New York, Sydney, both Springfields, Iași, São Paulo, Dublin DST gap, both Dublin folds, historical Bucharest, and unknown-time Dublin. It labels the five first-gate cases and evidence state. GeoNames coordinates are preliminary snapshots and must be re-import-verified before promotion to immutable golden values.

## 9. Independent reference methodology

For each promoted fixture, record the source, retrieval date, tropical/sidereal setting, house system, aspect/orb policy, coordinates, IANA zone, local time/fold, exact UTC instant, software/version, and notes. Compare Prokerala with (a) a numerical Swiss Ephemeris run from a separately versioned tool, (b) an Astrodienst-generated numerical chart inspected by a human, and (c) an astronomy source such as JPL Horizons for applicable geocentric planetary longitude checks. Swiss Ephemeris descendants share ancestry and must be labelled correlated, not fully independent. Store numerical values and our metadata only—no third-party interpretation/report prose.

## 10. Fixture comparison results

Timezone behavior is verified for ordinary Dublin time, the 2026 spring gap, and both 2026 autumn folds. Location behavior is verified offline for duplicates, Unicode/ASCII aliases, country filters, and misses. Contract behavior is verified for exact normalization and unknown omissions. Numerical Prokerala-versus-reference comparison is **not run**: credentials and independent captured reference values are absent. Therefore 0/5 required numerical fixtures are complete.

## 11. Tolerance assessment

Keep the proposed limits: planets/Sun <= 0.001°, Moon <= 0.003°, angles/MC/cusps <= 0.01°, aspect separation/orb <= 0.01°, UTC/offset/fold exact, sign exact except a documented numerical boundary, and unknown omissions exact. Prokerala documents float fields but not guaranteed digits, so do not loosen these thresholds until live measurements show a reproducible provider precision limit; any change needs a recorded justification and fixture evidence.

## 12. Adapter prototype status

The adapter uses OAuth2 client credentials, bearer auth, explicit 10-second timeouts, URL encoding, tropical/Placidus/default-orb request options, normalized errors, schema checking, a provider-neutral result, and reproducibility metadata. Required environment variables are `PROKERALA_CLIENT_ID` and `PROKERALA_CLIENT_SECRET`; live tests additionally require `RUN_LIVE_PROKERALA_TESTS=1`. No credential was found or requested. Default tests make no network or paid calls.

## 13. Automated tests added

Tests cover duplicate cities, Unicode names, country filtering, unknown locations, normal/ambiguous/nonexistent timezone conversion, exact response normalization, unknown-time suppression, error normalization, calculation metadata, five-point/adaptive sampling, sample-cap aspect suppression, and opt-in live provider execution. Current result: 15 discovered, 14 passed, 1 deliberately skipped.

## 14. Gate B decision

**CONDITIONAL PASS** for proceeding only to the first narrow vertical slice. Architecture and offline safeguards are ready; numerical correctness is not yet certified. Do not label the calculation engine production-correct until five independent fixture comparisons pass.

## 15. Remaining blockers

Provision Prokerala credentials via a secret manager/environment, confirm purchased-plan rate limits and actual error bodies, run explicitly budgeted calls, capture five independent numerical references, verify all 14 GeoNames IDs/coordinates from the selected import version, pin Python 3.13-compatible `timezonefinder` and `tzdata`, and promote measured fixtures only after review.

## 16. Exact next implementation phase

Create the first vertical slice: Django 5.2 LTS/DRF project on Python 3.13, PostgreSQL and migrations, Next.js App Router/TypeScript, authentication, offline GeoNames import/autocomplete, immutable `BirthProfile` and `ResolvedLocation`, `ChartCalculationVersion`, `NatalChart`, the Prokerala adapter, one exact chart flow, one unknown-time flow, and one minimal accessible result page with loading/error/empty states. Complete the five numerical fixtures alongside that slice before expanding chart features. No Stripe.

## 17. Files changed

`.gitignore` was hardened. Everything under `spikes/calculation_correctness/` plus `spikes/__init__.py` is new audit/test infrastructure. Pre-existing `run.py` changes were preserved and not edited.

## 18. Commands run

Read-only Git branch/status/diff/history inspection; redacted inspection of `.vscode/uptime.sh`; official Prokerala OpenAPI/docs and GeoNames/timezonefinder research; boolean-only credential presence check; `python -m unittest discover -s spikes/calculation_correctness/tests -v`; final Git/diff checks. No live provider calculation command ran.

## 19. Git status

Branch: `audit/commercial-mvp`. The final status is reported in the handoff after verification. Nothing was committed, pushed, deployed, or merged. No secret value was displayed or added to a file.
