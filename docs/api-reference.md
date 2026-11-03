# Meridian API reference

Base URL (production): `https://meridian-api-production-24fe.up.railway.app`

The running FastAPI server deliberately disables its public Swagger and OpenAPI paths. This file documents the routes directly. **Do not put `API_TOKEN` or `AISSTREAM_API_KEY` in browser JavaScript or public screenshots.**

## Public dashboard API

| Method | Endpoint | Input | Response |
| --- | --- | --- | --- |
| `GET` | `/` | None | HTML WebGL dashboard |
| `GET` | `/health` | None | `{"status":"ok","modelVersion":"0.1.0"}` |
| `GET` | `/public/passages` | None | `{"passages":[...]}`, 28 configured passage references |
| `GET` | `/public/traffic` | Query `scope=chokepoint1` | Recent passage sample and collector summary |
| `POST` | `/public/scenario` | JSON object of scenario assumptions | Model version, assumptions and deterministic result |
| `GET` | `/public/network` | Query `origin`, `destination`, `closed` | Illustrative connected flag, node path and days |

### Example: chokepoint sample

```bash
curl "https://meridian-api-production-24fe.up.railway.app/public/traffic?scope=chokepoint6"
```

Selected response fields (shape only; **values shown below are illustrative and not live vessel data**):

```json
{
  "scope": "chokepoint6",
  "matched": 2,
  "fresh": 9,
  "total": 80,
  "globalConnected": true,
  "retrievedAt": "2026-11-03T20:00:00+00:00",
  "sourceUpdatedAt": "2026-11-03T19:59:55+00:00",
  "vessels": []
}
```

`matched` counts recent database records inside the selected passage radius. `fresh` counts recent accepted records across the collector's latest-state table; it is **not** per-passage. `globalConnected` reports recent connected collector status, not guaranteed end-to-end world coverage. A public passage response is capped at 10 vessel objects.

Invalid passage ID returns HTTP 400. The catalog IDs are `chokepoint1` through `chokepoint28` in the [source catalog](../backend/meridian/passage_catalog.json).

### Example: scenario

```bash
curl -X POST "https://meridian-api-production-24fe.up.railway.app/public/scenario" \
  -H "Content-Type: application/json" \
  --data '{"cargoValue":2000000,"delayHours":48,"likelihood":25}'
```

Inputs accepted by the Pydantic model:

| Name | Default | Validation |
| --- | ---: | --- |
| `cargoValue` | 2,000,000 | 0 to 10 billion USD |
| `units` | 10,000 | Integer 1 to 1 billion |
| `delayHours` | 48 | 0 to 720 |
| `likelihood` | 25 | Percent from 0 to 100 |
| `dailyCost` | 18,000 | 0 to 10 million USD/day |
| `annualRate` | 12 | Percent from 0 to 100 |
| `passThrough` | 50 | Percent from 0 to 100 |
| `seed` | 42 | Unsigned 32-bit integer |

Results include `expected` (probability-weighted mean), `conditionalMean`, `low` / `high` (conditional 10th/90th percentiles), `p95`, `supplier`, `passed`, `perUnit`, and event share estimates. These are **simulation outputs**, not observed transport charges.

### Example: network route

```bash
curl "https://meridian-api-production-24fe.up.railway.app/public/network?origin=East%20Asia&destination=Rotterdam&closed=Suez"
```

Example result type:

```json
{"connected":true,"path":["East Asia","Malacca","Arabian Sea","Cape of Good Hope","Gibraltar","Rotterdam"],"illustrativeDays":42,"basis":"illustrative topology"}
```

The node graph is intentionally simplified and the resulting travel days are graph weights, not sailing-time forecasts. Unknown nodes return 422.

## Protected operational endpoints

These calls require `Authorization: Bearer <API_TOKEN>`. Use a local environment variable or secrets manager.

- `GET /vessels?watch=`: collector health/summary; optional comma-separated watched nine-digit MMSIs.
- `GET /traffic?scope=chokepoint6&limit=10`: scoped sample, `limit` from 1 to 500 (passage samples further capped to 10); `mmsi` selects a specific vessel; `after` handles MMSI pagination in non-passage modes.
- `GET /history?mmsi=123456789`: archive of up to 1,500 points per read. Optional `before` accepts a timezone-aware ISO timestamp.
- `POST /subscriptions`: `{"mmsis":[123456789]}`, 500 maximum in one request and in the shared watch set; adds subscriptions, does not remove them.
- `POST /scenarios`: same assumption body as the public scenario route but persists run data.
- `GET /network`: protected form of the illustrative shortest-path calculation.

For protected requests, 401 means missing or invalid token; 400 means invalid scope, vessel, page, or timestamp; 409 means incompatible collector mode or subscription capacity; 422 covers scenario schema or route validation failures.

## Operational notes

1. `/health` only verifies the HTTP process and startup, not live vessel freshness.
2. Public outputs contain bounded **sampled** positions, not the entirety of the upstream feed.
3. A timestamp in a position is its reported **observation time**, not the current request time.
4. Do not infer ship cargo manifests, route destination, or geographic completeness from the returned AIS fields.
