"""Indexed, bounded read models. The world map never downloads the world fleet."""
import json,time
from pathlib import Path
from datetime import datetime, timezone

PASSAGES = {p['id']:p for p in json.loads(Path(__file__).with_name('passage_catalog.json').read_text())}
def json_value(value): return json.loads(value) if isinstance(value, str) else value

def area_filter(scope, mmsi=None):
    if mmsi is not None:
        if not 100000000 <= mmsi <= 999999999: raise ValueError('Invalid MMSI')
        return 'mmsi=$1', [mmsi]
    if scope == 'Baltic':
        return 'position && ST_MakeEnvelope(9,53,32,67,4326)::geography AND ST_Intersects(position::geometry,ST_MakeEnvelope(9,53,32,67,4326))', []
    p=PASSAGES.get(scope)
    if p:
        return 'ST_DWithin(position,ST_SetSRID(ST_MakePoint($1,$2),4326)::geography,$3)', [p['longitude'],p['latitude'],p['radiusKm']*1000]
    if scope == 'Global': return 'FALSE', []
    raise ValueError('Unknown passage or region')

class TrafficReader:
    def __init__(self,pool): self.pool=pool;self.cached=None;self.cached_at=0
    async def summary(self):
        if self.cached and time.monotonic()-self.cached_at<15:return self.cached
        # Counts are a short-lived cache, not a position response cache.
        now=datetime.now(timezone.utc)
        row=await self.pool.fetchrow("SELECT updated_at,payload FROM collector_status WHERE id='aisstream'")
        status=json_value(row['payload']) if row else {}
        healthy=bool(row and (now-row['updated_at']).total_seconds()<60 and status.get('connected'))
        counts=await self.pool.fetchrow("SELECT count(*) AS total,count(*) FILTER(WHERE observed_at>=now()-interval '15 minutes') AS fresh FROM latest_position WHERE observed_at>=now()-interval '24 hours'")
        result=dict(retrievedAt=now.isoformat(),sourceUpdatedAt=row['updated_at'].isoformat() if row else None,
            source='AISStream',coverage='Global receiver network; incomplete reception',rejected=status.get('rejected',0),
            globalConnected=healthy,globalConfigured=True,persisted=True,total=counts['total'],fresh=counts['fresh'],
            collector={k:status.get(k) for k in ['connected','lastMessageAt','received','persisted','queueDepth','reconnects','rejected','evicted','storagePaused','databaseAndWalBytes','storageBudgetBytes','archiveMode','passageSampleLimit','retentionDays','watchedVessels']})
        self.cached=result;self.cached_at=time.monotonic();return result
    async def query(self,scope='Global',mmsi=None,after=0,limit=500):
        if not 1<=limit<=500 or after<0: raise ValueError('Invalid page')
        where,args=area_filter(scope,mmsi)
        # An individual lookup keeps its last known report even after reception stops.
        age='' if mmsi else " AND observed_at>=now()-interval '24 hours'"
        count=await self.pool.fetchval('SELECT count(*) FROM latest_position WHERE '+where+age,*args)
        n=len(args)
        sampled=scope in PASSAGES and mmsi is None
        if sampled:
            limit=min(limit,10)
            rows=await self.pool.fetch('SELECT payload,observed_at FROM latest_position WHERE '+where+age+f' ORDER BY observed_at DESC,mmsi LIMIT ${n+1}',*args,limit)
        else:
            rows=await self.pool.fetch('SELECT payload,observed_at FROM latest_position WHERE '+where+age+f' AND mmsi>${n+1} ORDER BY mmsi LIMIT ${n+2}',*args,after,limit+1)
        vessels=[]
        for r in rows[:limit]:
            v=json_value(r['payload']);v['observedAt']=r['observed_at'].isoformat();vessels.append(v)
        summary=await self.summary()
        return dict(**summary,vessels=vessels,scope=str(mmsi) if mmsi else scope,matched=count,limit=limit,
            nextCursor=vessels[-1]['mmsi'] if len(rows)>limit and not sampled else None)
    async def history(self,mmsi,before=None,limit=1500):
        args=[mmsi];where='mmsi=$1'
        if before:
            date=datetime.fromisoformat(before.replace('Z','+00:00'))
            if date.tzinfo is None:raise ValueError('History cursor must include a timezone')
            args.append(date);where+=' AND observed_at<$2'
        rows=await self.pool.fetch('SELECT observed_at,ST_X(position::geometry) AS longitude,ST_Y(position::geometry) AS latitude,speed_knots FROM observation WHERE '+where+f' ORDER BY observed_at DESC LIMIT ${len(args)+1}',*args,limit+1)
        points=[dict(observedAt=r['observed_at'].isoformat(),longitude=r['longitude'],latitude=r['latitude'],speed=r['speed_knots'],source='AISStream') for r in rows[:limit]]
        return dict(points=list(reversed(points)),limit=limit,nextBefore=points[-1]['observedAt'] if len(rows)>limit else None,source='AISStream',continuousCollector=False,archiveMode='hourly-sampled',retentionDays=7)
