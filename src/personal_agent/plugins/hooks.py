"""
Hook System - 钩子系统

支持在关键节点插入自定义逻辑
"""
import asyncio
from typing import Any, Callable, Dict, List

from loguru import logger


class HookSystem:
    """钩子系统"""

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, event: str, handler: Callable) -> None:
        """
        注册钩子

        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
        logger.debug(f"Hook registered: {event}")

    def unregister(self, event: str, handler: Callable) -> bool:
        """注销钩子"""
        if event in self._hooks and handler in self._hooks[event]:
            self._hooks[event].remove(handler)
            return True
        return False

    async def trigger(self, event: str, *args, **kwargs) -> List[Any]:
        """
        触发钩子

        Args:
            event: 事件名称
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            List[Any]: 所有处理函数的返回值
        """
        results = []
        handlers = self._hooks.get(event, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook handler error for {event}: {e}")

        return results

    def clear(self, event: str = None):
        """清除钩子"""
        if event:
            self._hooks.pop(event, None)
        else:
            self._hooks.clear()


# 预定义的事件常量
class HookEvents:
    """预定义钩子事件"""

    # Agent 生命周期
    AGENT_INIT = "agent:init"
    AGENT_SHUTDOWN = "agent:shutdown"

    # 消息处理
    MESSAGE_RECEIVE = "message:receive"
    MESSAGE_BEFORE_PROCESS = "message:before_process"
    MESSAGE_AFTER_PROCESS = "message:after_process"
    MESSAGE_SEND = "message:send"

    # LLM 调用
    LLM_BEFORE_CALL = "llm:before_call"
    LLM_AFTER_CALL = "llm:after_call"

    # 工具执行
    TOOL_BEFORE_EXECUTE = "tool:before_execute"
    TOOL_AFTER_EXECUTE = "tool:after_execute"

    # 记忆管理
    MEMORY_BEFORE_STORE = "memory:before_store"
    MEMORY_AFTER_STORE = "memory:after_store"
    MEMORY_BEFORE_RECALL = "memory:before_recall"
    MEMORY_AFTER_RECALL = "memory:after_recall"


# 全局钩子系统实例
hook_system = HookSystem()
