# Reproducible API examples

These examples are safe to run against the public dashboard API. They do **not** require private provider or operational credentials and do **not** use fabricated vessel observations.

The source service may be temporarily unavailable. Responses include actual sample positions only when the backend has valid recently accepted AIS reports.

## 1. Service health

```bash
curl -sS https://meridian-api-production-24fe.up.railway.app/health
```

A healthy process returns `{"status":"ok","modelVersion":"0.1.0"}`. This is **not** a guarantee that AIS is currently arriving.

## 2. Passage catalog

```bash
curl -sS https://meridian-api-production-24fe.up.railway.app/public/passages
```

Returns the catalog of 28 reference passage centers, names, regions and approximate study radii.

## 3. Recent, bounded vessel sample near Hormuz

```bash
curl -sS "https://meridian-api-production-24fe.up.railway.app/public/traffic?scope=chokepoint6"
```

Inspect `globalConnected`, `retrievedAt`, `matched`, and each vessel's **original** `observedAt`. The list is deliberately limited to 10 records.

## 4. Disruption model

```bash
curl -sS -X POST "https://meridian-api-production-24fe.up.railway.app/public/scenario" \
  -H "Content-Type: application/json" \
  --data @examples/scenario_request.json
```

Run this command from the repository root. Change `seed` to produce a different deterministic simulation. Inputs are assumptions, not inferred AIS cargo values.

## 5. Suez closure example

```bash
curl -sS "https://meridian-api-production-24fe.up.railway.app/public/network?origin=East%20Asia&destination=Rotterdam&closed=Suez"
```

The graph is demonstrative; a computed path is not a real vessel route. See [API reference](../docs/api-reference.md).
