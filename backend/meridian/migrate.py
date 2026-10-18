"""Run each migration once, under a PostgreSQL advisory lock."""
import asyncio,os
from pathlib import Path
import asyncpg
async def migrate():
    conn=await asyncpg.connect(os.environ['DATABASE_URL'])
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname='postgis'"):
            raise RuntimeError('Provision a PostGIS-enabled database before starting Meridian')
        await conn.execute('SELECT pg_advisory_lock(4326004)')
        await conn.execute('CREATE TABLE IF NOT EXISTS schema_migration(name text PRIMARY KEY,applied_at timestamptz NOT NULL DEFAULT now())')
        for path in sorted((Path(__file__).resolve().parents[1]/'sql').glob('*.sql')):
            if await conn.fetchval('SELECT 1 FROM schema_migration WHERE name=$1',path.name):continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute('INSERT INTO schema_migration(name) VALUES($1)',path.name)
    finally:await conn.close()
if __name__=='__main__':asyncio.run(migrate())
