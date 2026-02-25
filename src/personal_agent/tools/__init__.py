"""
Tools Module
"""
from .base import BaseTool, ToolResult, ToolRegistry, tool_registry
from .file_ops import register_file_tools
from .code_exec import register_code_tools
from .web_automation import register_web_tools
from .http_tools import register_http_tools
from .search_tools import register_search_tools
from .download import register_download_tools
from .installer import register_installer_tools
from .download_install import register_download_install_tools
from .smart_install import register_smart_install_tools
from .shell_tool import shell_tool
from .email_tool import register_email_tools
from .contact_tools import register_contact_tools
from .agent_tools import AgentTool, AgentToolsRegistry, get_tools_registry
from .react_engine import ReActEngine, ReActResult, ReActStep, ToolExecutor, create_react_engine
from .workflow_planner import WorkflowPlanner, WorkflowPlan, create_workflow_planner


def register_all_tools():
    register_file_tools()
    register_code_tools()
    register_web_tools()
    register_http_tools()
    register_search_tools()
    register_download_tools()
    register_installer_tools()
    register_download_install_tools()
    register_smart_install_tools()
    register_email_tools()
    register_contact_tools()
    tool_registry.register(shell_tool)


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "register_all_tools",
    "AgentTool",
    "AgentToolsRegistry",
    "get_tools_registry",
    "ReActEngine",
    "ReActResult",
    "ReActStep",
    "ToolExecutor",
    "create_react_engine",
    "WorkflowPlanner",
    "WorkflowPlan",
    "create_workflow_planner",
]
