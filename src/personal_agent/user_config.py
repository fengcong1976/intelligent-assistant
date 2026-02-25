"""
User Configuration - 用户配置管理
保存用户偏好设置，包括用户名等
"""
import json
from pathlib import Path
from typing import Optional


class UserConfig:
    """用户配置管理器"""

    def __init__(self, config_path: str = "./data/user_config.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._config = {
            "user_name": "",  # 用户昵称
            "formal_name": "",  # 正式名称（用于邮件署名）
            "first_run": True,  # 是否首次运行
            "theme": "default",  # 主题
            "language": "zh",  # 语言
        }

        self._load()

    def _load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self._config.update(loaded)
            except Exception as e:
                pass

    def save(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key: str, value):
        """设置配置项"""
        self._config[key] = value
        self.save()

    @property
    def user_name(self) -> str:
        """获取用户名（昵称）"""
        return self._config.get("user_name", "")

    @user_name.setter
    def user_name(self, name: str):
        """设置用户名（昵称）"""
        self._config["user_name"] = name
        self.save()

    @property
    def formal_name(self) -> str:
        """获取正式名称（用于邮件署名）"""
        return self._config.get("formal_name", "")

    @formal_name.setter
    def formal_name(self, name: str):
        """设置正式名称"""
        self._config["formal_name"] = name
        self.save()

    @property
    def first_run(self) -> bool:
        """是否首次运行"""
        return self._config.get("first_run", True)

    def mark_initialized(self):
        """标记已初始化"""
        self._config["first_run"] = False
        self.save()


# 全局用户配置实例
user_config = UserConfig()
