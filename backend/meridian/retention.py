"""User-approved seven-day, hourly archive; latest positions and goals survive.

Historic dense reports are reduced to one original report per UTC hour. Physical
compaction is bounded by measured headroom on the existing 500 MiB volume; no
volume growth, database reset, or guessed movement occurs.
"""
import json
import logging

log = logging.getLogger('meridian.retention')

async def maintain(pool, budget):
    async with pool.acquire() as conn:
        if not await conn.fetchval('SELECT pg_try_advisory_lock(4326005)'): return
        try:
            async with conn.transaction():
                old = await conn.execute("DELETE FROM observation WHERE observed_at < now()-interval '7 days'")
                quarantine = await conn.execute("DELETE FROM observation_quarantine WHERE observed_at < now()-interval '7 days'")
                # Once-only conversion of the previously dense archive. Keep an
                # actual newest ping, not a rounded time or averaged coordinate.
                converted = await conn.fetchval("SELECT 1 FROM archive_maintenance WHERE id='hourly-v1'")
                thinned = 'DELETE 0'
                if not converted:
                    thinned = await conn.execute("""DELETE FROM observation o USING (
                        SELECT mmsi, observed_at, row_number() OVER (
                          PARTITION BY mmsi,date_trunc('hour',observed_at AT TIME ZONE 'UTC')
                          ORDER BY observed_at DESC) AS n FROM observation
                        ) d WHERE d.n>1 AND o.mmsi=d.mmsi AND o.observed_at=d.observed_at""")
                raw = await conn.execute('DELETE FROM raw_snapshot r WHERE NOT EXISTS (SELECT 1 FROM observation o WHERE o.snapshot_id=r.id)')
                details = dict(expired=old,thinned=thinned,unreferencedRaw=raw,expiredQuarantine=quarantine)
                await conn.execute("INSERT INTO archive_maintenance(id,details) VALUES('hourly-v1',$1::jsonb) ON CONFLICT(id) DO UPDATE SET completed_at=now(),details=excluded.details",json.dumps(details))
            log.info('Archive retention %s; original retained pings and latest positions preserved',details)
            size = await conn.fetchval("SELECT pg_database_size(current_database())+coalesce((SELECT sum(size) FROM pg_ls_waldir()),0)")
            # VACUUM FULL rewrites just these archive tables, not the database.
            # Existing latest_position, vessel and tracking goals are untouched.
            if size >= budget * .8:
                for table in ('raw_snapshot','observation','observation_quarantine'):
                    size = await conn.fetchval("SELECT pg_database_size(current_database())+coalesce((SELECT sum(size) FROM pg_ls_waldir()),0)")
                    relation = await conn.fetchval('SELECT pg_total_relation_size($1::regclass)',table)
                    if size + relation*2 > 450*1024*1024:
                        log.warning('Skipping physical compaction of %s: insufficient measured headroom',table)
                        continue
                    await conn.execute('SET lock_timeout TO \'5s\'')
                    await conn.execute(f'VACUUM (FULL, ANALYZE) {table}')
                    log.info('Compacted archive table %s',table)
            else:
                for table in ('observation','raw_snapshot','observation_quarantine'):
                    await conn.execute(f'VACUUM (ANALYZE) {table}')
        finally:
            await conn.execute('RESET lock_timeout')
            await conn.execute('SELECT pg_advisory_unlock(4326005)')
