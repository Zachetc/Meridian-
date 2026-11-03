# Meridian roadmap and implementation status

This roadmap distinguishes **existing code**, **implemented but environment-dependent functionality**, and **proposed improvements**. It is intentionally not a list of features claimed to be production-proven.

## Implemented in this repository

- [x] FastAPI application with HTML globe dashboard and 2D Leaflet alternative
- [x] Catalog of 28 maritime chokepoint reference centers
- [x] AISStream WebSocket client, decoder, identity matching and reconnect loop
- [x] Cargo/tanker filtering with bounded per-passage hourly sampling
- [x] PostgreSQL/PostGIS storage for latest positions, event-time history and quarantine
- [x] Scoped passage/MMSI lookups and Bearer-protected operational endpoints
- [x] Public bounded passage data endpoint for the portfolio globe
- [x] Collector status, source timestamps, vessel detail on selection and automatic passage polling
- [x] Versioned, deterministic Monte Carlo cost sensitivity model
- [x] Illustrative NetworkX shortest-path analysis under chokepoint closure
- [x] Database migrations, archive retention rules and pytest/GitHub Actions checks

## Environment-dependent

- [ ] Repeated browser smoke tests across modern desktop/mobile engines, including failed CDN fallback
- [ ] Independent end-to-end verification of current vessel marker counts across every passage
- [ ] Long-running production monitoring for storage, outage frequency and source freshness
- [ ] Operator-visible incident alerts, provider quotas and outage response playbooks

## Potential enhancements

- [ ] Split dashboard HTML into independently tested TypeScript/JS modules with local build assets
- [ ] Add browser automated tests for selecting a passage and opening a real sampled marker
- [ ] Add source-time age badges and explicit empty/stale state visualizations per vessel
- [ ] Add opt-in ship watches with access controls and lifecycle management
- [ ] Add query telemetry and bounded operational metrics under load
- [ ] Add documented backup/restore drills and storage expansion plan
- [ ] Evaluate passage polygons, verified transit events and data-license-compliant historical benchmarking
- [ ] Add calibrated risk model **only after** obtaining an appropriate labeled incident dataset

## Non-goals

Meridian is not a navigational chart, validated vessel tracking platform, complete worldwide AIS archive, real-time ship insurance pricing service, or causal disruption forecasting tool.
