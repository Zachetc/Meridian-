"""One supervised API + optional continuous collector process for a container host."""
import asyncio,os,logging
import uvicorn
from .migrate import migrate
async def serve():
    await migrate()
    server=uvicorn.Server(uvicorn.Config('meridian.api:app',host='0.0.0.0',port=int(os.getenv('PORT','8000')),log_level='info'))
    collector=None
    if os.getenv('RUN_COLLECTOR')=='1':
        if not os.getenv('AISSTREAM_API_KEY'):raise RuntimeError('Set AISSTREAM_API_KEY before enabling RUN_COLLECTOR')
        if os.getenv('AIS_PROVIDER')!='aisstream':raise RuntimeError('RUN_COLLECTOR requires AIS_PROVIDER=aisstream')
        from .collector import main
        collector=asyncio.create_task(main())
    api=asyncio.create_task(server.serve())
    try:
        if collector:
            done,_=await asyncio.wait([api,collector],return_when=asyncio.FIRST_COMPLETED)
            for task in done:task.result()
        else:await api
    finally:
        server.should_exit=True
        if collector:
            collector.cancel()
            await asyncio.gather(collector,return_exceptions=True)
        await api
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
