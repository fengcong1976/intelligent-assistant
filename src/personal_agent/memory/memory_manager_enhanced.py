"""
Enhanced Memory Manager - 增强记忆管理器
支持记忆优先级、遗忘机制和智能检索
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, field
import math


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    category: str = "general"
    priority: int = 5
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    source: str = "user"
    metadata: Dict = field(default_factory=dict)
    
    def access(self):
        """访问记忆"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def calculate_importance(self) -> float:
        """计算重要性分数"""
        now = datetime.now()
        age_hours = (now - self.created_at).total_seconds() / 3600
        recency_hours = (now - self.last_accessed).total_seconds() / 3600
        
        priority_score = self.priority / 10.0
        
        access_score = min(self.access_count / 20.0, 1.0)
        
        recency_score = math.exp(-recency_hours / 168.0)
        
        age_decay = math.exp(-age_hours / 720.0)
        
        importance = (
            priority_score * 0.4 +
            access_score * 0.25 +
            recency_score * 0.2 +
            age_decay * 0.15
        )
        
        self.importance = max(0, min(1, importance))
        return self.importance
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "priority": self.priority,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata
        }


class EnhancedMemoryManager:
    """
    增强记忆管理器
    
    功能：
    1. 记忆优先级管理
    2. 遗忘机制
    3. 智能检索
    4. 记忆压缩
    5. 记忆过期清理
    """
    
    def __init__(
        self,
        max_items: int = 1000,
        forget_threshold: float = 0.15,
        cleanup_interval: int = 100
    ):
        self.max_items = max_items
        self.forget_threshold = forget_threshold
        self.cleanup_interval = cleanup_interval
        
        self.memories: Dict[str, MemoryItem] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.access_count = 0
        
        self.retention_policy = {
            "critical": 365,
            "important": 90,
            "normal": 30,
            "low": 7
        }
    
    def add_memory(
        self,
        content: str,
        category: str = "general",
        priority: int = 5,
        source: str = "user",
        metadata: Dict = None
    ) -> str:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            category: 记忆分类
            priority: 优先级 (1-10)
            source: 来源
            metadata: 元数据
        
        Returns:
            记忆ID
        """
        import uuid
        
        memory_id = str(uuid.uuid4())
        
        priority = max(1, min(10, priority))
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            category=category,
            priority=priority,
            source=source,
            metadata=metadata or {}
        )
        
        memory.calculate_importance()
        
        self.memories[memory_id] = memory
        
        if category not in self.category_index:
            self.category_index[category] = []
        self.category_index[category].append(memory_id)
        
        self.access_count += 1
        
        if len(self.memories) > self.max_items:
            self._forget_low_priority()
        
        if self.access_count % self.cleanup_interval == 0:
            self._cleanup_expired_memories()
        
        logger.debug(f"📝 添加记忆: {content[:50]}... (优先级: {priority})")
        
        return memory_id
    
    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.access()
            memory.calculate_importance()
            return memory
        return None
    
    def search_memories(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryItem]:
        """
        搜索记忆
        
        Args:
            query: 搜索关键词
            category: 分类过滤
            limit: 返回数量限制
            min_importance: 最小重要性阈值
        
        Returns:
            匹配的记忆列表
        """
        results = []
        query_lower = query.lower()
        
        search_pool = self.memories.values()
        if category and category in self.category_index:
            search_pool = [
                self.memories[mid] 
                for mid in self.category_index[category] 
                if mid in self.memories
            ]
        
        for memory in search_pool:
            if query_lower in memory.content.lower():
                memory.calculate_importance()
                
                if memory.importance >= min_importance:
                    memory.access()
                    results.append(memory)
        
        results.sort(key=lambda m: m.importance, reverse=True)
        
        return results[:limit]
    
    def get_recent_memories(
        self,
        category: str = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """获取最近记忆"""
        search_pool = self.memories.values()
        if category and category in self.category_index:
            search_pool = [
                self.memories[mid] 
                for mid in self.category_index[category] 
                if mid in self.memories
            ]
        
        sorted_memories = sorted(
            search_pool,
            key=lambda m: m.last_accessed,
            reverse=True
        )
        
        for memory in sorted_memories[:limit]:
            memory.access()
        
        return sorted_memories[:limit]
    
    def get_important_memories(
        self,
        limit: int = 10,
        min_priority: int = 7
    ) -> List[MemoryItem]:
        """获取重要记忆"""
        important = [
            m for m in self.memories.values()
            if m.priority >= min_priority
        ]
        
        for memory in important:
            memory.calculate_importance()
        
        important.sort(key=lambda m: m.importance, reverse=True)
        
        return important[:limit]
    
    def update_memory(
        self,
        memory_id: str,
        content: str = None,
        priority: int = None,
        metadata: Dict = None
    ) -> bool:
        """更新记忆"""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        if content is not None:
            memory.content = content
        
        if priority is not None:
            memory.priority = max(1, min(10, priority))
        
        if metadata is not None:
            memory.metadata.update(metadata)
        
        memory.calculate_importance()
        memory.access()
        
        logger.debug(f"📝 更新记忆: {memory_id}")
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        if memory.category in self.category_index:
            if memory_id in self.category_index[memory.category]:
                self.category_index[memory.category].remove(memory_id)
        
        del self.memories[memory_id]
        
        logger.debug(f"🗑️ 删除记忆: {memory_id}")
        return True
    
    def _forget_low_priority(self):
        """遗忘低优先级记忆"""
        for memory in self.memories.values():
            memory.calculate_importance()
        
        sorted_memories = sorted(
            self.memories.items(),
            key=lambda x: x[1].importance
        )
        
        forget_count = 0
        target_count = int(self.max_items * 0.9)
        
        for memory_id, memory in sorted_memories:
            if len(self.memories) <= target_count:
                break
            
            if memory.importance < self.forget_threshold:
                self.delete_memory(memory_id)
                forget_count += 1
        
        if forget_count > 0:
            logger.info(f"🧹 遗忘 {forget_count} 条低优先级记忆")
    
    def _cleanup_expired_memories(self):
        """清理过期记忆"""
        now = datetime.now()
        expired = []
        
        for memory_id, memory in self.memories.items():
            retention_days = self._get_retention_days(memory)
            expiry_date = memory.created_at + timedelta(days=retention_days)
            
            if now > expiry_date and memory.priority < 8:
                expired.append(memory_id)
        
        for memory_id in expired:
            self.delete_memory(memory_id)
        
        if expired:
            logger.info(f"🧹 清理 {len(expired)} 条过期记忆")
    
    def _get_retention_days(self, memory: MemoryItem) -> int:
        """获取记忆保留天数"""
        if memory.priority >= 9:
            return self.retention_policy["critical"]
        elif memory.priority >= 7:
            return self.retention_policy["important"]
        elif memory.priority >= 4:
            return self.retention_policy["normal"]
        else:
            return self.retention_policy["low"]
    
    def compress_memories(self, category: str = None) -> int:
        """
        压缩记忆（合并相似记忆）
        
        Args:
            category: 指定分类，None表示全部
        
        Returns:
            压缩后的记忆数量
        """
        search_pool = self.memories.values()
        if category and category in self.category_index:
            search_pool = [
                self.memories[mid] 
                for mid in self.category_index[category] 
                if mid in self.memories
            ]
        
        similar_groups = self._find_similar_memories(list(search_pool))
        
        compressed_count = 0
        for group in similar_groups:
            if len(group) > 1:
                merged = self._merge_memories(group)
                
                for memory in group[1:]:
                    self.delete_memory(memory.id)
                    compressed_count += 1
                
                self.memories[group[0].id] = merged
        
        if compressed_count > 0:
            logger.info(f"🗜️ 压缩 {compressed_count} 条相似记忆")
        
        return compressed_count
    
    def _find_similar_memories(
        self, 
        memories: List[MemoryItem],
        similarity_threshold: float = 0.8
    ) -> List[List[MemoryItem]]:
        """查找相似记忆"""
        groups = []
        processed = set()
        
        for i, memory1 in enumerate(memories):
            if memory1.id in processed:
                continue
            
            group = [memory1]
            processed.add(memory1.id)
            
            for j, memory2 in enumerate(memories[i+1:], i+1):
                if memory2.id in processed:
                    continue
                
                if self._calculate_similarity(memory1.content, memory2.content) >= similarity_threshold:
                    group.append(memory2)
                    processed.add(memory2.id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简单Jaccard相似度）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _merge_memories(self, memories: List[MemoryItem]) -> MemoryItem:
        """合并多条记忆"""
        best_memory = max(memories, key=lambda m: m.importance)
        
        total_access = sum(m.access_count for m in memories)
        best_memory.access_count = total_access
        
        best_memory.priority = max(m.priority for m in memories)
        
        best_memory.calculate_importance()
        
        return best_memory
    
    def get_stats(self) -> Dict:
        """获取记忆统计"""
        total_memories = len(self.memories)
        
        if not total_memories:
            return {
                "total": 0,
                "categories": {},
                "avg_importance": 0,
                "avg_access_count": 0
            }
        
        category_counts = {
            cat: len(ids) 
            for cat, ids in self.category_index.items()
        }
        
        avg_importance = sum(m.importance for m in self.memories.values()) / total_memories
        avg_access = sum(m.access_count for m in self.memories.values()) / total_memories
        
        return {
            "total": total_memories,
            "categories": category_counts,
            "avg_importance": round(avg_importance, 3),
            "avg_access_count": round(avg_access, 2),
            "max_items": self.max_items,
            "forget_threshold": self.forget_threshold
        }
    
    def clear_all(self):
        """清空所有记忆"""
        self.memories.clear()
        self.category_index.clear()
        self.access_count = 0
        logger.warning("⚠️ 所有记忆已清空")
    
    def export_memories(self) -> List[Dict]:
        """导出记忆"""
        return [m.to_dict() for m in self.memories.values()]
    
    def import_memories(self, memories_data: List[Dict]):
        """导入记忆"""
        for data in memories_data:
            memory = MemoryItem(
                id=data["id"],
                content=data["content"],
                category=data.get("category", "general"),
                priority=data.get("priority", 5),
                importance=data.get("importance", 0.5),
                created_at=datetime.fromisoformat(data["created_at"]),
                last_accessed=datetime.fromisoformat(data["last_accessed"]),
                access_count=data.get("access_count", 0),
                source=data.get("source", "user"),
                metadata=data.get("metadata", {})
            )
            
            self.memories[memory.id] = memory
            
            if memory.category not in self.category_index:
                self.category_index[memory.category] = []
            self.category_index[memory.category].append(memory.id)
        
        logger.info(f"📥 导入 {len(memories_data)} 条记忆")


enhanced_memory_manager = EnhancedMemoryManager()
