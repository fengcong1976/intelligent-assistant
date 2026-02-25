"""
Tool System - Base classes and registry
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._hooks_before: List[Callable] = []
        self._hooks_after: List[Callable] = []

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_definitions(self) -> List[Dict[str, Any]]:
        return [tool.to_definition() for tool in self._tools.values()]

    def add_before_hook(self, hook: Callable) -> None:
        self._hooks_before.append(hook)

    def add_after_hook(self, hook: Callable) -> None:
        self._hooks_after.append(hook)

    async def execute(self, name: str, progress_callback=None, **kwargs) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool not found: {name}"
            )

        for hook in self._hooks_before:
            await hook(name, kwargs)

        try:
            # 如果工具支持进度回调，设置回调函数
            if progress_callback and hasattr(tool, 'set_progress_callback'):
                tool.set_progress_callback(progress_callback)

            result = await tool.execute(**kwargs)
        except Exception as e:
            result = ToolResult(
                success=False,
                output="",
                error=str(e)
            )

        for hook in self._hooks_after:
            await hook(name, kwargs, result)

        return result


tool_registry = ToolRegistry()
