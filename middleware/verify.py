import hashlib
from loguru import logger
from aiohttp import web
from aiohttp.web_request import Request


def VerifyMiddleware(biz_token):

    @web.middleware
    async def verify_middleware(request:Request, handler):
        query = request.query
        timestamp = query.get("timestamp")
        signature = query.get("signature") 
        nonce = query.get("nonce") 
        echostr = query.get("echostr") 
        
        if not timestamp or not signature or not nonce:
            logger.info(request.url)
            raise web.HTTPForbidden(
                reason='Invalid parameter',
            )
        
        sign_str = "".join(sorted([biz_token, nonce, timestamp])).encode()
        sign = hashlib.sha1(sign_str).hexdigest()
        if sign != signature:
            logger.info(request.url)
            raise web.HTTPForbidden(
                reason='Signature verification failed',
            )
        
        return await handler(request)
    
    return verify_middleware
