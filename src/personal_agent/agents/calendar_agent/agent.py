"""
Calendar Agent - 日历管理智能体
支持创建、查询、修改、删除日程事件
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from loguru import logger

from ..base import BaseAgent, Task, Message


@dataclass
class CalendarEvent:
    """日程事件"""
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    title: str = ""
    date: str = ""
    time: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    reminder: Optional[str] = None
    repeat: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "CalendarEvent":
        return cls(**data)


class CalendarManager:
    """日历数据管理器"""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path.home() / ".personal_agent" / "calendar"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.data_dir / "events.json"
        self.events: Dict[str, CalendarEvent] = {}
        self._load_events()

    def _load_events(self):
        """加载事件数据"""
        try:
            if self.events_file.exists():
                with open(self.events_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.events = {
                        k: CalendarEvent.from_dict(v) for k, v in data.items()
                    }
                logger.info(f"📅 已加载 {len(self.events)} 个日程事件")
        except Exception as e:
            logger.error(f"加载日程数据失败: {e}")
            self.events = {}

    def _save_events(self):
        """保存事件数据"""
        try:
            with open(self.events_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self.events.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"保存日程数据失败: {e}")

    def add_event(self, event: CalendarEvent) -> CalendarEvent:
        """添加事件"""
        event.created_at = datetime.now().isoformat()
        event.updated_at = datetime.now().isoformat()
        self.events[event.id] = event
        self._save_events()
        return event

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """获取事件"""
        return self.events.get(event_id)

    def update_event(self, event_id: str, **kwargs) -> Optional[CalendarEvent]:
        """更新事件"""
        event = self.events.get(event_id)
        if event:
            for key, value in kwargs.items():
                if hasattr(event, key) and value is not None:
                    setattr(event, key, value)
            event.updated_at = datetime.now().isoformat()
            self._save_events()
        return event

    def delete_event(self, event_id: str) -> bool:
        """删除事件"""
        if event_id in self.events:
            del self.events[event_id]
            self._save_events()
            return True
        return False

    def query_events(
        self,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[CalendarEvent]:
        """查询事件"""
        results = []

        for event in self.events.values():
            if event.status != "active":
                continue

            if keyword and keyword.lower() not in event.title.lower():
                if not event.description or keyword.lower() not in event.description.lower():
                    continue

            if date:
                if event.date != date:
                    continue

            if start_date and event.date < start_date:
                continue

            if end_date and event.date > end_date:
                continue

            results.append(event)

        results.sort(key=lambda x: (x.date, x.time or "00:00"))
        return results

    def search_by_title(self, title: str, date: Optional[str] = None) -> List[CalendarEvent]:
        """按标题搜索"""
        results = []
        for event in self.events.values():
            if event.status != "active":
                continue
            if title.lower() in event.title.lower():
                if date is None or event.date == date:
                    results.append(event)
        return results

    def get_upcoming(self, count: int = 5, days: Optional[int] = None) -> List[CalendarEvent]:
        """获取即将到来的事件"""
        today = datetime.now().strftime("%Y-%m-%d")
        results = []

        for event in self.events.values():
            if event.status != "active":
                continue
            if event.date >= today:
                if days:
                    end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                    if event.date > end_date:
                        continue
                results.append(event)

        results.sort(key=lambda x: (x.date, x.time or "00:00"))
        return results[:count]


class DateParser:
    """日期解析器"""

    @staticmethod
    def parse_date(date_str: str) -> str:
        """解析日期字符串为 YYYY-MM-DD 格式"""
        today = datetime.now()

        relative_dates = {
            "今天": today,
            "今日": today,
            "明天": today + timedelta(days=1),
            "明日": today + timedelta(days=1),
            "后天": today + timedelta(days=2),
            "大后天": today + timedelta(days=3),
            "昨天": today - timedelta(days=1),
            "前天": today - timedelta(days=2),
        }

        if date_str in relative_dates:
            return relative_dates[date_str].strftime("%Y-%m-%d")

        weekday_map = {
            "周一": 0, "星期一": 0, "下周一": 0,
            "周二": 1, "星期二": 1, "下周二": 1,
            "周三": 2, "星期三": 2, "下周三": 2,
            "周四": 3, "星期四": 3, "下周四": 3,
            "周五": 4, "星期五": 4, "下周五": 4,
            "周六": 5, "星期六": 5, "下周六": 5,
            "周日": 6, "星期日": 6, "下周日": 6, "周天": 6,
        }

        this_week_map = {
            "本周一": 0, "这周一": 0,
            "本周二": 1, "这周二": 1,
            "本周三": 2, "这周三": 2,
            "本周四": 3, "这周四": 3,
            "本周五": 4, "这周五": 4,
            "本周六": 5, "这周六": 5,
            "本周日": 6, "这周日": 6, "本周天": 6,
        }

        if date_str in this_week_map:
            target_weekday = this_week_map[date_str]
            days_ahead = target_weekday - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        if date_str in weekday_map:
            target_weekday = weekday_map[date_str]
            days_ahead = target_weekday - today.weekday()
            if "下" in date_str or days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        if "-" in date_str and len(date_str) == 10:
            return date_str

        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

        return date_str

    @staticmethod
    def parse_time(time_str: str) -> str:
        """解析时间字符串为 HH:MM 格式"""
        if not time_str:
            return None

        time_str = time_str.replace("：", ":").strip()

        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"

        import re
        match = re.match(r"(\d{1,2})点(\d{0,2})分?", time_str)
        if match:
            hour = match.group(1).zfill(2)
            minute = match.group(2).zfill(2) if match.group(2) else "00"
            return f"{hour}:{minute}"

        match = re.match(r"(上午|下午|晚上|晚上)?(\d{1,2})点", time_str)
        if match:
            period = match.group(1)
            hour = int(match.group(2))
            if period in ["下午", "晚上"] and hour < 12:
                hour += 12
            elif period == "上午" and hour == 12:
                hour = 0
            return f"{hour:02d}:00"

        match = re.match(r"(\d{1,2}):(\d{2})", time_str)
        if match:
            return f"{match.group(1).zfill(2)}:{match.group(2)}"

        return time_str


class CalendarAgent(BaseAgent):
    """日历管理智能体"""
    
    KEYWORD_MAPPINGS = {
        "日程": ("query_events", {}),
        "今日日程": ("query_events", {}),
        "我的日程": ("query_events", {}),
        "日历": ("query_events", {}),
        "查看日程": ("query_events", {}),
        "明天日程": ("query_events", {"days": 1}),
        "后天日程": ("query_events", {"days": 2}),
        "本周日程": ("query_events", {"range": "week"}),
        "添加日程": ("add_event", {}),
        "新建日程": ("add_event", {}),
        "创建日程": ("add_event", {}),
        "添加事件": ("add_event", {}),
        "新建事件": ("add_event", {}),
        "删除日程": ("delete_event", {}),
        "修改日程": ("update_event", {}),
        "更新日程": ("update_event", {}),
    }

    def __init__(self):
        super().__init__(
            name="calendar_agent",
            description="日历管理智能体，支持创建、查询、修改、删除日程事件"
        )
        
        self.register_capability(
            capability="check_calendar",
            description="查看日程安排。可以查看今天的日程或指定日期的日程。",
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期（可选），格式如'2024-01-15'或'今天'、'明天'"
                    }
                },
                "required": []
            },
            category="calendar"
        )

        self.calendar = CalendarManager()
        self.date_parser = DateParser()
        self._reminder_task = None
        self._notification_callback = None

        self.register_capability("add_event", "添加事件")
        self.register_capability("query_events", "查询事件")
        self.register_capability("update_event", "更新事件")
        self.register_capability("delete_event", "删除事件")
        self.register_capability("list_upcoming", "列出即将到来的事件")

        logger.info("📅 日历智能体已初始化")

    async def start(self):
        """启动智能体"""
        await super().start()
        self._reminder_task = asyncio.create_task(self._reminder_checker())
        logger.info("📅 日历提醒检查器已启动")

    async def stop(self):
        """停止智能体"""
        if self._reminder_task:
            self._reminder_task.cancel()
        await super().stop()

    def set_notification_callback(self, callback):
        """设置通知回调函数"""
        self._notification_callback = callback

    async def _reminder_checker(self):
        """定时检查即将到来的事件并发送提醒"""
        notified_events = set()
        
        while True:
            try:
                await asyncio.sleep(30)
                
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                current_time = now.strftime("%H:%M")
                
                upcoming = self.calendar.get_upcoming(count=20, days=1)
                
                for event in upcoming:
                    if not event.time:
                        continue
                    
                    event_key = f"{event.id}_{event.date}_{event.time}"
                    
                    try:
                        event_date = event.date
                        event_time = event.time
                        
                        if len(event_time) > 5:
                            import re as re_module
                            time_match = re_module.search(r'(\d{1,2}:\d{2})', event_time)
                            if time_match:
                                event_time = time_match.group(1)
                        
                        if ' ' in event_date:
                            event_date = event_date.split()[0]
                        
                        event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
                    except ValueError as e:
                        logger.warning(f"解析事件时间失败: {event.date} {event.time}, 错误: {e}")
                        continue
                    
                    time_diff = (event_datetime - now).total_seconds()
                    
                    if 0 < time_diff <= 300 and event_key not in notified_events:
                        notified_events.add(event_key)
                        
                        minutes = int(time_diff // 60)
                        if minutes > 0:
                            message = f"⏰ 提醒：{event.title} 将在 {minutes} 分钟后（{event.time}）开始"
                        else:
                            message = f"⏰ 提醒：{event.title} 时间到了！"
                        
                        logger.info(f"📅 发送提醒: {message}")
                        
                        try:
                            from ..message_bus import message_bus
                            from ..base import Message
                            
                            notification_msg = Message(
                                from_agent="calendar_agent",
                                to_agent="master",
                                type="notification",
                                content=message,
                                data={
                                    "type": "calendar_reminder",
                                    "title": "日程提醒",
                                    "event_id": event.id
                                }
                            )
                            await message_bus.send_message(notification_msg)
                        except Exception as e:
                            logger.error(f"发送通知失败: {e}")
                
                if now.hour == 0 and now.minute == 0:
                    notified_events.clear()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"提醒检查出错: {e}")
                await asyncio.sleep(60)

    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params or {}

        logger.info(f"📅 执行日历任务: {task_type}")

        if task_type == "add_event":
            return await self._handle_add_event(params)
        elif task_type == "query_events":
            return await self._handle_query_events(params)
        elif task_type == "update_event":
            return await self._handle_update_event(params)
        elif task_type == "delete_event":
            return await self._handle_delete_event(params)
        elif task_type == "list_upcoming":
            return await self._handle_list_upcoming(params)
        else:
            return f"❌ 不支持的操作: {task_type}"

    async def _handle_add_event(self, params: Dict) -> str:
        """添加日程事件"""
        title = params.get("title") or params.get("content")
        date_str = params.get("date")
        time_str = params.get("time")
        
        original_text = params.get("original_text", "")
        
        datetime_str = params.get("datetime", "")
        if datetime_str:
            import re
            if not date_str:
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)', datetime_str)
                if date_match:
                    date_str = date_match.group(1)
            if not time_str:
                time_patterns = [
                    r'(\d{1,2})[:：](\d{2})',
                    r'(?:晚上|下午|傍晚)(\d{1,2})点(\d{1,2})?分?',
                    r'(?:上午|早上|早晨)(\d{1,2})点(\d{1,2})?分?',
                    r'(\d{1,2})点(\d{1,2})?分?',
                ]
                for pattern in time_patterns:
                    match = re.search(pattern, datetime_str)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.group(2) else 0
                        
                        if '晚上' in datetime_str or '下午' in datetime_str or '傍晚' in datetime_str:
                            if hour < 12:
                                hour += 12
                        elif ('上午' in datetime_str or '早上' in datetime_str or '早晨' in datetime_str) and hour == 12:
                            hour = 0
                        
                        time_str = f"{hour:02d}:{minute:02d}"
                        break
        
        if original_text:
            import re
            
            if not time_str:
                time_patterns = [
                    (r'(?:晚上|下午|傍晚)(\d{1,2})[:：](\d{2})', lambda m: (int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1)), int(m.group(2)))),
                    (r'(?:上午|早上|早晨)(\d{1,2})[:：](\d{2})', lambda m: (int(m.group(1)), int(m.group(2)))),
                    (r'(\d{1,2})[:：](\d{2})', lambda m: (int(m.group(1)), int(m.group(2)))),
                    (r'(?:晚上|下午|傍晚)(\d{1,2})点(\d{0,2})分?', lambda m: (int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1)), int(m.group(2)) if m.group(2) else 0)),
                    (r'(?:上午|早上|早晨)(\d{1,2})点(\d{0,2})分?', lambda m: (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)),
                    (r'(\d{1,2})点(\d{0,2})分?', lambda m: (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)),
                ]
                
                for pattern, extractor in time_patterns:
                    match = re.search(pattern, original_text)
                    if match:
                        hour, minute = extractor(match)
                        time_str = f"{hour:02d}:{minute:02d}"
                        break
            
            if not title:
                clean_text = original_text
                time_patterns_to_remove = [
                    r'(?:今天|明天|后天)?(?:晚上|下午|上午|早上|傍晚)?\d{1,2}[:：]\d{2}',
                    r'(?:今天|明天|后天)?(?:晚上|下午|上午|早上|傍晚)?\d{1,2}点\d{0,2}分?',
                    r'\d{1,2}月\d{1,2}日(?:晚上|下午|上午|早上)?\d{1,2}[:：]\d{2}',
                ]
                
                for pattern in time_patterns_to_remove:
                    clean_text = re.sub(pattern, '', clean_text)
                
                clean_text = re.sub(r'提醒我|提醒|去|帮我|设置|添加日程|添加|创建', '', clean_text)
                clean_text = re.sub(r'[，。！？、；：\s]+', ' ', clean_text).strip()
                
                if clean_text:
                    title = clean_text

        if not title:
            return "❌ 请提供事件标题"

        if not date_str:
            date_str = "今天"

        parsed_date = self.date_parser.parse_date(date_str)
        
        if time_str and len(time_str) > 5:
            import re as re_module
            time_match = re_module.search(r'(\d{1,2}:\d{2})', time_str)
            if time_match:
                time_str = time_match.group(1)
            else:
                time_match = re_module.search(r'(\d{1,2})[:：](\d{2})', time_str)
                if time_match:
                    time_str = f"{time_match.group(1)}:{time_match.group(2)}"
        
        parsed_time = self.date_parser.parse_time(time_str) if time_str else None

        existing = self.calendar.query_events(date=parsed_date)
        if parsed_time:
            for event in existing:
                if event.time == parsed_time:
                    return f"⚠️ {parsed_date} {parsed_time} 已有日程「{event.title}」，是否仍要添加？"

        event = CalendarEvent(
            title=title,
            date=parsed_date,
            time=parsed_time,
            duration=params.get("duration"),
            location=params.get("location"),
            description=params.get("description"),
            reminder=params.get("reminder"),
            repeat=params.get("repeat")
        )

        self.calendar.add_event(event)

        time_display = f" {parsed_time}" if parsed_time else ""
        location_display = f" @ {params.get('location')}" if params.get("location") else ""

        return f"✅ 已添加日程：{title}\n📅 {parsed_date}{time_display}{location_display}"

    async def _handle_query_events(self, params: Dict) -> str:
        """查询日程"""
        date_str = params.get("date")
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")
        keyword = params.get("keyword")

        if date_str:
            parsed_date = self.date_parser.parse_date(date_str)
            events = self.calendar.query_events(date=parsed_date)
            date_display = date_str
        elif start_date_str and end_date_str:
            start_date = self.date_parser.parse_date(start_date_str)
            end_date = self.date_parser.parse_date(end_date_str)
            events = self.calendar.query_events(start_date=start_date, end_date=end_date, keyword=keyword)
            date_display = f"{start_date_str} 至 {end_date_str}"
        else:
            parsed_date = datetime.now().strftime("%Y-%m-%d")
            events = self.calendar.query_events(date=parsed_date)
            date_display = "今天"

        if not events:
            return f"📭 {date_display} 没有日程安排"

        lines = [f"📅 {date_display} 的日程：", ""]
        for event in events:
            time_display = f"[{event.time}] " if event.time else ""
            location_display = f" @ {event.location}" if event.location else ""
            lines.append(f"• {time_display}{event.title}{location_display}")
            if event.description:
                lines.append(f"  └ {event.description}")

        return "\n".join(lines)

    async def _handle_update_event(self, params: Dict) -> str:
        """修改日程"""
        event_id = params.get("event_id")
        title = params.get("title")
        new_title = params.get("new_title")
        new_date = params.get("new_date")
        new_time = params.get("new_time")
        new_location = params.get("new_location")
        new_description = params.get("new_description")

        if event_id:
            event = self.calendar.get_event(event_id)
        elif title:
            events = self.calendar.search_by_title(title)
            if not events:
                return f"❌ 找不到标题包含「{title}」的日程"
            if len(events) > 1:
                lines = [f"找到多个匹配「{title}」的日程："]
                for i, e in enumerate(events, 1):
                    lines.append(f"{i}. {e.date} {e.time or ''} - {e.title}")
                lines.append("请指定更明确的标题或日期")
                return "\n".join(lines)
            event = events[0]
        else:
            return "❌ 请提供事件ID或标题"

        if not event:
            return "❌ 找不到指定的日程"

        update_fields = {}
        if new_title:
            update_fields["title"] = new_title
        if new_date:
            update_fields["date"] = self.date_parser.parse_date(new_date)
        if new_time:
            update_fields["time"] = self.date_parser.parse_time(new_time)
        if new_location:
            update_fields["location"] = new_location
        if new_description:
            update_fields["description"] = new_description

        if not update_fields:
            return "❌ 没有提供要修改的内容"

        self.calendar.update_event(event.id, **update_fields)

        changes = []
        if new_title:
            changes.append(f"标题: {event.title} → {new_title}")
        if new_date:
            changes.append(f"日期: {event.date} → {update_fields.get('date', event.date)}")
        if new_time:
            changes.append(f"时间: {event.time or '无'} → {update_fields.get('time', '无')}")

        return f"✅ 已修改日程「{event.title}」\n" + "\n".join(f"  • {c}" for c in changes)

    async def _handle_delete_event(self, params: Dict) -> str:
        """删除日程"""
        event_id = params.get("event_id")
        title = params.get("title")
        date_str = params.get("date")

        if event_id:
            event = self.calendar.get_event(event_id)
        elif title:
            parsed_date = self.date_parser.parse_date(date_str) if date_str else None
            events = self.calendar.search_by_title(title, parsed_date)
            if not events:
                return f"❌ 找不到标题包含「{title}」的日程"
            if len(events) > 1:
                lines = [f"找到多个匹配「{title}」的日程："]
                for i, e in enumerate(events, 1):
                    lines.append(f"{i}. {e.date} {e.time or ''} - {e.title}")
                lines.append("请指定更明确的标题或日期")
                return "\n".join(lines)
            event = events[0]
        else:
            return "❌ 请提供事件ID或标题"

        if not event:
            return "❌ 找不到指定的日程"

        deleted = self.calendar.delete_event(event.id)
        if deleted:
            time_display = f" {event.time}" if event.time else ""
            return f"✅ 已删除日程：{event.title}\n📅 {event.date}{time_display}"
        return "❌ 删除失败"

    async def _handle_list_upcoming(self, params: Dict) -> str:
        """查看即将到来的日程"""
        count = params.get("count", 5)
        days = params.get("days")

        events = self.calendar.get_upcoming(count=count, days=days)

        if not events:
            if days:
                return f"📭 未来 {days} 天没有日程安排"
            return "📭 近期没有日程安排"

        days_display = f"未来 {days} 天" if days else "近期"
        lines = [f"📅 {days_display}的日程：", ""]

        current_date = None
        for event in events:
            if event.date != current_date:
                current_date = event.date
                lines.append(f"【{event.date}】")

            time_display = f"[{event.time}] " if event.time else ""
            location_display = f" @ {event.location}" if event.location else ""
            lines.append(f"  • {time_display}{event.title}{location_display}")

        return "\n".join(lines)
