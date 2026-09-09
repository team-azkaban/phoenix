-- ============================================================
-- PHOENIX - Initial Database Schema
-- PostgreSQL + PostGIS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- DATA SOURCES
-- ============================================================

CREATE TABLE IF NOT EXISTS data_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL UNIQUE,

    description TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- FACILITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS facilities (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,

    operator TEXT,

    facility_type TEXT,

    latitude DOUBLE PRECISION NOT NULL,

    longitude DOUBLE PRECISION NOT NULL,

    geometry GEOGRAPHY(POINT, 4326),

    source TEXT NOT NULL,

    baseline_stats JSONB,

    historical_event_count INTEGER NOT NULL DEFAULT 0,

    anomalous_event_count INTEGER NOT NULL DEFAULT 0,

    current_risk DOUBLE PRECISION,

    cumulative_emissions DOUBLE PRECISION,

    last_incident TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- THERMAL OBSERVATIONS
-- Raw observations ingested from FIRMS and other sources.
-- These records should be preserved and never overwritten.
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

    geometry GEOGRAPHY(POINT, 4326),

    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),

    data_version TEXT
);


-- ============================================================
-- THERMAL EVENTS
-- Central/spine entity of PHOENIX.
-- ============================================================

CREATE TABLE IF NOT EXISTS thermal_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    first_seen TIMESTAMPTZ NOT NULL,

    last_seen TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,

    longitude DOUBLE PRECISION NOT NULL,

    geometry GEOGRAPHY(POINT, 4326),

    observation_count INTEGER NOT NULL DEFAULT 0,

    facility_id UUID,

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

    classification_reasons JSONB,

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

    risk_reasons JSONB,

    alert_status TEXT,

    alert_reasons JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_thermal_events_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(facility_id)
        ON DELETE SET NULL
);


-- ============================================================
-- EVENT ↔ OBSERVATION
-- Links clustered observations to their thermal event.
-- ============================================================

CREATE TABLE IF NOT EXISTS event_observations (
    event_id UUID NOT NULL,

    observation_id UUID NOT NULL,

    PRIMARY KEY (event_id, observation_id),

    CONSTRAINT fk_event_observations_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_event_observations_observation
        FOREIGN KEY (observation_id)
        REFERENCES thermal_observations(observation_id)
        ON DELETE CASCADE
);


-- ============================================================
-- SITE BASELINES
-- Represents normal historical thermal behaviour of a facility.
-- ============================================================

CREATE TABLE IF NOT EXISTS site_baselines (
    baseline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    facility_id UUID NOT NULL UNIQUE,

    baseline_frp DOUBLE PRECISION,

    frp_std DOUBLE PRECISION,

    typical_active_hours JSONB,

    typical_duration DOUBLE PRECISION,

    seasonal_pattern JSONB,

    historical_event_count INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_site_baselines_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(facility_id)
        ON DELETE CASCADE
);


-- ============================================================
-- CLASSIFICATIONS
-- Classification is a derived signal for an event.
-- ============================================================

CREATE TABLE IF NOT EXISTS classifications (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL,

    classification TEXT NOT NULL,

    confidence DOUBLE PRECISION,

    reasons JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_classifications_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE
);


-- ============================================================
-- RISK SCORES
-- Risk is separate from classification and anomaly state.
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_scores (
    risk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL,

    risk_score DOUBLE PRECISION NOT NULL,

    severity TEXT NOT NULL,

    reasons JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_risk_scores_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE
);


-- ============================================================
-- EMISSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS emissions (
    emission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL,

    facility_id UUID,

    emissions_estimate DOUBLE PRECISION,

    method TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_emissions_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_emissions_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(facility_id)
        ON DELETE SET NULL
);


-- ============================================================
-- SATELLITE IMAGES
-- Optional external confirmation/evidence for an event.
-- ============================================================

CREATE TABLE IF NOT EXISTS satellite_images (
    satellite_image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID,

    image_url TEXT,

    image_timestamp TIMESTAMPTZ,

    confirmation_status TEXT,

    confirmation_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_satellite_images_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE
);


-- ============================================================
-- ALERTS
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id UUID NOT NULL,

    severity TEXT NOT NULL,

    risk_score DOUBLE PRECISION,

    reasons JSONB,

    status TEXT NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_alerts_event
        FOREIGN KEY (event_id)
        REFERENCES thermal_events(event_id)
        ON DELETE CASCADE
);


-- ============================================================
-- INDEXES
-- ============================================================

-- Thermal observations

CREATE INDEX IF NOT EXISTS idx_thermal_observations_timestamp
    ON thermal_observations(timestamp);

CREATE INDEX IF NOT EXISTS idx_thermal_observations_geometry
    ON thermal_observations
    USING GIST(geometry);

CREATE INDEX IF NOT EXISTS idx_thermal_observations_source_record
    ON thermal_observations(source, source_record_id);


-- Thermal events

CREATE INDEX IF NOT EXISTS idx_thermal_events_first_seen
    ON thermal_events(first_seen);

CREATE INDEX IF NOT EXISTS idx_thermal_events_last_seen
    ON thermal_events(last_seen);

CREATE INDEX IF NOT EXISTS idx_thermal_events_classification
    ON thermal_events(classification);

CREATE INDEX IF NOT EXISTS idx_thermal_events_severity
    ON thermal_events(severity);

CREATE INDEX IF NOT EXISTS idx_thermal_events_facility
    ON thermal_events(facility_id);

CREATE INDEX IF NOT EXISTS idx_thermal_events_geometry
    ON thermal_events
    USING GIST(geometry);

CREATE INDEX IF NOT EXISTS idx_thermal_events_spread_geometry
    ON thermal_events
    USING GIST(spread_geometry);


-- Facilities

CREATE INDEX IF NOT EXISTS idx_facilities_geometry
    ON facilities
    USING GIST(geometry);


-- Event observations

-- Composite primary key already provides:
-- (event_id, observation_id)


-- Site baselines

CREATE INDEX IF NOT EXISTS idx_baselines_facility
    ON site_baselines(facility_id);


-- Classifications

CREATE INDEX IF NOT EXISTS idx_classifications_event
    ON classifications(event_id);


-- Risk scores

CREATE INDEX IF NOT EXISTS idx_risk_scores_event
    ON risk_scores(event_id);


-- Emissions

CREATE INDEX IF NOT EXISTS idx_emissions_event
    ON emissions(event_id);


-- Satellite images

-- No spatial index required.


-- Alerts

CREATE INDEX IF NOT EXISTS idx_alerts_event
    ON alerts(event_id);