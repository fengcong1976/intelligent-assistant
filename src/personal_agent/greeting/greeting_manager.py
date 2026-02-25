"""
Greeting Manager - 问候语管理器
动态生成问候语，集成天气和新闻
"""
import asyncio
from datetime import datetime, time
from typing import Optional, Dict, Any
from loguru import logger
import uuid

from ..agents.base import Task, TaskStatus
from ..memory.long_term_memory import LongTermMemory
from ..user_config import user_config


class GreetingManager:
    """问候语管理器"""

    def __init__(self, memory: LongTermMemory, weather_agent, news_agent, master_agent=None):
        self.memory = memory
        self.weather_agent = weather_agent
        self.news_agent = news_agent
        self.master_agent = master_agent
        self._last_greeting_time: Optional[str] = None
        logger.info("👋 问候语管理器已初始化")

    def set_master_agent(self, master_agent):
        """设置主智能体引用（用于懒加载获取子智能体）"""
        self.master_agent = master_agent

    async def _get_weather_agent(self):
        """获取天气智能体（支持懒加载）"""
        if self.weather_agent:
            return self.weather_agent
        if self.master_agent:
            self.weather_agent = await self.master_agent._get_or_create_agent("weather_agent")
            return self.weather_agent
        return None

    async def get_greeting(self, user_id: str = "gui_user") -> str:
        """获取动态问候语"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        current_date = now.strftime('%Y-%m-%d')

        is_first = self._is_first_open_today(user_id, current_date)
        logger.info(f"🌅 是否今天第一次打开: {is_first}")
        
        if is_first:
            logger.info(f"🌅 今天第一次打开: {current_date}")
            greeting = await self._generate_morning_greeting(user_id, now)
            self._record_open_time(user_id, current_date)
            logger.info(f"🌅 生成问候语长度: {len(greeting)}")
            return greeting
        else:
            return self._generate_time_based_greeting(now)

    def _is_first_open_today(self, user_id: str, current_date: str) -> bool:
        """检查是否是今天第一次打开"""
        profile = self.memory.get_user_profile(user_id)
        if not profile:
            return True

        last_open = profile.preferences.get("last_open_date", "")
        return last_open != current_date

    def _record_open_time(self, user_id: str, current_date: str):
        """记录打开时间"""
        profile = self.memory.get_user_profile(user_id)
        if profile:
            profile.preferences["last_open_date"] = current_date
            profile.preferences["last_open_time"] = datetime.now().strftime('%H:%M')
            self.memory.save_user_profile(profile)
            logger.info(f"💾 已记录打开时间: {current_date} {datetime.now().strftime('%H:%M')}")

    async def _generate_morning_greeting(self, user_id: str, now: datetime) -> str:
        """生成早上问候（包含天气和新闻）"""
        logger.info("🌅 生成早上问候...")

        profile = self.memory.get_user_profile(user_id)
        
        # 优先级：user_config.json > .env > 数据库 > 默认值
        user_name = (
            user_config.user_name or 
            (profile.name if profile else "") or 
            "用户"
        )
        
        city = None
        address = None
        
        try:
            from ..config import settings
            city = settings.user.city
            address = settings.user.address
            logger.info(f"📍 从配置获取城市: {city}, 地址: {address}")
        except:
            pass
        
        if not city and profile and profile.city:
            city = profile.city
            logger.info(f"📍 从用户档案获取城市: {city}")
        
        weather_location = f"{city}{address}" if city and address else city

        hour = now.hour
        if 5 <= hour < 9:
            time_greeting = "早上好"
        elif 9 <= hour < 12:
            time_greeting = "上午好"
        elif 12 <= hour < 14:
            time_greeting = "中午好"
        elif 14 <= hour < 18:
            time_greeting = "下午好"
        else:
            time_greeting = "晚上好"

        greeting = f"🌅 {time_greeting}，{user_name}！\n\n"

        logger.info("🌅 开始获取天气信息...")
        weather_info = await self._get_weather_info(weather_location)
        logger.info(f"🌅 天气信息: {'有' if weather_info else '无'}")
        if weather_info:
            greeting += weather_info + "\n\n"

        logger.info("🌅 开始获取新闻信息...")
        news_info = await self._get_news_info()
        logger.info(f"🌅 新闻信息: {'有' if news_info else '无'}")
        if news_info:
            greeting += news_info

        return greeting

    def _generate_time_based_greeting(self, now: datetime) -> str:
        """生成基于时间的问候"""
        hour = now.hour

        if 5 <= hour < 9:
            return "🌅 早上好！新的一天开始了，加油！"
        elif 9 <= hour < 12:
            return "☀️ 上午好！工作顺利吗？"
        elif 12 <= hour < 14:
            return "🌞 中午好！记得休息一下。"
        elif 14 <= hour < 18:
            return "🌤️ 下午好！继续努力！"
        elif 18 <= hour < 22:
            return "🌙 晚上好！辛苦了一天，好好休息。"
        else:
            return "🌜 夜深了，早点休息吧！"

    async def _get_weather_info(self, city: Optional[str]) -> Optional[str]:
        """获取天气信息"""
        if not city:
            return None
        
        weather_agent = await self._get_weather_agent()
        if not weather_agent:
            return None

        try:
            task = Task(
                type="current_weather",
                content=f"查询{city}天气",
                priority=3,
                params={
                    "city": city,
                    "action": "current"
                }
            )

            success = await weather_agent.assign_task(task)

            if not success:
                return None

            timeout_count = 0
            max_timeout = 30

            while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED] and timeout_count < max_timeout:
                await asyncio.sleep(0.1)
                timeout_count += 1

            if task.status == TaskStatus.COMPLETED and task.result:
                result_text = task.result
                if isinstance(result_text, dict):
                    if result_text.get("cannot_handle"):
                        logger.warning(f"天气智能体无法处理: {result_text.get('reason')}")
                        return None
                    result_text = str(result_text)
                return f"🌤️ 天气：\n{result_text[:200]}"
            else:
                return None
        except Exception as e:
            logger.error(f"获取天气信息失败: {e}")
            return None

    async def _get_news_info(self) -> Optional[str]:
        """获取新闻资讯"""
        if not self.news_agent:
            logger.info("📰 新闻智能体未初始化")
            return None
            
        try:
            task = Task(
                type="fetch_news",
                content="获取最新资讯",
                priority=3,
                params={
                    "action": "fetch_news",
                    "count": 3
                }
            )

            success = await self.news_agent.assign_task(task)
            logger.info(f"📰 新闻任务分配: {'成功' if success else '失败'}")

            if not success:
                return None

            timeout_count = 0
            max_timeout = 150

            while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED] and timeout_count < max_timeout:
                await asyncio.sleep(0.1)
                timeout_count += 1

            logger.info(f"📰 新闻任务状态: {task.status}, 结果: {str(task.result)[:100] if task.result else 'None'}...")

            if task.status == TaskStatus.COMPLETED and task.result:
                result_text = task.result
                if isinstance(result_text, dict):
                    if result_text.get("cannot_handle"):
                        logger.warning(f"新闻智能体无法处理: {result_text.get('reason')}")
                        return None
                    result_text = str(result_text)
                return f"📰 {result_text}"
            else:
                return None
        except Exception as e:
            logger.error(f"获取新闻资讯失败: {e}")
            return None

    def _get_morning_suggestions(self, hour: int) -> str:
        """获取早上建议"""
        suggestions = []

        if 5 <= hour < 9:
            suggestions = [
                "💡 建议今天制定一个清晰的目标",
                "💡 记得吃早餐，保持精力充沛",
                "💡 可以花10分钟规划今天的工作"
            ]
        elif 9 <= hour < 12:
            suggestions = [
                "💡 建议每工作1小时休息5分钟",
                "💡 保持良好的坐姿，保护颈椎",
                "💡 多喝水，保持身体水分"
            ]
        elif 12 <= hour < 14:
            suggestions = [
                "💡 建议午休20-30分钟",
                "💡 避免午饭后立即工作",
                "💡 可以进行简单的拉伸运动"
            ]
        else:
            suggestions = [
                "💡 建议回顾今天的工作成果",
                "💡 记得整理明天的计划",
                "💡 适当放松，准备休息"
            ]

        if suggestions:
            return "💡 今日建议：\n" + "\n".join(f"  • {s}" for s in suggestions)
        else:
            return ""

    def update_last_greeting_time(self):
        """更新最后问候时间"""
        self._last_greeting_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        logger.info(f"👋 已更新最后问候时间: {self._last_greeting_time}")

    def get_last_greeting_time(self) -> Optional[str]:
        """获取最后问候时间"""
        return self._last_greeting_time