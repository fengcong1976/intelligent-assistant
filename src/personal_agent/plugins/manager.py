"""
Plugin Manager - 插件管理器

功能：
- 插件注册和发现
- 依赖管理
- 生命周期管理
- 动态加载/卸载
"""
import asyncio
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable

from loguru import logger

from .base import Plugin, PluginContext, PluginPriority, PluginResult
from .executor import TaskExecutor, task_executor


class PluginManager:
    """
    插件管理器

    管理所有插件的注册、初始化和执行
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._executor = task_executor
        self._initialized = False

    async def initialize(self):
        """初始化管理器"""
        if self._initialized:
            return

        await self._executor.start()
        self._initialized = True
        logger.info("PluginManager initialized")

    async def shutdown(self):
        """关闭管理器"""
        # 关闭所有插件
        for name, plugin in list(self._plugins.items()):
            await self.unload_plugin(name)

        await self._executor.stop()
        self._initialized = False
        logger.info("PluginManager shutdown")

    def register(self, plugin_class: Type[Plugin]) -> bool:
        """
        注册插件类

        Args:
            plugin_class: 插件类

        Returns:
            bool: 是否注册成功
        """
        try:
            # 实例化插件
            plugin = plugin_class()

            if not plugin.name:
                logger.error("Plugin must have a name")
                return False

            if plugin.name in self._plugins:
                logger.warning(f"Plugin {plugin.name} already registered")
                return False

            self._plugins[plugin.name] = plugin
            self._plugin_classes[plugin.name] = plugin_class

            logger.info(f"Plugin registered: {plugin.name} v{plugin.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False

    async def load_plugin(
        self,
        name: str,
        config: Optional[Dict] = None
    ) -> bool:
        """
        加载并初始化插件

        Args:
            name: 插件名称
            config: 配置参数

        Returns:
            bool: 是否加载成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"Plugin not found: {name}")
            return False

        if plugin.is_initialized():
            return True

        # 检查依赖
        for dep in plugin.dependencies:
            if dep not in self._plugins:
                logger.error(f"Plugin {name} depends on {dep} which is not loaded")
                return False

            dep_plugin = self._plugins[dep]
            if not dep_plugin.is_initialized():
                await self.load_plugin(dep, config)

        # 初始化插件
        success = await plugin.initialize(config)
        if success:
            logger.info(f"Plugin loaded: {name}")
        else:
            logger.error(f"Failed to load plugin: {name}")

        return success

    async def unload_plugin(self, name: str) -> bool:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            bool: 是否卸载成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        # 检查是否有其他插件依赖此插件
        for other_name, other_plugin in self._plugins.items():
            if name in other_plugin.dependencies and other_plugin.is_initialized():
                logger.error(f"Cannot unload {name}, {other_name} depends on it")
                return False

        success = await plugin.shutdown()
        if success:
            logger.info(f"Plugin unloaded: {name}")

        return success

    async def execute(
        self,
        plugin_name: str,
        context: PluginContext,
        background: bool = False
    ) -> Optional[PluginResult]:
        """
        执行插件

        Args:
            plugin_name: 插件名称
            context: 执行上下文
            background: 是否在后台执行

        Returns:
            PluginResult: 执行结果（后台执行返回None）
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return PluginResult(
                success=False,
                error=f"Plugin not found: {plugin_name}"
            )

        if not plugin.is_initialized():
            return PluginResult(
                success=False,
                error=f"Plugin not initialized: {plugin_name}"
            )

        # 验证输入
        if not await plugin.validate(context):
            return PluginResult(
                success=False,
                error="Validation failed"
            )

        # 执行前钩子
        await self._run_hooks("before_execute", plugin_name, context)

        async def do_execute():
            try:
                result = await plugin.execute(context)
                result.plugin_name = plugin_name

                # 执行后钩子
                await self._run_hooks("after_execute", plugin_name, context, result)

                return result
            except Exception as e:
                logger.error(f"Plugin execution error: {e}")
                return PluginResult(
                    success=False,
                    error=str(e),
                    plugin_name=plugin_name
                )

        if background:
            # 后台执行
            await self._executor.submit_coroutine(
                do_execute(),
                name=f"plugin_{plugin_name}",
                priority=plugin.priority.value,
                timeout=plugin.timeout
            )
            return None
        else:
            # 同步执行
            return await do_execute()

    async def execute_pipeline(
        self,
        plugin_names: List[str],
        context: PluginContext,
        stop_on_error: bool = True
    ) -> List[PluginResult]:
        """
        执行插件管道

        Args:
            plugin_names: 插件名称列表
            context: 执行上下文
            stop_on_error: 出错时是否停止

        Returns:
            List[PluginResult]: 执行结果列表
        """
        results = []

        for name in plugin_names:
            result = await self.execute(name, context)
            results.append(result)

            if not result.success and stop_on_error:
                break

            # 将结果传递给下一个插件
            context.history.append({
                "plugin": name,
                "result": result
            })

        return results

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        return [plugin.to_dict() for plugin in self._plugins.values()]

    def get_plugins_by_priority(
        self,
        priority: PluginPriority
    ) -> List[Plugin]:
        """按优先级获取插件"""
        return [
            p for p in self._plugins.values()
            if p.priority == priority
        ]

    def add_hook(self, event: str, handler: Callable) -> None:
        """添加事件钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    async def _run_hooks(self, event: str, *args, **kwargs):
        """运行钩子"""
        handlers = self._hooks.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook error: {e}")

    def auto_discover(self, package_path: str = "personal_agent.plugins.builtin") -> int:
        """
        自动发现插件

        Args:
            package_path: 插件包路径

        Returns:
            int: 发现的插件数量
        """
        count = 0
        try:
            package = importlib.import_module(package_path)
            package_dir = Path(package.__file__).parent

            for file in package_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                module_name = f"{package_path}.{file.stem}"
                try:
                    module = importlib.import_module(module_name)

                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, Plugin) and
                            obj != Plugin and
                            hasattr(obj, 'name') and
                            obj.name):

                            if self.register(obj):
                                count += 1

                except Exception as e:
                    logger.error(f"Failed to load module {module_name}: {e}")

        except Exception as e:
            logger.error(f"Auto discover failed: {e}")

        return count


# 全局插件管理器实例
plugin_manager = PluginManager()
