import xmltodict
from aiohttp.web import View
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from loguru import logger
from .biz_api import BizApi


class MsgType:
    text = "text"
    image = "image"
    voice = "voice"
    video = "video"
    shortvideo = "shortvideo"
    location = "location"
    link = "link"
    event = "event"


class RenderApiView(View):
    def __init__(self, request: Request) -> None:
        super().__init__(request)
        self.ba:BizApi = self.request.app["ba"]

    async def get(self):
        echostr = self.request.query.get("echostr")
        return Response(body=echostr, status=200)

    async def post(self) :
        '''POST请求'''
        if not self.request.can_read_body:
            raise web.HTTPForbidden(
                reason='Invalid post_data',
            )
        text = await self.request.text()
        request_data = xmltodict.parse(text)['xml']
        logger.debug(request_data)
        msg_type = request_data['MsgType']
        reply_func = getattr(self, f"reply_{msg_type}_msg")
        if not reply_func:
            body = "success"
        else:
            response_data = await reply_func(request_data)
            if response_data:
                body = xmltodict.unparse(response_data)
            else:
                body = "success"
        return Response(body=body, status=200, content_type="text/xml")

    async def reply_text_msg(self, request_data:dict):
        '''处理文本消息内容'''
        content = request_data["Content"]
        # 非事件消息都有msgid，可用于去重
        msgid = request_data["MsgId"]
        # 如果消息来自于公众号某篇文章，会携带下面两个字段
        msg_dataid = request_data.get("MsgDataId")
        # 第几篇
        idx = request_data.get("Idx")
        logger.info(f"公众号接收到文本消息, 消息内容: {content}")
        # 回复文本消息
        response_data = await self.ba.reply("text", request_data, text=content)
        return response_data
    
    async def reply_image_msg(self, request_data:dict):
        '''处理图片消息内容'''
        pic_url = request_data["PicUrl"]
        media_id = request_data["MediaId"]
        logger.info(f"公众号接收到图片消息, 图片链接: {pic_url}")
        response_data = await self.ba.reply("image", request_data, media_id=media_id)
        return response_data

    async def reply_voice_msg(self, request_data:dict):
        '''处理语音消息内容'''
        media_id = request_data["MediaId"]
        format = request_data["Format"]
        recognition = request_data["Recognition"]
        logger.info(f"公众号接收到语音消息")
        response_data = await self.ba.reply("voice", request_data, media_id=media_id)
        return response_data

    async def reply_video_msg(self, request_data:dict):
        '''处理视频消息内容'''
        media_id = request_data["MediaId"]
        # 视频消息缩略图的媒体id，可以调用多媒体文件下载接口拉取数据
        ThumbMediaId = request_data["ThumbMediaId"]
        logger.info(f"公众号接收到视频消息")
        # 测试这样发送视频失败
        response_data = await self.ba.reply("video", request_data, title="原视频", introduction="简介", media_id=media_id)
        return response_data
    
    async def reply_shortvideo_msg(self, request_data:dict):
        '''处理短视频消息内容'''
        pass

    async def reply_location_msg(self, request_data:dict):
        '''处理位置消息内容'''
        x = request_data["Location_X"]
        y = request_data["Location_Y"]
        scale = request_data["Scale"]
        label = request_data["Label"]
        logger.info(f"公众号接收到地理位置消息，地点: {label}")

    async def reply_link_msg(self, request_data:dict):
        '''处理链接消息内容'''
        title = request_data["Title"]
        description = request_data["Description"]
        url = request_data["Url"]
        logger.info(f"公众号接收到链接消息，链接地址: {url}")
        response_data = await self.ba.reply("articles", request_data, title=title, description=description, url=url)
        return response_data

    async def reply_event_msg(self, request_data:dict):
        '''处理事件消息内容: 订阅号的事件主要是关注和取关'''
        event = request_data["Event"]
        user = request_data["FromUserName"]
        if event == "subscribe": # 关注
            logger.info(f"用户({user})关注了公众号")
        elif event == "unsubscribe": # 取消关注
            logger.info(f"用户({user})取关了公众号")
