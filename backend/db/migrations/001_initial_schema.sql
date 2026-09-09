-- ============================================================
-- Phoenix - Initial Database Schema
-- PostgreSQL + PostGIS
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- 1. DATA SOURCES
-- ============================================================

CREATE TABLE IF NOT EXISTS data_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    source_type TEXT,
    url TEXT,
    data_version TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 2. FACILITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS facilities (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    operator TEXT,
    facility_type TEXT,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    geometry GEOGRAPHY(POINT, 4326) NOT NULL,

    source TEXT,

    baseline_stats JSONB,

    historical_event_count INTEGER NOT NULL DEFAULT 0,
    anomalous_event_count INTEGER NOT NULL DEFAULT 0,

    current_risk DOUBLE PRECISION,
    cumulative_emissions DOUBLE PRECISION,
    last_incident TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 3. THERMAL OBSERVATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS thermal_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    timestamp TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    sensor TEXT,
    satellite TEXT,

    frp DOUBLE PRECISION,
    brightness_temperature DOUBLE PRECISION,

    confidence TEXT,
    day_night TEXT,

    source TEXT NOT NULL,
    source_record_id TEXT,

    geometry GEOGRAPHY(POINT, 4326) NOT NULL,

    acquisition_timestamp TIMESTAMPTZ,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_version TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. THERMAL EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS thermal_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    geometry GEOGRAPHY(POINT, 4326) NOT NULL,

    observation_count INTEGER NOT NULL DEFAULT 0,

    facility_id UUID REFERENCES facilities(facility_id)
        ON DELETE SET NULL,

    facility_distance_m DOUBLE PRECISION,
    facility_type TEXT,

    landcover_class TEXT,
    built_up_fraction DOUBLE PRECISION,
    forest_fraction DOUBLE PRECISION,
    cropland_fraction DOUBLE PRECISION,

    current_frp DOUBLE PRECISION,
    max_frp DOUBLE PRECISION,
    mean_frp DOUBLE PRECISION,
    frp_growth DOUBLE PRECISION,
    duration DOUBLE PRECISION,

    baseline_frp DOUBLE PRECISION,
    baseline_deviation DOUBLE PRECISION,
    anomaly_state TEXT,

    classification TEXT,
    classification_confidence DOUBLE PRECISION,
    classification_reasons TEXT[],

    satellite_image_id UUID,

    image_confirmation TEXT,
    image_notes TEXT,

    emissions_estimate DOUBLE PRECISION,
    emissions_method TEXT,

    population_exposed DOUBLE PRECISION,

    wind_speed DOUBLE PRECISION,
    wind_direction DOUBLE PRECISION,

    spread_geometry GEOGRAPHY(POLYGON, 4326),

    risk_score DOUBLE PRECISION,
    severity TEXT,
    risk_reasons TEXT[],

    alert_status TEXT,
    alert_reasons TEXT[],

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 5. EVENT ↔ OBSERVATION
-- ============================================================

CREATE TABLE IF NOT EXISTS event_observations (
    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    observation_id UUID NOT NULL
        REFERENCES thermal_observations(observation_id)
        ON DELETE CASCADE,

    PRIMARY KEY (event_id, observation_id)
);


-- ============================================================
-- 6. SITE BASELINES
-- ============================================================

CREATE TABLE IF NOT EXISTS site_baselines (
    baseline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    facility_id UUID NOT NULL
        REFERENCES facilities(facility_id)
        ON DELETE CASCADE,

    baseline_period TEXT,

    observation_count INTEGER,

    mean_frp DOUBLE PRECISION,
    median_frp DOUBLE PRECISION,
    std_frp DOUBLE PRECISION,
    percentile_95_frp DOUBLE PRECISION,

    statistics JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 7. CLASSIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS classifications (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    classification TEXT NOT NULL,

    confidence DOUBLE PRECISION,

    reasons TEXT[],

    model_version TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 8. RISK SCORES
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_scores (
    risk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    risk_score DOUBLE PRECISION NOT NULL,

    severity TEXT,

    reasons TEXT[],

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 9. EMISSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS emissions (
    emission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    emissions_estimate DOUBLE PRECISION NOT NULL,

    unit TEXT,

    method TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 10. SATELLITE IMAGES
-- ============================================================

CREATE TABLE IF NOT EXISTS satellite_images (
    satellite_image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    satellite TEXT,

    acquisition_timestamp TIMESTAMPTZ,

    image_url TEXT,

    confirmation TEXT,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 11. ALERTS
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    severity TEXT,

    risk_score DOUBLE PRECISION,

    reasons TEXT[],

    status TEXT NOT NULL DEFAULT 'active',

    message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    acknowledged_at TIMESTAMPTZ
);


-- ============================================================
-- SPATIAL INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_facilities_geometry
    ON facilities USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_observations_geometry
    ON thermal_observations USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_events_geometry
    ON thermal_events USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_events_spread_geometry
    ON thermal_events USING GIST (spread_geometry);


-- ============================================================
-- TIME INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_observations_timestamp
    ON thermal_observations (timestamp);

CREATE INDEX IF NOT EXISTS idx_events_first_seen
    ON thermal_events (first_seen);

CREATE INDEX IF NOT EXISTS idx_events_last_seen
    ON thermal_events (last_seen);


-- ============================================================
-- LOOKUP INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_events_facility
    ON thermal_events (facility_id);

CREATE INDEX IF NOT EXISTS idx_events_classification
    ON thermal_events (classification);

CREATE INDEX IF NOT EXISTS idx_events_severity
    ON thermal_events (severity);

CREATE INDEX IF NOT EXISTS idx_observations_source_record
    ON thermal_observations (source, source_record_id);

CREATE INDEX IF NOT EXISTS idx_baselines_facility
    ON site_baselines (facility_id);

CREATE INDEX IF NOT EXISTS idx_classifications_event
    ON classifications (event_id);

CREATE INDEX IF NOT EXISTS idx_risk_scores_event
    ON risk_scores (event_id);

CREATE INDEX IF NOT EXISTS idx_emissions_event
    ON emissions (event_id);

CREATE INDEX IF NOT EXISTS idx_alerts_event
    ON alerts (event_id);