import asyncio,json
from datetime import datetime,timezone,timedelta
import pytest
from meridian.traffic import area_filter,TrafficReader,PASSAGES
from meridian.store import suspect_jump

def test_spatial_scope_and_follow_identity_are_separate():
    clause,params=area_filter('chokepoint6')
    assert 'ST_DWithin' in clause and params[0]==PASSAGES['chokepoint6']['longitude']
    assert area_filter('chokepoint6',230000001)==('mmsi=$1',[230000001])
    assert area_filter('Global')==('FALSE',[])
    with pytest.raises(ValueError):area_filter('unknown')

def test_fast_jump_is_quarantined_without_mutating_positions():
    a=dict(latitude=60,longitude=24,observedAt='2026-10-18T01:00:00Z')
    b=dict(latitude=25,longitude=56,observedAt='2026-10-18T01:01:00Z')
    assert suspect_jump(a,b)
    assert b['latitude']==25
    assert not suspect_jump(a,dict(a,observedAt='2026-10-18T01:01:00Z'))

def test_query_is_bounded_and_keeps_stale_followed_positions():
    class Pool:
        def __init__(self):self.queries=[]
        async def fetchval(self,query,*args):self.queries.append((query,args));return 1
        async def fetch(self,query,*args):
            self.queries.append((query,args))
            return [dict(payload=json.dumps(dict(mmsi=230000001,name='Fixture',longitude=-110,latitude=-25)),observed_at=datetime.now(timezone.utc)-timedelta(days=2))]
    async def run():
        p=Pool();r=TrafficReader(p)
        async def summary():return dict(total=1,globalConnected=False)
        r.summary=summary
        d=await r.query('chokepoint6',mmsi=230000001)
        assert d['vessels'][0]['longitude']==-110
        assert all('ST_DWithin' not in sql and "interval '24 hours'" not in sql for sql,args in p.queries)
        assert p.queries[-1][1][-1]==501
        with pytest.raises(ValueError):await r.query(limit=501)
    asyncio.run(run())

def test_history_cursor_excludes_newer_points_and_is_bounded():
    class Pool:
        async def fetch(self,query,*args):
            assert 'observed_at<$2' in query and args[-1]==1501
            assert args[1].tzinfo is not None
            return []
    async def run():
        r=TrafficReader(Pool());d=await r.history(230000001,'2026-10-18T01:00:00Z')
        assert d['points']==[] and d['nextBefore'] is None
        with pytest.raises(ValueError):await r.history(230000001,'2026-10-18T01:00:00')
    asyncio.run(run())
