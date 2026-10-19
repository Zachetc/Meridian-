"""Long-running collector. No browser must remain open; run via Docker's global profile.

World subscription is deliberate: chokepoint-only bounding boxes lose outbound ships.
Coverage still depends on the provider's receivers; this cannot guarantee every ship.
"""
import asyncio,json,logging,os,random,time
from datetime import datetime,timezone
import asyncpg
from websockets.asyncio.client import connect
from .aisstream import StreamDecoder
from .store import PostgresStore

log=logging.getLogger('meridian.collector')
async def main():
    key=os.environ.get('AISSTREAM_API_KEY')
    if not key:raise RuntimeError('Set AISSTREAM_API_KEY; no global feed is fabricated without credentials')
    pool=await asyncpg.create_pool(os.environ['DATABASE_URL'],min_size=1,max_size=5)
    store=PostgresStore(pool);decoder=StreamDecoder();queue=asyncio.Queue(maxsize=20000)
    counts={'received':0,'persisted':0,'reconnects':0,'lastMessageAt':None,'connected':False,'storagePaused':False}
    budget=int(os.getenv('MAX_DATABASE_MB','250'))*1024*1024
    if budget<64*1024*1024:raise RuntimeError('MAX_DATABASE_MB must be at least 64')
    last_log=0
    async def capacity():
        # Include WAL: database size alone understates the starter volume footprint.
        size=await pool.fetchval("SELECT pg_database_size(current_database()) + coalesce((SELECT sum(size) FROM pg_ls_waldir()),0)")
        counts['databaseAndWalBytes']=int(size);counts['storageBudgetBytes']=budget
        counts['storagePaused']=size>=budget
        return not counts['storagePaused']
    for row in await pool.fetch('SELECT mmsi,payload FROM stream_metadata'):
        decoder._put(decoder.metadata,row['mmsi'],json.loads(row['payload']))
    async def status():
        await pool.execute("INSERT INTO collector_status(id,payload) VALUES('aisstream',$1::jsonb) ON CONFLICT(id) DO UPDATE SET updated_at=now(),payload=excluded.payload",json.dumps({**counts,'queueDepth':queue.qsize(),'rejected':decoder.rejected,'evicted':decoder.evicted}))
    async def flush():
        nonlocal last_log
        while True:
            batch=[]
            try:batch.append(await asyncio.wait_for(queue.get(),timeout=10))
            except asyncio.TimeoutError:await status();continue
            deadline=time.monotonic()+2
            while len(batch)<500 and time.monotonic()<deadline:
                try:batch.append(await asyncio.wait_for(queue.get(),timeout=max(.01,deadline-time.monotonic())))
                except asyncio.TimeoutError:break
            now=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
            snapshot={'vessels':batch,'retrievedAt':now,'sourceUpdatedAt':counts['lastMessageAt'],'source':'AISStream','coverage':'Global receiver network; incomplete coverage','rejected':decoder.rejected,'globalConnected':True}
            # Retry the same batch before draining more; bounded queue applies backpressure.
            attempt=0
            while True:
                try:
                    while not await capacity():
                        counts['connected']=False
                        await status()
                        log.warning('AIS archive paused at storage budget; existing observations retained; reception gap begins')
                        await asyncio.sleep(30)
                    await store.save_snapshot({'source':'AISStream','messages':batch},snapshot)
                    records=[(mmsi,decoder.metadata[mmsi]['timestamp']/1000,json.dumps(decoder.metadata[mmsi])) for mmsi in {v['mmsi'] for v in batch} if mmsi in decoder.metadata]
                    if records:await pool.executemany('INSERT INTO stream_metadata(mmsi,observed_at,payload) VALUES($1,to_timestamp($2),$3::jsonb) ON CONFLICT(mmsi) DO UPDATE SET observed_at=excluded.observed_at,payload=excluded.payload WHERE excluded.observed_at>stream_metadata.observed_at',records)
                    counts['persisted']+=len(batch)
                    if time.monotonic()-last_log>=30:
                        # Read a saved ping back with its original event time and coordinates.
                        v=batch[-1]
                        from .store import parse_date
                        verified=await pool.fetchval('SELECT EXISTS(SELECT 1 FROM observation WHERE mmsi=$1 AND observed_at=$2 AND abs(ST_X(position::geometry)-$3)<0.0000001 AND abs(ST_Y(position::geometry)-$4)<0.0000001)',v['mmsi'],parse_date(v['observedAt']),v['longitude'],v['latitude'])
                        fleet=await pool.fetchval('SELECT count(*) FROM latest_position')
                        log.info('AIS received=%s archivedIncludingQuarantine=%s vessels=%s pingReadback=%s mmsi=%s originalPing=%s storageBytes=%s',counts['received'],counts['persisted'],fleet,verified,v['mmsi'],v['observedAt'],counts['databaseAndWalBytes'])
                        last_log=time.monotonic()
                    await status();break
                except (asyncpg.PostgresError,OSError):
                    attempt+=1;log.error('Database batch failed; retrying without discarding records');await asyncio.sleep(min(30,2**min(attempt,5)))
            for _ in batch:queue.task_done()
    async def receive():
        attempt=0
        while True:
            while not await capacity():
                counts['connected']=False;await status();await asyncio.sleep(30)
            try:
                async with connect('wss://stream.aisstream.io/v0/stream',compression='deflate',max_queue=64,ping_interval=20,ping_timeout=20,open_timeout=20) as socket:
                    await socket.send(json.dumps({'APIKey':key,'BoundingBoxes':[[[-90,-180],[90,180]]],'FilterMessageTypes':['PositionReport','ShipStaticData','StandardClassBPositionReport','ExtendedClassBPositionReport']}))
                    counts['connected']=True;await status();attempt=0
                    async for raw in socket:
                        if counts['storagePaused']:
                            await socket.close();break
                        envelope=json.loads(raw)
                        if envelope.get('error') or envelope.get('Error'):raise RuntimeError('Provider rejected subscription')
                        if envelope.get('MessageType')=='SubscriptionConfirmation':
                            if not (envelope.get('Message') or {}).get('CompressionEnabled'):log.warning('Provider did not confirm compression')
                            continue
                        counts['received']+=1;counts['lastMessageAt']=datetime.now(timezone.utc).isoformat()
                        v=decoder.decode(envelope)
                        if v:await queue.put(v)
            except asyncio.CancelledError:raise
            except Exception as exc:
                # Do not log provider payloads or exception strings that could echo credentials.
                counts['connected']=False;counts['reconnects']+=1;await status();attempt+=1
                log.warning('AIS connection interrupted (%s); reconnecting',type(exc).__name__)
                await asyncio.sleep(min(60,2**min(attempt,6))+random.random())
    try:
        async with asyncio.TaskGroup() as group:group.create_task(flush());group.create_task(receive())
    finally:await pool.close()
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
