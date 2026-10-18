"""Async HTTP adapter, validation, hash-map joins and latest-event deduplication."""
import asyncio
import math
import random
import time
from datetime import datetime, timezone
from typing import Protocol
import httpx

BASE = 'https://meri.digitraffic.fi/api/ais/v1'
def iso(ms):
    return datetime.fromtimestamp(ms/1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def finite(x):
    return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)

class AISProvider(Protocol):
    async def fetch(self) -> tuple[dict,list]: ...

class DigitrafficProvider:
    def __init__(self,client: httpx.AsyncClient): self.client=client
    async def _get(self,path,from_ms):
        for attempt in range(3):
            try:
                response=await self.client.get(f'{BASE}/{path}',params={'from':from_ms},headers={'Digitraffic-User':'MeridianMaritime/0.1','Accept':'*/*'})
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException,httpx.NetworkError,httpx.HTTPStatusError) as exc:
                retryable=not isinstance(exc,httpx.HTTPStatusError) or exc.response.status_code in [429,500,502,503,504]
                if not retryable or attempt == 2: raise
                await asyncio.sleep(2**attempt + random.random()*.2)
    async def fetch(self):
        hour=int(time.time()//3600)*3600000
        positions,metadata=await asyncio.gather(self._get('locations',hour-24*3600000),self._get('vessels',hour-168*3600000))
        return positions,metadata

def normalize(locations,metadata,now_ms=None):
    now_ms=time.time()*1000 if now_ms is None else now_ms
    if not isinstance(locations,dict) or not isinstance(locations.get('features'),list) or not isinstance(metadata,list):
        raise ValueError('Invalid provider schema')
    by_id={}
    for m in metadata:
        if not isinstance(m,dict) or not finite(m.get('mmsi')): continue
        previous=by_id.get(m['mmsi'])
        if not previous or (m.get('timestamp') or 0) > (previous.get('timestamp') or 0): by_id[m['mmsi']]=m
    ships={}; rejected=0
    for f in locations['features']:
        p=f.get('properties') or {};mmsi=f.get('mmsi',p.get('mmsi'));xy=(f.get('geometry') or {}).get('coordinates') or []
        if not finite(mmsi) or not 100000000<=mmsi<=999999999:
            rejected+=1;continue
        m=by_id.get(mmsi);ship_type=m.get('shipType') if m else None
        if not finite(ship_type) or not 70<=ship_type<90:continue
        # AIS timestamp is a second-of-minute, NOT event time. Use timestampExternal only.
        ms=p.get('timestampExternal')
        if finite(ms) and ms<1e12:ms*=1000
        if len(xy)<2 or not all(finite(x) for x in xy[:2]) or abs(xy[0])>180 or abs(xy[1])>90 or not finite(ms) or not now_ms-86400000<=ms<=now_ms+300000:
            rejected+=1;continue
        clean=lambda s:s.replace('@','').strip() if isinstance(s,str) else ''
        v=dict(mmsi=int(mmsi),name=clean(m.get('name')) or f'MMSI {mmsi}',kind='Cargo' if ship_type<80 else 'Tanker',longitude=xy[0],latitude=xy[1],
               speed=p['sog'] if finite(p.get('sog')) and 0<=p['sog']<102.3 else None,
               course=p['cog'] if finite(p.get('cog')) and 0<=p['cog']<360 else None,
               shipType=int(ship_type),destination=clean(m.get('destination')) or 'Not reported',observedAt=iso(ms),metadataAt=iso(m['timestamp']) if finite(m.get('timestamp')) else None)
        if mmsi not in ships or ships[mmsi]['observedAt']<v['observedAt']: ships[mmsi]=v
    return dict(vessels=sorted(ships.values(),key=lambda v:v['observedAt'],reverse=True),retrievedAt=iso(now_ms),sourceUpdatedAt=locations.get('dataUpdatedTime'),source='Fintraffic / Digitraffic',coverage='Finnish AIS reception area · Baltic Sea',rejected=rejected)
