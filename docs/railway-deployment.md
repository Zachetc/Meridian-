# Meridian on Railway

Project: https://railway.com/project/bda8c061-97b5-4080-9fb6-51080e2ff178

Services: PostGIS and meridian-api. The API builds from the repository's `/backend` directory with its Dockerfile. Database migrations run on API startup. Secrets are platform variables, never repository files. One API replica runs an optional asyncio collector; do not enable a second collector replica with the same key inadvertently.

## Activation

1. Obtain your own key at https://aisstream.io/ and enter it in the **meridian-api** Railway Variables panel as `AISSTREAM_API_KEY`.
2. Set `RUN_COLLECTOR=1`, retaining `AIS_PROVIDER=aisstream`, and deploy those variable changes.
3. Verify `/health`, then authorized `/vessels` reports `globalConnected: true`, recent `collector.lastMessageAt`, increasing persisted counts and nonzero `total`. Verify a scoped `/traffic` response and `/history` readback retain original event times. A connected socket alone is insufficient evidence of ship reception.
4. Only after receipt verification, set the Site's server-side `MARITIME_API_URL` to this API's HTTPS origin and `MARITIME_API_TOKEN` to the matching API credential, then redeploy the Site. Until then the Site keeps its working Fintraffic feed.

`API_TOKEN` is generated separately from the provider key. The Site can retain it securely before activation without setting the upstream URL. Never place either secret in client variables, screenshots, logs or source control.

## Storage and operational limits

The initial Railway template provisions a 500 MB persistent volume. This is a starter database, not sized for sustained worldwide AIS archiving. Measure incoming cargo/tanker volume and retained bytes, configure volume capacity and retention/partitioning before unattended global collection. Raw normalized batches and accepted positions both use storage. No retention deletion is enabled automatically. Costs depend on the Railway plan and actual usage; no plan upgrade is performed by this source.

The subscription covers worldwide receiver bounds, with incomplete reception. It filters cargo/tanker classes when identity metadata is available. No AIS provider guarantees all vessels. Queue size 20,000, metadata LRU 100,000, batches up to 500, exponential reconnect backoff, observation primary keys, and speed-jump quarantine bound work and preserve data provenance. Backpressure and reconnect gaps remain visible gaps; there is no replay guarantee.

`GET /health` proves the process started after schema setup, not reception or full coverage. Bearer-protected `/traffic` supports study-area IDs, MMSI follow, a 500-row cap and MMSI cursors. `/history` has a 1,500-point cap and exclusive timestamp cursor. The global `/vessels` call carries a summary and watched MMSIs only; it does not download the worldwide fleet.

## Verification

Local TypeScript and Node checks, Python unit tests, deployment status, API authorization checks and query readbacks are separate gates. The optional PostGIS integration test must run against a disposable database, never the user's live archive. It is skipped locally without `DATABASE_URL`. No browser performance guarantee or calibrated prediction accuracy is claimed.
