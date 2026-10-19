import asyncio
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import asdict
import asyncpg
import httpx
from fastapi import FastAPI,HTTPException,Header,Depends
from pydantic import BaseModel,Field,ConfigDict
from .ingestion import DigitrafficProvider,normalize
from .store import PostgresStore
from .model import Assumptions,CostModel
from .graph import MaritimeNetwork
from .traffic import TrafficReader

@asynccontextmanager
async def lifespan(app):
    if not os.environ.get('API_TOKEN'):raise RuntimeError('Set API_TOKEN before starting the service')
    pool=await asyncpg.create_pool(os.environ['DATABASE_URL'],min_size=1,max_size=5)
    client=httpx.AsyncClient(timeout=15,limits=httpx.Limits(max_connections=4))
    app.state.store=PostgresStore(pool);app.state.provider=DigitrafficProvider(client)
    app.state.lock=asyncio.Lock();app.state.traffic=TrafficReader(pool)
    yield
    await client.aclose();await pool.close()
app=FastAPI(title='Meridian Maritime API',version='0.5.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
async def authorize(authorization:str|None=Header(default=None)):
    expected='Bearer '+os.environ.get('API_TOKEN','')
    if not authorization or not secrets.compare_digest(authorization,expected):raise HTTPException(401,'Bearer token required')
@app.get('/health')
async def health():return {'status':'ok','modelVersion':CostModel.version}
@app.get('/vessels',dependencies=[Depends(authorize)])
async def vessels(watch:str=''):
    # Summary only: the browser requests a passage or MMSI separately.
    if os.environ.get('AIS_PROVIDER')=='aisstream':
        result=await app.state.traffic.query()
        ids=watch.split(',') if watch else []
        if len(ids)>500 or any(not x.isdigit() or len(x)!=9 for x in ids):raise HTTPException(400,'Invalid watched MMSIs')
        if ids:
            from .traffic import json_value
            rows=await app.state.store.pool.fetch("SELECT payload,observed_at FROM latest_position WHERE mmsi=ANY($1::bigint[]) AND observed_at>=now()-interval '24 hours'",[int(x) for x in ids])
            result['vessels']=[dict(json_value(r['payload']),observedAt=r['observed_at'].isoformat()) for r in rows]
        return result
    # Serialize writes; the provider performs its two reads concurrently.
    async with app.state.lock:
        try:
            positions,metadata=await app.state.provider.fetch()
            snapshot=normalize(positions,metadata)
            await app.state.store.save_snapshot({'locations':positions,'metadata':metadata},snapshot)
            return snapshot
        except (httpx.HTTPError,ValueError):raise HTTPException(502,'AIS provider unavailable or malformed')
class ScenarioInput(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    cargoValue:float=Field(default=2000000,ge=0,le=1e10)
    units:int=Field(default=10000,ge=1,le=1e9)
    delayHours:float=Field(default=48,ge=0,le=720)
    likelihood:float=Field(default=25,ge=0,le=100)
    dailyCost:float=Field(default=18000,ge=0,le=1e7)
    annualRate:float=Field(default=12,ge=0,le=100)
    passThrough:float=Field(default=50,ge=0,le=100)
    seed:int=Field(default=42,ge=0,le=4294967295)
@app.post('/scenarios',dependencies=[Depends(authorize)])
async def scenario(body:ScenarioInput):
    a=Assumptions(**body.model_dump());result=CostModel().run(a)
    sid=await app.state.store.save_scenario(None,CostModel.version,asdict(a),result)
    return {'id':sid,'modelVersion':CostModel.version,'result':result}
@app.get('/network',dependencies=[Depends(authorize)])
async def network(origin:str='Gulf',destination:str='Rotterdam',closed:str=''):
    try:return MaritimeNetwork().route(origin,destination,[x for x in closed.split(',') if x])
    except ValueError as e:raise HTTPException(422,str(e))

@app.get('/traffic',dependencies=[Depends(authorize)])
async def traffic(scope:str='Global',mmsi:int|None=None,after:int=0,limit:int=500):
    if os.environ.get('AIS_PROVIDER')!='aisstream':raise HTTPException(409,'Global collector mode is not enabled')
    try:return await app.state.traffic.query(scope,mmsi,after,limit)
    except ValueError as e:raise HTTPException(400,str(e))

@app.get('/history',dependencies=[Depends(authorize)])
async def observed_history(mmsi:int,before:str|None=None):
    if not 100000000<=mmsi<=999999999:raise HTTPException(400,'Invalid MMSI')
    try:return await app.state.traffic.history(mmsi,before)
    except ValueError as e:raise HTTPException(400,str(e))
