import asyncio
from loguru import logger
from typing import Literal, Any
from aiohttp import ClientSession, ClientConnectorError


async def aiohttp_request(
    session:ClientSession, 
    method:Literal['GET', 'POST'],
    url:str, 
    params:dict=None,
    post_data:Any=None, 
    retry:int=0
):
    if retry > 3:
        return {}
    try:
        async with session.request(method, url, params=params, data=post_data) as resp:
            text = await resp.text()
            if resp.status == 200:
                return text
            else:
                logger.debug(f"url: {url}, status: {resp.status}")
                asyncio.sleep(retry+1)
                return await aiohttp_request(session, method, url, params, post_data, retry+1)
    except (ClientConnectorError, TimeoutError):
        logger.warning(f'url: {url}, data: {post_data}')
        await asyncio.sleep(2)
        return await aiohttp_request(session, method, url, params, post_data, retry+1)
    except:
        logger.exception("aiohttp_request出现异常")
        return None