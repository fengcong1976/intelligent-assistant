"""
Proactive Task Scheduler - 主动任务调度系统
定时和事件触发任务
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable, Optional
from loguru import logger
import uuid

from ..agents.base import Task, TaskStatus, TaskPriority


class ScheduledTask:
    """定时任务"""
    task_id: str
    name: str
    schedule_type: str  # daily, weekly, monthly, yearly, one_time
    schedule_time: str  # 格式: HH:MM 或 YYYY-MM-DD HH:MM
    task_generator: Callable  # 生成任务的函数
    params: Dict[str, Any] = None
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None

    def __init__(self, task_id: str, name: str, schedule_type: str, schedule_time: str, task_generator: Callable, params: Dict[str, Any] = None):
        self.task_id = task_id
        self.name = name
        self.schedule_type = schedule_type
        self.schedule_time = schedule_time
        self.task_generator = task_generator
        self.params = params or {}
        self.enabled = True
        self.last_run = None
        self.next_run = self._calculate_next_run()

    def _calculate_next_run(self) -> Optional[str]:
        """计算下次运行时间"""
        try:
            now = datetime.now()

            if self.schedule_type == "daily":
                # 每天在指定时间运行
                hour, minute = map(int, self.schedule_time.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run.isoformat()

            elif self.schedule_type == "weekly":
                # 每周在指定时间运行
                weekday, time_str = self.schedule_time.split(' ')
                hour, minute = map(int, time_str.split(':'))
                weekday_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
                target_weekday = weekday_map.get(weekday.lower(), 0)
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                days_ahead = (target_weekday - now.weekday() + 7) % 7
                if days_ahead > 0:
                    next_run += timedelta(days=days_ahead)
                elif next_run <= now:
                    next_run += timedelta(days=7)
                return next_run.isoformat()

            elif self.schedule_type == "monthly":
                # 每月在指定时间运行
                day, time_str = self.schedule_time.split(' ')
                day = int(day)
                hour, minute = map(int, time_str.split(':'))
                next_run = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=now.month + 1)
                return next_run.isoformat()

            elif self.schedule_type == "yearly":
                # 每年在指定时间运行
                date_str, time_str = self.schedule_time.split(' ')
                month, day = map(int, date_str.split('-'))
                hour, minute = map(int, time_str.split(':'))
                next_run = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run = next_run.replace(year=now.year + 1)
                return next_run.isoformat()

            elif self.schedule_type == "one_time":
                # 一次性任务
                return self.schedule_time

            return None
        except Exception as e:
            logger.error(f"❌ 计算下次运行时间失败: {e}")
            return None

    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.enabled or not self.next_run:
            return False

        now = datetime.now()
        next_run = datetime.fromisoformat(self.next_run)
        return now >= next_run

    def mark_as_run(self):
        """标记为已运行"""
        self.last_run = datetime.now().isoformat()
        self.next_run = self._calculate_next_run()
        logger.info(f"✅ 任务已运行: {self.name}, 下次运行: {self.next_run}")


class ProactiveTaskScheduler:
    """主动任务调度器"""

    def __init__(self):
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_handlers: Dict[str, Callable] = {}
        logger.info("⏰ 主动任务调度器已初始化")

    async def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        logger.info("🚀 主动任务调度器已启动")

        # 启动调度循环
        asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("🛑 主动任务调度器已停止")

    async def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                # 检查所有定时任务
                for task_id, scheduled_task in self._scheduled_tasks.items():
                    if scheduled_task.should_run():
                        logger.info(f"⏰ 执行定时任务: {scheduled_task.name}")
                        
                        # 生成并执行任务
                        try:
                            task = scheduled_task.task_generator(scheduled_task.params)
                            await self._handle_task(task)
                            scheduled_task.mark_as_run()
                        except Exception as e:
                            logger.error(f"❌ 执行定时任务失败: {e}")

                # 每分钟检查一次
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"❌ 调度循环失败: {e}")
                await asyncio.sleep(60)

    async def _handle_task(self, task: Task):
        """处理任务"""
        # 这里可以调用相应的智能体来处理任务
        # 或者将任务添加到主智能体的任务队列
        logger.info(f"📋 处理主动任务: {task.type} - {task.content}")

        # 示例：发送通知
        if task.type == "notification":
            await self._send_notification(task)
        elif task.type == "send_email":
            await self._send_email(task)

    async def _send_notification(self, task: Task):
        """发送通知"""
        # 这里可以调用 GUI 的通知功能
        message = task.params.get("message", "")
        user_id = task.params.get("user_id", "")
        logger.info(f"🔔 发送通知: {message} -> {user_id}")

    async def _send_email(self, task: Task):
        """发送邮件"""
        # 这里可以调用邮件智能体
        recipient = task.params.get("recipient", "")
        subject = task.params.get("subject", "")
        body = task.params.get("body", "")
        logger.info(f"📧 发送邮件: {subject} -> {recipient}")

    def add_scheduled_task(self, task: ScheduledTask):
        """添加定时任务"""
        self._scheduled_tasks[task.task_id] = task
        logger.info(f"📅 已添加定时任务: {task.name} ({task.schedule_type})")

    def remove_scheduled_task(self, task_id: str):
        """移除定时任务"""
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
            logger.info(f"🗑️ 已移除定时任务: {task_id}")

    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """获取所有定时任务"""
        return list(self._scheduled_tasks.values())

    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
        logger.info(f"🔌 已注册任务处理器: {task_type}")

    def setup_default_tasks(self):
        """设置默认定时任务"""
        # 每天早上9点提醒用户查看日程
        morning_reminder = ScheduledTask(
            task_id="morning_reminder",
            name="早上日程提醒",
            schedule_type="daily",
            schedule_time="09:00",
            task_generator=lambda params: Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content="早上日程提醒",
                priority=TaskPriority.LOW,
                params={
                    "message": "🌅 早上好！记得查看今天的日程安排。",
                    "user_id": "gui_user"
                }
            )
        )
        self.add_scheduled_task(morning_reminder)

        # 每周一早上9点提醒用户设置周目标
        weekly_goal = ScheduledTask(
            task_id="weekly_goal",
            name="每周目标提醒",
            schedule_type="weekly",
            schedule_time="mon 09:00",
            task_generator=lambda params: Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content="每周目标提醒",
                priority=TaskPriority.LOW,
                params={
                    "message": "📅 新的一周开始了，记得设置本周目标！",
                    "user_id": "gui_user"
                }
            )
        )
        self.add_scheduled_task(weekly_goal)

        # 每月1号早上9点提醒用户设置月目标
        monthly_goal = ScheduledTask(
            task_id="monthly_goal",
            name="每月目标提醒",
            schedule_type="monthly",
            schedule_time="1 09:00",
            task_generator=lambda params: Task(
                task_id=str(uuid.uuid4()),
                type="notification",
                content="每月目标提醒",
                priority=TaskPriority.LOW,
                params={
                    "message": "📅 新的一月开始了，记得设置本月目标！",
                    "user_id": "gui_user"
                }
            )
        )
        self.add_scheduled_task(monthly_goal)

        logger.info("✅ 默认定时任务已设置")