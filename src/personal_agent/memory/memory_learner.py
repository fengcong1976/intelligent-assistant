"""
Memory Learner - 记忆学习器
从对话中自动提取和更新记忆
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
import re

from .unified_memory import UnifiedMemory


class MemoryLearner:
    """
    记忆学习器 - 从对话中自动学习
    
    功能：
    1. 提取用户信息（姓名、位置、生日等）
    2. 学习用户偏好
    3. 识别重要事件
    4. 提取关键信息作为备忘
    """
    
    def __init__(self, memory: UnifiedMemory = None):
        self.memory = memory or UnifiedMemory()
        
        self.extraction_patterns = {
            "name": [
                (r"我叫([^\s，。！？,]+)", 0.9),
                (r"我是([^\s，。！？,]+)", 0.7),
                (r"我的名字(?:叫|是)([^\s，。！？,]+)", 0.9),
                (r"你可以叫我([^\s，。！？,]+)", 0.9),
            ],
            "nickname": [
                (r"我的昵称(?:叫|是)([^\s，。！？,]+)", 0.9),
                (r"大家叫我([^\s，。！？,]+)", 0.8),
            ],
            "location": [
                (r"我在([^\s，。！？,]+)", 0.8),
                (r"我住在([^\s，。！？,]+)", 0.9),
                (r"我的位置(?:是|在)([^\s，。！？,]+)", 0.9),
                (r"我在([^\s，。！？,]+)(?:工作|生活)", 0.8),
            ],
            "city": [
                (r"我在([^\s，。！？,]+)市", 0.9),
                (r"我住在([^\s，。！？,]+)市", 0.9),
                (r"我的城市(?:是|在)([^\s，。！？,]+)", 0.9),
            ],
            "birthday": [
                (r"我的生日(?:是|在)(\d{1,2})月(\d{1,2})[日号]?", 0.9),
                (r"我(\d{1,2})月(\d{1,2})[日号]?出生", 0.9),
                (r"我的生日(?:是|在)(\d{4})年(\d{1,2})月(\d{1,2})[日号]?", 0.9),
            ],
            "email": [
                (r"我的邮箱(?:是|:)?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", 0.95),
                (r"发到([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", 0.7),
            ],
            "phone": [
                (r"我的电话(?:是|:)?\s*(1[3-9]\d{9})", 0.9),
                (r"我的手机(?:是|:)?\s*(1[3-9]\d{9})", 0.9),
            ],
            "occupation": [
                (r"我是([^\s，。！？,]+)(?:工程师|设计师|经理|老师|医生|学生)", 0.8),
                (r"我是一名([^\s，。！？,]+)", 0.7),
                (r"我的职业(?:是|:)([^\s，。！？,]+)", 0.9),
            ],
            "company": [
                (r"我在([^\s，。！？,]+)工作", 0.8),
                (r"我的公司(?:是|:)([^\s，。！？,]+)", 0.9),
            ],
        }
        
        self.preference_patterns = {
            "communication_style": [
                (r"我喜欢(简洁|详细|简短|详细)的回复", "简洁回复" if "简洁" in r"我喜欢简洁的回复" else "详细回复", 0.8),
                (r"请(简洁|简短)一点", "简洁回复", 0.9),
                (r"请(详细|具体)一点", "详细回复", 0.9),
            ],
            "language": [
                (r"请用(中文|英文|粤语)回复", lambda m: m.group(1), 0.9),
                (r"我喜欢用(中文|英文|粤语)交流", lambda m: m.group(1), 0.8),
            ],
            "time_format": [
                (r"我喜欢(24小时|12小时)制", lambda m: m.group(1), 0.8),
            ],
            "general": [
                (r"我喜欢([^\s，。！？,]+)", lambda m: m.group(1), 0.6),
                (r"我偏好([^\s，。！？,]+)", lambda m: m.group(1), 0.7),
                (r"我比较喜欢([^\s，。！？,]+)", lambda m: m.group(1), 0.7),
                (r"我不喜欢([^\s，。！？,]+)", lambda m: f"不喜欢{m.group(1)}", 0.7),
            ],
        }
        
        self.event_patterns = [
            (r"(\d{1,2})月(\d{1,2})[日号]?我有([^\s，。！？,]+)", "date_event"),
            (r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]?是([^\s，。！？,]+)", "date_event"),
            (r"下周([一二三四五六日天])(?:有|是|要)([^\s，。！？,]+)", "weekday_event"),
            (r"明天(?:有|是|要)([^\s，。！？,]+)", "tomorrow_event"),
            (r"后天(?:有|是|要)([^\s，。！？,]+)", "day_after_event"),
        ]
        
        self.important_keywords = [
            "生日", "结婚", "纪念日", "会议", "面试", "考试", 
            "航班", "火车", "预约", "截止", "重要"
        ]
    
    def learn_from_message(self, role: str, content: str) -> Dict:
        """
        从消息中学习
        
        Args:
            role: 消息角色 (user/assistant)
            content: 消息内容
        
        Returns:
            学习结果
        """
        if role != "user":
            return {"learned": False, "reason": "只从用户消息学习"}
        
        results = {
            "learned": False,
            "profile_updates": [],
            "preference_updates": [],
            "events_detected": [],
            "notes_added": []
        }
        
        profile_updates = self._extract_user_info(content)
        results["profile_updates"] = profile_updates
        if profile_updates:
            results["learned"] = True
        
        preference_updates = self._extract_preferences(content)
        results["preference_updates"] = preference_updates
        if preference_updates:
            results["learned"] = True
        
        events_detected = self._extract_events(content)
        results["events_detected"] = events_detected
        if events_detected:
            results["learned"] = True
        
        notes_added = self._extract_important_info(content)
        results["notes_added"] = notes_added
        if notes_added:
            results["learned"] = True
        
        if results["learned"]:
            logger.info(f"🧠 从消息中学习: {len(profile_updates)} 档案, {len(preference_updates)} 偏好, {len(events_detected)} 事件")
        
        return results
    
    def _extract_user_info(self, content: str) -> List[Dict]:
        """提取用户信息"""
        updates = []
        
        for field, patterns in self.extraction_patterns.items():
            for pattern, confidence in patterns:
                match = re.search(pattern, content)
                if match:
                    value = self._extract_value(match, field)
                    if value:
                        old_value = getattr(self.memory.user_profile, field, None)
                        if old_value and old_value != value:
                            continue
                        
                        self.memory.update_user_profile(field, value)
                        updates.append({
                            "field": field,
                            "value": value,
                            "confidence": confidence
                        })
                        break
        
        return updates
    
    def _extract_value(self, match, field: str) -> Optional[str]:
        """从匹配中提取值"""
        if field == "birthday":
            groups = match.groups()
            if len(groups) == 2:
                month, day = groups
                return f"{datetime.now().year}-{int(month):02d}-{int(day):02d}"
            elif len(groups) == 3:
                year, month, day = groups
                return f"{year}-{int(month):02d}-{int(day):02d}"
        else:
            return match.group(1).strip()
        
        return None
    
    def _extract_preferences(self, content: str) -> List[Dict]:
        """提取用户偏好"""
        updates = []
        
        for category, patterns in self.preference_patterns.items():
            for pattern, value_extractor, confidence in patterns:
                match = re.search(pattern, content)
                if match:
                    if callable(value_extractor):
                        value = value_extractor(match)
                    else:
                        value = value_extractor
                    
                    if value:
                        self.memory.update_preference(
                            key=category,
                            value=value,
                            category="preference",
                            confidence=confidence
                        )
                        updates.append({
                            "category": category,
                            "value": value,
                            "confidence": confidence
                        })
                        break
        
        return updates
    
    def _extract_events(self, content: str) -> List[Dict]:
        """提取重要事件"""
        events = []
        today = datetime.now()
        
        for pattern, event_type in self.event_patterns:
            match = re.search(pattern, content)
            if match:
                groups = match.groups()
                
                if event_type == "date_event":
                    if len(groups) == 3:
                        month, day, title = groups
                        event_date = f"{today.year}-{int(month):02d}-{int(day):02d}"
                    elif len(groups) == 4:
                        year, month, day, title = groups
                        event_date = f"{year}-{int(month):02d}-{int(day):02d}"
                    else:
                        continue
                    
                    self.memory.add_important_event(
                        title=title,
                        event_date=event_date,
                        event_type="user_mentioned"
                    )
                    events.append({
                        "title": title,
                        "date": event_date,
                        "type": event_type
                    })
                
                elif event_type == "tomorrow_event":
                    title = groups[0]
                    event_date = (today + __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
                    self.memory.add_important_event(
                        title=title,
                        event_date=event_date,
                        event_type="user_mentioned"
                    )
                    events.append({
                        "title": title,
                        "date": event_date,
                        "type": event_type
                    })
                
                elif event_type == "day_after_event":
                    title = groups[0]
                    event_date = (today + __import__('datetime').timedelta(days=2)).strftime("%Y-%m-%d")
                    self.memory.add_important_event(
                        title=title,
                        event_date=event_date,
                        event_type="user_mentioned"
                    )
                    events.append({
                        "title": title,
                        "date": event_date,
                        "type": event_type
                    })
        
        return events
    
    def _extract_important_info(self, content: str) -> List[str]:
        """提取重要信息作为备忘"""
        notes = []
        
        for keyword in self.important_keywords:
            if keyword in content:
                sentences = re.split(r'[。！？\n]', content)
                for sentence in sentences:
                    if keyword in sentence and len(sentence) > 5:
                        self.memory.add_memory_note(
                            content=sentence.strip(),
                            category="important",
                            priority=7,
                            source="auto_extracted"
                        )
                        notes.append(sentence.strip())
                        break
        
        return notes
    
    def learn_from_conversation(self, messages: List[Dict]) -> Dict:
        """
        从完整对话中学习
        
        Args:
            messages: 消息列表 [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            学习结果汇总
        """
        results = {
            "total_learned": 0,
            "profile_updates": [],
            "preference_updates": [],
            "events_detected": [],
            "notes_added": []
        }
        
        for message in messages:
            if message.get("role") == "user":
                msg_result = self.learn_from_message(
                    message["role"],
                    message["content"]
                )
                
                if msg_result.get("learned"):
                    results["total_learned"] += 1
                    results["profile_updates"].extend(msg_result.get("profile_updates", []))
                    results["preference_updates"].extend(msg_result.get("preference_updates", []))
                    results["events_detected"].extend(msg_result.get("events_detected", []))
                    results["notes_added"].extend(msg_result.get("notes_added", []))
        
        if results["total_learned"] > 0:
            logger.info(f"🧠 从对话中学习完成: {results['total_learned']} 条新信息")
        
        return results
    
    def summarize_conversation(self, messages: List[Dict]) -> str:
        """
        总结对话内容
        
        Args:
            messages: 消息列表
        
        Returns:
            对话摘要
        """
        user_messages = [
            m["content"] for m in messages 
            if m.get("role") == "user"
        ]
        
        if not user_messages:
            return ""
        
        topics = []
        
        action_keywords = ["发邮件", "查天气", "定闹钟", "提醒", "搜索", "播放", "下载", "保存"]
        for msg in user_messages:
            for keyword in action_keywords:
                if keyword in msg:
                    topics.append(f"用户请求{keyword}")
                    break
        
        if topics:
            summary = f"对话涉及: {', '.join(set(topics[:5]))}"
        else:
            summary = f"对话包含 {len(user_messages)} 条用户消息"
        
        return summary


memory_learner = MemoryLearner()
