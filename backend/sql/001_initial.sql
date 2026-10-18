-- PostGIS must already be enabled by the database image or administrator.
CREATE TABLE IF NOT EXISTS raw_snapshot (
 id bigserial PRIMARY KEY,
 retrieved_at timestamptz NOT NULL DEFAULT now(),
 source text NOT NULL,
 payload jsonb NOT NULL,
 payload_sha256 text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS vessel (
 mmsi bigint PRIMARY KEY CHECK (mmsi BETWEEN 100000000 AND 999999999),
 name text NOT NULL,
 kind text NOT NULL CHECK (kind IN ('Cargo','Tanker')),
 destination text NOT NULL,
 metadata_at timestamptz
);
CREATE TABLE IF NOT EXISTS observation (
 mmsi bigint NOT NULL REFERENCES vessel(mmsi),
 observed_at timestamptz NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now(),
 position geography(Point,4326) NOT NULL,
 speed_knots real CHECK (speed_knots >= 0 AND speed_knots < 102.3),
 course_degrees real CHECK (course_degrees >= 0 AND course_degrees < 360),
 snapshot_id bigint NOT NULL REFERENCES raw_snapshot(id),
 PRIMARY KEY(mmsi,observed_at)
);
CREATE INDEX IF NOT EXISTS observation_position_gist ON observation USING gist(position);
CREATE INDEX IF NOT EXISTS observation_time_idx ON observation(observed_at DESC);
CREATE TABLE IF NOT EXISTS scenario_run (
 id bigserial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),
 mmsi bigint REFERENCES vessel(mmsi), model_version text NOT NULL,
 assumptions jsonb NOT NULL, result jsonb NOT NULL
);
CREATE OR REPLACE VIEW latest_vessel_observation AS
 SELECT DISTINCT ON (o.mmsi) o.*,v.name,v.kind,v.destination
 FROM observation o JOIN vessel v USING(mmsi)
 ORDER BY o.mmsi,o.observed_at DESC;
CREATE OR REPLACE VIEW vessel_freshness AS
 SELECT mmsi,name,kind,observed_at,
 extract(epoch FROM (now()-observed_at))/60 AS age_minutes,
 observed_at >= now()-interval '15 minutes' AS fresh
 FROM latest_vessel_observation;
