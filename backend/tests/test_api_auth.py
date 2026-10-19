import asyncio
import httpx
from meridian.api import app

def test_api_requires_token_and_does_not_publish_schema(monkeypatch):
    monkeypatch.setenv('API_TOKEN','test-only-secret')
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
            for path in ['/traffic','/history?mmsi=123456789','/vessels','/network']:
                assert (await c.get(path)).status_code==401
                assert (await c.get(path,headers={'Authorization':'Bearer wrong'})).status_code==401
            assert (await c.post('/scenarios',json={})).status_code==401
            for path in ['/docs','/redoc','/openapi.json']:assert (await c.get(path)).status_code==404
            assert (await c.get('/health')).status_code==200
    asyncio.run(run())
