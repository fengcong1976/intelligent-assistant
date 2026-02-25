"""
Agent Tools Registry - 将子智能体注册为 Function Calling 工具

这个模块实现了将子智能体转换为 LLM 可调用的工具，遵循 Function Calling 最佳实践。
"""
from typing import Any, Dict, List, Optional, Callable
from loguru import logger
from dataclasses import dataclass, field
import asyncio
from pathlib import Path
import importlib
import inspect


@dataclass
class AgentTool:
    """智能体工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    agent_name: str
    aliases: List[str] = field(default_factory=list)
    alias_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_function_definition(self) -> Dict[str, Any]:
        """转换为 Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class AgentToolsRegistry:
    """
    智能体工具注册中心
    
    将子智能体注册为 LLM 可调用的工具，支持：
    1. 工具发现和注册
    2. 参数验证
    3. 工具执行
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, AgentTool] = {}
            cls._instance._alias_map: Dict[str, str] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def register(self, tool: AgentTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        for alias in tool.aliases:
            self._alias_map[alias.lower()] = tool.name
        logger.debug(f"注册工具: {tool.name}, 别名: {tool.aliases}")
    
    def get_tool(self, name: str) -> Optional[AgentTool]:
        """获取工具"""
        if name in self._tools:
            return self._tools[name]
        if name.lower() in self._alias_map:
            return self._tools[self._alias_map[name.lower()]]
        return None
    
    def get_all_tools(self) -> List[AgentTool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """获取 Function Calling 格式的工具定义"""
        return [tool.to_function_definition() for tool in self._tools.values()]
    
    def resolve_agent(self, tool_name: str) -> Optional[str]:
        """根据工具名解析智能体名"""
        tool = self.get_tool(tool_name)
        return tool.agent_name if tool else None
    
    def query_tools(self, keyword: str = "", include_params: bool = False) -> str:
        """
        查询工具 - 供 LLM 调用
        
        Args:
            keyword: 搜索关键词，为空则返回所有工具列表
            include_params: 是否包含参数详情
        
        Returns:
            工具信息字符串
        """
        if not keyword:
            tools_list = []
            for tool in self._tools.values():
                tools_list.append(f"- {tool.name}: {tool.description.split('。')[0]}")
            return "可用工具列表:\n" + "\n".join(tools_list)
        
        keyword_lower = keyword.lower()
        matched = []
        
        for tool in self._tools.values():
            if (keyword_lower in tool.name.lower() or 
                keyword_lower in tool.description.lower() or
                any(keyword_lower in alias.lower() for alias in tool.aliases)):
                matched.append(tool)
        
        if not matched:
            return f"未找到与「{keyword}」相关的工具。调用 query_tools() 查看所有可用工具。"
        
        result_parts = []
        for tool in matched:
            if include_params:
                params_info = []
                props = tool.parameters.get("properties", {})
                required = tool.parameters.get("required", [])
                for param_name, param_info in props.items():
                    req_mark = "(必需)" if param_name in required else ""
                    param_desc = param_info.get("description", "")
                    params_info.append(f"  - {param_name}{req_mark}: {param_desc}")
                
                result_parts.append(f"**{tool.name}**\n{tool.description}\n参数:\n" + "\n".join(params_info))
            else:
                result_parts.append(f"- {tool.name}: {tool.description}")
        
        return "\n\n".join(result_parts)
    
    def get_tool_card(self, tool_name: str) -> Optional[str]:
        """获取工具名片（简短描述）"""
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        return f"{tool.name}: {tool.description.split('。')[0]}"
    
    def get_tool_detail(self, tool_name: str) -> Optional[str]:
        """获取工具详情（包含参数）"""
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        return self.query_tools(tool_name, include_params=True)
    
    def load_tools_from_agents(self, agents_base_path: Path) -> None:
        """
        动态加载子智能体的工具定义
        
        Args:
            agents_base_path: 智能体目录路径
        """
        try:
            # 动态导入 BaseAgent
            import sys
            agents_path = str(agents_base_path.parent)
            if agents_path not in sys.path:
                sys.path.insert(0, agents_path)
            
            from personal_agent.agents.base import BaseAgent
            
            if not agents_base_path.exists():
                logger.warning(f"⚠️ 智能体目录不存在: {agents_base_path}")
                return
            
            # 遍历所有智能体目录
            for agent_dir in agents_base_path.iterdir():
                if not agent_dir.is_dir() or agent_dir.name.startswith('_'):
                    continue
                
                # 查找 agent.py 文件
                agent_file = agent_dir / "agent.py"
                if not agent_file.exists():
                    continue
                
                try:
                    # 动态导入智能体模块
                    module_name = f"personal_agent.agents.{agent_dir.name}.agent"
                    spec = importlib.util.spec_from_file_location(module_name, agent_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 查找所有 BaseAgent 子类
                        for item_name in dir(module):
                            item = getattr(module, item_name)
                            if (inspect.isclass(item) and 
                                issubclass(item, BaseAgent) and 
                                item is not BaseAgent):
                                
                                # 创建智能体实例
                                try:
                                    agent_instance = item()
                                    logger.info(f"📦 加载智能体: {agent_instance.name}")
                                    
                                    # 从智能体的 capability_details 中提取工具定义
                                    for capability_name, capability_detail in agent_instance.capability_details.items():
                                        self._register_capability_as_tool(
                                            capability_name,
                                            capability_detail,
                                            agent_instance.name
                                        )
                                except Exception as e:
                                    logger.warning(f"⚠️ 无法实例化智能体 {item_name}: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ 加载智能体模块失败 {agent_dir.name}: {e}")
            
            logger.info(f"✅ 动态加载完成，共 {len(self._tools)} 个工具")
        except Exception as e:
            logger.error(f"❌ 动态加载智能体工具失败: {e}")
    
    def _register_capability_as_tool(self, capability_name: str, capability_detail: Dict, agent_name: str) -> None:
        """
        将智能体能力注册为工具
        
        Args:
            capability_name: 能力名称
            capability_detail: 能力详细信息
            agent_name: 智能体名称
        """
        # 构建工具定义
        tool = AgentTool(
            name=capability_name,
            description=capability_detail.get("description", f"{capability_name} 功能"),
            parameters=capability_detail.get("parameters", {"type": "object", "properties": {}}),
            agent_name=agent_name,
            aliases=capability_detail.get("aliases", []),
            alias_params=capability_detail.get("alias_params", {})
        )
        
        # 注册工具
        self.register(tool)
        
        logger.debug(f"✅ 注册工具: {tool.name} (来自 {agent_name})")


def get_tools_registry() -> AgentToolsRegistry:
    """获取工具注册中心单例"""
    registry = AgentToolsRegistry()
    if not registry._initialized:
        # 动态加载子智能体的工具
        agents_base_path = Path(__file__).parent.parent / "agents"
        registry.load_tools_from_agents(agents_base_path)
        
        registry._initialized = True
    return registry



