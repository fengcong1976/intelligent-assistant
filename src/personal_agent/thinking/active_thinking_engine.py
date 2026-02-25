"""
Active Thinking Engine - 主动思考引擎
定期分析用户数据，预测用户需求，主动生成任务
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid

from ..memory.long_term_memory import LongTermMemory, UserProfile, ImportantEvent, UserInsight
from ..agents.base import Task, TaskStatus, TaskPriority


class ActiveThinkingEngine:
    """主动思考引擎"""

    def __init__(self, memory: LongTermMemory):
        self.memory = memory
        self._running = False
        self._task_queue: List[Task] = []
        self._insights: List[UserInsight] = []
        logger.info("🧠 主动思考引擎已初始化")

    async def start(self):
        """启动主动思考引擎"""
        if self._running:
            return

        self._running = True
        logger.info("🚀 主动思考引擎已启动")

        # 启动定期思考任务
        asyncio.create_task(self._periodic_thinking())

    async def stop(self):
        """停止主动思考引擎"""
        self._running = False
        logger.info("🛑 主动思考引擎已停止")

    async def _periodic_thinking(self):
        """定期思考"""
        while self._running:
            try:
                # 每小时思考一次
                await self._think()
                await asyncio.sleep(3600)  # 1小时
            except Exception as e:
                logger.error(f"❌ 主动思考失败: {e}")
                await asyncio.sleep(60)  # 1分钟后重试

    async def _think(self):
        """主动思考"""
        logger.info("🤔 开始主动思考...")

        # 1. 分析即将到来的事件
        await self._analyze_upcoming_events()

        # 2. 分析用户偏好和习惯
        await self._analyze_user_preferences()

        # 3. 生成主动任务
        await self._generate_proactive_tasks()

        # 4. 更新用户洞察
        await self._update_user_insights()

        logger.info("✅ 主动思考完成")

    async def _analyze_upcoming_events(self):
        """分析即将到来的事件"""
        logger.info("📅 分析即将到来的事件...")

        # 获取所有用户档案
        # 这里简化处理，实际应该从数据库获取所有用户
        user_ids = ["gui_user"]  # 示例

        for user_id in user_ids:
            # 获取即将到来的事件（7天内）
            events = self.memory.get_upcoming_events(user_id, days=7)

            for event in events:
                # 分析事件类型
                if event.event_type == "birthday":
                    await self._handle_birthday_event(user_id, event)
                elif event.event_type == "anniversary":
                    await self._handle_anniversary_event(user_id, event)
                elif event.event_type == "reminder":
                    await self._handle_reminder_event(user_id, event)

    async def _handle_birthday_event(self, user_id: str, event: ImportantEvent):
        """处理生日事件"""
        logger.info(f"🎂 检测到生日事件: {event.title}")

        # 计算距离生日的天数
        event_date = datetime.strptime(event.event_date, '%Y-%m-%d')
        today = datetime.now()
        days_until = (event_date - today).days

        if days_until == 0:
            # 今天是生日，发送祝福
            task = Task(
                task_id=str(uuid.uuid4()),
                type="send_email",
                content=f"发送生日祝福邮件给 {event.title}",
                priority=TaskPriority.HIGH,
                params={
                    "recipient": self._get_user_email(user_id),
                    "subject": f"生日快乐！🎂",
                    "body": self._generate_birthday_message(event)
                }
            )
            self._task_queue.append(task)
            logger.info(f"📧 已生成生日祝福任务")

        elif days_until == 1:
            # 明天是生日，提醒准备
            task = Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content=f"提醒: 明天是 {event.title} 的生日",
                priority=TaskPriority.MEDIUM,
                params={
                    "message": f"明天是 {event.title} 的生日，记得准备祝福！🎂",
                    "user_id": user_id
                }
            )
            self._task_queue.append(task)
            logger.info(f"🔔 已生成生日提醒任务")

    async def _handle_anniversary_event(self, user_id: str, event: ImportantEvent):
        """处理纪念日事件"""
        logger.info(f"💕 检测到纪念日事件: {event.title}")

        event_date = datetime.strptime(event.event_date, '%Y-%m-%d')
        today = datetime.now()
        days_until = (event_date - today).days

        if days_until == 0:
            # 今天是纪念日，发送祝福
            task = Task(
                task_id=str(uuid.uuid4()),
                type="send_email",
                content=f"发送纪念日祝福邮件给 {event.title}",
                priority=TaskPriority.HIGH,
                params={
                    "recipient": self._get_user_email(user_id),
                    "subject": f"纪念日快乐！💕",
                    "body": self._generate_anniversary_message(event)
                }
            )
            self._task_queue.append(task)
            logger.info(f"📧 已生成纪念日祝福任务")

    async def _handle_reminder_event(self, user_id: str, event: ImportantEvent):
        """处理提醒事件"""
        logger.info(f"⏰ 检测到提醒事件: {event.title}")

        event_date = datetime.strptime(event.event_date, '%Y-%m-%d')
        today = datetime.now()
        days_until = (event_date - today).days

        if days_until == 0:
            # 今天是提醒日期
            task = Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content=f"提醒: {event.title}",
                priority=TaskPriority.HIGH,
                params={
                    "message": f"⏰ 提醒: {event.description}",
                    "user_id": user_id
                }
            )
            self._task_queue.append(task)
            logger.info(f"🔔 已生成提醒任务")

    async def _analyze_user_preferences(self):
        """分析用户偏好和习惯"""
        logger.info("📊 分析用户偏好和习惯...")

        # 获取用户洞察
        user_ids = ["gui_user"]
        for user_id in user_ids:
            insights = self.memory.get_user_insights(user_id)

            # 分析查询模式
            weather_queries = [i for i in insights if i.insight_type == "weather_query"]
            if len(weather_queries) > 5:
                # 用户经常查询天气，可以主动推送天气信息
                task = Task(
                    task_id=str(uuid.uuid4()),
                    type="notification",
                    content="主动推送天气信息",
                    priority=TaskPriority.LOW,
                    params={
                        "message": "🌤️ 今天天气不错，适合户外活动！",
                        "user_id": user_id
                    }
                )
                self._task_queue.append(task)

            # 分析工作时间
            work_hours = [i for i in insights if i.insight_type == "work_hours"]
            if work_hours:
                # 可以在工作时间外主动提醒休息
                pass

    async def _generate_proactive_tasks(self):
        """生成主动任务"""
        logger.info(f"🎯 生成主动任务，当前队列: {len(self._task_queue)} 个任务")

        # 这里可以添加更多的主动任务生成逻辑
        # 例如：
        # - 定期健康提醒
        # - 工作效率建议
        # - 学习计划提醒
        # - 社交活动建议

        # 示例：每月1日提醒用户设置目标
        today = datetime.now()
        if today.day == 1 and today.hour < 10:
            task = Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content="每月目标提醒",
                priority=TaskPriority.LOW,
                params={
                    "message": "📅 新的一月开始了，记得设置本月目标！",
                    "user_id": "gui_user"
                }
            )
            self._task_queue.append(task)
            logger.info(f"📅 已生成每月目标提醒任务")

    async def _update_user_insights(self):
        """更新用户洞察"""
        logger.info("💡 更新用户洞察...")

        # 这里可以添加更多的洞察更新逻辑
        # 例如：
        # - 分析对话模式
        # - 识别用户兴趣
        # - 发现用户习惯
        # - 预测用户需求

    def _get_user_email(self, user_id: str) -> str:
        """获取用户邮箱"""
        profile = self.memory.get_user_profile(user_id)
        if profile:
            return profile.email
        return ""

    def _generate_birthday_message(self, event: ImportantEvent) -> str:
        """生成生日祝福消息"""
        return f"""
亲爱的 {event.title}，

生日快乐！🎂🎉

在这个特殊的日子里，祝你：
身体健康，工作顺利，家庭幸福！

你的智能助理
{datetime.now().strftime('%Y年%m月%d日')}
        """

    def _generate_anniversary_message(self, event: ImportantEvent) -> str:
        """生成纪念日祝福消息"""
        return f"""
亲爱的 {event.title}，

纪念日快乐！💕🎉

{event.description}

愿你们的爱情永远甜蜜！

你的智能助理
{datetime.now().strftime('%Y年%m月%d日')}
        """

    def get_pending_tasks(self) -> List[Task]:
        """获取待处理的主动任务"""
        return self._task_queue.copy()

    def clear_tasks(self):
        """清空任务队列"""
        self._task_queue.clear()
        logger.info("🗑️ 主动任务队列已清空")

    def add_insight(self, insight: UserInsight):
        """添加用户洞察"""
        self._insights.append(insight)
        self.memory.save_user_insight(insight)