"""
Memory Manager - 统一记忆管理器
整合所有记忆组件，提供统一接口
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from .base import MemoryItem as BaseMemoryItem
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .unified_memory import UnifiedMemory, unified_memory
from .memory_learner import MemoryLearner
from .memory_manager_enhanced import EnhancedMemoryManager


class MemoryManager:
    """
    统一记忆管理器
    
    整合：
    1. ShortTermMemory - 短期记忆（会话历史）
    2. LongTermMemory - 向量记忆（语义搜索）
    3. UnifiedMemory - 统一记忆（用户档案、偏好、事件）
    4. MemoryLearner - 记忆学习器
    5. EnhancedMemoryManager - 增强记忆管理器
    """
    
    def __init__(
        self,
        session_id: str,
        db_path: Path = Path("./data/memory"),
        collection_name: str = "agent_memory",
        enable_learning: bool = True
    ):
        self.session_id = session_id
        self.db_path = db_path
        self.enable_learning = enable_learning
        
        self.short_term = ShortTermMemory(
            session_id=session_id,
            storage_path=db_path / "sessions"
        )
        
        self.long_term = LongTermMemory(
            db_path=db_path / "chroma",
            collection_name=collection_name
        )
        
        self.unified = unified_memory
        
        self.learner = MemoryLearner(self.unified) if enable_learning else None
        
        self.enhanced = EnhancedMemoryManager()

    async def add_conversation(
        self,
        role: str,
        content: str,
        save_to_long_term: bool = False,
        learn: bool = True
    ):
        """
        添加对话
        
        Args:
            role: 角色 (user/assistant/tool)
            content: 内容
            save_to_long_term: 是否保存到长期记忆
            learn: 是否学习
        """
        if role == "user":
            await self.short_term.add_user_message(content)
        elif role == "assistant":
            await self.short_term.add_assistant_message(content)
        else:
            await self.short_term.add_tool_message(content, role)

        if save_to_long_term and role in ["user", "assistant"]:
            await self.long_term.add(
                BaseMemoryItem(
                    content=content,
                    metadata={"role": role, "session_id": self.session_id}
                )
            )

        if learn and self.enable_learning and self.learner and role == "user":
            self.learner.learn_from_message(role, content)

    async def get_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """获取对话上下文"""
        return self.short_term.get_last_n_messages(max_turns)

    async def recall(self, query: str, limit: int = 5) -> List[BaseMemoryItem]:
        """回忆（向量搜索）"""
        return await self.long_term.search(query, limit)

    async def remember_important(self, content: str, metadata: Optional[Dict] = None):
        """记住重要信息"""
        await self.long_term.add(
            BaseMemoryItem(content=content, metadata=metadata or {})
        )

    async def clear_session(self):
        """清空当前会话"""
        await self.short_term.clear()

    async def clear_all(self):
        """清空所有记忆"""
        await self.short_term.clear()
        await self.long_term.clear()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.short_term.get_messages()

    def get_memory_for_llm(self) -> str:
        """获取给LLM的记忆内容（MEMORY.md）"""
        return self.unified.get_memory_for_llm()

    def update_user_profile(self, key: str, value: Any) -> bool:
        """更新用户档案"""
        return self.unified.update_user_profile(key, value)

    def get_user_profile(self) -> Dict:
        """获取用户档案"""
        return self.unified.user_profile.to_dict()

    def update_preference(self, key: str, value: Any, confidence: float = 0.5) -> bool:
        """更新用户偏好"""
        return self.unified.update_preference(key, value, confidence=confidence)

    def get_preference(self, key: str) -> Optional[Any]:
        """获取用户偏好"""
        return self.unified.get_preference(key)

    def add_important_event(
        self,
        title: str,
        event_date: str,
        event_type: str = "general",
        description: str = ""
    ) -> str:
        """添加重要事件"""
        return self.unified.add_important_event(
            title=title,
            event_date=event_date,
            event_type=event_type,
            description=description
        )

    def get_upcoming_events(self, days: int = 7) -> List:
        """获取即将到来的事件"""
        return self.unified.get_upcoming_events(days)

    def add_memory_note(self, content: str, priority: int = 5):
        """添加记忆笔记"""
        self.unified.add_memory_note(content, priority=priority)

    def search_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        return self.unified.search_memory(query, limit)

    def add_enhanced_memory(
        self,
        content: str,
        category: str = "general",
        priority: int = 5
    ) -> str:
        """添加增强记忆"""
        return self.enhanced.add_memory(
            content=content,
            category=category,
            priority=priority
        )

    def search_enhanced_memories(
        self,
        query: str,
        category: str = None,
        limit: int = 10
    ) -> List:
        """搜索增强记忆"""
        return self.enhanced.search_memories(query, category, limit)

    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        return {
            "unified": self.unified.get_stats(),
            "enhanced": self.enhanced.get_stats(),
            "short_term_count": len(self.short_term.conversation_history)
        }

    def learn_from_conversation(self, messages: List[Dict]) -> Dict:
        """从对话中学习"""
        if self.learner:
            return self.learner.learn_from_conversation(messages)
        return {"learned": False, "reason": "学习器未启用"}

    def export_all_memory(self) -> Dict:
        """导出所有记忆"""
        return {
            "unified": self.unified.export_memory(),
            "enhanced": self.enhanced.export_memories(),
            "session_id": self.session_id
        }

    def import_all_memory(self, data: Dict):
        """导入所有记忆"""
        if "unified" in data:
            self.unified.import_memory(data["unified"])
        
        if "enhanced" in data:
            self.enhanced.import_memories(data["enhanced"])
        
        logger.info("📥 所有记忆已导入")
