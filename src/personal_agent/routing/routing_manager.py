"""
路由管理器 - 使用 ConfigCenter 统一管理
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger

from ..config_center import config_center


@dataclass
class AgentRoutingConfig:
    """单个智能体的路由配置"""
    name: str
    class_name: str
    intent_type: Optional[str] = None
    valid_actions: List[str] = field(default_factory=list)
    default_action: str = ""
    file_types: List[str] = field(default_factory=list)


class RoutingManager:
    """路由管理器 - 单例模式，使用 ConfigCenter"""
    
    _instance: Optional["RoutingManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._agent_configs: Dict[str, AgentRoutingConfig] = {}
        
        self._build_agent_configs()
    
    def _build_agent_configs(self):
        """从 ConfigCenter 构建智能体配置"""
        self._agent_configs.clear()
        
        for agent_name, meta in config_center.get_all_agents(include_hidden=True).items():
            intent_type = config_center.get_agent_by_intent(
                next((k for k, v in config_center._intent_mapping.items() if v == agent_name), None)
            )
            
            actions = config_center.get_agent_actions(agent_name)
            default = config_center.get_default_action(agent_name)
            
            self._agent_configs[agent_name] = AgentRoutingConfig(
                name=agent_name,
                class_name=meta.class_name,
                intent_type=intent_type,
                valid_actions=actions,
                default_action=default,
                file_types=meta.supported_file_types
            )
    
    def get_agent_classes(self) -> List[tuple]:
        """获取智能体类列表 (agent_name, class_name)"""
        return [
            (cfg.name, cfg.class_name) 
            for cfg in self._agent_configs.values()
        ]
    
    def get_intent_to_agent(self) -> Dict[str, str]:
        """获取意图到智能体的映射"""
        return dict(config_center._intent_mapping)
    
    def get_agent_to_intent(self) -> Dict[str, str]:
        """获取智能体到意图的映射"""
        return {v: k for k, v in config_center._intent_mapping.items()}
    
    def get_task_to_agent(self) -> Dict[str, str]:
        """获取任务到智能体的映射"""
        return config_center.get_task_mapping()
    
    def get_valid_actions(self, agent_name: str) -> List[str]:
        """获取智能体的有效操作列表"""
        return config_center.get_agent_actions(agent_name)
    
    def get_default_action(self, agent_name: str) -> str:
        """获取智能体的默认操作"""
        return config_center.get_default_action(agent_name)
    
    def get_file_type_mapping(self) -> Dict[str, str]:
        """获取文件类型到智能体的映射"""
        mapping = {}
        for name, meta in config_center.get_all_agents(include_hidden=True).items():
            for ft in meta.supported_file_types:
                mapping[ft] = name
        return mapping
    
    def get_agent_for_task(self, task_type: str) -> Optional[str]:
        """根据任务类型获取智能体"""
        return config_center.get_agent_by_intent(task_type)
    
    def get_agent_for_intent(self, intent_type: str) -> Optional[str]:
        """根据意图类型获取智能体"""
        return config_center.get_agent_by_intent(intent_type)
    
    def get_agent_for_file(self, file_ext: str) -> Optional[str]:
        """根据文件扩展名获取智能体"""
        ext = file_ext.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        
        for name, meta in config_center.get_all_agents(include_hidden=True).items():
            if ext in meta.supported_file_types:
                return name
        return None
    
    def get_intent_for_agent(self, agent_name: str) -> Optional[str]:
        """根据智能体获取意图类型"""
        for intent, agent in config_center._intent_mapping.items():
            if agent == agent_name:
                return intent
        return None
    
    def get_all_agents(self) -> List[str]:
        """获取所有智能体名称"""
        return list(self._agent_configs.keys())
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentRoutingConfig]:
        """获取智能体配置"""
        return self._agent_configs.get(agent_name)
    
    def reload(self):
        """重新加载配置"""
        config_center.reload()
        self._build_agent_configs()
    
    def reload_if_changed(self) -> bool:
        """检查并重新加载配置（如果发生变化）"""
        self.reload()
        return True


routing_manager = RoutingManager()


def get_routing_manager() -> RoutingManager:
    """获取路由管理器单例"""
    return routing_manager
