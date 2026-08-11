# Gate B correctness-certification summary

Decision: **BLOCKED**

The real GeoNames and independent-reference work is complete, but Prokerala credentials and `RUN_LIVE_PROKERALA_TESTS=1` were absent. No paid request was made. Mocked or documented-schema tests cannot promote this gate to PASS.

## Completed evidence

- Official GeoNames `cities500` production candidate imported into PostgreSQL 18.3.
- 235,215 active locations and 476,883 selected alternate names imported in 42.167 seconds, including source hashing.
- Database size after import and compaction: 147 MB.
- Dublin, Bucharest, Berlin, New York City, Sydney, Springfield IL, Springfield MA, Iaşi, and São Paulo match the official downloaded rows.
- ASCII and Unicode queries for Iasi/Iași and Sao Paulo/São Paulo resolve correctly.
- Springfield results remain distinct and display their administrative region.
- Five numerical reference fixtures were generated with Swiss Ephemeris 2.10.03 using official DE441-derived planet and Moon files.
- Exact UTC conversion, both Dublin ambiguous folds, and the Dublin nonexistent-time gap are covered.
- A machine-readable tolerance comparator and full blocked comparison tables are committed.

## Provider contract findings

The official Prokerala OpenAPI v2 document was retrieved on 2026-08-11 with SHA-256 `b015dc1d8744b3571497f83abb1d8b0e849af6029a4c7694a451f7b1a9ef357e`.

Its documented natal response contains:

- top-level `status` and `data`;
- `houses`, `planet_positions`, `angles`, `aspects`, and `declinations` under `data`;
- 12 houses;
- ten required planets plus True Nodes, Lilith, and Chiron;
- angle labels `Ascendant`, `Nadir`, `Descendant`, and `Mid Heaven`.

The prior adapter expected `Midheaven` and `Imum Coeli`. It was narrowly corrected to accept the documented `Mid Heaven` and `Nadir` labels while retaining the original aliases. It now filters public results to the required ten planets and five major aspects and rejects missing planets, houses, Ascendant, or MC.

This validates the documented contract only. A real provider response has not yet been observed.

## Independent-reference limitations

Swiss Ephemeris is independent of Prokerala as an execution path, but Prokerala may use Swiss Ephemeris internally. Therefore shared ancestry is possible and has not been represented as full engine independence. No third-party interpretation prose is stored.

Swiss Ephemeris is certification-only tooling here, not a runtime fallback. Its licensing must be reviewed before any product integration.

## Live safety

- Every live call requires `RUN_LIVE_PROKERALA_TESTS=1`.
- Certification tooling additionally requires `PROKERALA_LIVE_CREDIT_BUDGET>=500`.
- Paid calculation calls are never retried automatically.
- A privacy-minimal provider-credit event is reserved before an outgoing request.
- If usage cannot be recorded, the paid request is refused.
- Events contain endpoint, estimated credits, chart UUID, flow, sample number, outcome, safe failure code, HTTP status, latency, and date.
- Events do not contain birth identity, birth date/time, coordinates, or placements.

## Remaining blocker

Provide server-side Prokerala credentials and explicitly approve the initial 500-credit run with:

```text
RUN_LIVE_PROKERALA_TESTS=1
PROKERALA_LIVE_CREDIT_BUDGET=500
```

Run the guarded Dublin fixture exactly once. If it succeeds, compare the normalized response against fixture A before authorizing any other paid call. If it fails, do not retry until the safe error is diagnosed.
