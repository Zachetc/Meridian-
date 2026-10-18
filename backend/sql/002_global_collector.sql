CREATE TABLE IF NOT EXISTS collector_status (
 id text PRIMARY KEY,
 updated_at timestamptz NOT NULL DEFAULT now(),
 payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS stream_metadata (
 mmsi bigint PRIMARY KEY,
 observed_at timestamptz NOT NULL,
 payload jsonb NOT NULL
);
