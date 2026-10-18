"""Server-side AISStream decoding. Missing/invalid event times never become 'now'."""
import re,time
from collections import OrderedDict
from datetime import datetime,timezone
from .ingestion import normalize

def event_ms(meta):
    value=meta.get('time_utc')
    if not isinstance(value,str):return None
    match=re.match(r'^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?',value)
    if not match:return None
    try:
        date=f'{match[1]}T{match[2]}.{(match[3] or "0")[:6]:0<6}+00:00'
        return datetime.fromisoformat(date).timestamp()*1000
    except ValueError:return None

class StreamDecoder:
    """Bounded LRU metadata and one pending position per MMSI until identity arrives."""
    def __init__(self,limit=100000):
        self.metadata=OrderedDict();self.pending=OrderedDict();self.limit=limit
        self.rejected=0;self.evicted=0
    def _put(self,cache,key,value):
        cache[key]=value;cache.move_to_end(key)
        if len(cache)>self.limit:cache.popitem(last=False);self.evicted+=1
    def decode(self,envelope,now_ms=None):
        now_ms=time.time()*1000 if now_ms is None else now_ms
        meta=envelope.get('MetaData') or {};mmsi=meta.get('MMSI');ms=event_ms(meta)
        kind=envelope.get('MessageType');message=(envelope.get('Message') or {}).get(kind) or {}
        if not isinstance(mmsi,int) or not ms or not now_ms-86400000<=ms<=now_ms+300000:
            self.rejected+=1;return None
        if kind=='ShipStaticData':
            if message.get('Valid') is False:return None
            previous=self.metadata.get(mmsi)
            if previous and previous['timestamp']>=ms:return None
            record=dict(mmsi=mmsi,name=message.get('Name') or meta.get('ShipName'),shipType=message.get('Type'),destination=message.get('Destination'),timestamp=ms)
            self._put(self.metadata,mmsi,record)
            if mmsi in self.pending:return self._normalize(mmsi,self.pending.pop(mmsi),now_ms)
            return None
        if kind not in ['PositionReport','StandardClassBPositionReport','ExtendedClassBPositionReport'] or message.get('Valid') is False:return None
        feature=dict(mmsi=mmsi,geometry={'coordinates':[message.get('Longitude',meta.get('longitude',meta.get('Longitude'))),message.get('Latitude',meta.get('latitude',meta.get('Latitude')))]},properties=dict(timestampExternal=ms,sog=message.get('Sog'),cog=message.get('Cog')))
        if mmsi not in self.metadata:
            previous=self.pending.get(mmsi)
            if not previous or previous['properties']['timestampExternal']<ms:self._put(self.pending,mmsi,feature)
            return None
        return self._normalize(mmsi,feature,now_ms)
    def _normalize(self,mmsi,feature,now_ms):
        result=normalize({'features':[feature]},[self.metadata[mmsi]],now_ms)
        self.rejected+=result['rejected']
        if not result['vessels']:return None
        v=result['vessels'][0];v['source']='AISStream';return v
