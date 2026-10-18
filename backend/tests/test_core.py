from dataclasses import replace
import pytest
from meridian.model import Assumptions,CostModel
from meridian.graph import MaritimeNetwork
from meridian.ingestion import normalize

def test_hormuz_closure_is_disconnection_not_a_route_around_the_gulf():
    n=MaritimeNetwork()
    assert n.route('Gulf','Rotterdam')['connected']
    assert not n.route('Gulf','Rotterdam',['Hormuz'])['connected']

def test_suez_closure_changes_shortest_path():
    n=MaritimeNetwork();base=n.route('East Asia','Rotterdam');closed=n.route('East Asia','Rotterdam',['Suez'])
    assert 'Suez' in base['path']
    assert 'Cape of Good Hope' in closed['path']
    assert closed['illustrativeDays']>base['illustrativeDays']

def test_unknown_node_rejected():
    with pytest.raises(ValueError):MaritimeNetwork().route('Atlantis','Gulf')

def test_zero_cost_and_conservation():
    a=Assumptions();m=CostModel();r=m.run(a)
    assert r['supplier']+r['passed']==pytest.approx(r['expected'])
    assert m.run(replace(a,likelihood=0))['expected']==0
    assert m.run(replace(a,delayHours=0))['expected']==0
    assert r==m.run(a)

def test_feed_filters_invalid_types_and_missing_external_timestamp():
    now=1792152000000
    metadata=[dict(mmsi=123456789,name='TEST',shipType=70,timestamp=now)]
    f=dict(mmsi=123456789,geometry=dict(coordinates=[24,60]),properties=dict(timestamp=42,sog=102.3,cog=360))
    assert normalize({'features':[f]},metadata,now)['rejected']==1
    f['properties']['timestampExternal']=now
    result=normalize({'features':[f,f]},metadata,now)
    assert len(result['vessels'])==1
    assert result['vessels'][0]['speed'] is None
    metadata[0]['shipType']=35
    assert not normalize({'features':[f]},metadata,now)['vessels']
