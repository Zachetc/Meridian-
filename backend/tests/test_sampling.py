from copy import deepcopy
from meridian.sampling import PassageSampler
from meridian.traffic import PASSAGES

def vessel(mmsi=230000001, passage='chokepoint6', stamp='2026-10-26T12:01:23Z'):
    p=PASSAGES[passage]
    return dict(mmsi=mmsi,kind='Cargo',longitude=p['longitude'],latitude=p['latitude'],observedAt=stamp)

def test_independent_quota_for_every_passage():
    s=PassageSampler()
    for index,p in enumerate(PASSAGES):
        for j in range(10):assert s.accept(vessel(230000000+index*100+j,p))
        assert not s.accept(vessel(230000099+index*100,p))
    assert len(s.members)==28
    assert all(len(ids)==10 for ids in s.members.values())

def test_followed_ship_bypasses_area_and_quota_without_changing_ping():
    s=PassageSampler();s.watched={230000001}
    v=dict(vessel(),longitude=-140,latitude=0)
    original=deepcopy(v)
    assert s.accept(v) and v==original
    assert not s.accept(v)
    assert s.accept(dict(v,observedAt='2026-10-26T12:02:10Z'))
    assert not s.accept(dict(v,mmsi=230000002))

def test_source_minute_throttling_and_hour_rotation():
    s=PassageSampler(limit=1)
    assert s.accept(vessel())
    assert not s.accept(vessel(stamp='2026-10-26T12:01:59Z'))
    assert not s.accept(vessel(230000002))
    assert s.accept(vessel(230000002,stamp='2026-10-26T13:00:09Z'))
    assert not s.accept(vessel(stamp='2026-10-26T12:59:59Z'))
    assert not s.accept(dict(vessel(),kind='Fishing'))
