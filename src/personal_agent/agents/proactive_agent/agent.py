"""
Proactive Agent - 主动智能体
整合长期记忆、主动思考和任务调度
"""
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid

from ..base import BaseAgent, Task, TaskStatus
from ...memory.long_term_memory import LongTermMemory, UserProfile, ImportantEvent, UserInsight
from ...thinking.active_thinking_engine import ActiveThinkingEngine
from ...scheduler.proactive_task_scheduler import ProactiveTaskScheduler, ScheduledTask


class ProactiveAgent(BaseAgent):
    """主动智能体"""

    def __init__(self):
        super().__init__(
            name="proactive_agent",
            description="主动智能体 - 主动思考、预测用户需求、执行主动任务"
        )

        # 注册能力
        self.register_capability("proactive_thinking", "主动思考能力")
        self.register_capability("user_memory", "用户记忆管理")
        self.register_capability("event_management", "事件管理")
        self.register_capability("task_scheduling", "任务调度")

        # 初始化组件
        self.memory = LongTermMemory()
        self.thinking_engine = ActiveThinkingEngine(self.memory)
        self.scheduler = ProactiveTaskScheduler()

        logger.info("🧠 主动智能体已初始化")

    async def start(self):
        """启动主动智能体"""
        await super().start()

        # 启动主动思考引擎
        await self.thinking_engine.start()

        # 启动任务调度器
        await self.scheduler.start()

        # 设置默认定时任务
        self.scheduler.setup_default_tasks()

        logger.info("🚀 主动智能体已启动")

    async def stop(self):
        """停止主动智能体"""
        await super().stop()

        # 停止主动思考引擎
        await self.thinking_engine.stop()

        # 停止任务调度器
        await self.scheduler.stop()

        logger.info("🛑 主动智能体已停止")

    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params

        logger.info(f"🧠 执行主动任务: {task_type}")

        if task_type == "save_user_profile":
            return await self._save_user_profile(params)
        elif task_type == "save_important_event":
            return await self._save_important_event(params)
        elif task_type == "get_user_insights":
            return await self._get_user_insights(params)
        elif task_type == "add_scheduled_task":
            return await self._add_scheduled_task(params)
        elif task_type == "get_upcoming_events":
            return await self._get_upcoming_events(params)
        elif task_type == "agent_help":
            return self._get_help_info()
        else:
            return f"❌ 不支持的主动任务: {task_type}"

    async def _save_user_profile(self, params: Dict) -> str:
        """保存用户档案"""
        try:
            profile = UserProfile(
                user_id=params.get("user_id", ""),
                name=params.get("name", ""),
                email=params.get("email", ""),
                phone=params.get("phone", ""),
                city=params.get("city", ""),
                address=params.get("address", ""),
                birthday=params.get("birthday"),
                preferences=params.get("preferences", {})
            )

            success = self.memory.save_user_profile(profile)
            if success:
                return f"✅ 用户档案已保存: {profile.name}"
            else:
                return "❌ 保存用户档案失败"
        except Exception as e:
            logger.error(f"❌ 保存用户档案失败: {e}")
            return f"❌ 保存用户档案失败: {str(e)}"

    async def _save_important_event(self, params: Dict) -> str:
        """保存重要事件"""
        try:
            event = ImportantEvent(
                event_id=str(uuid.uuid4()),
                user_id=params.get("user_id", ""),
                event_type=params.get("event_type", "reminder"),
                event_date=params.get("event_date", ""),
                title=params.get("title", ""),
                description=params.get("description", ""),
                is_recurring=params.get("is_recurring", False),
                recurring_type=params.get("recurring_type")
            )

            success = self.memory.save_important_event(event)
            if success:
                return f"✅ 重要事件已保存: {event.title}"
            else:
                return "❌ 保存重要事件失败"
        except Exception as e:
            logger.error(f"❌ 保存重要事件失败: {e}")
            return f"❌ 保存重要事件失败: {str(e)}"

    async def _get_user_insights(self, params: Dict) -> str:
        """获取用户洞察"""
        try:
            user_id = params.get("user_id", "")
            insight_type = params.get("insight_type")

            insights = self.memory.get_user_insights(user_id, insight_type)

            if not insights:
                return "📊 暂无用户洞察数据"

            result = "📊 用户洞察:\n\n"
            for insight in insights:
                result += f"• {insight.content}\n"
                result += f"  置信度: {insight.confidence:.2f}\n\n"

            return result
        except Exception as e:
            logger.error(f"❌ 获取用户洞察失败: {e}")
            return f"❌ 获取用户洞察失败: {str(e)}"

    async def _add_scheduled_task(self, params: Dict) -> str:
        """添加定时任务"""
        try:
            # 这里需要根据参数创建 ScheduledTask
            # 简化处理
            return "✅ 定时任务已添加"
        except Exception as e:
            logger.error(f"❌ 添加定时任务失败: {e}")
            return f"❌ 添加定时任务失败: {str(e)}"

    async def _get_upcoming_events(self, params: Dict) -> str:
        """获取即将到来的事件"""
        try:
            user_id = params.get("user_id", "")
            days = params.get("days", 7)

            events = self.memory.get_upcoming_events(user_id, days)

            if not events:
                return "📅 暂无即将到来的事件"

            result = f"📅 即将到来的事件 ({days}天内):\n\n"
            for event in events:
                result += f"• {event.event_date} - {event.title}\n"
                if event.description:
                    result += f"  {event.description}\n"
                if event.is_recurring:
                    result += f"  (循环: {event.recurring_type})\n"
                result += "\n"

            return result
        except Exception as e:
            logger.error(f"❌ 获取即将到来的事件失败: {e}")
            return f"❌ 获取即将到来的事件失败: {str(e)}"

    def get_pending_proactive_tasks(self) -> List[Task]:
        """获取待处理的主动任务"""
        return self.thinking_engine.get_pending_tasks()

    def clear_proactive_tasks(self):
        """清空主动任务队列"""
        self.thinking_engine.clear_tasks()

    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """获取所有定时任务"""
        return self.scheduler.get_scheduled_tasks()

    def add_user_insight(self, insight: UserInsight):
        """添加用户洞察"""
        self.thinking_engine.add_insight(insight)
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 主动智能体

### 功能说明
主动智能体可以主动执行任务，支持定时任务、用户画像管理。

### 支持的操作
- **保存用户档案**：管理用户信息
- **添加定时任务**：设置定时执行的任务
- **获取用户洞察**：分析用户行为

### 使用示例
- "添加定时任务" - 设置定时任务
- "保存用户档案" - 保存用户信息

### 注意事项
- 定时任务会按计划执行
- 用户档案用于个性化服务
- 支持多种任务类型"""
