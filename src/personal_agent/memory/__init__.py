"""
Memory Module - 记忆模块

包含：
1. UnifiedMemory - 统一记忆系统（推荐使用）
2. MemoryLearner - 记忆学习器
3. EnhancedMemoryManager - 增强记忆管理器
4. ShortTermMemory - 短期记忆
5. VectorMemory - 向量记忆（原LongTermMemory）
6. SQLiteMemory - SQLite记忆（原long_term_memory.py）
7. HistoryManager - 历史记录管理
"""

from .base import BaseMemory, MemoryItem as BaseMemoryItem
from .short_term import ShortTermMemory, ConversationTurn
from .long_term import LongTermMemory as VectorMemory
from .manager import MemoryManager
from .history_manager import HistoryManager, history_manager

from .unified_memory import (
    UnifiedMemory, 
    UserProfile, 
    UserPreference, 
    ImportantEvent,
    MemoryNote,
    unified_memory
)
from .memory_learner import MemoryLearner, memory_learner
from .memory_manager_enhanced import (
    EnhancedMemoryManager, 
    MemoryItem,
    enhanced_memory_manager
)

__all__ = [
    "BaseMemory",
    "BaseMemoryItem",
    "ShortTermMemory",
    "ConversationTurn",
    "VectorMemory",
    "LongTermMemory",
    "MemoryManager",
    "HistoryManager",
    "history_manager",
    "UnifiedMemory",
    "UserProfile",
    "UserPreference",
    "ImportantEvent",
    "MemoryNote",
    "unified_memory",
    "MemoryLearner",
    "memory_learner",
    "EnhancedMemoryManager",
    "MemoryItem",
    "enhanced_memory_manager",
]

LongTermMemory = VectorMemory
