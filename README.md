# Meridian (In progress)

Maritime AIS data engineering and supply-chain scenario analysis by Zachary Amachee.

This repository currently contains the deployable Python backend: an asyncio AISStream collector, PostgreSQL/PostGIS persistence, scoped chokepoint queries, individual MMSI follow, timestamped history, a deterministic cost scenario model and NetworkX routing analysis. The interactive globe frontend is maintained in the Meridian Site and available through its Download project source action.

Railway service root: `/backend`. Dockerfile: `backend/Dockerfile`. Setup and activation: [Railway deployment](docs/railway-deployment.md).

An AISStream API key is required for global reception. Until activated, no global vessel locations are claimed. Reception is incomplete, even with a global subscription. AIS classification does not reveal cargo manifests or a vessel's home country. Cost outputs are assumption-based scenarios, not calibrated predictions.

Run tests with `pip install -r backend/requirements.txt` then `PYTHONPATH=backend pytest backend/tests -q`. The PostGIS test uses a disposable DATABASE_URL; otherwise it is skipped.
