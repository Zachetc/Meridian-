"""Runs against disposable CI PostGIS, skipped when no DATABASE_URL is configured."""
import asyncio,json,os,time
from pathlib import Path
import pytest
from meridian.store import PostgresStore
from meridian.ingestion import normalize

@pytest.mark.skipif(not os.getenv('DATABASE_URL'),reason='PostGIS integration requires DATABASE_URL')
def test_snapshot_replay_is_idempotent_and_geo_query_works():
    async def run():
        import asyncpg
        pool=await asyncpg.create_pool(os.environ['DATABASE_URL'])
        try:
            for migration in sorted(Path('backend/sql').glob('*.sql')):await pool.execute(migration.read_text())
            now=int(time.time()*1000)
            meta=[dict(mmsi=123456789,name='INTEGRATION TEST',shipType=70,timestamp=now)]
            locations={'features':[dict(mmsi=123456789,geometry=dict(coordinates=[24,60]),properties=dict(timestampExternal=now,sog=12,cog=90))]}
            raw={'locations':locations,'metadata':meta};snapshot=normalize(locations,meta,now);store=PostgresStore(pool)
            first=await store.save_snapshot(raw,snapshot);second=await store.save_snapshot(raw,snapshot)
            assert first==second
            assert await pool.fetchval('SELECT count(*) FROM observation WHERE mmsi=123456789')==1
            assert await pool.fetchval('SELECT count(*) FROM latest_position WHERE mmsi=123456789')==1
            assert await pool.fetchval('SELECT ST_DWithin(position,ST_SetSRID(ST_MakePoint(24,60),4326)::geography,100) FROM observation WHERE mmsi=123456789')
            from meridian.traffic import TrafficReader,PASSAGES
            reader=TrafficReader(pool)
            assert (await reader.query())['vessels']==[]
            assert (await reader.query('Baltic'))['vessels'][0]['mmsi']==123456789
            assert (await reader.query('chokepoint6',mmsi=123456789))['vessels'][0]['longitude']==24
            for scope in PASSAGES:assert len((await reader.query(scope))['vessels'])<=500
            assert (await reader.history(123456789))['points'][0]['observedAt'].startswith(snapshot['vessels'][0]['observedAt'][:19])
        finally:await pool.close()
    asyncio.run(run())
