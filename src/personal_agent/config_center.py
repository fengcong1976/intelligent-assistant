"""
统一配置中心 - 整合所有配置到一个地方
"""
import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from loguru import logger

from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_FILE)


@dataclass
class AgentMeta:
    """智能体元信息"""
    name: str
    class_name: str
    display_name: str = ""
    icon: str = "🤖"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    supported_file_types: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    hidden: bool = False
    priority: int = 5
    help: str = ""
    module_path: str = ""


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "zhipu"
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    dashscope_enable_search: bool = True
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4-turbo-preview"
    voice_provider: str = "dashscope"
    voice_dashscope_api_key: str = ""
    tts_enabled: bool = True
    tts_voice: str = "longyue_v3"
    tts_speech_rate: float = 1.0


@dataclass
class UserConfig:
    """用户配置"""
    name: str = "主人"
    nickname: str = ""
    formal_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    timezone: str = "Asia/Shanghai"
    tushare_token: str = ""


@dataclass
class AgentSettings:
    """智能体设置"""
    name: str = "小助手"
    gender: str = "neutral"
    voice: str = "default"
    personality: str = "friendly"
    greeting: str = ""
    avatar: str = "🤖"
    email: str = ""
    email_password: str = ""
    email_smtp: str = "smtp.qq.com"
    email_port: int = 465
    email_imap: str = "imap.qq.com"
    email_imap_port: int = 993
    max_iterations: int = 10
    timeout: int = 300


@dataclass
class DirectorySettings:
    """目录设置"""
    music_library: str = ""
    download_dir: str = ""
    documents_dir: str = ""
    pictures_dir: str = ""
    
    def get_music_library(self) -> Path:
        return Path(self.music_library) if self.music_library else Path.home() / "Music"
    
    def get_download_dir(self) -> Path:
        return Path(self.download_dir) if self.download_dir else Path.home() / "Downloads"
    
    def get_documents_dir(self) -> Path:
        return Path(self.documents_dir) if self.documents_dir else Path.home() / "Documents"
    
    def get_pictures_dir(self) -> Path:
        return Path(self.pictures_dir) if self.pictures_dir else Path.home() / "Pictures"


@dataclass
class MemorySettings:
    """记忆设置"""
    db_path: str = "./data/chroma"
    collection: str = "agent_memory"


@dataclass
class SecuritySettings:
    """安全设置"""
    allowed_directories: str = "./workspace,./data,E:/,E:\\,C:/Users"
    dangerous_commands: str = "format,sudo,su"
    
    @property
    def allowed_dirs(self) -> List[Path]:
        return [Path(d.strip()) for d in self.allowed_directories.split(",")]


@dataclass
class AppSettings:
    """应用设置"""
    data_dir: str = "./data"
    skills_dir: str = "./skills"


class ConfigCenter:
    """统一配置中心 - 单例模式"""
    
    _instance: Optional["ConfigCenter"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._config_dir = Path(__file__).parent
        self._agents: Dict[str, AgentMeta] = {}
        self._intent_mapping: Dict[str, str] = {}
        self._task_mapping: Dict[str, str] = {}
        self._action_mapping: Dict[str, List[str]] = {}
        self._default_actions: Dict[str, str] = {}
        
        self._load_env_config()
        self._load_agents_config()
        self._load_routing_config()
    
    def _load_env_config(self):
        """从环境变量加载配置"""
        self.llm = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "zhipu"),
            zhipu_api_key=os.getenv("ZHIPU_API_KEY", ""),
            zhipu_model=os.getenv("ZHIPU_MODEL", "glm-4"),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            dashscope_model=os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
            dashscope_enable_search=os.getenv("DASHSCOPE_ENABLE_SEARCH", "true").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            voice_provider=os.getenv("VOICE_PROVIDER", "dashscope"),
            voice_dashscope_api_key=os.getenv("VOICE_DASHSCOPE_API_KEY", ""),
            tts_enabled=os.getenv("TTS_ENABLED", "true").lower() == "true",
            tts_voice=os.getenv("TTS_VOICE", "longyue_v3"),
            tts_speech_rate=float(os.getenv("TTS_SPEECH_RATE", "1.0")),
        )
        
        self.user = UserConfig(
            name=os.getenv("USER_NAME", "主人"),
            nickname=os.getenv("USER_NICKNAME", ""),
            formal_name=os.getenv("USER_FORMAL_NAME", ""),
            email=os.getenv("USER_EMAIL", ""),
            phone=os.getenv("USER_PHONE", ""),
            address=os.getenv("USER_ADDRESS", ""),
            city=os.getenv("USER_CITY", ""),
            timezone=os.getenv("USER_TIMEZONE", "Asia/Shanghai"),
            tushare_token=os.getenv("TUSHARE_TOKEN", ""),
        )
        
        self.agent = AgentSettings(
            name=os.getenv("AGENT_NAME", "小助手"),
            gender=os.getenv("AGENT_GENDER", "neutral"),
            voice=os.getenv("AGENT_VOICE", "default"),
            personality=os.getenv("AGENT_PERSONALITY", "friendly"),
            greeting=os.getenv("AGENT_GREETING", ""),
            avatar=os.getenv("AGENT_AVATAR", "🤖"),
            email=os.getenv("AGENT_EMAIL", ""),
            email_password=os.getenv("AGENT_EMAIL_PASSWORD", ""),
            email_smtp=os.getenv("AGENT_EMAIL_SMTP", "smtp.qq.com"),
            email_port=int(os.getenv("AGENT_EMAIL_PORT", "465")),
            email_imap=os.getenv("AGENT_EMAIL_IMAP", "imap.qq.com"),
            email_imap_port=int(os.getenv("AGENT_EMAIL_IMAP_PORT", "993")),
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
            timeout=int(os.getenv("AGENT_TIMEOUT", "300")),
        )
        
        self.directories = DirectorySettings(
            music_library=os.getenv("MUSIC_LIBRARY_PATH", ""),
            download_dir=os.getenv("DOWNLOAD_DIR", ""),
            documents_dir=os.getenv("DOCUMENTS_DIR", ""),
            pictures_dir=os.getenv("PICTURES_DIR", ""),
        )
        
        self.memory = MemorySettings(
            db_path=os.getenv("MEMORY_DB_PATH", "./data/chroma"),
            collection=os.getenv("MEMORY_COLLECTION", "agent_memory"),
        )
        
        self.security = SecuritySettings(
            allowed_directories=os.getenv("ALLOWED_DIRECTORIES", "./workspace,./data,E:/,E:\\,C:/Users"),
            dangerous_commands=os.getenv("DANGEROUS_COMMANDS", "format,sudo,su"),
        )
        
        self.app = AppSettings(
            data_dir=os.getenv("APP_DATA_DIR", "./data"),
            skills_dir=os.getenv("APP_SKILLS_DIR", "./skills"),
        )
    
    def _load_agents_config(self):
        """加载智能体配置 - 从各个agent.json文件和直接在agents目录下的py文件"""
        agents_dir = self._config_dir / "agents"
        logger.info(f"📁 加载智能体配置，目录: {agents_dir}")
        
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            config_file = agent_dir / "agent.json"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                agent_name = agent_dir.name
                class_name = self._to_class_name(agent_name)
                
                self._agents[agent_name] = AgentMeta(
                    name=agent_name,
                    class_name=class_name,
                    display_name=data.get("display_name", ""),
                    icon=data.get("icon", "🤖"),
                    description=data.get("description", ""),
                    capabilities=data.get("capabilities", []),
                    supported_file_types=data.get("supported_file_types", []),
                    keywords=data.get("keywords", []),
                    version=data.get("version", "1.0.0"),
                    author=data.get("author", ""),
                    hidden=data.get("hidden", False),
                    priority=data.get("priority", 5),
                    help=data.get("help", ""),
                    module_path=f".{agent_name}",
                )
                logger.info(f"✅ 加载智能体: {agent_name} -> {class_name}")
            except Exception as e:
                logger.warning(f"加载智能体配置失败 {config_file}: {e}")
        
        logger.info(f"📊 共加载 {len(self._agents)} 个智能体: {list(self._agents.keys())}")
        
        for py_file in agents_dir.glob("*_agent.py"):
            agent_name = py_file.stem
            if agent_name in self._agents:
                continue
            
            class_name = self._to_class_name(agent_name)
            self._agents[agent_name] = AgentMeta(
                name=agent_name,
                class_name=class_name,
                display_name=agent_name.replace("_agent", "").replace("_", " ").title(),
                module_path=f".{agent_name}",
            )
    
    def _to_class_name(self, agent_name: str) -> str:
        """转换智能体名称为类名"""
        parts = agent_name.split("_")
        return "".join(p.capitalize() for p in parts)
    
    def _load_routing_config(self):
        """加载路由配置"""
        routing_file = self._config_dir / "routing" / "routing.json"
        
        if not routing_file.exists():
            logger.warning(f"路由配置文件不存在: {routing_file}")
            return
        
        try:
            with open(routing_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._intent_mapping = data.get("intent_types", {})
            self._task_mapping = data.get("task_to_agent", {})
            self._action_mapping = data.get("valid_actions", {})
            self._default_actions = data.get("default_actions", {})
            
            for agent_info in data.get("agent_classes", []):
                name = agent_info["name"]
                if name in self._agents:
                    self._agents[name].class_name = agent_info["class"]
        
        except Exception as e:
            logger.error(f"加载路由配置失败: {e}")
    
    def get_agent(self, name: str) -> Optional[AgentMeta]:
        """获取智能体配置"""
        return self._agents.get(name)
    
    def get_all_agents(self, include_hidden: bool = False) -> Dict[str, AgentMeta]:
        """获取所有智能体配置"""
        if include_hidden:
            return dict(self._agents)
        return {k: v for k, v in self._agents.items() if not v.hidden}
    
    def get_agent_by_intent(self, intent: str) -> Optional[str]:
        """根据意图获取智能体名称"""
        return self._intent_mapping.get(intent)
    
    def get_agent_by_task(self, task_type: str) -> Optional[str]:
        """根据任务类型获取智能体名称"""
        return self._task_mapping.get(task_type)
    
    def get_task_mapping(self) -> Dict[str, str]:
        """获取任务到智能体的映射"""
        return dict(self._task_mapping)
    
    def get_agent_actions(self, agent_name: str) -> List[str]:
        """获取智能体支持的操作"""
        return self._action_mapping.get(agent_name, [])
    
    def get_default_action(self, agent_name: str) -> str:
        """获取智能体默认操作"""
        return self._default_actions.get(agent_name, "")
    
    def get_agent_by_keyword(self, keyword: str) -> Optional[str]:
        """根据关键词查找智能体"""
        keyword_lower = keyword.lower()
        for name, meta in self._agents.items():
            if keyword_lower in [k.lower() for k in meta.keywords]:
                return name
        return None
    
    def get_agent_by_capability(self, capability: str) -> List[str]:
        """根据能力查找智能体"""
        return [
            name for name, meta in self._agents.items()
            if capability in meta.capabilities
        ]
    
    def save_env_config(self, key: str, value: str) -> bool:
        """保存环境变量配置到.env文件"""
        env_file = Path(__file__).parent.parent.parent / ".env"
        try:
            existing_content = ""
            if env_file.exists():
                existing_content = env_file.read_text(encoding="utf-8")
            
            lines = existing_content.split("\n")
            updated = False
            new_lines = []
            
            for line in lines:
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}")
                    updated = True
                else:
                    new_lines.append(line)
            
            if not updated:
                new_lines.append(f"{key}={value}")
            
            env_file.write_text("\n".join(new_lines), encoding="utf-8")
            
            if hasattr(self, key.split("_")[0].lower()):
                setattr(self, key.lower(), value)
            
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def reload(self):
        """重新加载所有配置"""
        self._load_env_config()
        self._load_agents_config()
        self._load_routing_config()


config_center = ConfigCenter()
