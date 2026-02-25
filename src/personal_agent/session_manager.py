"""
Simple Session Manager - 轻量级会话管理器
支持会话持久化，无需常驻服务
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


class SimpleSessionManager:
    """
    轻量级会话管理器
    
    功能：
    1. 会话持久化（保存到文件）
    2. 会话恢复（从文件加载）
    3. 自动清理过期会话
    
    特点：
    - 无需常驻服务
    - 简单易维护
    - 自动保存
    """
    
    def __init__(self, storage_path: Path = None, auto_save: bool = True):
        self.storage_path = storage_path or Path.home() / ".personal_agent" / "sessions"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save
        
        self.current_session: Dict[str, Any] = {}
        self._current_user_id: str = "default"
        
        self._load_session()
    
    def _get_session_file(self, user_id: str) -> Path:
        """获取会话文件路径"""
        return self.storage_path / f"{user_id}.json"
    
    def _load_session(self, user_id: str = "default") -> Dict:
        """加载会话"""
        session_file = self._get_session_file(user_id)
        
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session = json.load(f)
                    
                self.current_session = session
                self._current_user_id = user_id
                return session
                
            except Exception as e:
                pass
        
        self.current_session = self._create_new_session(user_id)
        self._current_user_id = user_id
        return self.current_session
    
    def _create_new_session(self, user_id: str) -> Dict:
        """创建新会话"""
        return {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "context": {},
            "preferences": {},
            "last_intent": None,
            "statistics": {
                "total_messages": 0,
                "total_tasks": 0,
                "successful_tasks": 0
            }
        }
    
    def save_session(self, user_id: str = None):
        """保存会话"""
        if user_id is None:
            user_id = self._current_user_id
        
        session_file = self._get_session_file(user_id)
        
        try:
            self.current_session["updated_at"] = datetime.now().isoformat()
            
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(self.current_session, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 会话已保存: {user_id}")
            
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
    
    def switch_user(self, user_id: str):
        """切换用户"""
        if user_id != self._current_user_id:
            self.save_session()
            self._load_session(user_id)
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息到会话"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.current_session["messages"].append(message)
        
        self.current_session["statistics"]["total_messages"] += 1
        
        if len(self.current_session["messages"]) > 100:
            self.current_session["messages"] = self.current_session["messages"][-50:]
        
        if self.auto_save:
            self.save_session()
    
    def get_messages(self, limit: int = 20) -> List[Dict]:
        """获取最近的消息"""
        return self.current_session["messages"][-limit:]
    
    def get_context(self) -> Dict:
        """获取会话上下文"""
        return self.current_session.get("context", {})
    
    def set_context(self, key: str, value: Any):
        """设置会话上下文"""
        self.current_session["context"][key] = value
        
        if self.auto_save:
            self.save_session()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好"""
        return self.current_session.get("preferences", {}).get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        if "preferences" not in self.current_session:
            self.current_session["preferences"] = {}
        
        self.current_session["preferences"][key] = value
        
        if self.auto_save:
            self.save_session()
    
    def update_statistics(self, task_success: bool = True):
        """更新统计信息"""
        stats = self.current_session["statistics"]
        stats["total_tasks"] += 1
        if task_success:
            stats["successful_tasks"] += 1
        
        if self.auto_save:
            self.save_session()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.current_session.get("statistics", {})
    
    def clear_messages(self):
        """清空消息历史"""
        self.current_session["messages"] = []
        
        if self.auto_save:
            self.save_session()
        
        logger.info("🧹 会话消息已清空")
    
    def clear_session(self):
        """清空当前会话"""
        user_id = self._current_user_id
        self.current_session = self._create_new_session(user_id)
        
        if self.auto_save:
            self.save_session()
        
        logger.info("🧹 会话已重置")
    
    def export_session(self) -> str:
        """导出会话为JSON字符串"""
        return json.dumps(self.current_session, ensure_ascii=False, indent=2)
    
    def import_session(self, json_str: str):
        """从JSON字符串导入会话"""
        try:
            self.current_session = json.loads(json_str)
            
            if self.auto_save:
                self.save_session()
            
            logger.info("📥 会话已导入")
            
        except Exception as e:
            logger.error(f"导入会话失败: {e}")
    
    def cleanup_old_sessions(self, days: int = 30):
        """清理过期会话"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session = json.load(f)
                
                updated_at = datetime.fromisoformat(session.get("updated_at", ""))
                
                if updated_at < cutoff:
                    session_file.unlink()
                    cleaned += 1
                    
            except Exception as e:
                logger.debug(f"清理会话文件失败 {session_file}: {e}")
        
        if cleaned > 0:
            logger.info(f"🧹 已清理 {cleaned} 个过期会话")


simple_session_manager = SimpleSessionManager()
