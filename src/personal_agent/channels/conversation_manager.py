"""
Conversation Manager - 对话管理器（单对话模式）
负责对话的持久化存储和管理，支持智能历史查询
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from loguru import logger


@dataclass
class Message:
    """消息数据类"""
    role: str  # "user" or "agent"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(**data)


@dataclass
class Conversation:
    """对话数据类"""
    id: str = "default"
    title: str = "智能助手对话"
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息"""
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
    
    def clear_messages(self):
        """清空消息"""
        self.messages.clear()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Conversation":
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        return cls(
            id=data.get("id", "default"),
            title=data.get("title", "智能助手对话"),
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


class ConversationManager:
    """对话管理器（单对话模式）"""
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "data", "conversations")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.conversation: Optional[Conversation] = None
        
        self._load()
    
    def _get_conversation_file(self) -> Path:
        """获取对话文件路径"""
        return self.storage_path / "conversation.json"
    
    def _load(self):
        """加载对话（只加载最新50条消息）"""
        file_path = self._get_conversation_file()
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.conversation = Conversation.from_dict(data)
                
                if len(self.conversation.messages) > 50:
                    self.conversation.messages = self.conversation.messages[-50:]
                
                logger.info(f"✅ 已加载对话，共 {len(self.conversation.messages)} 条消息")
            except json.JSONDecodeError as e:
                logger.error(f"❌ 对话文件JSON格式错误: {e}")
                self.conversation = Conversation()
                self._save()
            except Exception as e:
                logger.error(f"❌ 加载对话失败: {e}")
                self.conversation = Conversation()
        else:
            self.conversation = Conversation()
            logger.info("✅ 创建新对话")
    
    def _save(self):
        """保存对话"""
        if not self.conversation:
            return
        
        file_path = self._get_conversation_file()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.conversation.to_dict(), f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 对话已保存，共 {len(self.conversation.messages)} 条消息")
        except Exception as e:
            logger.error(f"❌ 保存对话失败: {e}")
    
    def get_conversation(self) -> Optional[Conversation]:
        """获取对话"""
        return self.conversation
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息到对话"""
        if self.conversation:
            self.conversation.add_message(role, content, metadata)
            self._save()
    
    def clear_messages(self):
        """清空对话消息"""
        if self.conversation:
            self.conversation.clear_messages()
            self._save()
            logger.info("🗑️ 对话内容已清空")
    
    def get_messages(self) -> List[Message]:
        """获取所有消息"""
        if self.conversation:
            return self.conversation.messages
        return []
    
    def search_history(self, query_type: str, keyword: str = None) -> Dict[str, Any]:
        """
        搜索对话历史
        
        Args:
            query_type: 查询类型
                - "last_file": 最近提到的文件
                - "last_contact": 最近提到的联系人
                - "last_action": 最近执行的操作
                - "keyword": 关键词搜索
            keyword: 关键词（当query_type为keyword时使用）
        
        Returns:
            查询结果字典
        """
        if not self.conversation or not self.conversation.messages:
            return {"found": False, "result": None, "message": "没有对话历史"}
        
        messages = list(reversed(self.conversation.messages))
        
        if query_type == "last_file":
            return self._search_last_file(messages)
        elif query_type == "last_contact":
            return self._search_last_contact(messages)
        elif query_type == "last_action":
            return self._search_last_action(messages)
        elif query_type == "keyword" and keyword:
            return self._search_keyword(messages, keyword)
        else:
            return {"found": False, "result": None, "message": f"未知查询类型: {query_type}"}
    
    def _search_last_file(self, messages: List[Message]) -> Dict[str, Any]:
        """搜索最近提到的文件"""
        file_patterns = [
            r'[A-Za-z]:\\[^\s<>"|*?\n]+\.\w+',
            r'/[^\s<>"|*?\n]+\.\w+',
            r'[^\s<>"|*?\n]+\.(ncm|mp3|mp4|pdf|doc|docx|xls|xlsx|ppt|pptx|txt|jpg|png|zip|rar)',
        ]
        
        for msg in messages:
            for pattern in file_patterns:
                matches = re.findall(pattern, msg.content, re.IGNORECASE)
                if matches:
                    file_path = matches[0]
                    return {
                        "found": True,
                        "result": {
                            "file_path": file_path,
                            "mentioned_at": msg.timestamp,
                            "context": msg.content[:200],
                            "role": msg.role
                        },
                        "message": f"找到最近文件: {file_path}"
                    }
            
            if msg.metadata and msg.metadata.get("files"):
                files = msg.metadata["files"]
                if files:
                    return {
                        "found": True,
                        "result": {
                            "file_path": files[0],
                            "mentioned_at": msg.timestamp,
                            "context": "用户拖入的文件",
                            "role": "user"
                        },
                        "message": f"找到最近文件: {files[0]}"
                    }
        
        return {"found": False, "result": None, "message": "没有找到文件相关记录"}
    
    def _search_last_contact(self, messages: List[Message]) -> Dict[str, Any]:
        """搜索最近提到的联系人"""
        contact_patterns = [
            r'[\w\.-]+@[\w\.-]+\.\w+',
            r'给\s*([^\s，。！？]+)\s*[发发送邮件]',
            r'联系人[：:]\s*([^\s，。！？]+)',
        ]
        
        for msg in messages:
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', msg.content)
            if emails:
                return {
                    "found": True,
                    "result": {
                        "email": emails[0],
                        "mentioned_at": msg.timestamp,
                        "context": msg.content[:200],
                        "role": msg.role
                    },
                    "message": f"找到最近联系人邮箱: {emails[0]}"
                }
            
            name_match = re.search(r'给\s*([^\s，。！？]+)\s*[发发送]', msg.content)
            if name_match:
                return {
                    "found": True,
                    "result": {
                        "name": name_match.group(1),
                        "mentioned_at": msg.timestamp,
                        "context": msg.content[:200],
                        "role": msg.role
                    },
                    "message": f"找到最近联系人: {name_match.group(1)}"
                }
        
        return {"found": False, "result": None, "message": "没有找到联系人相关记录"}
    
    def _search_last_action(self, messages: List[Message]) -> Dict[str, Any]:
        """搜索最近执行的操作"""
        action_keywords = {
            "decrypt": ["解密", "转换", "转成", "ncm"],
            "email": ["发邮件", "发送", "邮件"],
            "music": ["播放", "音乐", "歌曲"],
            "download": ["下载", "保存"],
            "search": ["搜索", "查找", "找"],
        }
        
        for msg in messages:
            content_lower = msg.content.lower()
            for action_type, keywords in action_keywords.items():
                if any(kw in content_lower for kw in keywords):
                    return {
                        "found": True,
                        "result": {
                            "action_type": action_type,
                            "mentioned_at": msg.timestamp,
                            "context": msg.content[:200],
                            "role": msg.role
                        },
                        "message": f"找到最近操作: {action_type}"
                    }
        
        return {"found": False, "result": None, "message": "没有找到操作相关记录"}
    
    def _search_keyword(self, messages: List[Message], keyword: str) -> Dict[str, Any]:
        """关键词搜索"""
        results = []
        
        for msg in messages:
            if keyword.lower() in msg.content.lower():
                results.append({
                    "content": msg.content[:300],
                    "timestamp": msg.timestamp,
                    "role": msg.role
                })
        
        if results:
            return {
                "found": True,
                "result": results[:5],
                "message": f"找到 {len(results)} 条包含 '{keyword}' 的记录"
            }
        
        return {"found": False, "result": None, "message": f"没有找到包含 '{keyword}' 的记录"}
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """获取最近的消息（用于上下文）"""
        if not self.conversation:
            return []
        
        messages = self.conversation.messages[-limit:]
        return [
            {
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content[:500]
            }
            for msg in messages
        ]


conversation_manager = ConversationManager()
