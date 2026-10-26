-- Explicit tracking subscriptions only; voyage goals remain owned by the Site.
CREATE TABLE IF NOT EXISTS tracking_subscription (
 mmsi bigint PRIMARY KEY CHECK (mmsi BETWEEN 100000000 AND 999999999),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS archive_maintenance (
 id text PRIMARY KEY, completed_at timestamptz NOT NULL DEFAULT now(), details jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS observation_snapshot_idx ON observation(snapshot_id);
