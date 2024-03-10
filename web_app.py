import sys
import os
import asyncio
import settings
from loguru import logger
from aiohttp import web
from tools.biz_api import BizApi
from tools.render_view import RenderApiView
from aiohttp.web import Application
from middleware.verify import VerifyMiddleware
from middleware.whitelist import whitelist_middleware

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def on_startup_tasks(app: Application):
    app["ba"] = BizApi(settings.APPID, settings.SECRET, getattr(settings, "AES_key", None))


async def on_cleanup_tasks(app: Application):
    await app["ba"].close()

def init_app():
    logger.remove(handler_id=None)
    os.makedirs("log", exist_ok=True)
    logger.add(sys.stdout,  level="INFO")
    logger.add("log/web_app.log",  level="DEBUG", compression="zip", rotation="1 days")
    
    middlewares=[whitelist_middleware, VerifyMiddleware(settings.TOKEN)]
    app = web.Application(middlewares=middlewares)
    app.router.add_view('/WeChatBizServer', RenderApiView)
    app.on_startup.append(on_startup_tasks)
    app.on_cleanup.append(on_cleanup_tasks)
    return app

    
if __name__ == "__main__":
    app = init_app()
    port = settings.API_PORT
    loop = asyncio.get_event_loop()
    web.run_app(app, port=port, loop=loop)
    