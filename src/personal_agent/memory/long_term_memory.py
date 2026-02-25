"""
Long-term Memory System - 长期记忆系统
永久保存用户信息、对话历史和重要事件
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger
from pathlib import Path


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    name: str
    email: str
    phone: str
    city: str
    address: str
    birthday: Optional[str] = None  # 格式: YYYY-MM-DD
    preferences: Dict[str, Any] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class ImportantEvent:
    """重要事件"""
    event_id: str
    user_id: str
    event_type: str  # birthday, anniversary, reminder, etc.
    event_date: str  # 格式: YYYY-MM-DD
    title: str
    description: str
    is_recurring: bool = False
    recurring_type: Optional[str] = None  # yearly, monthly, weekly
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class UserInsight:
    """用户洞察"""
    insight_id: str
    user_id: str
    insight_type: str  # preference, habit, interest, etc.
    content: str
    confidence: float  # 0.0 - 1.0
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class LongTermMemory:
    """长期记忆系统"""

    def __init__(self, db_path: str = "long_term_memory.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"🧠 长期记忆系统已初始化: {db_path}")

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 用户档案表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                city TEXT,
                address TEXT,
                birthday TEXT,
                preferences TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 重要事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS important_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT,
                event_type TEXT,
                event_date TEXT,
                title TEXT,
                description TEXT,
                is_recurring INTEGER,
                recurring_type TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        # 用户洞察表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_insights (
                insight_id TEXT PRIMARY KEY,
                user_id TEXT,
                insight_type TEXT,
                content TEXT,
                confidence REAL,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        # 对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def save_user_profile(self, profile: UserProfile) -> bool:
        """保存用户档案"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            profile.updated_at = datetime.now().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, name, email, phone, city, address, birthday, preferences, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                profile.name,
                profile.email,
                profile.phone,
                profile.city,
                profile.address,
                profile.birthday,
                json.dumps(profile.preferences),
                profile.created_at,
                profile.updated_at
            ))

            conn.commit()
            conn.close()
            logger.info(f"💾 用户档案已保存: {profile.name}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存用户档案失败: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户档案"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return UserProfile(
                    user_id=row[0],
                    name=row[1],
                    email=row[2],
                    phone=row[3],
                    city=row[4],
                    address=row[5],
                    birthday=row[6],
                    preferences=json.loads(row[7]) if row[7] else {},
                    created_at=row[8],
                    updated_at=row[9]
                )
            return None
        except Exception as e:
            logger.error(f"❌ 获取用户档案失败: {e}")
            return None

    def save_important_event(self, event: ImportantEvent) -> bool:
        """保存重要事件"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO important_events
                (event_id, user_id, event_type, event_date, title, description, is_recurring, recurring_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.user_id,
                event.event_type,
                event.event_date,
                event.title,
                event.description,
                1 if event.is_recurring else 0,
                event.recurring_type,
                event.created_at
            ))

            conn.commit()
            conn.close()
            logger.info(f"📅 重要事件已保存: {event.title}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存重要事件失败: {e}")
            return False

    def get_upcoming_events(self, user_id: str, days: int = 7) -> List[ImportantEvent]:
        """获取即将到来的事件"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT * FROM important_events
                WHERE user_id = ? AND event_date >= ? AND event_date <= date('now', '+' || ? || ' days')
                ORDER BY event_date
            """, (user_id, today, days))

            rows = cursor.fetchall()
            conn.close()

            events = []
            for row in rows:
                events.append(ImportantEvent(
                    event_id=row[0],
                    user_id=row[1],
                    event_type=row[2],
                    event_date=row[3],
                    title=row[4],
                    description=row[5],
                    is_recurring=bool(row[6]),
                    recurring_type=row[7],
                    created_at=row[8]
                ))

            return events
        except Exception as e:
            logger.error(f"❌ 获取即将到来的事件失败: {e}")
            return []

    def save_user_insight(self, insight: UserInsight) -> bool:
        """保存用户洞察"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            insight.updated_at = datetime.now().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO user_insights
                (insight_id, user_id, insight_type, content, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.insight_id,
                insight.user_id,
                insight.insight_type,
                insight.content,
                insight.confidence,
                insight.created_at,
                insight.updated_at
            ))

            conn.commit()
            conn.close()
            logger.info(f"💡 用户洞察已保存: {insight.content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"❌ 保存用户洞察失败: {e}")
            return False

    def get_user_insights(self, user_id: str, insight_type: Optional[str] = None) -> List[UserInsight]:
        """获取用户洞察"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if insight_type:
                cursor.execute("""
                    SELECT * FROM user_insights
                    WHERE user_id = ? AND insight_type = ?
                    ORDER BY updated_at DESC
                """, (user_id, insight_type))
            else:
                cursor.execute("""
                    SELECT * FROM user_insights
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                """, (user_id))

            rows = cursor.fetchall()
            conn.close()

            insights = []
            for row in rows:
                insights.append(UserInsight(
                    insight_id=row[0],
                    user_id=row[1],
                    insight_type=row[2],
                    content=row[3],
                    confidence=row[4],
                    created_at=row[5],
                    updated_at=row[6]
                ))

            return insights
        except Exception as e:
            logger.error(f"❌ 获取用户洞察失败: {e}")
            return []

    def save_conversation(self, user_id: str, conversation_id: str, role: str, content: str):
        """保存对话历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversation_history
                (user_id, conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                conversation_id,
                role,
                content,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ 保存对话历史失败: {e}")

    def get_conversation_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """获取对话历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT role, content, timestamp
                FROM conversation_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ 获取对话历史失败: {e}")
            return []
