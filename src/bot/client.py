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
        self.token = token
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
        return {"Authorization": f"Bot {self.token}"}
    
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
    
    async def _connect(self):
        """连接 WebSocket"""
        gateway = await self._get_gateway()
        logger.info(f"连接网关: {gateway}")
        
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
