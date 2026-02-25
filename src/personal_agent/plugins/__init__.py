"""
Plugin System - 模块化插件框架

架构设计：
- Plugin: 插件基类，定义标准接口
- PluginManager: 插件管理器，负责注册和调度
- TaskExecutor: 任务执行器，异步线程池执行
- HookSystem: 钩子系统，支持扩展点
"""
from .base import Plugin, PluginResult, PluginContext
from .manager import PluginManager, plugin_manager
from .executor import TaskExecutor, Task, TaskStatus
from .hooks import HookSystem, hook_system

__all__ = [
    # 基础类
    "Plugin",
    "PluginResult",
    "PluginContext",
    # 管理器
    "PluginManager",
    "plugin_manager",
    # 执行器
    "TaskExecutor",
    "Task",
    "TaskStatus",
    # 钩子
    "HookSystem",
    "hook_system",
]
