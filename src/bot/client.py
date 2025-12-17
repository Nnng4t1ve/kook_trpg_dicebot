"""KOOK WebSocket 客户端"""
import asyncio
import json
import zlib
import aiohttp
from typing import Callable, Optional
from loguru import logger


class KookClient:
    """KOOK WebSocket 客户端"""
    
    def __init__(self, token: str, api_base: str = "https://www.kookapp.cn/api/v3"):
        self._token = token  # 使用私有属性存储 token
        self.api_base = api_base
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._sn = 0
        self._session_id: Optional[str] = None
        self._running = False
        self._message_handler: Optional[Callable] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bot {self._token}"}
    
    def __repr__(self) -> str:
        """安全的字符串表示，不暴露 token"""
        return f"KookClient(api_base={self.api_base!r}, connected={self._ws is not None and not self._ws.closed})"
    
    def __str__(self) -> str:
        """安全的字符串表示"""
        return self.__repr__()
    
    async def start(self, message_handler: Callable):
        """启动客户端"""
        self._message_handler = message_handler
        self._session = aiohttp.ClientSession()
        self._running = True
        
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"连接错误: {e}")
                if self._running:
                    await asyncio.sleep(5)
    
    async def stop(self):
        """停止客户端"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()

    async def _get_gateway(self) -> str:
        """获取 WebSocket 网关地址"""
        async with self._session.get(
            f"{self.api_base}/gateway/index",
            headers=self.headers,
            params={"compress": 1}
        ) as resp:
            data = await resp.json()
            if data["code"] != 0:
                raise Exception(f"获取网关失败: {data['message']}")
            return data["data"]["url"]
    
    def _mask_gateway_url(self, url: str) -> str:
        """掩码网关 URL 中的 token 参数"""
        if "token=" in url:
            # 只显示 URL 的基础部分，隐藏 token
            base_url = url.split("token=")[0]
            return f"{base_url}token=****"
        return url
    
    async def _connect(self):
        """连接 WebSocket"""
        gateway = await self._get_gateway()
        logger.info(f"连接网关: {self._mask_gateway_url(gateway)}")
        
        async with self._session.ws_connect(gateway) as ws:
            self._ws = ws
            
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    data = json.loads(zlib.decompress(msg.data))
                    await self._handle_signal(data)
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_signal(data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket 错误: {ws.exception()}")
                    break
    
    async def _handle_signal(self, data: dict):
        """处理信令"""
        signal = data.get("s")
        
        if signal == 0:  # EVENT
            sn = data.get("sn", 0)
            if sn > self._sn:
                self._sn = sn
                if self._message_handler:
                    await self._message_handler(data.get("d", {}))
        
        elif signal == 1:  # HELLO
            d = data.get("d", {})
            if d.get("code") == 0:
                self._session_id = d.get("session_id")
                logger.info(f"连接成功, session_id: {self._session_id}")
                self._heartbeat_task = asyncio.create_task(self._heartbeat())
            else:
                logger.error(f"连接失败: {d}")
        
        elif signal == 3:  # PONG
            logger.debug("收到 PONG")
        
        elif signal == 5:  # RECONNECT
            logger.warning("收到重连信令")
            self._sn = 0
            self._session_id = None
            if self._ws:
                await self._ws.close()
    
    async def _heartbeat(self):
        """心跳"""
        while self._running and self._ws and not self._ws.closed:
            try:
                await self._ws.send_json({"s": 2, "sn": self._sn})
                logger.debug(f"发送 PING, sn={self._sn}")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"心跳错误: {e}")
                break
    
    async def send_message(self, target_id: str, content: str, 
                          msg_type: int = 9, quote: str = None) -> dict:
        """发送频道消息"""
        payload = {
            "type": msg_type,
            "target_id": target_id,
            "content": content
        }
        if quote:
            payload["quote"] = quote
        
        async with self._session.post(
            f"{self.api_base}/message/create",
            headers=self.headers,
            json=payload
        ) as resp:
            return await resp.json()
    
    async def send_direct_message(self, target_id: str, content: str,
                                  msg_type: int = 9) -> dict:
        """发送私聊消息"""
        payload = {
            "type": msg_type,
            "target_id": target_id,
            "content": content
        }
        
        async with self._session.post(
            f"{self.api_base}/direct-message/create",
            headers=self.headers,
            json=payload
        ) as resp:
            return await resp.json()

    async def upload_asset(self, file_data: bytes, filename: str = "image.png") -> str | None:
        """
        上传媒体文件到 KOOK
        
        Args:
            file_data: 文件二进制数据
            filename: 文件名
        
        Returns:
            上传成功返回 URL，失败返回 None
        """
        import aiohttp
        
        form = aiohttp.FormData()
        form.add_field("file", file_data, filename=filename, content_type="image/png")
        
        async with self._session.post(
            f"{self.api_base}/asset/create",
            headers=self.headers,
            data=form
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("url")
            logger.error(f"上传文件失败: {data}")
            return None

    async def delete_message(self, msg_id: str) -> bool:
        """
        删除频道消息
        
        Args:
            msg_id: 消息 ID
        
        Returns:
            是否删除成功
        """
        async with self._session.post(
            f"{self.api_base}/message/delete",
            headers=self.headers,
            json={"msg_id": msg_id}
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return True
            logger.error(f"删除消息失败: {data}")
            return False

    async def pin_message(self, msg_id: str, channel_id: str) -> bool:
        """
        置顶频道消息
        
        Args:
            msg_id: 消息 ID
            channel_id: 频道 ID
        
        Returns:
            是否置顶成功
        """
        async with self._session.post(
            f"{self.api_base}/message/pin",
            headers=self.headers,
            json={"msg_id": msg_id, "target_id": channel_id}
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return True
            logger.error(f"置顶消息失败: {data}")
            return False

    async def unpin_message(self, msg_id: str, channel_id: str) -> bool:
        """
        取消置顶频道消息
        
        Args:
            msg_id: 消息 ID
            channel_id: 频道 ID
        
        Returns:
            是否取消成功
        """
        async with self._session.post(
            f"{self.api_base}/message/unpin",
            headers=self.headers,
            json={"msg_id": msg_id, "target_id": channel_id}
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return True
            logger.error(f"取消置顶失败: {data}")
            return False

    async def get_friend_requests(self) -> list[dict]:
        """
        获取好友申请列表
        
        Returns:
            好友申请列表，每项包含 id, friend_info 等
        """
        # KOOK API: GET /api/v3/friend?type=request
        async with self._session.get(
            f"{self.api_base}/friend",
            headers=self.headers,
            params={"type": "request"},
        ) as resp:
            data = await resp.json()
            logger.debug(f"好友申请响应: {data}")
            if data.get("code") == 0:
                return data.get("data", {}).get("request", [])
            logger.error(f"获取好友申请失败: {data}")
            return []

    async def handle_friend_request(self, request_id: int, accept: bool = True) -> bool:
        """
        处理好友申请
        
        Args:
            request_id: 好友申请的 ID（不是用户 ID）
            accept: True 同意，False 拒绝
        
        Returns:
            是否操作成功
        """
        # KOOK API: POST /api/v3/friend/handle-request
        async with self._session.post(
            f"{self.api_base}/friend/handle-request",
            headers=self.headers,
            json={"id": request_id, "accept": 1 if accept else 0},
        ) as resp:
            data = await resp.json()
            logger.debug(f"处理好友申请响应: {data}")
            if data.get("code") == 0:
                return True
            logger.error(f"处理好友申请失败: {data}")
            return False
