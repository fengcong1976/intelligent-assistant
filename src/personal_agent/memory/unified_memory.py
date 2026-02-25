"""
Unified Memory System - 统一记忆系统
整合所有记忆组件，提供LLM友好的MEMORY.md机制
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, field, asdict
import json
import re


@dataclass
class UserProfile:
    """用户档案"""
    name: str = ""
    nickname: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    location: str = ""
    birthday: str = ""
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"
    occupation: str = ""
    company: str = ""
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class UserPreference:
    """用户偏好"""
    category: str
    key: str
    value: Any
    confidence: float = 0.5
    source: str = "learned"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ImportantEvent:
    """重要事件"""
    event_id: str
    title: str
    event_date: str
    event_type: str = "general"
    description: str = ""
    is_recurring: bool = False
    recurring_type: str = ""
    reminder_days: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MemoryNote:
    """记忆笔记"""
    content: str
    category: str = "general"
    priority: int = 5
    source: str = "manual"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class UnifiedMemory:
    """
    统一记忆系统
    
    功能：
    1. 用户档案管理
    2. 用户偏好学习
    3. 重要事件管理
    4. 记忆笔记
    5. MEMORY.md生成（LLM友好）
    6. 记忆搜索
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, user_id: str = "default", storage_path: str = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.user_id = user_id
        
        if storage_path is None:
            storage_path = Path.home() / '.personal_agent' / 'memory'
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.storage_path / 'MEMORY.md'
        self.data_file = self.storage_path / 'memory_data.json'
        
        self.user_profile: UserProfile = UserProfile()
        self.preferences: Dict[str, UserPreference] = {}
        self.important_events: List[ImportantEvent] = []
        self.memory_notes: List[MemoryNote] = []
        self.recent_context: List[str] = []
        self.conversation_summary: List[str] = []
        
        self._load_memory_data()
        self._initialized = True
    
    def _load_memory_data(self):
        """加载记忆数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.user_profile = UserProfile.from_dict(data.get("user_profile", {}))
                
                self.preferences = {
                    k: UserPreference(**v) 
                    for k, v in data.get("preferences", {}).items()
                }
                
                self.important_events = [
                    ImportantEvent(**e) 
                    for e in data.get("important_events", [])
                ]
                
                self.memory_notes = [
                    MemoryNote(**n) 
                    for n in data.get("memory_notes", [])
                ]
                
                self.recent_context = data.get("recent_context", [])
                self.conversation_summary = data.get("conversation_summary", [])
                
            except Exception as e:
                logger.error(f"❌ 加载记忆数据失败: {e}")
    
    def _save_memory_data(self):
        """保存记忆数据"""
        try:
            data = {
                "user_profile": self.user_profile.to_dict(),
                "preferences": {k: asdict(v) for k, v in self.preferences.items()},
                "important_events": [asdict(e) for e in self.important_events],
                "memory_notes": [asdict(n) for n in self.memory_notes],
                "recent_context": self.recent_context[-100:],
                "conversation_summary": self.conversation_summary[-50:],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ 保存记忆数据失败: {e}")
    
    def generate_memory_md(self) -> str:
        """生成MEMORY.md内容（LLM友好格式）"""
        lines = ["# Memory\n"]
        lines.append(f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if self.user_profile.to_dict():
            lines.append("## 用户档案\n")
            profile = self.user_profile.to_dict()
            for key, value in profile.items():
                if value:
                    key_cn = self._translate_key(key)
                    lines.append(f"- **{key_cn}**: {value}")
            lines.append("")
        
        if self.preferences:
            lines.append("## 用户偏好\n")
            for pref in self.preferences.values():
                if pref.confidence >= 0.3:
                    lines.append(f"- {pref.key}: {pref.value}")
            lines.append("")
        
        if self.important_events:
            lines.append("## 重要事件\n")
            sorted_events = sorted(
                self.important_events, 
                key=lambda e: e.event_date
            )
            for event in sorted_events[:20]:
                lines.append(f"- **{event.event_date}**: {event.title}")
                if event.description:
                    lines.append(f"  - {event.description}")
            lines.append("")
        
        if self.conversation_summary:
            lines.append("## 对话摘要\n")
            for summary in self.conversation_summary[-10:]:
                lines.append(f"- {summary}")
            lines.append("")
        
        if self.recent_context:
            lines.append("## 最近上下文\n")
            for ctx in self.recent_context[-10:]:
                lines.append(f"- {ctx}")
            lines.append("")
        
        if self.memory_notes:
            lines.append("## 备忘录\n")
            sorted_notes = sorted(
                self.memory_notes, 
                key=lambda n: n.priority, 
                reverse=True
            )
            for note in sorted_notes[:20]:
                priority_mark = "⭐" * min(note.priority, 5)
                lines.append(f"- {priority_mark} {note.content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _translate_key(self, key: str) -> str:
        """翻译键名为中文"""
        translations = {
            "name": "姓名",
            "nickname": "昵称",
            "email": "邮箱",
            "phone": "电话",
            "city": "城市",
            "location": "位置",
            "birthday": "生日",
            "timezone": "时区",
            "language": "语言",
            "occupation": "职业",
            "company": "公司"
        }
        return translations.get(key, key)
    
    def update_memory_md(self):
        """更新MEMORY.md文件"""
        content = self.generate_memory_md()
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"📝 MEMORY.md 已更新")
        except Exception as e:
            logger.error(f"❌ 更新MEMORY.md失败: {e}")
    
    def update_user_profile(self, key: str, value: Any) -> bool:
        """更新用户档案"""
        if hasattr(self.user_profile, key):
            setattr(self.user_profile, key, value)
            self._save_memory_data()
            self.update_memory_md()
            logger.info(f"👤 用户档案已更新: {key} = {value}")
            return True
        return False
    
    def set_user_profile(self, profile: UserProfile):
        """设置用户档案"""
        self.user_profile = profile
        self._save_memory_data()
        self.update_memory_md()
        logger.info(f"👤 用户档案已设置: {profile.name}")
    
    def update_preference(
        self, 
        key: str, 
        value: Any, 
        category: str = "general",
        confidence: float = 0.5,
        source: str = "learned"
    ) -> bool:
        """更新用户偏好"""
        pref_key = f"{category}:{key}"
        
        if pref_key in self.preferences:
            self.preferences[pref_key].value = value
            self.preferences[pref_key].confidence = min(confidence, 1.0)
            self.preferences[pref_key].updated_at = datetime.now().isoformat()
        else:
            self.preferences[pref_key] = UserPreference(
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source=source
            )
        
        self._save_memory_data()
        self.update_memory_md()
        logger.info(f"⚙️ 用户偏好已更新: {key} = {value} (置信度: {confidence:.2f})")
        return True
    
    def get_preference(self, key: str, category: str = "general") -> Optional[Any]:
        """获取用户偏好"""
        pref_key = f"{category}:{key}"
        if pref_key in self.preferences:
            return self.preferences[pref_key].value
        return None
    
    def add_important_event(
        self,
        title: str,
        event_date: str,
        event_type: str = "general",
        description: str = "",
        is_recurring: bool = False,
        recurring_type: str = "",
        reminder_days: int = 1
    ) -> str:
        """添加重要事件"""
        import uuid
        
        event = ImportantEvent(
            event_id=str(uuid.uuid4()),
            title=title,
            event_date=event_date,
            event_type=event_type,
            description=description,
            is_recurring=is_recurring,
            recurring_type=recurring_type,
            reminder_days=reminder_days
        )
        
        self.important_events.append(event)
        self._save_memory_data()
        self.update_memory_md()
        logger.info(f"📅 重要事件已添加: {title} @ {event_date}")
        
        return event.event_id
    
    def get_upcoming_events(self, days: int = 7) -> List[ImportantEvent]:
        """获取即将到来的事件"""
        today = datetime.now().date()
        future = today + timedelta(days=days)
        
        upcoming = []
        for event in self.important_events:
            try:
                event_date = datetime.strptime(event.event_date, "%Y-%m-%d").date()
                if today <= event_date <= future:
                    upcoming.append(event)
            except ValueError:
                continue
        
        return sorted(upcoming, key=lambda e: e.event_date)
    
    def remove_event(self, event_id: str) -> bool:
        """删除事件"""
        for i, event in enumerate(self.important_events):
            if event.event_id == event_id:
                self.important_events.pop(i)
                self._save_memory_data()
                self.update_memory_md()
                logger.info(f"📅 事件已删除: {event_id}")
                return True
        return False
    
    def add_memory_note(
        self, 
        content: str, 
        category: str = "general",
        priority: int = 5,
        source: str = "manual"
    ):
        """添加记忆笔记"""
        note = MemoryNote(
            content=content,
            category=category,
            priority=min(max(priority, 1), 10),
            source=source
        )
        
        self.memory_notes.append(note)
        
        if len(self.memory_notes) > 100:
            self.memory_notes = sorted(
                self.memory_notes, 
                key=lambda n: n.priority, 
                reverse=True
            )[:100]
        
        self._save_memory_data()
        self.update_memory_md()
        logger.info(f"📝 备忘录已添加: {content[:50]}...")
    
    def add_context(self, context: str):
        """添加上下文"""
        self.recent_context.append(context)
        
        if len(self.recent_context) > 100:
            self.recent_context = self.recent_context[-100:]
        
        self._save_memory_data()
    
    def add_conversation_summary(self, summary: str):
        """添加对话摘要"""
        self.conversation_summary.append(summary)
        
        if len(self.conversation_summary) > 50:
            self.conversation_summary = self.conversation_summary[-50:]
        
        self._save_memory_data()
        self.update_memory_md()
    
    def get_memory_for_llm(self) -> str:
        """获取给LLM的记忆内容"""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding='utf-8')
        return self.generate_memory_md()
    
    def search_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        results = []
        query_lower = query.lower()
        
        for note in self.memory_notes:
            if query_lower in note.content.lower():
                results.append({
                    "type": "note",
                    "content": note.content,
                    "category": note.category,
                    "priority": note.priority
                })
        
        for event in self.important_events:
            if (query_lower in event.title.lower() or 
                query_lower in event.description.lower()):
                results.append({
                    "type": "event",
                    "content": f"{event.event_date}: {event.title}",
                    "date": event.event_date
                })
        
        for key, pref in self.preferences.items():
            if (query_lower in pref.key.lower() or 
                query_lower in str(pref.value).lower()):
                results.append({
                    "type": "preference",
                    "content": f"{pref.key}: {pref.value}",
                    "confidence": pref.confidence
                })
        
        return results[:limit]
    
    def get_stats(self) -> Dict:
        """获取记忆统计"""
        return {
            "user_profile_set": bool(self.user_profile.name),
            "preferences_count": len(self.preferences),
            "events_count": len(self.important_events),
            "notes_count": len(self.memory_notes),
            "context_count": len(self.recent_context),
            "summary_count": len(self.conversation_summary)
        }
    
    def clear_all(self):
        """清空所有记忆（慎用）"""
        self.user_profile = UserProfile()
        self.preferences.clear()
        self.important_events.clear()
        self.memory_notes.clear()
        self.recent_context.clear()
        self.conversation_summary.clear()
        
        self._save_memory_data()
        self.update_memory_md()
        logger.warning("⚠️ 所有记忆已清空")
    
    def export_memory(self) -> Dict:
        """导出记忆"""
        return {
            "user_profile": self.user_profile.to_dict(),
            "preferences": {k: asdict(v) for k, v in self.preferences.items()},
            "important_events": [asdict(e) for e in self.important_events],
            "memory_notes": [asdict(n) for n in self.memory_notes],
            "recent_context": self.recent_context,
            "conversation_summary": self.conversation_summary
        }
    
    def import_memory(self, data: Dict):
        """导入记忆"""
        if "user_profile" in data:
            self.user_profile = UserProfile.from_dict(data["user_profile"])
        
        if "preferences" in data:
            self.preferences = {
                k: UserPreference(**v) 
                for k, v in data["preferences"].items()
            }
        
        if "important_events" in data:
            self.important_events = [
                ImportantEvent(**e) 
                for e in data["important_events"]
            ]
        
        if "memory_notes" in data:
            self.memory_notes = [
                MemoryNote(**n) 
                for n in data["memory_notes"]
            ]
        
        self.recent_context = data.get("recent_context", [])
        self.conversation_summary = data.get("conversation_summary", [])
        
        self._save_memory_data()
        self.update_memory_md()
        logger.info("📥 记忆已导入")


unified_memory = UnifiedMemory()
