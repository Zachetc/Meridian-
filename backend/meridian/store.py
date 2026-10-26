import hashlib,json,math
from datetime import datetime,timezone
import asyncpg

def parse_date(s):return datetime.fromisoformat(s.replace('Z','+00:00')) if s else None
def suspect_jump(previous,current):
    hours=(parse_date(current['observedAt'])-parse_date(previous['observedAt'])).total_seconds()/3600
    if not 0<hours<6:return False
    a,b=math.radians(previous['latitude']),math.radians(current['latitude'])
    dlon=math.radians(current['longitude']-previous['longitude'])
    distance=6371*2*math.asin(min(1,math.sqrt(math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(dlon/2)**2)))
    return distance/hours>100

class PostgresStore:
    def __init__(self,pool:asyncpg.Pool):self.pool=pool
    async def save_snapshot(self,raw,snapshot,hourly=False):
        encoded=json.dumps(raw,sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256(encoded.encode()).hexdigest()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                sid=None
                if not snapshot['vessels']:return sid
                rows=await conn.fetch('SELECT mmsi,payload FROM latest_position WHERE mmsi=ANY($1::bigint[])',[v['mmsi'] for v in snapshot['vessels']])
                prior={r['mmsi']:json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload'] for r in rows}
                accepted=[];quarantine=[]
                for v in sorted(snapshot['vessels'],key=lambda v:v['observedAt']):
                    old=prior.get(v['mmsi'])
                    if old and suspect_jump(old,v):
                        quarantine.append((v['mmsi'],parse_date(v['observedAt']),'speed_jump_over_100_kmh',json.dumps(v)));continue
                    accepted.append(v)
                    if not old or parse_date(v['observedAt'])>parse_date(old['observedAt']):prior[v['mmsi']]=v
                if quarantine:await conn.executemany('INSERT INTO observation_quarantine(mmsi,observed_at,reason,payload) VALUES($1,$2,$3,$4::jsonb) ON CONFLICT DO NOTHING',quarantine)
                if not accepted:return sid
                await conn.executemany('''INSERT INTO vessel(mmsi,name,kind,destination,metadata_at) VALUES($1,$2,$3,$4,$5)
                    ON CONFLICT(mmsi) DO UPDATE SET name=EXCLUDED.name,kind=EXCLUDED.kind,destination=EXCLUDED.destination,metadata_at=EXCLUDED.metadata_at
                    WHERE vessel.metadata_at IS NULL OR EXCLUDED.metadata_at>=vessel.metadata_at''',[(v['mmsi'],v['name'],v['kind'],v['destination'],parse_date(v.get('metadataAt'))) for v in accepted])
                archived=accepted
                if hourly:
                    # Source-hour identity survives process restarts. Latest state
                    # can refresh independently without growing the track archive.
                    hours=await conn.fetch("SELECT mmsi,date_trunc('hour',observed_at AT TIME ZONE 'UTC') AS hour FROM observation WHERE mmsi=ANY($1::bigint[]) AND observed_at>=now()-interval '25 hours'",[v['mmsi'] for v in accepted])
                    seen={(r['mmsi'],r['hour']) for r in hours};archived=[]
                    for v in accepted:
                        key=(v['mmsi'],parse_date(v['observedAt']).astimezone(timezone.utc).replace(minute=0,second=0,microsecond=0,tzinfo=None))
                        if key not in seen:archived.append(v);seen.add(key)
                    encoded=json.dumps({'source':'AISStream','messages':archived},sort_keys=True,separators=(',',':'))
                    digest=hashlib.sha256(encoded.encode()).hexdigest()
                if archived:
                    sid=await conn.fetchval('INSERT INTO raw_snapshot(source,payload,payload_sha256) VALUES($1,$2::jsonb,$3) ON CONFLICT(payload_sha256) DO UPDATE SET payload_sha256=EXCLUDED.payload_sha256 RETURNING id',snapshot.get('source','digitraffic'),encoded,digest)
                    await conn.executemany('''INSERT INTO observation(mmsi,observed_at,position,speed_knots,course_degrees,snapshot_id)
                    VALUES($1,$2,ST_SetSRID(ST_MakePoint($3,$4),4326)::geography,$5,$6,$7) ON CONFLICT(mmsi,observed_at) DO NOTHING''',[(v['mmsi'],parse_date(v['observedAt']),v['longitude'],v['latitude'],v['speed'],v['course'],sid) for v in archived])
                await conn.executemany('''INSERT INTO latest_position(mmsi,observed_at,position,payload)
                    VALUES($1,$2,ST_SetSRID(ST_MakePoint($3,$4),4326)::geography,$5::jsonb)
                    ON CONFLICT(mmsi) DO UPDATE SET observed_at=excluded.observed_at,position=excluded.position,payload=excluded.payload
                    WHERE excluded.observed_at>latest_position.observed_at''',[(v['mmsi'],parse_date(v['observedAt']),v['longitude'],v['latitude'],json.dumps(v)) for v in accepted])
        return sid
    async def save_scenario(self,mmsi,version,assumptions,result):
        return await self.pool.fetchval('INSERT INTO scenario_run(mmsi,model_version,assumptions,result) VALUES($1,$2,$3::jsonb,$4::jsonb) RETURNING id',mmsi,version,json.dumps(assumptions),json.dumps(result))
