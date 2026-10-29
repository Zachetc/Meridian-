# Meridian project status — 2026-10-29

## Verified live
- Repository: `Zachetc/Meridian-`, default branch `main`.
- Railway project: `bda8c061-97b5-4080-9fb6-51080e2ff178` (production).
- `meridian-api` latest deployment `390c6767-48ad-424e-aa41-017029fa8ecd` succeeded 2026-10-27.
- PostGIS service deployed with a 500 MB persistent volume.
- Railway variables include `AISSTREAM_API_KEY`, `RUN_COLLECTOR`, `API_TOKEN`, `DATABASE_URL` (values intentionally not copied).
- Runtime logs on 2026-10-29 show >19.4 million cumulative AIS messages, 10,751 distinct vessel records, >32,520 sampled state writes, and `pingReadback=True`. Collector reports ~127 MB storageBytes. These are cumulative collector counters, not simultaneous active vessels or a promise of complete global coverage.

## Remaining gates before calling Meridian finished
1. Verify live HTTP `/health`, authorized `/vessels`, scoped `/traffic`, and `/history` responses; ensure correct freshness, cursor behavior, and public auth.
2. Locate the separately maintained Meridian Site frontend and connect its **server-side** `MARITIME_API_URL` and `MARITIME_API_TOKEN` to the live Railway API. Never expose API tokens to browser code.
3. Confirm actual chokepoint vessel markers, ship details, loading performance, and error/fallback states in a browser.
4. Run Python tests and frontend build/lint checks. Do not run integration tests against production PostGIS.
5. Check storage headroom and retention during continued collection; 500 MB is a starter volume.
6. Deploy frontend and verify the public site. Backend is already deployed; do not redeploy it without a change.

## Safety and constraints
- No secrets in git, frontend bundles, logs, or status files.
- AIS messages are incomplete coverage; cargo type, home country, and cost estimates must be clearly labeled when inferred or modeled.
- Keep work incremental and update this file after verified milestones.

## Frontend source discovery (2026-10-29)
- Existing hosted Meridian Site: https://meridian-maritime.ardentchick1.chatgpt.site
- Site project slug: `meridian-maritime`; this frontend is a separately hosted ChatGPT Site, not a file in the GitHub backend repository.
- Do not claim the Site is integrated or deployed from GitHub without inspecting its complete source and verifying server-side `MARITIME_API_URL` / `MARITIME_API_TOKEN` configuration.
- Railway API public domain: `https://meridian-api-production-24fe.up.railway.app` (domain present in Railway configuration; public HTTP response could not be verified from current execution environment).
- **Release blocker:** current connected tools cannot edit or redeploy the existing ChatGPT Site directly, and the complete Site source is not available in the GitHub repository. Obtain/export the full Site source or use a Site-editing capability before migrating or switching public links.
