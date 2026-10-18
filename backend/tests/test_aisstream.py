from meridian.aisstream import StreamDecoder,event_ms

NOW=1792238400000
TIME='2026-10-17 12:00:00.123456789 +0000 UTC'
def envelope(kind,data):return {'MessageType':kind,'MetaData':{'MMSI':123456789,'time_utc':TIME,'ShipName':'TEST CARGO'},'Message':{kind:data}}
def static(kind=70):return envelope('ShipStaticData',{'Type':kind,'Name':'TEST CARGO','Destination':'NL RTM','Valid':True})
def position():return envelope('PositionReport',{'Longitude':24,'Latitude':60,'Sog':12,'Cog':90,'Valid':True})
def test_missing_event_time_never_becomes_now():
    assert event_ms({}) is None
    d=StreamDecoder();p=position();p['MetaData'].pop('time_utc');assert d.decode(p,NOW) is None

def test_out_of_order_metadata_and_position_are_joined_without_fabricating_identity():
    d=StreamDecoder();assert d.decode(position(),NOW) is None
    result=d.decode(static(),NOW)
    assert result['kind']=='Cargo' and result['source']=='AISStream'
    assert result['observedAt']=='2026-10-17T12:00:00.123Z'

def test_only_commercial_types_pass_and_invalid_locations_are_rejected():
    for kind in [35,60,90]:
        d=StreamDecoder();d.decode(static(kind),NOW);assert d.decode(position(),NOW) is None
    d=StreamDecoder();d.decode(static(),NOW);p=position();p['Message']['PositionReport']['Longitude']=181
    assert d.decode(p,NOW) is None

def test_bounded_unknown_vessel_cache_records_eviction():
    d=StreamDecoder(limit=2)
    for mmsi in [123456789,123456788,123456787]:
        p=position();p['MetaData']['MMSI']=mmsi;d.decode(p,NOW)
    assert len(d.pending)==2 and d.evicted==1
