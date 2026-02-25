"""
WeChat Channel using itchat (web-based)
Note: Web WeChat has limitations, consider using WeChaty for production
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid

from .base import BaseChannel, IncomingMessage, OutgoingMessage, MessageHandler, MessageType

logger = logging.getLogger(__name__)

try:
    import itchat
    from itchat.content import TEXT, PICTURE, RECORDING
    ITCHAT_AVAILABLE = True
except ImportError:
    ITCHAT_AVAILABLE = False


class WeChatChannel(BaseChannel):
    name = "wechat"
    _instance = None

    def __init__(self, auto_login: bool = True, hot_reload: bool = True):
        if not ITCHAT_AVAILABLE:
            raise ImportError(
                "itchat is not installed. Install it with: pip install itchat"
            )

        self.auto_login = auto_login
        self.hot_reload = hot_reload
        self._running = False
        self._message_handlers: List[MessageHandler] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        WeChatChannel._instance = self

    async def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._running = True

        if self.auto_login:
            itchat.auto_login(
                hotReload=self.hot_reload,
                enableCmdQR=2,
                statusStorageDir="data/itchat.pkl"
            )

        itchat.set_logging(show=False)

        @itchat.msg_register([TEXT, PICTURE, RECORDING])
        def handle_message(msg):
            self._on_itchat_message(msg)

        await self._process_messages()

    async def _process_messages(self):
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                for handler in self._message_handlers:
                    try:
                        response = handler(msg)
                        if response:
                            await self.send(response)
                    except Exception as e:
                        logger.error(f"Handler error: {e}")
            except asyncio.TimeoutError:
                continue

    def _on_itchat_message(self, msg):
        try:
            message_type = MessageType.TEXT
            if msg["Type"] == "Picture":
                message_type = MessageType.IMAGE
            elif msg["Type"] == "Recording":
                message_type = MessageType.VOICE

            is_group = msg.get("isAt", False) or "@chat" in msg.get("FromUserName", "")

            incoming = IncomingMessage(
                message_id=str(uuid.uuid4()),
                sender_id=msg.get("FromUserName", ""),
                sender_name=msg.get("ActualNickName", msg.get("NickName", "Unknown")),
                content=msg.get("Text", ""),
                message_type=message_type,
                timestamp=datetime.now(),
                channel=self.name,
                raw_data=msg,
                is_group=is_group,
                group_id=msg.get("FromUserName") if is_group else None,
                is_mentioned=msg.get("isAt", False)
            )

            if self._loop and self._running:
                self._loop.call_soon_threadsafe(
                    self._message_queue.put_nowait, incoming
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def stop(self) -> None:
        self._running = False
        itchat.logout()

    async def send(self, message: OutgoingMessage) -> bool:
        try:
            receiver = message.receiver_id or message.reply_to

            if not receiver:
                return False

            if message.message_type == MessageType.TEXT:
                itchat.send(message.content, toUserName=receiver)
            elif message.message_type == MessageType.IMAGE:
                itchat.send_image(message.content, toUserName=receiver)
            elif message.message_type == MessageType.FILE:
                itchat.send_file(message.content, toUserName=receiver)

            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    def on_message(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    async def is_running(self) -> bool:
        return self._running

    def get_friends(self) -> List[Dict]:
        return itchat.get_friends(update=True)

    def get_groups(self) -> List[Dict]:
        return itchat.get_chatrooms(update=True)

    def search_friends(self, name: str) -> Optional[Dict]:
        return itchat.search_friends(name=name)

    def search_groups(self, name: str) -> Optional[Dict]:
        return itchat.search_chatrooms(name=name)
