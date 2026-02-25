"""
智能体扫描器 - 使用 ConfigCenter 统一管理
"""
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from loguru import logger

from ..config_center import config_center, AgentMeta
from .base import BaseAgent


@dataclass
class AgentMetadata:
    """智能体元数据 - 向后兼容"""
    name: str
    class_name: str
    module_path: str
    display_name: str
    mention_prefix: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    supported_file_types: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    icon: str = "🤖"
    hidden: bool = False
    priority: int = 5
    keywords: List[str] = field(default_factory=list)
    help: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_agent_meta(cls, meta: AgentMeta) -> "AgentMetadata":
        """从 ConfigCenter 的 AgentMeta 转换"""
        return cls(
            name=meta.name,
            class_name=meta.class_name,
            module_path=meta.module_path,
            display_name=meta.display_name,
            mention_prefix=f"@{meta.display_name}智能体 ",
            description=meta.description,
            capabilities=meta.capabilities,
            supported_file_types=meta.supported_file_types,
            version=meta.version,
            author=meta.author,
            icon=meta.icon,
            hidden=meta.hidden,
            priority=meta.priority,
            keywords=meta.keywords,
            help=meta.help,
        )


class AgentScanner:
    """智能体扫描器 - 使用 ConfigCenter"""
    
    def __init__(self, agents_package_path: Optional[Path] = None):
        self.agents_path = agents_package_path or Path(__file__).parent
    
    def scan_agents(self, use_cache: bool = True) -> Dict[str, AgentMetadata]:
        """扫描所有智能体 - 从 ConfigCenter 获取"""
        agents = {}
        for name, meta in config_center.get_all_agents(include_hidden=True).items():
            agents[name] = AgentMetadata.from_agent_meta(meta)
        return agents
    
    def get_agent_metadata(self, agent_name: str) -> Optional[AgentMetadata]:
        """获取单个智能体元数据"""
        meta = config_center.get_agent(agent_name)
        if meta:
            return AgentMetadata.from_agent_meta(meta)
        return None
    
    def get_agent_class(self, agent_name: str) -> Optional[type]:
        """获取智能体类"""
        meta = config_center.get_agent(agent_name)
        if not meta:
            return None
        
        try:
            module = importlib.import_module(f".{meta.name}", package="personal_agent.agents")
            agent_class = getattr(module, meta.class_name)
            return agent_class
        except Exception as e:
            logger.error(f"加载智能体类失败 {agent_name}: {e}")
            return None
    
    def get_all_agents_info(self) -> List[Dict[str, Any]]:
        """获取所有智能体信息"""
        return [
            meta.to_dict() 
            for meta in self.scan_agents().values()
        ]
    
    def get_agent_registry(self) -> Dict[str, tuple]:
        """获取智能体注册表 {name: (module_path, class_name)}"""
        registry = {}
        for name, meta in self.scan_agents().items():
            registry[name] = (meta.module_path, meta.class_name)
        return registry
    
    def get_capability_map(self) -> Dict[str, str]:
        """获取能力到智能体的映射"""
        capability_map = {}
        for name, meta in self.scan_agents().items():
            for cap in meta.capabilities:
                capability_map[cap] = name
        return capability_map
    
    def refresh(self):
        """刷新缓存"""
        config_center.reload()


agent_scanner = AgentScanner()


def get_agent_scanner() -> AgentScanner:
    """获取智能体扫描器单例"""
    return agent_scanner
