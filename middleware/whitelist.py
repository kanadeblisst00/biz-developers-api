import os
import time
import json
import aiofiles
from loguru import logger
from aiohttp import web
from aiohttp.web_request import Request


_wechat_ip_whitelist = []
curdir = os.path.dirname(os.path.dirname(__file__))

async def load_whitelist(ba):
    filename = os.path.join(curdir, "log", "whitelist_" + time.strftime("%Y%m%d"))
    if not os.path.exists(filename):
        whitelist = await ba.get_callback_whitelist()
        async with aiofiles.open(filename, 'w', encoding='utf-8') as fw:
            await fw.write(json.dumps(whitelist))
    else:
        if not os.path.getsize(filename):
            os.remove(filename)
            return await load_whitelist(ba)
        async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
            d = await f.read()
        try:
            whitelist = json.loads(d)
        except:
            os.remove(filename)
            return await load_whitelist(ba)
    logger.info(f"获取的白名单列表: {whitelist}")
    return whitelist

@web.middleware
async def whitelist_middleware(request:Request, handler):
    '''只允许微信服务器发过来的请求'''
    global _wechat_ip_whitelist
    if not _wechat_ip_whitelist:
        _wechat_ip_whitelist = await load_whitelist(request.app["ba"])
        
    remote = request.remote
    logger.debug(f"远程ip: {remote}")
    if remote not in _wechat_ip_whitelist:
        raise web.HTTPForbidden(
            reason='Invalid net parameter',
        )
    return await handler(request)

