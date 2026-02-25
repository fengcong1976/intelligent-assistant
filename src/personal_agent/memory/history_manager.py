"""
History Manager - 历史记录管理器
独立于对话管理，持久化存储所有对话历史，供 LLM 上下文使用
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from loguru import logger


@dataclass
class HistoryMessage:
    """历史消息数据类"""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = "default"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HistoryMessage":
        return cls(**data)


class HistoryManager:
    """历史记录管理器 - 持久化存储所有对话"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, storage_path: str = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "data", "history")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.storage_path / "all_history.json"
        self.messages: List[HistoryMessage] = []
        
        self._load()
        self._initialized = True
    
    def _load(self):
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = [HistoryMessage.from_dict(m) for m in data.get("messages", [])]
            except Exception as e:
                logger.error(f"❌ 加载历史记录失败: {e}")
                self.messages = []
        else:
            self.messages = []
    
    def _save(self):
        """保存历史记录"""
        try:
            data = {
                "messages": [m.to_dict() for m in self.messages],
                "updated_at": datetime.now().isoformat()
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存历史记录失败: {e}")
    
    def add_message(self, role: str, content: str, session_id: str = "default"):
        """添加消息到历史记录"""
        message = HistoryMessage(
            role=role,
            content=content,
            session_id=session_id
        )
        self.messages.append(message)
        self._save()
        logger.debug(f"📝 已添加历史记录: [{role}] {content[:50]}...")
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取历史记录（用于 LLM 上下文）"""
        if not self.messages:
            return []
        
        recent = self.messages[-limit:] if limit else self.messages
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in recent
        ]
    
    def get_history_text(self, limit: int = 30) -> str:
        """获取历史记录文本（用于 LLM 提示）"""
        history = self.get_history(limit)
        if not history:
            return ""
        
        lines = []
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"]
            if content and len(content) > 5:
                lines.append(f"[{role}] {content[:300]}")
        
        return "\n".join(lines)
    
    def search_in_history(self, keyword: str, limit: int = 10) -> List[Dict]:
        """在历史记录中搜索"""
        results = []
        for msg in reversed(self.messages):
            if keyword.lower() in msg.content.lower():
                results.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                })
                if len(results) >= limit:
                    break
        return results
    
    def get_message_count(self) -> int:
        """获取消息总数"""
        return len(self.messages)
    
    def clear_all(self):
        """清空所有历史记录（慎用）"""
        self.messages.clear()
        self._save()
        logger.warning("⚠️ 所有历史记录已清空")


history_manager = HistoryManager()
