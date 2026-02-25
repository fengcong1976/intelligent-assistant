"""
Plugin Base - 插件基类和接口定义
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginPriority(Enum):
    """插件优先级"""
    CRITICAL = 0    # 关键插件，必须执行
    HIGH = 1        # 高优先级
    NORMAL = 2      # 普通优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass
class PluginResult:
    """插件执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    plugin_name: str = ""


@dataclass
class PluginContext:
    """插件执行上下文"""
    task_id: str
    session_id: str
    user_id: str
    input_data: Any
    parameters: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default=None):
        return self.parameters.get(key, default)


class Plugin(ABC):
    """
    插件基类

    所有功能模块都继承此类，实现标准接口
    """
    # 插件元数据
    name: str = ""                          # 插件名称
    description: str = ""                   # 插件描述
    version: str = "1.0.0"                  # 版本号
    author: str = ""                        # 作者

    # 执行配置
    priority: PluginPriority = PluginPriority.NORMAL
    timeout: float = 30.0                   # 超时时间（秒）
    retry_count: int = 1                    # 重试次数
    concurrent_limit: int = 5               # 并发限制

    # 依赖配置
    dependencies: List[str] = []            # 依赖的其他插件
    required_permissions: List[str] = []    # 需要的权限

    def __init__(self):
        self._initialized = False
        self._config: Dict[str, Any] = {}

    async def initialize(self, config: Optional[Dict] = None) -> bool:
        """初始化插件"""
        try:
            self._config = config or {}
            await self._setup()
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Plugin {self.name} initialization failed: {e}")
            return False

    async def shutdown(self) -> bool:
        """关闭插件"""
        try:
            await self._cleanup()
            self._initialized = False
            return True
        except Exception as e:
            logger.warning(f"Plugin {self.name} shutdown failed: {e}")
            return False

    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """
        执行插件功能

        Args:
            context: 执行上下文

        Returns:
            PluginResult: 执行结果
        """
        pass

    async def validate(self, context: PluginContext) -> bool:
        """
        验证输入参数

        Returns:
            bool: 验证是否通过
        """
        return True

    async def _setup(self):
        """子类重写：初始化设置"""
        pass

    async def _cleanup(self):
        """子类重写：清理资源"""
        pass

    def get_config(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def is_initialized(self) -> bool:
        return self._initialized

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "priority": self.priority.value,
            "timeout": self.timeout,
            "dependencies": self.dependencies,
            "initialized": self._initialized,
        }


class PluginDecorator:
    """插件装饰器，用于快速创建简单插件"""

    def __init__(
        self,
        name: str,
        description: str = "",
        priority: PluginPriority = PluginPriority.NORMAL,
        timeout: float = 30.0
    ):
        self.name = name
        self.description = description
        self.priority = priority
        self.timeout = timeout

    def __call__(self, func: Callable) -> Type[Plugin]:
        """将函数转换为插件类"""

        class DynamicPlugin(Plugin):
            name = self.name
            description = self.description or func.__doc__ or ""
            priority = self.priority
            timeout = self.timeout

            async def execute(self, context: PluginContext) -> PluginResult:
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(context)
                    else:
                        result = func(context)

                    if isinstance(result, PluginResult):
                        return result
                    return PluginResult(success=True, output=result)
                except Exception as e:
                    return PluginResult(success=False, error=str(e))

        return DynamicPlugin


def create_plugin(
    name: str,
    description: str = "",
    priority: PluginPriority = PluginPriority.NORMAL
):
    """创建插件的装饰器工厂"""
    return PluginDecorator(name, description, priority)
