# Data quality, provenance, and known limitations

Meridian prioritizes **auditable observations over visual completeness**. If no suitable AIS report is received, the globe should show no vessel rather than a fabricated symbol.

## Source provenance

| Data or model | Source | Interpretation |
| --- | --- | --- |
| AIS messages | AISStream, from participating terrestrial/satellite receivers | Observed broadcasts, with gaps and possible erroneous transmissions |
| Alternate regional AIS adapter | Fintraffic/Digitraffic | Finnish/Baltic-oriented AIS; **not** the global collector |
| Passage reference centers | Curated JSON catalog of 28 named passages | Approximate study-area lookup centers, not canal polygons or audited transit counts |
| Vessel identity | AIS static message metadata keyed by MMSI | Name, ship type and reported destination may be unavailable or stale |
| Maritime network | Hand-authored NetworkX graph | Demonstration of constrained route analysis |
| Cost model | User-provided assumptions and deterministic model | Scenario sensitivity analysis, **not** calibrated prediction |
| Map baselayers | Third-party globe imagery and Leaflet tiles | Contextual cartography, subject to upstream terms/availability |

## Ingestion integrity

1. **Decode and join by MMSI.** A position lacking eligible cargo/tanker static metadata may be buffered, not immediately counted. The pending buffer and metadata cache are bounded to avoid memory exhaustion.
2. **Validate source time.** Reports require a source event timestamp within an allowable 24-hour past / five-minute future window relative to receive time. An AIS second-of-minute field is never substituted as an absolute timestamp.
3. **Validate geography and motion.** Latitude/longitude must be finite and in range. A large (>100 km/h inferred) short-interval position jump is quarantined. The pipeline does **not** shift coordinates from land to water.
4. **Deduplicate.** History is keyed by `(mmsi, observed_at)`; latest state updates only when the accepted event time advances.
5. **Sample intentionally.** At most 10 eligible unique vessel identities per passage per hour enter the normal passage cohort, plus any explicitly watched vessels. Accepted snapshots may update latest vessel state more frequently, while historical archives are reduced to original hourly observations.
6. **Retain bounds.** Sampled historical observations are retained for approximately seven days. Collector pause thresholds account for measured database plus WAL size.

## Interpreting freshness

- **`globalConnected=true`**: the persisted status record was updated within 60 seconds and reports a connected WebSocket. It does not prove a new valid position in your chosen region.
- **`retrievedAt`**: when the API constructed the response.
- **`sourceUpdatedAt`**: last collector status write, not necessarily the last AIS ping.
- **`observedAt`**: source observation timestamp for the individual vessel.
- **`fresh`**: latest-state records received with observation times inside the recent 15-minute reporting window across **all** stored vessels; **not** a local passage census.
- **`matched`**: latest-state vessel records inside one approximate passage radius with observation times inside 24 hours.
- **`vessels`**: bounded sample returned to the browser; a passage may contain zero eligible records despite an active collector.

## Scope and statistical caveats

- A world-bounded subscription does not guarantee vessels in the world are visible. Coverage depends on third-party receivers, class metadata, sampling, and temporal gaps.
- Some vessel pings can be erroneous, spoofed, delayed, misclassified or missing. A raw vessel position near land is not proof of being on land or off course; similarly, a snapped-to-water visual would corrupt source coordinates.
- AIS speed, course, name and destination are self-reported or equipment-derived fields. A `destination` string is **not** a verified shipment itinerary, and MMSI is not a vessel home-country guarantee.
- A position within a passage radius does not establish that the vessel transited the waterway, incurred a delay, or belongs to an economically exposed fleet.
- Ten-vessel samples are designed to constrain storage and API cost. They must **not** be interpreted as random or representative samples for estimating total ship traffic.
- Historic observations are sparse. Missing points must not be interpolated as actual tracks.

## Economic model caveats

`CostModel` samples conditional delay duration using an asymmetric triangular distribution with user-entered mode `delayHours`, range approximately 0.5× to 1.75×. A separate Bernoulli likelihood gate decides whether a disruption occurs per trial. Modeled per-trial cost combines daily exposure and inventory financing. A `passThrough` fraction allocates expected cost into supplier/consumer components.

- No AIS record supplies the default likelihood, shipment value, financing rate, or daily delay expense.
- Outputs are sensitive to input assumptions and are not calibrated against historical disruption outcomes.
- P10/P90 and P95 summaries must be read with their exact model definitions; they are not confidence intervals for real-world impacts.

## Operational checks

| Check | Healthy indication | Caveat |
| --- | --- | --- |
| HTTP process | `GET /health` responds `status=ok` | Does not verify receiver or database data freshness |
| Receiver | Collector reports connected recently | Socket alone does not establish position sampling |
| Receiving | `received` and `lastMessageAt` advance | A message might fail validation or classification |
| Persistence | `persisted` increases and `pingReadback=True` appears in logs | Still only sampled accepted observations |
| Map | Passage catalog loads, sample endpoint returns and markers display where positions exist | Empty areas may be expected |
| Archive | Retrieved history records preserve original timestamp and coordinate | Seven-day sampled archive, not exhaustive |
| Storage | `storagePaused=false` | Monitor available volume space and WAL headroom |

See [deployment runbook](railway-deployment.md) for operational prerequisites.
