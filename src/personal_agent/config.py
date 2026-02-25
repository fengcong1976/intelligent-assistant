"""
Configuration management - 使用 ConfigCenter 统一管理
保持向后兼容的接口
"""
from pathlib import Path
from typing import List
import os

from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_FILE)

from .config_center import config_center


class LLMConfig:
    def __init__(self):
        self._config = config_center.llm
    
    @property
    def provider(self): return self._config.provider
    @property
    def zhipu_api_key(self): return self._config.zhipu_api_key
    @property
    def zhipu_model(self): return self._config.zhipu_model
    @property
    def dashscope_api_key(self): return self._config.dashscope_api_key
    @property
    def dashscope_model(self): return self._config.dashscope_model
    @property
    def dashscope_enable_search(self): return self._config.dashscope_enable_search
    @property
    def openai_api_key(self): return self._config.openai_api_key
    @property
    def openai_base_url(self): return self._config.openai_base_url
    @property
    def openai_model(self): return self._config.openai_model
    @property
    def voice_provider(self): return self._config.voice_provider
    @property
    def voice_dashscope_api_key(self): return self._config.voice_dashscope_api_key
    @property
    def tts_enabled(self): return self._config.tts_enabled
    @property
    def tts_voice(self): return self._config.tts_voice
    @property
    def tts_speech_rate(self): return self._config.tts_speech_rate


class WeChatConfig:
    def __init__(self):
        self.auto_login = os.getenv("WECHAT_AUTO_LOGIN", "True").lower() == "true"
        self.hot_reload = os.getenv("WECHAT_HOT_RELOAD", "True").lower() == "true"


class MemoryConfig:
    def __init__(self):
        self._config = config_center.memory
    
    @property
    def db_path(self): return Path(self._config.db_path)
    @property
    def collection(self): return self._config.collection


class AgentConfig:
    def __init__(self):
        self._config = config_center.agent
    
    @property
    def name(self): return self._config.name
    
    @name.setter
    def name(self, value: str):
        config_center.save_env_config("AGENT_NAME", value)
    
    @property
    def max_iterations(self): return self._config.max_iterations
    
    @max_iterations.setter
    def max_iterations(self, value: int):
        config_center.save_env_config("AGENT_MAX_ITERATIONS", str(value))
    
    @property
    def timeout(self): return self._config.timeout
    
    @timeout.setter
    def timeout(self, value: int):
        config_center.save_env_config("AGENT_TIMEOUT", str(value))
    
    @property
    def gender(self): return self._config.gender
    
    @gender.setter
    def gender(self, value: str):
        config_center.save_env_config("AGENT_GENDER", value)
    
    @property
    def voice(self): return self._config.voice
    
    @voice.setter
    def voice(self, value: str):
        config_center.save_env_config("AGENT_VOICE", value)
    
    @property
    def personality(self): return self._config.personality
    
    @personality.setter
    def personality(self, value: str):
        config_center.save_env_config("AGENT_PERSONALITY", value)
    
    @property
    def greeting(self): return self._config.greeting
    
    @greeting.setter
    def greeting(self, value: str):
        config_center.save_env_config("AGENT_GREETING", value)
    
    @property
    def avatar(self): return self._config.avatar
    
    @avatar.setter
    def avatar(self, value: str):
        config_center.save_env_config("AGENT_AVATAR", value)
    
    @property
    def email(self): return self._config.email
    
    @email.setter
    def email(self, value: str):
        config_center.save_env_config("AGENT_EMAIL", value)
    
    @property
    def email_password(self): return self._config.email_password
    
    @email_password.setter
    def email_password(self, value: str):
        config_center.save_env_config("AGENT_EMAIL_PASSWORD", value)
    
    @property
    def email_smtp(self): return self._config.email_smtp
    
    @email_smtp.setter
    def email_smtp(self, value: str):
        config_center.save_env_config("AGENT_EMAIL_SMTP", value)
    
    @property
    def email_port(self): return self._config.email_port
    
    @email_port.setter
    def email_port(self, value: int):
        config_center.save_env_config("AGENT_EMAIL_PORT", str(value))
    
    @property
    def email_imap(self): return self._config.email_imap
    
    @email_imap.setter
    def email_imap(self, value: str):
        config_center.save_env_config("AGENT_EMAIL_IMAP", value)
    
    @property
    def email_imap_port(self): return self._config.email_imap_port
    
    @email_imap_port.setter
    def email_imap_port(self, value: int):
        config_center.save_env_config("AGENT_EMAIL_IMAP_PORT", str(value))


class UserConfig:
    def __init__(self):
        self._config = config_center.user
    
    @property
    def name(self): return self._config.name
    
    @name.setter
    def name(self, value: str):
        config_center.save_env_config("USER_NAME", value)
    
    @property
    def nickname(self): return self._config.nickname
    
    @nickname.setter
    def nickname(self, value: str):
        config_center.save_env_config("USER_NICKNAME", value)
    
    @property
    def formal_name(self): return self._config.formal_name
    
    @formal_name.setter
    def formal_name(self, value: str):
        config_center.save_env_config("USER_FORMAL_NAME", value)
    
    @property
    def email(self): return self._config.email
    
    @email.setter
    def email(self, value: str):
        config_center.save_env_config("USER_EMAIL", value)
    
    @property
    def phone(self): return self._config.phone
    
    @phone.setter
    def phone(self, value: str):
        config_center.save_env_config("USER_PHONE", value)
    
    @property
    def address(self): return self._config.address
    
    @address.setter
    def address(self, value: str):
        config_center.save_env_config("USER_ADDRESS", value)
    
    @property
    def city(self): return self._config.city
    
    @city.setter
    def city(self, value: str):
        config_center.save_env_config("USER_CITY", value)
    
    @property
    def timezone(self): return self._config.timezone
    
    @timezone.setter
    def timezone(self, value: str):
        config_center.save_env_config("USER_TIMEZONE", value)
    
    @property
    def tushare_token(self): return self._config.tushare_token
    
    @tushare_token.setter
    def tushare_token(self, value: str):
        config_center.save_env_config("TUSHARE_TOKEN", value)


class AppConfig:
    def __init__(self):
        self._config = config_center.app
    
    @property
    def data_dir(self): return Path(self._config.data_dir)
    @property
    def skills_dir(self): return Path(self._config.skills_dir)


class DirectoryConfig:
    def __init__(self):
        self._config = config_center.directories
    
    @property
    def music_library(self): return self._config.music_library
    
    @music_library.setter
    def music_library(self, path: str):
        config_center.save_env_config("MUSIC_LIBRARY_PATH", path)
    
    @property
    def download_dir(self): return self._config.download_dir
    
    @download_dir.setter
    def download_dir(self, path: str):
        config_center.save_env_config("DOWNLOAD_DIR", path)
    
    @property
    def documents_dir(self): return self._config.documents_dir
    
    @documents_dir.setter
    def documents_dir(self, path: str):
        config_center.save_env_config("DOCUMENTS_DIR", path)
    
    @property
    def pictures_dir(self): return self._config.pictures_dir
    
    @pictures_dir.setter
    def pictures_dir(self, path: str):
        config_center.save_env_config("PICTURES_DIR", path)
    
    def get_music_library(self) -> Path:
        return self._config.get_music_library()
    
    def set_music_library(self, path: str) -> bool:
        return config_center.save_env_config("MUSIC_LIBRARY_PATH", path)
    
    def get_download_dir(self) -> Path:
        return self._config.get_download_dir()
    
    def get_documents_dir(self) -> Path:
        return self._config.get_documents_dir()
    
    def get_pictures_dir(self) -> Path:
        return self._config.get_pictures_dir()


class SecurityConfig:
    def __init__(self):
        self._config = config_center.security
    
    @property
    def allowed_directories(self): return self._config.allowed_directories
    
    @allowed_directories.setter
    def allowed_directories(self, value: str):
        config_center.save_env_config("ALLOWED_DIRECTORIES", value)
    
    @property
    def dangerous_commands(self): return self._config.dangerous_commands
    
    @dangerous_commands.setter
    def dangerous_commands(self, value: str):
        config_center.save_env_config("DANGEROUS_COMMANDS", value)
    
    @property
    def allowed_dirs(self) -> List[Path]:
        return self._config.allowed_dirs

    @property
    def blocked_commands(self) -> List[str]:
        return [c.strip().lower() for c in self.dangerous_commands.split(",")]


class QQBotConfig:
    def __init__(self):
        self.enabled = os.getenv("QQ_BOT_ENABLED", "false").lower() == "true"
        self.appid = os.getenv("QQ_BOT_APPID", "")
        self.secret = os.getenv("QQ_BOT_SECRET", "")
        self.intents = os.getenv("QQ_BOT_INTENTS", "public_guild_messages,group_and_c2c")
        self.auto_start = os.getenv("QQ_BOT_AUTO_START", "false").lower() == "true"
    
    def get_intents_list(self) -> List[str]:
        return [i.strip() for i in self.intents.split(",") if i.strip()]


class HomeAssistantConfig:
    def __init__(self):
        self._enabled = os.getenv("HOMEASSISTANT_ENABLED", "false").lower() == "true"
        self._url = os.getenv("HOMEASSISTANT_URL", "")
        self._token = os.getenv("HOMEASSISTANT_TOKEN", "")
    
    @property
    def enabled(self): return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        config_center.save_env_config("HOMEASSISTANT_ENABLED", "true" if value else "false")
    
    @property
    def url(self): return self._url
    
    @url.setter
    def url(self, value: str):
        self._url = value
        config_center.save_env_config("HOMEASSISTANT_URL", value)
    
    @property
    def token(self): return self._token
    
    @token.setter
    def token(self, value: str):
        self._token = value
        config_center.save_env_config("HOMEASSISTANT_TOKEN", value)


class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.llm = LLMConfig()
        self.wechat = WeChatConfig()
        self.memory = MemoryConfig()
        self.agent = AgentConfig()
        self.user = UserConfig()
        self.app = AppConfig()
        self.directory = DirectoryConfig()
        self.security = SecurityConfig()
        self.qq_bot = QQBotConfig()
        self.homeassistant = HomeAssistantConfig()
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = Path(os.getenv("LOG_FILE", "./logs/agent.log"))
    
    def reload(self):
        config_center.reload()
        self.__init__()


settings = Settings()
