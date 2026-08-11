-- Design artifact only. Apply through a future Django migration, not manually.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE location_place (
    geoname_id bigint PRIMARY KEY,
    canonical_name varchar(200) NOT NULL,
    ascii_name varchar(200) NOT NULL,
    search_name text NOT NULL,
    country_code char(2) NOT NULL,
    admin1_code varchar(20),
    admin2_code varchar(80),
    latitude numeric(9, 6) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude numeric(9, 6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    population bigint NOT NULL DEFAULT 0 CHECK (population >= 0),
    feature_class char(1) NOT NULL,
    feature_code varchar(10) NOT NULL,
    source_timezone_id varchar(64),
    source_modified_on date,
    imported_at timestamptz NOT NULL DEFAULT now(),
    retired_at timestamptz
);

CREATE TABLE location_alternate_name (
    alternate_name_id bigint PRIMARY KEY,
    geoname_id bigint NOT NULL REFERENCES location_place(geoname_id) ON DELETE CASCADE,
    iso_language varchar(16),
    name varchar(400) NOT NULL,
    search_name text NOT NULL,
    is_preferred boolean NOT NULL DEFAULT false,
    is_short boolean NOT NULL DEFAULT false,
    is_colloquial boolean NOT NULL DEFAULT false,
    is_historic boolean NOT NULL DEFAULT false,
    valid_from varchar(32),
    valid_to varchar(32)
);

CREATE INDEX location_place_country_population_idx
    ON location_place (country_code, population DESC) WHERE retired_at IS NULL;
CREATE INDEX location_place_admin_idx
    ON location_place (country_code, admin1_code, admin2_code);
CREATE INDEX location_place_search_trgm_idx
    ON location_place USING gin (search_name gin_trgm_ops);
CREATE INDEX location_alternate_search_trgm_idx
    ON location_alternate_name USING gin (search_name gin_trgm_ops);
CREATE INDEX location_alternate_place_idx
    ON location_alternate_name (geoname_id, is_preferred DESC);

-- A NatalChart must copy geoname_id, display names, coordinates, timezone ID,
-- and source/import versions into an immutable ResolvedLocation snapshot. It
-- must never foreign-key live search data as its sole historical location.
