# Contributing to Meridian

This is a portfolio/research application. Bug reports, reproducible test cases and narrowly scoped code improvements are welcome.

## Development workflow

1. Read [the architecture](docs/architecture.md) and [data limitations](docs/data-quality.md).
2. Create a branch from `main`; keep changes focused and avoid production secrets.
3. Install Python 3.12 and the dependencies from `backend/requirements.txt`.
4. Run the tests: `PYTHONPATH=backend pytest backend/tests -q`. The PostGIS integration test needs an **isolated disposable database**.
5. Include tests for changed behavior, especially event-time handling, spatial filters, sampling quotas, and auth.
6. Open a pull request describing expected vs actual behavior, data provenance implications and deployment impact.

## Integrity and security expectations

- Never commit API tokens, connection passwords, private user information or raw licensed receiver feeds.
- Never fabricate AIS positions, silently rewrite source coordinates, or substitute the request time for observation time.
- Identify whether reported quantities are complete, sampled, observed, estimated or assumed.
- Keep public payloads bounded and avoid exposing operational credentials to browser code.
- Do not assume successful HTTP health checks prove collector freshness.
- Do not introduce a large unbounded database history query or remove retention limits without storage planning.

## Scope

The repository includes backend source, a browser dashboard, database migrations, and tests. Suggestions to split the dashboard into modules and add visual regression tests are welcome, but please avoid purely decorative files without engineering value.
