"""
Message Bus - 智能体间消息总线
实现智能体间的异步通信
"""
import asyncio
from typing import Dict, List, Callable
from loguru import logger
from .base import Message


class MessageBus:
    """
    消息总线

    负责智能体间的消息路由和分发
    """

    def __init__(self):
        self._agents: Dict[str, asyncio.Queue] = {}  # 智能体消息队列
        self._subscribers: Dict[str, List[Callable]] = {}  # 消息订阅者
        self._running = False

    def register_agent(self, agent_name: str, queue: asyncio.Queue):
        """注册智能体"""
        self._agents[agent_name] = queue
        logger.info(f"✅ 智能体 '{agent_name}' 已注册到消息总线，当前注册: {list(self._agents.keys())}")

    def unregister_agent(self, agent_name: str):
        """注销智能体"""
        if agent_name in self._agents:
            del self._agents[agent_name]

    async def send_message(self, message: Message):
        """
        发送消息

        Args:
            message: 消息对象
        """
        logger.debug(f"📨 消息总线当前注册的智能体: {list(self._agents.keys())}")
        
        # 广播消息
        if message.to_agent == "*":
            for name, queue in self._agents.items():
                if name != message.from_agent:  # 不发送给自己
                    await queue.put(message)
                    logger.debug(f"📢 广播消息给 '{name}': {message.type}")

        # 发送给特定智能体
        elif message.to_agent in self._agents:
            await self._agents[message.to_agent].put(message)
            logger.debug(f"📨 消息已路由到 '{message.to_agent}': {message.type}")

        else:
            logger.warning(f"⚠️ 消息无法送达，智能体 '{message.to_agent}' 不存在")

    def subscribe(self, message_type: str, handler: Callable):
        """
        订阅特定类型的消息

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if message_type not in self._subscribers:
            self._subscribers[message_type] = []
        self._subscribers[message_type].append(handler)
        logger.info(f"📬 已订阅消息类型: {message_type}")

    async def broadcast(self, from_agent: str, message_type: str, content: str, data: Dict = None):
        """
        广播消息给所有智能体

        Args:
            from_agent: 发送者
            message_type: 消息类型
            content: 消息内容
            data: 附加数据
        """
        message = Message(
            from_agent=from_agent,
            to_agent="*",  # 广播
            type=message_type,
            content=content,
            data=data or {}
        )
        await self.send_message(message)


# 全局消息总线实例
message_bus = MessageBus()
