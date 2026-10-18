-- A bounded latest-state table avoids rescanning the full observation history.
CREATE TABLE IF NOT EXISTS latest_position (
 mmsi bigint PRIMARY KEY REFERENCES vessel(mmsi),
 observed_at timestamptz NOT NULL,
 position geography(Point,4326) NOT NULL,
 payload jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS latest_position_geo ON latest_position USING gist(position);
CREATE INDEX IF NOT EXISTS latest_position_time ON latest_position(observed_at DESC);
INSERT INTO latest_position(mmsi,observed_at,position,payload)
 SELECT mmsi,observed_at,position,jsonb_build_object('mmsi',mmsi,'name',name,'kind',kind,
 'destination',destination,'speed',speed_knots,'course',course_degrees,
 'longitude',ST_X(position::geometry),'latitude',ST_Y(position::geometry),
 'observedAt',observed_at,'metadataAt',NULL,'source',(SELECT source FROM raw_snapshot WHERE id=latest_vessel_observation.snapshot_id))
 FROM latest_vessel_observation WHERE true ON CONFLICT(mmsi) DO NOTHING;
CREATE TABLE IF NOT EXISTS observation_quarantine (
 mmsi bigint NOT NULL, observed_at timestamptz NOT NULL, reason text NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(mmsi,observed_at)
);
