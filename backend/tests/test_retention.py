"""Uses the disposable CI database only. Never point tests at production."""
import asyncio,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest

@pytest.mark.skipif(not os.getenv('DATABASE_URL'),reason='Disposable PostGIS required')
def test_hourly_archive_restart_and_retention_preserve_latest():
    async def run():
        import asyncpg
        from meridian.store import PostgresStore
        from meridian.retention import maintain
        pool=await asyncpg.create_pool(os.environ['DATABASE_URL'])
        try:
            for p in sorted(Path('backend/sql').glob('*.sql')):await pool.execute(p.read_text())
            now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
            def ship(stamp):return dict(mmsi=230000099,name='TEST ONLY',kind='Cargo',longitude=24,latitude=60,speed=10,course=90,destination='UNRESOLVED',metadataAt=stamp.isoformat(),observedAt=stamp.isoformat())
            async def save(stamp,hourly=True):
                v=ship(stamp)
                return await PostgresStore(pool).save_snapshot({'messages':[v]},{'source':'AISStream','vessels':[v]},hourly=hourly)
            await save(now+timedelta(seconds=1))
            await save(now+timedelta(seconds=61))
            assert await pool.fetchval('SELECT count(*) FROM observation WHERE mmsi=230000099')==1
            assert await pool.fetchval('SELECT observed_at FROM latest_position WHERE mmsi=230000099')==now+timedelta(seconds=61)
            await save(now-timedelta(days=8),False)
            await save(now+timedelta(seconds=90),False) # old dense archive
            await pool.execute('INSERT INTO tracking_subscription(mmsi) VALUES(230000099) ON CONFLICT DO NOTHING')
            await maintain(pool,100000000000) # ordinary vacuum, no compaction needed in CI
            assert await pool.fetchval('SELECT count(*) FROM observation WHERE mmsi=230000099')==1
            assert await pool.fetchval('SELECT observed_at FROM observation WHERE mmsi=230000099')==now+timedelta(seconds=90)
            assert await pool.fetchval('SELECT observed_at FROM latest_position WHERE mmsi=230000099')==now+timedelta(seconds=90)
            assert await pool.fetchval('SELECT count(*) FROM tracking_subscription WHERE mmsi=230000099')==1
            assert not await pool.fetchval('SELECT EXISTS(SELECT 1 FROM observation o LEFT JOIN raw_snapshot r ON r.id=o.snapshot_id WHERE r.id IS NULL)')
            await maintain(pool,100000000000)
            assert await pool.fetchval('SELECT count(*) FROM observation WHERE mmsi=230000099')==1
        finally:await pool.close()
    asyncio.run(run())
