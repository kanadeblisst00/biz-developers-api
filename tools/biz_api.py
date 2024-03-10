import os
import json
import time
import aiohttp
import aiofiles
from loguru import logger
from hashlib import md5
from .request import aiohttp_request


class BizApi:
    def __init__(self, appid:str, secret:str, aes_key:str=None) -> None:
        self.appid = appid
        self.secret = secret
        self.aes_key = aes_key
        client_timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=client_timeout)
        curdir = os.path.dirname(os.path.dirname(__file__))
        self.access_token_data = {}
        self.access_token_file = os.path.join(curdir, "log", md5(f"{appid}{secret}".encode()).hexdigest() + '.json')
    
    async def close(self):
        self.session.close()

    async def get_access_token(self):
        if self.access_token_data and self.access_token_data.get("expires_at", 0) > int(time.time()):
            return self.access_token_data
        if not os.path.exists(self.access_token_file):
            return await self.get_access_token_from_net()
        else:
            return await self.get_access_token_from_file()
        
    async def get_access_token_from_net(self):
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }
        text = await aiohttp_request(self.session, "GET", url, params=params)
        if text:
            data = json.loads(text)
            if data.get("access_token"):
                async with aiofiles.open(self.access_token_file, 'w', encoding='utf-8') as fw:
                    await fw.write(text)
                self.access_token_data = data
                return data
            else:
                logger.warning(f"获取access_token失败,响应内容: {text}！")
        else:
            logger.warning("获取access_token时请求失败！")

    async def get_access_token_from_file(self):
        async with aiofiles.open(self.access_token_file, 'r') as f:
            access_token_str = await f.read()
            data = json.loads(access_token_str)
            if data.get("expires_at", 0) > int(time.time()):
                self.access_token_data = data
                return data
        return await self.get_access_token_from_net()
    
    async def upload_tmp_image(self, image_path:str):
        '''图片仅支持jpg/png格式，大小必须在1MB以下'''
        token_data = await self.get_access_token()
        if not token_data:
            return
        if not os.path.exists(image_path):
            logger.info(f"给定图片路径({image_path})不存在")
            return
        if not image_path.endswith(".jpg") and not image_path.endswith(".png"):
            logger.info(f"给定的图片不是jpg/png后缀")
            return
        if os.path.getsize(image_path) >= 1024 * 1024:
            return await self.upload_media("image", image_path)
        access_token = token_data["access_token"]
        url = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
        params = {
            "access_token": access_token
        }
        post_data = aiohttp.FormData()
        post_data.add_field('file',
                    open(image_path, 'rb'),
                    filename=os.path.basename(image_path),
                    content_type=f'image/{image_path[-3:]}')
        text = await aiohttp_request(self.session, "POST", url, params=params, post_data=post_data)
        logger.debug(text)
        data = json.loads(text)
        return data.get('url')
    
    async def upload_tmp_media(self, media_type:str, media_path:str):
        '''未通过企业认证的订阅号没有上传临时素材的权限'''
        token_data = await self.get_access_token()
        if not token_data:
            return
        if not os.path.exists(media_path):
            logger.info(f"给定文件路径({media_path})不存在")
            return
        access_token = token_data["access_token"]
        url = "https://api.weixin.qq.com/cgi-bin/media/upload"
        params = {
            "access_token": access_token,
            "type": media_type
        }
        post_data = aiohttp.FormData()
        if media_type == "image":
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'image/{media_path[-3:]}')
        elif media_type == "voice": #2M，播放长度不超过60s，mp3/wma/wav/amr格式
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'audio/mp3')
        elif media_type == "video": # 10MB，支持MP4格式
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'video/mp4')
        text = await aiohttp_request(self.session, "POST", url, params=params, post_data=post_data)
        logger.debug(text)
        data = json.loads(text)
        return data
    
    async def upload_media(self, media_type:str, media_path:str, title=None, introduction=None):
        '''上传视频时需要title和introduction'''
        token_data = await self.get_access_token()
        if not token_data:
            return
        if not os.path.exists(media_path):
            logger.info(f"给定文件路径({media_path})不存在")
            return
        access_token = token_data["access_token"]
        url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
        params = {
            "access_token": access_token,
            "type": media_type
        }
        post_data = aiohttp.FormData()
        if media_type == "image":
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'image/{media_path[-3:]}')
        elif media_type == "voice": #2M，播放长度不超过60s，mp3/wma/wav/amr格式
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'audio/mp3')
        elif media_type == "video": # 10MB，支持MP4格式
            if not title or not introduction:
                logger.warning("上传视频需指定标题和简介")
                return
            post_data.add_field('file',
                        open(media_path, 'rb'),
                        filename=os.path.basename(media_path),
                        content_type=f'video/mp4')
            post_data.add_field("description", json.dumps({"title": title, "introduction": introduction}))
        text = await aiohttp_request(self.session, "POST", url, params=params, post_data=post_data)
        logger.debug(text)
        data = json.loads(text)
        return data
    
    async def reply(self, _type:str, request_data:dict, **kwargs):
        '''回复消息，回复图片、语音或视频时需先上传到素材
        _type取值有: "text"、"image"、"voice"、"video"、"articles"
        request_data为请求数据
        '''
        touser = kwargs.get("touser") or request_data["FromUserName"]
        data = {
            "ToUserName": touser,
            "FromUserName": request_data["ToUserName"],
            "CreateTime": int(time.time())
        }
        extra_data = await getattr(self, f"reply_{_type}")(**kwargs)
        data.update(extra_data)
        return {"xml": data}
    
    async def reply_text(self, **kwargs):
        data = {
            "MsgType": "text",
            "Content": kwargs["text"]
        }
        return data
    
    async def reply_image(self, **kwargs):
        media_id = kwargs.get("media_id")
        media_type = "image"
        if not media_id:
            path = kwargs["path"]
            media_data = await self.upload_media(media_type, path)
            media_id = media_data["media_id"]
        data = {
            "MsgType": media_type,
            "Image": {'MediaId': media_id}
        }
        return data
    
    async def reply_voice(self, **kwargs):
        media_id = kwargs.get("media_id")
        media_type = "voice"
        if not media_id:
            path = kwargs["path"]
            media_data = await self.upload_media(media_type, path)
            media_id = media_data["media_id"]
        data = {
            "MsgType": media_type,
            "Voice": {'MediaId': media_id}
        }
        return data
    
    async def reply_video(self, **kwargs):
        media_id = kwargs.get("media_id")
        media_type = "video"
        title = kwargs["title"]
        introduction = kwargs["introduction"]
        if not media_id:
            path = kwargs["path"]
            media_data = await self.upload_media(media_type, path, title=title, introduction=introduction)
            media_id = media_data["media_id"]
        data = {
            "MsgType": media_type,
            "Video": {
                "Title": title,
                "Description": introduction,
                'MediaId': media_id
            }
        }
        return data
    
    async def reply_articles(self, **kwargs):
        data = {
            "MsgType": "news",
            "ArticleCount": 1,
            "Articles": {
                "item": {
                    "Title": kwargs["title"],
                    "Description": kwargs["description"],
                    'PicUrl': None,
                    "Url": kwargs["url"]
                }
            }
        }
        return data
    
    async def get_callback_whitelist(self):
        '''获取微信发送数据过来的ip列表'''
        token_data = await self.get_access_token()
        if not token_data:
            return
        access_token = token_data["access_token"]
        url = "https://api.weixin.qq.com/cgi-bin/getcallbackip"
        params = {
            "access_token": access_token,
        }
        text = await aiohttp_request(self.session, "GET", url, params=params)
        logger.debug(text)
        data = json.loads(text)
        return data.get("ip_list", [])
    
    async def get_api_whitelist(self):
        '''获取api.weixin.qq.com的ip列表'''
        token_data = await self.get_access_token()
        if not token_data:
            return
        access_token = token_data["access_token"]
        url = "https://api.weixin.qq.com/cgi-bin/get_api_domain_ip"
        params = {
            "access_token": access_token,
        }
        text = await aiohttp_request(self.session, "GET", url, params=params)
        logger.debug(text)
        data = json.loads(text)
        return data.get("ip_list", [])
