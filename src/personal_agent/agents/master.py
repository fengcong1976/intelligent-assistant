"""
Master Agent - 主智能体（调度器）
负责任务分配和智能体协调
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger

from .base import BaseAgent, Task, TaskStatus, Message
from .message_bus import message_bus
from .agent_scanner import get_agent_scanner

try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from personal_agent.config import Settings
except ImportError:
    Settings = None


class MasterAgent(BaseAgent):
    """
    主智能体

    作为系统的中央调度器，负责：
    1. 解析用户意图
    2. 任务分解和分配
    3. 智能体管理（懒加载）
    4. 结果汇总
    """

    _BASE_AGENT_REGISTRY: Dict[str, tuple] = {
        "music_agent": (".music_agent", "MusicAgent"),
        "email_agent": (".email_agent", "EmailAgent"),
        "file_agent": (".file_agent", "FileAgent"),
        "crawler_agent": (".crawler_agent", "CrawlerAgent"),
        "weather_agent": (".weather_agent", "WeatherAgent"),
        "contact_agent": (".contact_agent", "ContactAgent"),
        "developer_agent": (".developer_agent", "DeveloperAgent"),
        "document_agent": (".document_agent", "DocumentAgent"),
        "video_agent": (".video_agent", "VideoAgent"),
        "calendar_agent": (".calendar_agent", "CalendarAgent"),
        "audio_decrypt_agent": (".audio_decrypt_agent", "AudioDecryptAgent"),
        "qq_bot_agent": (".qq_bot_agent", "QQBotAgent"),
        "homeassistant_agent": (".homeassistant_agent", "HomeAssistantAgent"),
        "image_agent": (".image_agent", "ImageAgent"),
        "download_agent": (".download_agent", "DownloadAgent"),
        "news_agent": (".news_agent", "NewsAgent"),
        "stock_query_agent": (".stock_query_agent", "StockQueryAgent"),
        "travel_itinerary_agent": (".travel_itinerary_agent", "TravelItineraryAgent"),
        "shopping_agent": (".shopping_agent", "ShoppingAgent"),
        "tts_agent": (".tts_agent", "TTSAgent"),
        "proactive_agent": (".proactive_agent", "ProactiveAgent"),
        "screen_cast_agent": (".screen_cast_agent", "ScreenCastAgent"),
        "web_server_agent": (".web_server_agent", "WebServerAgent"),
        "llm_agent": (".llm_agent", "LLMAgent"),
        "app_agent": (".app_agent", "AppAgent"),
        "os_agent": (".os_agent", "OSAgent"),
        "image_converter_agent": (".image_converter_agent", "ImageConverterAgent"),
    }
    
    _pending_skill_confirmation: Dict[str, Dict] = {}
    _pending_action: Optional[Dict] = None

    def _get_agent_registry(self) -> Dict[str, tuple]:
        """获取智能体注册表（使用缓存）"""
        try:
            scanner = get_agent_scanner()
            return scanner.get_agent_registry()
        except Exception as e:
            logger.warning(f"获取智能体注册表失败: {e}")
            return self._BASE_AGENT_REGISTRY

    def _get_capability_map(self) -> Dict[str, str]:
        """动态获取能力到智能体的映射（每次强制刷新）"""
        try:
            scanner = get_agent_scanner()
            scanner.refresh()
            return scanner.get_capability_map()
        except Exception as e:
            logger.warning(f"动态获取能力映射失败: {e}")
            # 回退到基础映射
            return {
                "play_audio": "music_agent",
                "play_video": "video_agent",
                "email_management": "email_agent",
                "file_management": "file_agent",
                "web_search": "crawler_agent",
                "weather_query": "weather_agent",
                "contact_management": "contact_agent",
                "code_generate": "developer_agent",
                "add_event": "calendar_agent",
                "query_events": "calendar_agent",
                "update_event": "calendar_agent",
                "delete_event": "calendar_agent",
                "list_upcoming": "calendar_agent",
            }
    
    def _get_file_type_map(self) -> Dict[str, str]:
        """动态获取文件类型到智能体的映射（每次强制刷新）"""
        try:
            scanner = get_agent_scanner()
            scanner.refresh()
            file_map = scanner.get_file_type_map()
            if ".ncm" not in file_map:
                file_map[".ncm"] = "audio_decrypt_agent"
            if ".qmc" not in file_map:
                file_map[".qmc"] = "audio_decrypt_agent"
            if ".kwm" not in file_map:
                file_map[".kwm"] = "audio_decrypt_agent"
            return file_map
        except Exception as e:
            logger.warning(f"动态获取文件类型映射失败: {e}")
            return {
                ".mp3": "music_agent",
                ".mp4": "video_agent",
                ".pdf": "document_agent",
                ".txt": "file_agent",
                ".py": "developer_agent",
                ".ncm": "audio_decrypt_agent",
                ".qmc": "audio_decrypt_agent",
                ".kwm": "audio_decrypt_agent",
            }

    def __init__(self):
        super().__init__(
            name="master",
            description="主智能体 - 负责任务调度和智能体协调"
        )

        self.register_capability("task_dispatch", "任务调度")
        self.register_capability("agent_management", "智能体管理")
        self.register_capability("result_aggregation", "结果聚合")

        self.sub_agents: Dict[str, BaseAgent] = {}
        self.task_agent_map: Dict[str, str] = {}
        self._notification_callback: Optional[Callable] = None
        self._play_video_callback: Optional[Callable] = None
        
        self._intent_parser = None
        self._tool_intent_parser = None
        self.multi_agent = None
        
        self._init_skill_manager()
        self._check_unregistered_agents()

        message_bus.register_agent(self.name, self.message_queue)
        logger.info(f"✅ Master 智能体已注册到消息总线，实例 ID: {id(message_bus)}")
        
        self.on_message(self._handle_agent_message)
    
    def _check_unregistered_agents(self):
        """检查未注册路由的智能体"""
        try:
            from .agent_scanner import get_agent_scanner
            scanner = get_agent_scanner()
            unregistered = scanner.get_unregistered_agents()
            
            if unregistered:
                logger.warning(f"⚠️ 发现 {len(unregistered)} 个未注册路由的智能体: {', '.join(unregistered)}")
                logger.warning("⚠️ 这些智能体可能无法正常工作，请手动添加路由映射或使用开发者智能体重新生成")
        except Exception as e:
            logger.debug(f"检查未注册智能体失败: {e}")
    
    def _init_skill_manager(self):
        """初始化 Skill 管理器"""
        try:
            from ..skills import get_skill_manager, DisclosureLevel
            self.skill_manager = get_skill_manager()
            
            project_root = Path(__file__).parent.parent.parent.parent
            skills_dirs = [
                project_root / "skills",
                Path.cwd() / "skills",
                Path.home() / ".personal_agent" / "skills",
            ]
            
            for skills_dir in skills_dirs:
                if skills_dir.exists():
                    self.skill_manager.add_skills_dir(skills_dir)
            
            self.skill_manager.load_all_skills()
        except Exception as e:
            logger.warning(f"Skill 管理器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.skill_manager = None

    def register_sub_agent(self, agent: BaseAgent):
        """注册子智能体"""
        self.sub_agents[agent.name] = agent
        message_bus.register_agent(agent.name, agent.message_queue)
        agent.on_message(self._handle_agent_message)

    def get_sub_agent(self, name: str) -> Optional[BaseAgent]:
        """获取子智能体"""
        return self.sub_agents.get(name)

    def get_agent_for_file(self, file_path: str, action: str = "open") -> Optional[str]:
        """
        根据文件路径获取合适的智能体（类似Windows文件关联）
        
        Args:
            file_path: 文件路径，如 "e:\\music\\a.mp3"
            action: 操作类型，"open" 或 "edit"
            
        Returns:
            智能体名称，如 "music_agent"
        """
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        
        # 首先检查已注册的智能体的文件格式支持
        for agent_name, agent in self.sub_agents.items():
            if action == "open" and agent.can_open_file(file_path):
                logger.info(f"📁 文件 '{file_path}' 由 '{agent_name}' 打开（智能体注册）")
                return agent_name
            elif action == "edit" and agent.can_edit_file(file_path):
                logger.info(f"📁 文件 '{file_path}' 由 '{agent_name}' 编辑（智能体注册）")
                return agent_name
        
        # 然后检查全局文件类型映射
        file_type_map = self._get_file_type_map()
        if ext in file_type_map:
            agent_name = file_type_map[ext]
            logger.info(f"📁 文件 '{file_path}' ({ext}) 由 '{agent_name}' 处理")
            return agent_name
        
        logger.warning(f"📁 文件 '{file_path}' ({ext}) 没有对应的智能体")
        return None

    async def _get_or_create_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        获取或创建智能体（懒加载，支持热更新）
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            智能体实例或None
        """
        agent_name_lower = agent_name.lower()
        
        if agent_name_lower in self.sub_agents:
            return self.sub_agents[agent_name_lower]
        
        agent_registry = self._get_agent_registry()
        
        if agent_name_lower not in agent_registry:
            logger.warning(f"未知的智能体: {agent_name_lower}")
            return None
        
        try:
            module_path, class_name = agent_registry[agent_name_lower]
            
            import importlib
            import sys
            
            if not module_path.startswith("."):
                module_path = f".{module_path}"
            
            full_module_name = f"personal_agent.agents{module_path}"
            old_module_name = f"src.personal_agent.agents{module_path}"
            
            if old_module_name in sys.modules:
                del sys.modules[old_module_name]
                logger.debug(f"🧹 清理旧模块缓存: {old_module_name}")
            
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
            else:
                module = importlib.import_module(module_path, package="personal_agent.agents")
            
            agent_class: Type[BaseAgent] = getattr(module, class_name)
            
            agent = agent_class()
            await agent.start()
            self.register_sub_agent(agent)
            
            return agent
            
        except Exception as e:
            logger.error(f"❌ 懒加载智能体 '{agent_name}' 失败: {e}")
            return None

    async def _resolve_recipient_email(self, recipient_name: str) -> Optional[str]:
        """
        解析收件人邮箱
        
        Args:
            recipient_name: 收件人名称（可能是联系人名称或邮箱）
            
        Returns:
            邮箱地址或None
        """
        if "@" in recipient_name:
            return recipient_name
        
        from ..contacts.smart_contact_book import SmartContactBook
        contact_book = SmartContactBook()
        contact = contact_book.get_contact(recipient_name)
        
        if contact and contact.email:
            logger.info(f"📧 解析收件人: {recipient_name} -> {contact.email}")
            return contact.email
        
        logger.warning(f"⚠️ 未找到联系人「{recipient_name}」的邮箱")
        return None

    async def _get_contact_info(self, recipient_name: str) -> Optional[Dict]:
        """
        获取联系人信息（包含邮箱和关系）
        
        Args:
            recipient_name: 联系人名称
            
        Returns:
            联系人信息字典或None
        """
        if "@" in recipient_name:
            return {"email": recipient_name, "relationship": ""}
        
        from ..contacts.smart_contact_book import SmartContactBook
        contact_book = SmartContactBook()
        contact = contact_book.get_contact(recipient_name)
        
        if contact:
            return {
                "email": contact.email,
                "relationship": contact.relationship,
                "company": contact.company,
                "position": contact.position,
                "notes": contact.notes
            }
        
        return None

    def _try_quick_response(self, request: str) -> Optional[str]:
        """
        尝试快速响应简单问候语，跳过 LLM 调用
        
        Args:
            request: 用户请求
            
        Returns:
            快速响应内容，如果不是简单问候则返回 None
        """
        import re
        
        text = request.strip()
        text_lower = text.lower()
        
        agent_name = self._get_agent_name()
        user_name = self._get_user_name()
        
        simple_greetings = ["你好", "您好", "hi", "hello", "hey", "嗨", "哈喽"]
        time_greetings = ["早上好", "上午好", "中午好", "下午好", "晚上好", "早安", "晚安"]
        
        clean_text = re.sub(r'[！!。.？?，,\s]+$', '', text_lower)
        
        if clean_text in simple_greetings or clean_text in time_greetings:
            return self._generate_greeting_response(agent_name, user_name)
        
        if clean_text.startswith(tuple(simple_greetings)):
            for g in simple_greetings:
                if clean_text.startswith(g):
                    rest = clean_text[len(g):].strip()
                    if not rest or rest == agent_name.lower():
                        return self._generate_greeting_response(agent_name, user_name)
        
        simple_patterns = [
            (r"^谢谢[你您]?[！!。.]*$", "不客气！有什么我可以帮您的吗？"),
            (r"^再见[！!。.]*$", "再见！有需要随时找我。"),
            (r"^拜拜[！!。.]*$", "拜拜！祝您一切顺利！"),
            (r"^好的?[！!。.]*$", "好的！请问还有什么需要帮助的吗？"),
            (r"^嗯[！!。.]*$", "嗯嗯，我在听，请说~"),
            (r"^在吗[？?！!。.]*$", "在的！请问有什么可以帮您？"),
            (r"^在不在[？?！!。.]*$", "在的！请问有什么可以帮您？"),
        ]
        
        for pattern, response in simple_patterns:
            if re.match(pattern, text_lower):
                return response
        
        return None
    
    def _try_direct_agent_route(self, request: str) -> Optional[Tuple[str, str]]:
        """
        尝试直接路由到指定智能体
        
        当请求以 @ 开头时，解析智能体名称并直接路由
        
        Returns:
            (agent_name, query) 或 None
        """
        request = request.strip()
        if not request.startswith("@"):
            return None
        
        agent_aliases = {
            "音乐": "music_agent", "music": "music_agent",
            "视频": "video_agent", "video": "video_agent",
            "邮件": "email_agent", "email": "email_agent",
            "天气": "weather_agent", "weather": "weather_agent",
            "文件": "file_agent", "file": "file_agent",
            "系统": "os_agent", "os": "os_agent",
            "爬虫": "crawler_agent", "crawler": "crawler_agent",
            "下载": "download_agent", "download": "download_agent",
            "联系人": "contact_agent", "contact": "contact_agent", "通讯录": "contact_agent",
            "日历": "calendar_agent", "calendar": "calendar_agent",
            "新闻": "news_agent", "news": "news_agent",
            "应用": "app_agent", "app": "app_agent",
            "开发": "developer_agent", "developer": "developer_agent",
            "图片": "image_agent", "image": "image_agent",
            "股票": "stock_query_agent", "stock": "stock_query_agent",
            "旅行": "travel_itinerary_agent", "travel": "travel_itinerary_agent",
            "文档": "document_agent", "document": "document_agent", "pdf": "document_agent",
            "智能家居": "homeassistant_agent", "home": "homeassistant_agent",
            "购物": "shopping_agent", "shopping": "shopping_agent",
            "语音合成": "tts_agent", "tts": "tts_agent",
            "投屏": "screen_cast_agent", "screencast": "screen_cast_agent",
            "QQ": "qq_bot_agent", "qq": "qq_bot_agent",
            "LLM": "llm_agent", "llm": "llm_agent", "AI": "llm_agent", "ai": "llm_agent",
            "大模型": "llm_agent",
        }
        
        content = request[1:].strip()
        
        space_idx = content.find(" ")
        if space_idx == -1:
            space_idx = content.find("　")
        
        if space_idx > 0:
            agent_hint = content[:space_idx].strip()
            query = content[space_idx:].strip()
        else:
            agent_hint = content
            query = ""
        
        agent_hint_lower = agent_hint.lower()
        
        if agent_hint_lower in agent_aliases:
            return (agent_aliases[agent_hint_lower], query)
        
        if agent_hint.endswith("智能体"):
            base_name = agent_hint[:-3]
            if base_name.lower() in agent_aliases:
                return (agent_aliases[base_name.lower()], query)
            return None
        
        for alias, agent_name in agent_aliases.items():
            if agent_hint_lower == alias.lower() or agent_hint_lower == alias.lower() + "智能体":
                return (agent_name, query)
        
        return None
    
    def _get_agent_name(self) -> str:
        """获取智能体名称"""
        try:
            if Settings:
                settings = Settings()
                return settings.agent.name
        except:
            pass
        return "小助手"
    
    def _generate_greeting_response(self, agent_name: str, user_name: str = "") -> str:
        """根据时间生成问候响应"""
        from datetime import datetime
        
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            time_greeting = "早上好"
        elif 12 <= hour < 14:
            time_greeting = "中午好"
        elif 14 <= hour < 18:
            time_greeting = "下午好"
        else:
            time_greeting = "晚上好"
        
        if not user_name:
            user_name = self._get_user_name()
        
        if user_name:
            responses = [
                f"{time_greeting}！{user_name}，我是{agent_name}，请问有什么能帮到您？",
                f"{time_greeting}！{user_name}，很高兴为您服务。请问有什么需要帮助的吗？",
                f"{time_greeting}！{user_name}，我是{agent_name}，随时待命。请问有什么可以帮您的？",
            ]
        else:
            responses = [
                f"{time_greeting}！我是{agent_name}，您的智能助手。请问有什么能帮到您？",
                f"{time_greeting}！很高兴为您服务。请问有什么需要帮助的吗？",
                f"{time_greeting}！我是{agent_name}，随时待命。请问有什么可以帮您的？",
            ]
        
        import random
        return random.choice(responses)
    
    def _get_user_name(self) -> str:
        """获取用户昵称"""
        try:
            if Settings:
                settings = Settings()
                return settings.user.name
        except:
            pass
        return ""

    async def process_user_request(self, request: str, context: Dict = None) -> str:
        """
        处理用户请求

        Args:
            request: 用户请求内容
            context: 上下文信息，包含可能的文件附件

        Returns:
            处理结果
        """
        import time
        total_start = time.time()
        
        logger.info(f"👤 用户请求: {request}")
        
        if request.strip().startswith("@"):
            direct_route = self._try_direct_agent_route(request)
            if direct_route:
                agent_name, query = direct_route
                logger.info(f"🎯 @直接路由: {agent_name} <- '{query}'")
                task = Task(
                    type="general",
                    content=request,
                    params={"text": query, "_force_agent": agent_name},
                    priority=7
                )
                tasks = [task]
                completed_tasks = await self._dispatch_tasks(tasks)
                if completed_tasks and completed_tasks[0].result:
                    logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
                    return str(completed_tasks[0].result)
            else:
                logger.info(f"🎯 @智能体未匹配，交给 LLM 解析: {request}")
                result = await self._call_llm_for_general(request, context)
                logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
                return result
        
        quick_response = self._try_quick_response(request)
        if quick_response:
            logger.info(f"⚡ 快速响应: {quick_response[:30]}...")
            logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
            return quick_response
        
        direct_params = context.get("direct_params") if context else None
        if direct_params:
            force_agent = direct_params.get("_force_agent")
            if force_agent:
                logger.info(f"⚡ 直接参数路由: {force_agent}")
                params = direct_params if isinstance(direct_params, dict) else {"text": request}
                task = Task(
                    type="general",
                    content=request,
                    params=params,
                    priority=7
                )
                tasks = [task]
                completed_tasks = await self._dispatch_tasks(tasks)
                if completed_tasks and completed_tasks[0].result:
                    return str(completed_tasks[0].result)

        files = context.get("files", []) if context else []
        tool_name = context.get("tool_name") if context else None
        tool_args = context.get("tool_args") if context else None

        if tool_name and tool_args:
            logger.info(f"🔧 直接使用工具参数: {tool_name}, {tool_args}")
            
            # 首先检查用户原始请求中是否有@智能体指定
            force_agent = None
            agent_patterns = {
                "music_agent": ["@音乐智能体", "@音乐", "@music"],
                "video_agent": ["@视频智能体", "@视频", "@video"],
                "email_agent": ["@邮件智能体", "@邮件", "@email"],
                "weather_agent": ["@天气智能体", "@天气", "@weather"],
                "file_agent": ["@文件智能体", "@文件", "@file"],
                "os_agent": ["@系统智能体", "@系统", "@os"],
                "crawler_agent": ["@爬虫智能体", "@爬虫", "@crawler"],
                "download_agent": ["@下载智能体", "@下载", "@download"],
                "audio_decrypt_agent": ["@音频解密智能体", "@音频解密", "@audio"],
                "contact_agent": ["@联系人智能体", "@联系人", "@contact"],
                "calendar_agent": ["@日历智能体", "@日历", "@calendar"],
                "news_agent": ["@新闻智能体", "@新闻", "@news"],
                "app_agent": ["@应用智能体", "@应用", "@app"],
                "developer_agent": ["@开发智能体", "@开发", "@developer"],
                "image_agent": ["@图片智能体", "@图片", "@image"],
                "proactive_agent": ["@主动智能体", "@主动", "@proactive"],
                "web_server_agent": ["@Web服务智能体", "@Web服务", "@web", "@webserver"],
                "screen_cast_agent": ["@投屏智能体", "@投屏", "@screencast"],
                "stock_query_agent": ["@股票查询智能体", "@股票智能体", "@股票", "@stock"],
                "image_converter_agent": ["@图片转换智能体", "@图片转换", "@imgconv"],
                "llm_agent": ["@LLM智能体", "@Llm智能体", "@大模型", "@AI", "@ai", "@llm"],
                "travel_itinerary_agent": ["@旅行智能体", "@旅行", "@travel"],
                "qq_bot_agent": ["@QQ智能体", "@QQ"],
                "tts_agent": ["@语音合成智能体", "@语音合成", "@TTS", "@tts"],
                "document_agent": ["@文档智能体", "@文档", "@document", "@PDF智能体", "@pdf"],
                "homeassistant_agent": ["@智能家居智能体", "@智能家居", "@home"],
                "shopping_agent": ["@购物智能体", "@购物", "@shopping"],
            }
            
            all_patterns = []
            for agent_name, patterns in agent_patterns.items():
                for pattern in patterns:
                    all_patterns.append((pattern, agent_name, patterns))
            
            all_patterns.sort(key=lambda x: len(x[0]), reverse=True)
            
            original_request = context.get("original_request", request) if context else request
            for pattern, agent_name, all_agent_patterns in all_patterns:
                if pattern.startswith("@"):
                    if original_request.startswith(pattern) or original_request.lower().startswith(pattern.lower()):
                        force_agent = agent_name
                        break
                else:
                    if pattern in original_request or pattern.lower() in original_request.lower():
                        force_agent = agent_name
                        break
            
            if force_agent:
                logger.info(f"🎯 尊重用户原始请求中的智能体指定: {force_agent}")
                task_type = tool_name
                params = tool_args.copy()
                params["_force_agent"] = force_agent
                
                intent = {
                    "type": task_type,
                    "params": params,
                    "confidence": 1.0
                }
                logger.info(f"🎯 工具调用意图（强制智能体）: {intent}")
            else:
                from ..routing.routing_manager import get_routing_manager
                routing = get_routing_manager()
                
                task_type = tool_name
                params = tool_args.copy()
                
                agent_name = routing.get_agent_for_task(task_type)
                if not agent_name:
                    all_valid_actions = routing._config.get("valid_actions", {})
                    for agent, actions in all_valid_actions.items():
                        if task_type in actions:
                            agent_name = agent
                            break
                
                if agent_name:
                    intent = {
                        "type": task_type,
                        "params": params,
                        "confidence": 1.0
                    }
                    params["_force_agent"] = agent_name
                    
                    logger.info(f"🎯 工具调用意图: {intent}")
                else:
                    intent = await self._parse_intent(request, files[0] if files else None)
                    logger.info(f"🎯 意图识别: {intent}")
        else:
            intent = await self._parse_intent(request, files[0] if files else None)
            logger.info(f"🎯 意图识别: {intent}")
        
        from ..intent.intent_parser import IntentType
        if intent.get("type") == IntentType.CREATE_SKILL:
            return await self._handle_create_skill(intent.get("params", {}))

        if files:
            intent["params"]["attachments"] = files
            logger.info(f"📎 检测到附件: {len(files)} 个文件")
            
            request_lower = request.lower().strip()
            if request_lower in ["打开", "打开文件", "打开附件", "open"]:
                file_path = files[0] if files else None
                if file_path:
                    logger.info(f"📎 打开附件文件: {file_path}")
                    intent["type"] = "app_control"
                    intent["params"]["action"] = "open_default"
                    intent["params"]["file_path"] = file_path
            else:
                if files:
                    current_file_path = intent["params"].get("file_path", "")
                    if not current_file_path or not Path(current_file_path).exists():
                        intent["params"]["file_path"] = files[0]
                        logger.info(f"📎 使用附件作为文件路径: {files[0]}")

        if "_quick_jump_answer" in intent.get("params", {}):
            quick_jump_answer = intent["params"].pop("_quick_jump_answer")
            logger.info(f"⚡ 快速跳转完成，直接返回答案，跳过任务分解和分配")
            logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
            return quick_jump_answer

        # 2. 自动提取联系人信息（如果文本中包含）
        auto_extract_result = await self._auto_extract_contact_info(request)
        
        # 3. 任务分解
        logger.info(f"⏱️ [计时] 开始任务分解")
        t_decompose = time.time()
        tasks = await self._decompose_task(intent, request, context)
        logger.info(f"⏱️ [计时] 任务分解完成，耗时: {time.time() - t_decompose:.2f}秒")
        
        # 如果返回的是字符串，直接返回（如帮助信息）
        if isinstance(tasks, str):
            logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
            return tasks
        
        logger.info(f"📋 任务分解: {len(tasks)} 个子任务")

        # 4. 分配任务
        logger.info(f"⏱️ [计时] 开始任务分配")
        t_dispatch = time.time()
        results = await self._dispatch_tasks(tasks)
        logger.info(f"⏱️ [计时] 任务分配完成，耗时: {time.time() - t_dispatch:.2f}秒")

        # 5. 汇总结果
        response = await self._aggregate_results(results, intent)
        
        # 6. 如果有自动提取的联系人信息，添加到响应中
        if auto_extract_result:
            response = f"{response}\n\n{auto_extract_result}"

        logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
        return response
    
    async def _execute_intent(self, intent: Dict, request: str, context: Dict = None) -> str:
        """执行意图（用于快速路由）"""
        total_start = time.time()
        from ..intent.intent_parser import IntentType
        
        if intent.get("type") == IntentType.CREATE_SKILL:
            return await self._handle_create_skill(intent.get("params", {}))

        files = context.get("files", []) if context else []
        if files:
            intent["params"]["attachments"] = files
            logger.info(f"📎 检测到附件: {len(files)} 个文件")
            
            request_lower = request.lower().strip()
            if request_lower in ["打开", "打开文件", "打开附件", "open"]:
                file_path = files[0] if files else None
                if file_path:
                    logger.info(f"📎 打开附件文件: {file_path}")
                    intent["type"] = "app_control"
                    intent["params"]["action"] = "open_default"
                    intent["params"]["file_path"] = file_path

        # 2. 自动提取联系人信息（如果文本中包含）
        auto_extract_result = await self._auto_extract_contact_info(request)
        
        # 3. 任务分解
        logger.info(f"⏱️ [计时] 开始任务分解")
        t_decompose = time.time()
        tasks = await self._decompose_task(intent, request, context)
        logger.info(f"⏱️ [计时] 任务分解完成，耗时: {time.time() - t_decompose:.2f}秒")
        
        # 如果返回的是字符串，直接返回（如帮助信息）
        if isinstance(tasks, str):
            logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
            return tasks
        
        logger.info(f"📋 任务分解: {len(tasks)} 个子任务")

        # 4. 分配任务
        logger.info(f"⏱️ [计时] 开始任务分配")
        t_dispatch = time.time()
        results = await self._dispatch_tasks(tasks)
        logger.info(f"⏱️ [计时] 任务分配完成，耗时: {time.time() - t_dispatch:.2f}秒")

        # 5. 汇总结果
        response = await self._aggregate_results(results, intent)
        
        # 6. 如果有自动提取的联系人信息，添加到响应中
        if auto_extract_result:
            response = f"{response}\n\n{auto_extract_result}"

        logger.info(f"⏱️ [计时] process_user_request 总耗时: {time.time() - total_start:.2f}秒")
        return response
    
    async def _auto_extract_contact_info(self, text: str) -> Optional[str]:
        """自动提取联系人信息"""
        try:
            from ..contacts.smart_contact_book import smart_contact_book
            
            result = smart_contact_book.extract_and_save_info(text)
            
            if result["saved"]:
                info_items = [f"{k}: {v}" for k, v in result["extracted_info"].items()]
                return f"📝 已自动记录 {result['contact_name']} 的信息: {', '.join(info_items)}"
        except Exception as e:
            logger.debug(f"自动提取联系人信息失败: {e}")
        
        return None

    async def _parse_intent(self, request: str, file_path: str = None) -> Dict[str, Any]:
        """解析用户意图（优先使用工具选择机制）"""
        import time
        start_time = time.time()
        
        from ..intent.intent_parser import IntentParser, IntentType
        from ..intent.tool_intent_parser import parse_intent_with_tools

        if self._intent_parser is None:
            self._intent_parser = IntentParser()
        parser = self._intent_parser
        
        force_agent = None
        agent_patterns = {
            "music_agent": ["@音乐智能体", "@音乐", "@music"],
            "video_agent": ["@视频智能体", "@视频", "@video"],
            "email_agent": ["@邮件智能体", "@邮件", "@email"],
            "weather_agent": ["@天气智能体", "@天气", "@weather"],
            "file_agent": ["@文件智能体", "@文件", "@file"],
            "os_agent": ["@系统智能体", "@系统", "@os"],
            "crawler_agent": ["@爬虫智能体", "@爬虫", "@crawler"],
            "download_agent": ["@下载智能体", "@下载", "@download"],
            "audio_decrypt_agent": ["@音频解密智能体", "@音频解密", "@audio"],
            "contact_agent": ["@联系人智能体", "@联系人", "@contact"],
            "calendar_agent": ["@日历智能体", "@日历", "@calendar"],
            "news_agent": ["@新闻智能体", "@新闻", "@news"],
            "app_agent": ["@应用智能体", "@应用", "@app"],
            "developer_agent": ["@开发智能体", "@开发", "@developer"],
            "image_agent": ["@图片智能体", "@图片", "@image"],
            "proactive_agent": ["@主动智能体", "@主动", "@proactive"],
            "web_server_agent": ["@Web服务智能体", "@Web服务", "@web", "@webserver"],
            "screen_cast_agent": ["@投屏智能体", "@投屏", "@screencast"],
            "stock_query_agent": ["@股票查询智能体", "@股票智能体", "@股票", "@stock"],
            "image_converter_agent": ["@图片转换智能体", "@图片转换", "@imgconv"],
            "llm_agent": ["@LLM智能体", "@Llm智能体", "@大模型", "@AI", "@ai", "@llm"],
            "travel_itinerary_agent": ["@旅行智能体", "@旅行", "@travel"],
            "qq_bot_agent": ["@QQ智能体", "@QQ"],
            "tts_agent": ["@语音合成智能体", "@语音合成", "@TTS", "@tts"],
            "document_agent": ["@文档智能体", "@文档", "@document", "@PDF智能体", "@pdf"],
            "homeassistant_agent": ["@智能家居智能体", "@智能家居", "@home"],
            "shopping_agent": ["@购物智能体", "@购物", "@shopping"],
        }
        
        all_patterns = []
        for agent_name, patterns in agent_patterns.items():
            for pattern in patterns:
                all_patterns.append((pattern, agent_name, patterns))
        
        all_patterns.sort(key=lambda x: len(x[0]), reverse=True)
        
        force_agent = None
        for pattern, agent_name, all_agent_patterns in all_patterns:
            if pattern.startswith("@"):
                if request.startswith(pattern) or request.lower().startswith(pattern.lower()):
                    force_agent = agent_name
                    for p in all_agent_patterns:
                        if request.startswith(p):
                            request = request[len(p):].strip()
                        elif request.lower().startswith(p.lower()):
                            request = request[len(p):].strip()
                    break
            else:
                if pattern in request or pattern.lower() in request.lower():
                    force_agent = agent_name
                    for p in all_agent_patterns:
                        request = request.replace(p, "").strip()
                    break
        
        if force_agent:
            help_patterns = ['/?', '/？', '?', '？', 'help', '帮助']
            request_clean = request.strip().lower()
            if request_clean in help_patterns or any(request_clean == p for p in help_patterns):
                return {
                    "type": "agent_help",
                    "params": {"agent_name": force_agent},
                    "confidence": 1.0
                }
            
            return {
                "type": "general",
                "params": {"text": request, "_force_agent": force_agent},
                "confidence": 1.0
            }
        
        from ..intent.tool_intent_parser import parse_intent_with_tools_all, WorkflowResult
        context_for_parser = {"files": [file_path] if file_path else []}
        logger.info(f"⏱️ [计时] 开始工具选择机制")
        t1 = time.time()
        tool_result = await parse_intent_with_tools_all(request, context_for_parser)
        logger.info(f"⏱️ [计时] 工具选择机制完成，耗时: {time.time() - t1:.2f}秒")
        
        if tool_result:
            if isinstance(tool_result, WorkflowResult):
                logger.info(f"📋 工具选择机制创建工作流: {len(tool_result.steps)} 个步骤")
                
                from ..tools.reverse_workflow_planner import ReverseWorkflowPlanner
                planner = ReverseWorkflowPlanner()
                
                tool_calls = [
                    {"name": step.tool_name, "arguments": step.arguments}
                    for step in tool_result.steps
                ]
                
                nodes, execution_plan = planner.analyze_tool_calls(tool_calls)
                
                tool_to_agent = {step.tool_name: step.agent_name for step in tool_result.steps}
                
                if execution_plan:
                    logger.info(f"📋 反向工作流规划完成: {execution_plan}")
                    
                    workflow_steps = []
                    for layer in execution_plan:
                        for node_name in layer:
                            for node in nodes:
                                if node.node_name == node_name:
                                    workflow_steps.append({
                                        "agent": tool_to_agent.get(node.tool_name, ""),
                                        "action": node.tool_name,
                                        "params": node.resolved_inputs,
                                        "dependencies": node.dependencies
                                    })
                                    break
                    
                    return {
                        "type": "workflow",
                        "params": {
                            "steps": workflow_steps,
                            "original_text": request,
                            "execution_plan": execution_plan
                        },
                        "confidence": 0.95
                    }
                
                workflow_steps = []
                for step in tool_result.steps:
                    workflow_steps.append({
                        "agent": step.agent_name,
                        "action": step.tool_name,
                        "params": step.arguments
                    })
                
                return {
                    "type": "workflow",
                    "params": {
                        "steps": workflow_steps,
                        "original_text": request
                    },
                    "confidence": 0.95
                }
            
            logger.info(f"🎯 工具选择机制成功: {tool_result.tool_name} -> {tool_result.agent_name}")
            
            # 如果工具选择返回了答案（不需要工具），直接使用这个答案
            if hasattr(tool_result, 'answer') and tool_result.answer:
                logger.info(f"💬 工具选择已返回答案，直接使用，不再调用 LLM")
                return {
                    "type": tool_result.tool_name,
                    "params": {
                        "original_text": request,
                        "answer": tool_result.answer
                    },
                    "confidence": 0.95
                }
            
            # 如果是快速跳转匹配，直接执行工具调用，跳过 LLM 任务分配
            if hasattr(tool_result, 'is_quick_jump') and tool_result.is_quick_jump:
                logger.info(f"⚡ 快速跳转匹配，直接执行工具调用，跳过 LLM 任务分配")
                
                # 直接执行工具调用
                from ..tools.react_engine import ToolExecutor
                
                # 创建工具执行器，传入multi_agent以访问master
                tool_executor = ToolExecutor(multi_agent=self.multi_agent)
                
                # 执行工具调用
                result = await tool_executor.execute(
                    tool_result.tool_name,
                    tool_result.arguments,
                    original_request=request
                )
                
                logger.info(f"⚡ 快速跳转工具执行完成: {result[:100] if len(result) > 100 else result}")
                
                return {
                    "type": tool_result.tool_name,
                    "params": {
                        "original_text": request,
                        "answer": result,
                        "_quick_jump_answer": result
                    },
                    "confidence": 0.95
                }
            
            from ..routing.routing_manager import get_routing_manager
            routing = get_routing_manager()
            
            intent_type = tool_result.tool_name
            params = tool_result.arguments
            
            if force_agent:
                params["_force_agent"] = force_agent
            
            return {
                "type": intent_type or tool_result.tool_name,
                "params": params,
                "confidence": 0.95
            }
        
        # 工具选择未匹配，需要判断是否强制使用某个智能体
        if force_agent:
            logger.info(f"🎯 工具选择未匹配，但强制使用智能体: {force_agent}")
            
            # 获取强制智能体的默认意图类型
            from ..routing.routing_manager import get_routing_manager
            routing = get_routing_manager()
            
            intent_type = routing.get_intent_for_agent(force_agent)
            valid_actions = routing.get_valid_actions(force_agent)
            default_action = routing.get_default_action(force_agent)
            
            params = {
                "original_text": request,
                "_force_agent": force_agent
            }
            
            action = ""
            
            # 特殊处理音量控制
            if force_agent == "os_agent" and "volume" in request.lower():
                if "调高" in request or "大" in request or "increase" in request.lower():
                    action = "volume_up"
                elif "调低" in request or "小" in request or "decrease" in request.lower():
                    action = "volume_down"
                elif "静音" in request or "mute" in request.lower():
                    action = "volume_mute"
                elif "取消静音" in request or "unmute" in request.lower():
                    action = "volume_unmute"
                else:
                    action = "volume_get"
                params["action"] = action
                logger.info(f"🎯 音量控制动作映射: {action}")
            
            # 特殊处理天气查询
            if force_agent == "weather_agent":
                if "明天" in request or "后天" in request or "forecast" in request.lower():
                    action = "weather_forecast"
                    params["action"] = action
                    logger.info(f"🎯 天气查询动作映射: weather_forecast")
            
            # 特殊处理股票查询
            if force_agent == "stock_query_agent":
                if "指数" in request or "index" in request.lower():
                    action = "query_index"
                    intent_type = "query_index"
                    params["action"] = action
                    logger.info(f"🎯 股票查询动作映射: query_index")
                else:
                    action = "query_stock"
                    params["action"] = action
                    logger.info(f"🎯 股票查询动作映射: query_stock")
            
            # 设置默认 action
            if not action or action not in valid_actions:
                action = default_action or "default"
                params["action"] = action
                logger.info(f"🎯 强制智能体 {force_agent}，自动设置 action={action}")
            
            return {
                "type": intent_type,
                "params": params,
                "confidence": 0.95
            }
        
        # 没有强制智能体，直接返回 general 类型
        # 这样可以避免发送所有智能体信息（约 5000 tokens）
        logger.info("🎯 工具选择未匹配，直接返回 general 类型")
        return {
            "type": "general",
            "params": {
                "original_text": request
            },
            "confidence": 0.95
        }

    async def _prepare_email_content(self, request: str, params: Dict = None) -> Dict:
        """
        准备邮件内容
        
        使用 LLM 生成邮件的收件人、主题和正文
        """
        from ..config import settings
        from ..user_config import user_config
        
        params = params or {}
        
        user_email = settings.user.email or settings.agent.email
        user_name = user_config.user_name or settings.user.name or "主人"
        user_formal_name = user_config.formal_name or settings.user.formal_name or user_name
        agent_name = settings.agent.name or "智能助手"
        
        import re
        direct_patterns = [
            r"让(.+?)(做|干|去|来|把|给|发|送|告诉|通知|提醒|转告)(.+)",
            r"告诉(.+?)(.+)",
            r"通知(.+?)(.+)",
            r"提醒(.+?)(.+)",
            r"转告(.+?)(.+)",
            r"叫(.+?)(.+)",
        ]
        
        is_direct_instruction = False
        recipient_name = None
        instruction_content = None
        
        email_pattern = r"给(.+?)发.*?邮件[,，]?\s*让他?(.+)"
        email_match = re.search(email_pattern, request)
        if email_match:
            is_direct_instruction = True
            recipient_name = email_match.group(1).strip()
            instruction_content = email_match.group(2).strip()
            logger.info(f"📧 匹配到邮件模式: recipient={recipient_name}, content={instruction_content}")
        
        if not is_direct_instruction:
            for pattern in direct_patterns:
                match = re.search(pattern, request)
                if match:
                    is_direct_instruction = True
                    recipient_name = match.group(1).strip()
                    instruction_content = match.group(2).strip() if len(match.groups()) > 1 else None
                    if instruction_content and len(match.groups()) > 2 and match.group(3):
                        instruction_content = match.group(3).strip()
                    logger.info(f"📧 匹配到直接指令模式: recipient={recipient_name}, content={instruction_content}")
                    break
        
        if is_direct_instruction and recipient_name:
            contact_info = await self._get_contact_info(recipient_name)
            to_email = None
            if contact_info and contact_info.get("email"):
                to_email = contact_info["email"]
                logger.info(f"📧 找到联系人邮箱: {recipient_name} -> {to_email}")
            
            if to_email:
                content = f"{user_formal_name}让我转告你：{instruction_content}\n\n--\n{user_formal_name}的智能助理-{agent_name}"
                logger.info(f"📧 直接指令邮件: {content}")
                return {
                    "to": to_email,
                    "subject": f"{user_formal_name}的转告信息",
                    "content": content,
                    "original_text": request
                }
            else:
                logger.warning(f"📧 未找到联系人邮箱: {recipient_name}，将使用LLM生成")
        
        recipient_name = params.get("recipient_name")
        contact_info = None
        if recipient_name and not params.get("to"):
            contact_info = await self._get_contact_info(recipient_name)
            if contact_info and contact_info.get("email"):
                params["to"] = contact_info["email"]
        elif recipient_name and params.get("to"):
            contact_info = await self._get_contact_info(recipient_name)
        
        attachments_info = ""
        if params.get("attachments"):
            attachments_info = f"\n附件文件: {', '.join(params['attachments'])}"
        
        recipient_note = ""
        if recipient_name:
            recipient_note = f"\n收件人名称: {recipient_name}"
            if contact_info:
                if contact_info.get("relationship"):
                    recipient_note += f"\n与我的关系: {contact_info['relationship']}"
                if contact_info.get("company"):
                    recipient_note += f"\n所在公司: {contact_info['company']}"
                if contact_info.get("position"):
                    recipient_note += f"\n职位: {contact_info['position']}"
                if contact_info.get("notes"):
                    recipient_note += f"\n备注: {contact_info['notes']}"
            if not params.get("to"):
                recipient_note += "\n（未找到邮箱地址，请在 to 字段填入 null）"
        
        from datetime import datetime
        current_year = datetime.now().year
        zodiac_map = {2024: "龙年", 2025: "蛇年", 2026: "马年", 2027: "羊年", 2028: "猴年"}
        current_zodiac = zodiac_map.get(current_year, "")
        
        lunar_info = ""
        try:
            from zhdate import ZhDate
            today = datetime.now()
            lunar_date = ZhDate.from_datetime(today)
            # 使用chinese()方法获取正确的中文农历日期表示
            lunar_info = f"（农历{lunar_date.chinese()}）"
        except ImportError:
            lunar_info = ""
        except Exception as e:
            logger.warning(f"获取农历日期失败: {e}")
            lunar_info = ""
        
        prompt = f"""你是一个专业的邮件撰写助手。请根据用户的请求撰写一封得体、专业的邮件。

当前日期: {datetime.now().strftime("%Y年%m月%d日")}{lunar_info}（{current_year}年是{current_zodiac}）
用户请求: {request}
用户邮箱: {user_email}{attachments_info}{recipient_note}

请撰写邮件，要求如下：
1. 邮件主题：简洁明了，准确反映邮件内容
2. 邮件正文：
   - 开头称呼：直接使用收件人名字，不要加"亲爱的"、"敬爱的"等修饰词
   - 正文内容要丰富充实，至少100字，表达真诚
   - 必须根据关系调整语气和用词风格
   - 如果是祝福类邮件，要写得温暖感人，体现诚意
   - 结尾要有恰当的祝福语
   - 重要：不要假设或臆测收件人的具体情况（如求学、工作、年龄等），只写通用、确定的祝福内容
   - 如果联系人备注中有具体信息，可以适当引用；否则保持内容通用
   - 如需提到生肖年份，必须使用当前年份对应的正确生肖（{current_year}年是{current_zodiac}）
   - 重要：不要在邮件正文中提及文件路径（如"E盘video目录下"等），只需提及附件的文件名（如"《长相思》视频"）或简单说"附件"即可
3. 署名格式（必须严格遵守）：
   - 如果收件人是用户自己（{user_email}），署名：{agent_name}
   - 如果收件人是其他人，署名：{user_formal_name}的智能助理-{agent_name}
   - 不要写"此致 敬礼"，直接在正文最后换行写署名

请以 JSON 格式返回：
{{
    "to": "收件人邮箱（如果已知）",
    "subject": "邮件主题",
    "content": "完整的邮件正文（包含称呼、正文、祝福语和署名）"
}}

只返回 JSON，不要其他内容。"""

        try:
            from ..llm import LLMGateway
            llm = LLMGateway(settings.llm)
            
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            import json
            result = json.loads(response.content.strip().replace("```json", "").replace("```", "").strip())
            
            llm_to = result.get("to")
            if llm_to == "null" or llm_to == "None":
                llm_to = None
            
            final_to = params.get("to")
            if not final_to:
                if llm_to and "@" in llm_to:
                    final_to = llm_to
                elif llm_to:
                    contact_info = await self._get_contact_info(llm_to)
                    if contact_info and contact_info.get("email"):
                        final_to = contact_info["email"]
            
            logger.info(f"📧 主智能体生成邮件: to={final_to}, subject={result.get('subject')}")
            
            email_params = {
                "to": final_to or user_email,
                "subject": params.get("subject") or result.get("subject", "来自智能助手的邮件"),
                "content": params.get("content") or result.get("content", ""),
                "original_text": request
            }
            
            if params.get("attachments"):
                email_params["attachments"] = params["attachments"]
                
                if not params.get("subject") and not result.get("subject"):
                    from pathlib import Path
                    attachment_names = [Path(f).name for f in params["attachments"]]
                    if len(attachment_names) == 1:
                        email_params["subject"] = attachment_names[0]
                    else:
                        email_params["subject"] = f"{attachment_names[0]} 等{len(attachment_names)}个文件"
                
                if not params.get("content") and not result.get("content"):
                    attachment_names = [Path(f).name for f in params["attachments"]]
                    email_params["content"] = f"附件：\n" + "\n".join(f"- {name}" for name in attachment_names)
            
            return email_params
            
        except Exception as e:
            logger.error(f"主智能体生成邮件内容失败: {e}")
            
            fallback_subject = "来自智能助手的邮件"
            fallback_content = f"用户请求: {request}"
            
            if params.get("attachments"):
                from pathlib import Path
                attachment_names = [Path(f).name for f in params["attachments"]]
                if len(attachment_names) == 1:
                    fallback_subject = attachment_names[0]
                else:
                    fallback_subject = f"{attachment_names[0]} 等{len(attachment_names)}个文件"
                
                fallback_content = f"附件：\n" + "\n".join(f"- {name}" for name in attachment_names)
            
            return {
                "to": params.get("to") or user_email,
                "subject": params.get("subject") or fallback_subject,
                "content": params.get("content") or fallback_content,
                "original_text": request,
                "attachments": params.get("attachments", [])
            }

    async def _decompose_task(self, intent: Dict, request: str, context: Dict = None) -> List[Task]:
        """
        任务分解

        根据意图将用户请求分解为多个子任务
        """
        tasks = []
        intent_type = intent.get("type", "")
        params = intent.get("params", {})
        
        if "original_text" not in params:
            params["original_text"] = request

        if intent_type == "play_music":
            action = params.get("action", "play")
            
            if action == "search":
                task = Task(
                    type="search",
                    content=request,
                    params=params,
                    priority=5
                )
            elif action == "list":
                task = Task(
                    type="list",
                    content=request,
                    params=params,
                    priority=5
                )
            elif action in ("pause", "stop", "next", "previous", "resume"):
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
            elif action in ("volume_mute", "volume_unmute", "volume_up", "volume_down"):
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
            elif action in ("open_player", "scan_library"):
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
            elif action in ("adjust_volume", "volume", "volume_up", "volume_down"):
                volume_action = "down" if params.get("level") == "lower" else "up" if params.get("level") == "higher" else params.get("direction", "")
                task = Task(
                    type="volume",
                    content=request,
                    params={"action": volume_action} if volume_action else params,
                    priority=5
                )
            elif action == "set_volume":
                task = Task(
                    type="volume",
                    content=request,
                    params={"action": "set", "value": params.get("value", 0.5)},
                    priority=5
                )
            else:
                task = Task(
                    type="play",
                    content=request,
                    params=params,
                    priority=5
                )
            tasks.append(task)

        elif intent_type == "play_video":
            action = params.get("action", "play")
            
            if action == "search":
                task = Task(
                    type="video_search",
                    content=request,
                    params=params,
                    priority=5
                )
            elif action == "list":
                task = Task(
                    type="video_list",
                    content=request,
                    params=params,
                    priority=5
                )
            elif action in ("pause", "stop", "next", "previous", "resume"):
                task = Task(
                    type=f"video_{action}",
                    content=request,
                    params=params,
                    priority=5
                )
            else:
                task = Task(
                    type="video_play",
                    content=request,
                    params=params,
                    priority=5
                )
            tasks.append(task)

        elif intent_type == "weather_query" or intent_type == "get_weather":
            query_type = params.get("query_type", "current")
            action = params.get("action", "current")
            days = params.get("days", 0)
            
            if query_type == "forecast" or action == "forecast" or days > 0:
                task_type = "weather_forecast"
            else:
                task_type = "current_weather"
            
            task_params = params.copy()
            task_params["days"] = days
            
            task = Task(
                type=task_type,
                content=request,
                params=task_params,
                priority=6
            )
            tasks.append(task)

        elif intent_type == "send_email":
            action = params.get("action", "send")
            
            if action == "send_bulk":
                recipients = params.get("recipients", "")
                
                if isinstance(recipients, list) and len(recipients) > 0:
                    recipient_names = recipients
                elif recipients == "all_contacts":
                    from ..contacts.smart_contact_book import smart_contact_book
                    
                    all_contacts = smart_contact_book.list_all_contacts()
                    contacts_with_email = [c for c in all_contacts if c.email]
                    
                    if not contacts_with_email:
                        logger.warning("❌ 通讯录中没有联系人有邮箱地址")
                        return []
                    
                    max_recipients = 20
                    if len(contacts_with_email) > max_recipients:
                        logger.warning(f"❌ 通讯录中有邮箱的联系人共{len(contacts_with_email)}人，超过限制（最多{max_recipients}人）")
                        return []
                    
                    logger.info(f"📧 向通讯录所有联系人发送邮件，共 {len(contacts_with_email)} 人")
                    for contact in contacts_with_email:
                        task = Task(
                            type="send_email",
                            content=request,
                            params={
                                "recipient_name": contact.name,
                                "to": contact.email,
                                "subject": params.get("subject"),
                                "message": params.get("message"),
                                "original_text": request
                            },
                            priority=7
                        )
                        tasks.append(task)
                    return tasks
                else:
                    logger.warning(f"❌ 不支持的群发方式: recipients={recipients}")
                    return []
                
                if recipient_names:
                    max_recipients = 20
                    if len(recipient_names) > max_recipients:
                        logger.warning(f"❌ 收件人数量超过限制（最多{max_recipients}人），当前有{len(recipient_names)}人")
                        return []
                    
                    logger.info(f"📧 群发邮件给 {len(recipient_names)} 人: {recipient_names}")
                    for name in recipient_names:
                        task = Task(
                            type="send_email",
                            content=request,
                            params={
                                "recipient_name": name,
                                "subject": params.get("subject"),
                                "original_text": request
                            },
                            priority=7
                        )
                        tasks.append(task)
                    return tasks
            
            if action == "save_attachment":
                # 处理保存邮件附件
                save_path = params.get("save_path", "")
                # 从 context 获取附件信息（由 email_monitor 传递）
                attachments = params.get("attachments", [])
                if not attachments and context:
                    attachments = context.get("attachments", [])
                
                if not save_path:
                    logger.warning("❌ 未指定保存路径")
                    return []
                
                if not attachments:
                    logger.warning("❌ 邮件中没有附件需要保存")
                    return []
                
                task = Task(
                    type="save_attachment",
                    content=request,
                    params={
                        "save_path": save_path,
                        "attachments": attachments
                    },
                    priority=7
                )
                tasks.append(task)
            
            elif action == "send_with_attachment":
                # 处理发送带附件的邮件
                email_params = await self._prepare_email_content(request, params)
                email_params["attachment"] = params.get("attachment", "")
                # 如果有收件人提示，尝试查找联系人
                recipient_hint = params.get("recipient_hint", "")
                if recipient_hint:
                    email_params["recipient_hint"] = recipient_hint
                    # 尝试查找联系人邮箱
                    contact_info = await self._get_contact_info(recipient_hint)
                    if contact_info and contact_info.get("email"):
                        email_params["to"] = contact_info["email"]
                        logger.info(f"📧 找到联系人邮箱: {recipient_hint} -> {contact_info['email']}")
                task = Task(
                    type="send_with_attachment",
                    content=request,
                    params=email_params,
                    priority=7
                )
                tasks.append(task)
            
            elif action == "send_current_music":
                email_params = await self._prepare_email_content(request, params)
                email_params["send_current_music"] = True
                if params.get("recipient_name"):
                    email_params["recipient_name"] = params["recipient_name"]
                task = Task(
                    type="send_current_music_email",
                    content=request,
                    params=email_params,
                    priority=7
                )
                tasks.append(task)
            
            elif action == "send_music":
                song_query = params.get("song_query", "")
                email_params = await self._prepare_email_content(request, params)
                email_params["search_music"] = True
                email_params["song_query"] = song_query
                if params.get("recipient_name"):
                    email_params["recipient_name"] = params["recipient_name"]
                task = Task(
                    type="send_email_with_music",
                    content=request,
                    params=email_params,
                    priority=7
                )
                tasks.append(task)
            
            elif action == "send_to_relationship":
                relationship = params.get("relationship", "")
                if not relationship:
                    logger.warning("❌ 未指定关系类型")
                    return []
                
                task = Task(
                    type="send_to_relationship",
                    content=request,
                    params={
                        "relationship": relationship,
                        "subject": params.get("subject"),
                        "content_template": params.get("content_template"),
                        "original_text": request
                    },
                    priority=7
                )
                tasks.append(task)
            
            elif action == "send" and (params.get("attachment") or params.get("attachment_path")):
                attachment = params.get("attachment") or params.get("attachment_path", "")
                recipient_name = params.get("recipient_name", "")
                subject = params.get("subject", "")
                body = params.get("body") or params.get("content", "")
                
                if recipient_name in ["我", "自己", "本人", "我的邮箱"]:
                    from ..config import settings
                    to_email = settings.user.email or settings.agent.email
                    logger.info(f"📧 收件人是用户自己，使用默认邮箱: {to_email}")
                elif recipient_name:
                    contact_info = await self._get_contact_info(recipient_name)
                    to_email = contact_info.get("email") if contact_info else None
                    if to_email:
                        logger.info(f"📧 找到联系人邮箱: {recipient_name} -> {to_email}")
                else:
                    to_email = params.get("to")
                
                task_params = {
                    "recipient_name": recipient_name,
                    "to": to_email,
                    "subject": subject,
                    "content": body,
                    "body": body,
                    "attachment": attachment,
                    "original_text": request
                }
                if params.get("_force_agent"):
                    task_params["_force_agent"] = params["_force_agent"]
                
                task = Task(
                    type="send_email",
                    content=request,
                    params=task_params,
                    priority=7
                )
                tasks.append(task)
            
            else:
                recipient_name = params.get("recipient_name", "")
                recipients = params.get("recipients", "")
                
                all_contacts_patterns = ["通讯录所有人", "通讯录所有人员", "通讯录的人员", "通讯录所有人", "所有联系人", "全部联系人", "all_contacts"]
                is_all_contacts = any(p in recipient_name for p in all_contacts_patterns) or recipient_name == "所有人" or recipients == "all_contacts"
                
                if is_all_contacts:
                    from ..contacts.smart_contact_book import smart_contact_book
                    
                    all_contacts = smart_contact_book.list_all_contacts()
                    contacts_with_email = [c for c in all_contacts if c.email]
                    
                    if not contacts_with_email:
                        logger.warning("❌ 通讯录中没有联系人有邮箱地址")
                        return []
                    
                    max_recipients = 20
                    if len(contacts_with_email) > max_recipients:
                        logger.warning(f"❌ 通讯录中有邮箱的联系人共{len(contacts_with_email)}人，超过限制（最多{max_recipients}人）")
                        return []
                    
                    logger.info(f"📧 向通讯录所有联系人发送邮件，共 {len(contacts_with_email)} 人")
                    for contact in contacts_with_email:
                        task = Task(
                            type="send_email",
                            content=request,
                            params={
                                "recipient_name": contact.name,
                                "to": contact.email,
                                "subject": params.get("subject"),
                                "original_text": request
                            },
                            priority=7
                        )
                        tasks.append(task)
                    return tasks
                
                if recipient_name:
                    separators = ["，", ",", "、", "和", "与", "及"]
                    recipient_names = [recipient_name]
                    for sep in separators:
                        if sep in recipient_name:
                            recipient_names = [n.strip() for n in recipient_name.split(sep) if n.strip()]
                            break
                    
                    if len(recipient_names) > 1:
                        max_recipients = 20
                        if len(recipient_names) > max_recipients:
                            logger.warning(f"❌ 收件人数量超过限制（最多{max_recipients}人），当前有{len(recipient_names)}人")
                            return []
                        
                        logger.info(f"📧 检测到多收件人，拆分为 {len(recipient_names)} 个独立任务: {recipient_names}")
                        for name in recipient_names:
                            task = Task(
                                type="send_email",
                                content=request,
                                params={
                                    "recipient_name": name,
                                    "subject": params.get("subject"),
                                    "message": params.get("message"),
                                    "original_text": request
                                },
                                priority=7
                            )
                            tasks.append(task)
                        return tasks
                
                task_params = {
                    "recipient_name": params.get("recipient_name"),
                    "subject": params.get("subject"),
                    "message": params.get("message"),
                    "body": params.get("body"),
                    "content": params.get("content"),
                    "attachment": params.get("attachment"),
                    "to": params.get("to"),
                    "original_text": request
                }
                if params.get("_force_agent"):
                    task_params["_force_agent"] = params["_force_agent"]
                
                task = Task(
                    type="send_email",
                    content=request,
                    params=task_params,
                    priority=7
                )
                tasks.append(task)

        elif intent_type == "contact_manage":
            action = params.get("action", "query")
            params["original_text"] = request
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "contact_add":
            params["original_text"] = request
            task = Task(
                type="add",
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "contact_lookup":
            params["original_text"] = request
            task = Task(
                type="query",
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "contact_list":
            params["original_text"] = request
            task = Task(
                type="list",
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type in ["calendar", "calendar_operation"]:
            action = params.get("action", "query_events")
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "tts" or intent_type == "text_to_speech":
            action = params.get("action", "synthesize")
            
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "llm_chat":
            action = params.get("action", "chat")
            
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "image_generation":
            action = params.get("action", "generate")
            
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "audio_decrypt":
            action = params.get("action", "decrypt_ncm")
            
            file_path = params.get("file_path", "")
            directory = params.get("directory", "")
            
            if file_path and Path(file_path).is_dir():
                ncm_files = list(Path(file_path).glob("*.ncm"))
                if ncm_files:
                    task = Task(
                        type="batch_decrypt",
                        content=request,
                        params={
                            "files": [str(f) for f in ncm_files],
                            "directory": file_path
                        },
                        priority=5
                    )
                    tasks.append(task)
                    logger.info(f"🔓 批量解密 {len(ncm_files)} 个 NCM 文件")
                else:
                    task = Task(
                        type=action,
                        content=request,
                        params={"error": f"目录中没有找到 NCM 文件: {file_path}"},
                        priority=5
                    )
                    tasks.append(task)
            elif file_path:
                task = Task(
                    type=action,
                    content=request,
                    params={"file_path": file_path},
                    priority=5
                )
                tasks.append(task)
            else:
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
                tasks.append(task)

        elif intent_type in ["travel_itinerary", "create_travel_plan"]:
            destination = params.get("destination", "")
            days = params.get("days", 3)
            
            task = Task(
                type="create_travel_plan",
                content=request,
                params={
                    "destination": destination,
                    "days": days,
                    "original_text": request
                },
                priority=5
            )
            tasks.append(task)

        elif intent_type == "confirm_skill":
            agent_name = params.get("agent_name", "new_agent")
            description = params.get("skill_description", params.get("description", ""))
            trigger_keywords = params.get("trigger_keywords", [])
            
            self._pending_skill_confirmation[agent_name] = params
            
            confirm_msg = f"""🔍 检测到可能需要新技能: {agent_name}

📝 描述: {description}
🔑 触发词: {', '.join(trigger_keywords) if trigger_keywords else '无'}

是否创建此智能体？
• 输入 "是" 或 "y" 确认创建
• 输入其他内容取消，由 LLM 直接处理"""
            
            task = Task(
                type="confirm_skill",
                content=request,
                params=params,
                priority=8
            )
            task.result = confirm_msg
            task.status = TaskStatus.COMPLETED
            tasks.append(task)

        elif intent_type == "create_skill":
            task = Task(
                type="create_skill",
                content=request,
                params=params,
                priority=8
            )
            tasks.append(task)

        elif intent_type == "disk_space":
            task = Task(
                type="disk_space",
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "file_operation":
            action = params.get("action", "file_operation")
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        # 复杂任务：需要多个智能体协作
        elif intent_type == "complex_task":
            # 示例：发送邮件带附件
            if "attachment" in params:
                # 子任务1：准备附件
                tasks.append(Task(
                    type="prepare_attachment",
                    content=f"准备附件: {params['attachment']}",
                    params={"path": params['attachment']},
                    priority=6
                ))

                # 子任务2：发送邮件
                tasks.append(Task(
                    type="send_email",
                    content=request,
                    params=params,
                    priority=7,
                    depends_on=[]  # 依赖子任务1
                ))

        elif intent_type == "pdf_operation":
            action = params.get("action", "pdf_read")
            pdf_actions = ["pdf_read", "pdf_extract_text", "pdf_summarize", "pdf_generate", 
                          "pdf_merge", "pdf_split", "pdf_to_word", "pdf_to_image",
                          "word_to_pdf", "txt_to_pdf", "image_to_pdf", "excel_to_pdf"]
            if action not in pdf_actions and not action.startswith("pdf_"):
                action = f"pdf_{action}"
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "agent_help":
            agent_name = params.get("agent_name", "")
            if agent_name:
                help_info = await self._get_agent_help_from_skill(agent_name)
                logger.debug(f"帮助信息类型: {type(help_info)}, 长度: {len(help_info) if isinstance(help_info, str) else 'N/A'}")
                return help_info
            return "暂无帮助信息"

        elif intent_type == "os_control":
            action = params.get("action", "")
            if action in ("volume_mute", "volume_unmute", "volume_up", "volume_down", "volume_get", "volume_set", "volume_control"):
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
            else:
                task = Task(
                    type=action,
                    content=request,
                    params=params,
                    priority=5
                )
            tasks.append(task)

        elif intent_type == "app_control":
            action = params.get("action", "open")
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "app_management":
            action = params.get("action", "list_apps")
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "download":
            action = params.get("action", "download")
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)
        
        elif intent_type == "crawler_task":
            action = params.get("action", "search")
            url_range = params.get("url_range", [])
            file_type = params.get("file_type", "")
            
            if url_range and len(url_range) == 2:
                import re
                url1 = url_range[0]
                url2 = url_range[1]
                
                if isinstance(url1, list):
                    url1 = url1[0] if url1 else ""
                if isinstance(url2, list):
                    url2 = url2[0] if url2 else ""
                
                url1 = str(url1).strip().strip('`').strip('"').strip("'")
                url2 = str(url2).strip().strip('`').strip('"').strip("'")
                
                id1_match = re.search(r'/(\d+)(?:[/\?]|$)', url1)
                id2_match = re.search(r'/(\d+)(?:[/\?]|$)', url2)
                
                if id1_match and id2_match:
                    start_id = int(id1_match.group(1))
                    end_id = int(id2_match.group(1))
                    
                    task = Task(
                        type="batch_scrape",
                        content=request,
                        params={
                            "url": url1,
                            "start_id": start_id,
                            "end_id": end_id,
                            "link_type": file_type or "mp4"
                        },
                        priority=5
                    )
                    tasks.append(task)
                    logger.info(f"🔄 批量爬取任务: {start_id} 到 {end_id}")
                    return tasks
            
            action_mapping = {
                "search": "web_search",
                "crawl": "crawl_webpage",
                "crawl_webpage": "crawl_webpage",
                "image_search": "search_image",
                "video_search": "search_video",
                "mp3_search": "search_mp3",
                "scrape_links": "scrape_links",
                "scrape": "scrape_links",
                "scrape_video_links": "scrape_video_links",
                "scrape_m3u8_links": "scrape_m3u8_links",
                "extract_mp4_links": "extract_mp4_links",
                "extract_video_links": "extract_video_links",
                "scrape_mp4_links": "scrape_mp4_links",
                "extract_page_links": "extract_page_links",
                "scrape_page_links": "scrape_page_links",
                "batch_scrape": "batch_scrape",
                "file_download": "file_download",
            }
            task_type = action_mapping.get(action, action)
            task = Task(
                type=task_type,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)
        
        elif intent_type == "download_file":
            urls = params.get("urls", [])
            save_dir = params.get("save_dir")
            if urls:
                task = Task(
                    type="download",
                    content=request,
                    params={
                        "action": "download",
                        "url": urls[0],
                        "save_dir": save_dir
                    },
                    priority=5
                )
                tasks.append(task)

        elif intent_type == "news":
            action = params.get("action", "fetch_news")
            # 统一 action 名称格式
            if action.startswith("news_"):
                action = action.replace("news_", "fetch_")
                if action == "fetch_fetch":
                    action = "fetch_news"
            task = Task(
                type=action,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "web_server":
            action = params.get("action", "status")
            task_type_mapping = {
                "start": "start_web_server",
                "启动": "start_web_server",
                "启动服务": "start_web_server",
                "service_start": "start_web_server",
                "stop": "stop_web_server",
                "停止": "stop_web_server",
                "停止服务": "stop_web_server",
                "status": "get_web_status",
                "状态": "get_web_status",
                "restart": "restart_web_server",
                "重启": "restart_web_server",
                "show_qr": "show_qr_code",
                "二维码": "show_qr_code",
            }
            task_type = task_type_mapping.get(action, "start_web_server" if action in ["start", "启动", "开启", "启动服务"] else "get_web_status")
            task = Task(
                type=task_type,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "qq_bot":
            action = params.get("action", "status")
            task_type_mapping = {
                "start": "start_qq_bot",
                "启动": "start_qq_bot",
                "stop": "stop_qq_bot",
                "停止": "stop_qq_bot",
                "status": "get_qq_status",
                "状态": "get_qq_status",
                "configure": "configure_qq_bot",
                "配置": "configure_qq_bot",
            }
            task_type = task_type_mapping.get(action, "start_qq_bot" if action in ["start", "启动", "开启"] else "get_qq_status")
            task = Task(
                type=task_type,
                content=request,
                params=params,
                priority=5
            )
            tasks.append(task)

        elif intent_type == "workflow":
            steps = params.get("steps", [])
            file_path = params.get("file_path") or params.get("attachments", [None])[0] if params.get("attachments") else None
            
            if steps:
                for i, step in enumerate(steps):
                    step_agent = step.get("agent", "")
                    step_action = step.get("action", "")
                    step_params = step.get("params", {})
                    step_params["action"] = step_action
                    step_params["step_index"] = i
                    step_params["is_workflow"] = True
                    
                    if file_path and not step_params.get("file_path"):
                        step_params["file_path"] = file_path
                    
                    task = Task(
                        type=step_action,
                        content=f"步骤{i+1}: {step_action}",
                        params=step_params,
                        priority=5 + i,
                        depends_on=[] if i == 0 else [tasks[i-1].id]
                    )
                    tasks.append(task)
                logger.info(f"📋 工作流分解: {len(steps)} 个步骤")

        # 默认：作为一般任务处理
        else:
            if intent_type == "master":
                action = params.get("action", "")
                if action == "help":
                    return self._get_help_info()
                elif action == "status":
                    return await self._get_system_status()
                elif action == "reload_agents":
                    return self._reload_agents()
            
            if intent_type in ["save_document", "send_email", "contact_list", "contact_add", "contact_lookup", "generate_image", "query_stock", "query_index", "stock_query", "query_price", "query_kline", "get_news", "disk_space", "find_file", "clipboard_write", "take_screenshot"]:
                task = Task(
                    type=intent_type,
                    content=request,
                    params=params,
                    priority=5
                )
                tasks.append(task)
                
                # 特殊处理：如果 generate_image 任务的用户请求包含"并发到邮箱"、"发送到邮箱"等完整短语，添加邮件发送步骤
                if intent_type == "generate_image":
                    logger.info(f"🔍 检查 generate_image 请求: {request[:100]}...")
                    matched_keywords = [kw for kw in ["并发到邮箱", "发送到邮箱", "发到邮箱", "并发到邮件", "发送到邮件", "发到邮件", "并发到我的邮箱", "发送到我的邮箱", "发到我的邮箱", "并发到我的邮件", "发送到我的邮件", "发到我的邮件"] if kw in request]
                    logger.info(f"🔍 匹配到的关键词: {matched_keywords}")
                    
                    if matched_keywords:
                        logger.info(f"📧 检测到图片生成+邮件发送请求，添加邮件步骤")
                        
                        # 获取用户配置
                        from ..config import settings
                        user_email = settings.user.email if settings.user else ""
                        user_name = settings.user.name if settings.user else "用户"
                        
                        # 标记第一个任务为工作流步骤
                        task.params["is_workflow"] = True
                        task.params["step_index"] = 0
                        
                        email_task = Task(
                            type="send_email",
                            content=f"发送图片到邮箱",
                            params={
                                "recipient_name": user_name,
                                "to": user_email,
                                "attachment": "{previous_result}",
                                "is_workflow": True,
                                "step_index": 1
                            },
                            priority=5
                        )
                        tasks.append(email_task)
            else:
                # 如果 params 中包含 answer 字段，说明工具选择已经返回了答案，直接使用 params
                if "answer" in params:
                    task = Task(
                        type="general",
                        content=params,
                        params=params,
                        priority=3
                    )
                else:
                    task = Task(
                        type="general",
                        content=request,
                        params=params,
                        priority=3
                    )
                tasks.append(task)

        return tasks
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """🤖 智能助手帮助

📌 音乐控制：
• 播放音乐 / 播放 [歌曲名]
• 暂停 / 停止 / 继续
• 下一首 / 上一首

📌 系统控制：
• 静音 / 取消静音
• 声音大一点 / 声音小一点
• 关机 / 重启 / 锁屏 / 休眠

📌 其他功能：
• 查天气 [城市]
• 发邮件给 [联系人]
• 搜索 [内容]

💡 提示：使用 @智能体名称 可以指定特定智能体处理"""

    async def _get_system_status(self) -> str:
        """获取系统状态"""
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('C:')
        return f"""📊 系统状态：
• CPU 使用率: {cpu}%
• 内存使用: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)
• 磁盘使用: {disk.percent}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)"""

    def _reload_agents(self) -> str:
        """热更新智能体"""
        from ..multi_agent_system import multi_agent_system
        
        result = multi_agent_system.reload_agents()
        
        if result.get("status") == "success":
            return f"✅ 智能体热更新完成，共 {result['agents_count']} 个智能体"
        else:
            return f"❌ 热更新失败: {result.get('error', '未知错误')}"

    def _get_task_description(self, task_type: str) -> str:
        """获取任务类型的中文描述"""
        task_descriptions = {
            "generate_image": "生成图片",
            "text_to_image": "生成图片",
            "image_generation": "生成图片",
            "play_music": "播放音乐",
            "play_video": "播放视频",
            "send_email": "发送邮件",
            "weather_query": "查询天气",
            "file_download": "下载文件",
            "download": "下载文件",
            "doc_generate": "生成文档",
            "pdf_generate": "生成PDF",
            "save_document": "保存文档",
            "web_search": "搜索网页",
            "crawl_webpage": "爬取网页",
        }
        return task_descriptions.get(task_type, task_type)

    async def _get_agent_help_from_skill(self, agent_name: str) -> str:
        """从智能体获取帮助信息（优先从配置文件读取）"""
        from .agent_scanner import get_agent_scanner
        
        scanner = get_agent_scanner()
        metadata = scanner.get_agent_metadata(agent_name)
        
        if metadata and metadata.help:
            return metadata.help
        
        agent = await self._get_or_create_agent(agent_name)
        if not agent:
            return f"❌ 未找到智能体: {agent_name}"
        
        parts = []
        agent_display_name = agent_name.replace('_agent', '').replace('_', ' ').title()
        parts.append(f"## 🤖 {agent_display_name}智能体")
        
        if hasattr(agent, 'KEYWORD_MAPPINGS') and agent.KEYWORD_MAPPINGS:
            parts.append("\n### 支持的关键词：")
            
            action_keywords = {}
            for keyword, (action, params) in agent.KEYWORD_MAPPINGS.items():
                if action not in action_keywords:
                    action_keywords[action] = []
                action_keywords[action].append(keyword)
            
            for action, keywords in sorted(action_keywords.items()):
                parts.append(f"\n**{action}**：")
                parts.append(f"  {', '.join(keywords)}")
        
        if hasattr(agent, 'skill') and agent.skill and agent.skill.get('help'):
            parts.append("\n\n" + agent.skill['help'])
        
        return "\n".join(parts)

    async def _dispatch_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        分配任务给合适的智能体

        Args:
            tasks: 任务列表

        Returns:
            完成的任务列表
        """
        completed_tasks = []
        previous_result = None

        for task in tasks:
            logger.info(f"📋 处理任务: {task.type}, step_index={task.params.get('step_index')}, is_workflow={task.params.get('is_workflow')}")
            
            if task.params.get("is_workflow") and task.params.get("step_index", 0) > 0:
                prev_str = str(previous_result)[:100] if previous_result else 'None'
                logger.info(f"🔍 检查 previous_result: {prev_str}...")
                
                if previous_result:
                    prev_output = previous_result
                    if isinstance(previous_result, dict):
                        prev_output = previous_result.get("output", previous_result.get("message", str(previous_result)))
                    
                    for key, value in task.params.items():
                        if isinstance(value, str):
                            import re
                            
                            output_pattern = r'\{output:([^}]+)\}'
                            output_matches = re.findall(output_pattern, value)
                            if output_matches:
                                for match in output_matches:
                                    placeholder = f"{{output:{match}}}"
                                    replacement = str(prev_output)
                                    task.params[key] = value.replace(placeholder, replacement)
                                    logger.info(f"🔄 工作流: 使用前一步骤结果替换 {placeholder} -> {str(replacement)[:100]}...")
                            
                            placeholders = [
                                "{{previous_result}}",
                                "{previous_result}",
                                "{previouss_result}",
                                "{{previouss_result}}",
                            ]
                            for placeholder in placeholders:
                                if placeholder in value:
                                    replacement = str(prev_output)
                                    
                                    if key == "attachment":
                                        path_match = re.search(r'([A-Za-z]:\\[^\n\r]+\.(xlsx|xls|docx|doc|pdf|txt|csv))', replacement)
                                        if path_match:
                                            replacement = path_match.group(1)
                                            logger.info(f"📎 从结果中提取文件路径: {replacement}")
                                    
                                    task.params[key] = value.replace(placeholder, replacement)
                                    logger.info(f"🔄 工作流: 使用前一步骤结果作为参数 {key} = {str(task.params[key])[:100]}...")
                                    break
                else:
                    logger.warning(f"⚠️ 工作流步骤 {task.params.get('step_index', 0)} 没有前一步骤结果可用")
            
            if task.type in ["current_weather", "weather_forecast"] and Settings:
                city = task.params.get("city", "")
                if not city or city in ["当前城市", "当前", "本地", "这里", "此地"]:
                    settings = Settings()
                    address = settings.user.address or ""
                    city_only = settings.user.city or ""
                    
                    if address and city_only:
                        task.params["city"] = f"{city_only}{address}"
                    elif address:
                        task.params["city"] = address
                    elif city_only:
                        task.params["city"] = city_only
                    
                    if task.params.get("city"):
                        logger.info(f"🏙️ 使用用户设置的地址: {task.params['city']}")

            agent = await self._select_agent(task)

            if agent:
                success = await agent.assign_task(task)

                if success:
                    self.task_agent_map[task.id] = agent.name
                    logger.info(f"📤 任务 '{task.id}' 分配给 '{agent.name}'")

                    # 脉冲询问方式等待任务完成
                    # 下载任务需要更长的超时时间
                    if task.type in ['file_download', 'download', 'video_download']:
                        max_wait = 3600  # 下载任务最多等待30分钟
                    elif task.type in ['generate_image', 'text_to_image', 'image_generation']:
                        max_wait = 120  # 图片生成最多等待2分钟
                    else:
                        max_wait = 600  # 其他任务最多等待5分钟
                    wait_interval = 0.5  # 每次间隔0.5秒
                    wait_count = 0
                    
                    # 任务执行超时提示
                    task_timeout_sent = False
                    
                    async def check_task_timeout():
                        nonlocal task_timeout_sent
                        await asyncio.sleep(3.0)
                        if not task_timeout_sent:
                            task_timeout_sent = True
                            logger.info(f"⏳ 任务 '{task.type}' 执行时间超过3秒，发送提示消息")
                            from ..session_manager import simple_session_manager
                            simple_session_manager.add_message("system", f"⏳ 正在{self._get_task_description(task.type)}，请稍候...")
                            if hasattr(self, '_send_temp_message'):
                                self._send_temp_message(f"⏳ 正在{self._get_task_description(task.type)}，请稍候...")
                    
                    task_timeout_task = asyncio.create_task(check_task_timeout())
                    
                    while wait_count < max_wait:
                        # 从智能体的任务列表中获取最新状态
                        latest_task = agent.tasks.get(task.id)
                        if latest_task:
                            if latest_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                                break
                        else:
                            # 任务不在列表中，可能已完成被清理
                            break
                        
                        await asyncio.sleep(wait_interval)
                        wait_count += 1
                    
                    task_timeout_sent = True
                    if not task_timeout_task.done():
                        task_timeout_task.cancel()
                        try:
                            await task_timeout_task
                        except asyncio.CancelledError:
                            pass
                    
                    if wait_count >= max_wait:
                        logger.warning(f"⏰ 任务 '{task.id}' 等待超时")
                    
                    # 保存任务结果供后续工作流步骤使用
                    if task.params.get("is_workflow"):
                        # 从智能体获取最新的任务状态和结果
                        final_task = agent.tasks.get(task.id)
                        if final_task and final_task.result:
                            previous_result = final_task.result
                            logger.info(f"💾 工作流: 保存步骤结果，长度: {len(str(final_task.result))}")
                        elif task.result:
                            previous_result = task.result
                            logger.info(f"💾 工作流: 保存步骤结果（本地），长度: {len(str(task.result))}")
                        else:
                            logger.warning(f"⚠️ 工作流步骤没有返回结果")
                    
                    completed_tasks.append(task)
                else:
                    logger.error(f"❌ 任务 '{task.id}' 分配失败")
                    task.status = TaskStatus.FAILED
                    task.error = "智能体拒绝接受任务"
                    completed_tasks.append(task)
            else:
                logger.warning(f"⚠️ 没有找到合适的智能体处理任务: {task.type}")
                
                file_path = task.params.get("file_path", "")
                file_ext = Path(file_path).suffix.lower() if file_path else None
                
                from ..intent.intent_parser import IntentParser
                if self._intent_parser is None:
                    self._intent_parser = IntentParser()
                parser = self._intent_parser
                
                missing_skill = await parser._analyze_missing_skill_with_llm(
                    task.content or task.type, 
                    file_ext
                )
                
                if missing_skill:
                    logger.info(f"🔍 检测到缺失技能: {missing_skill['agent_name']}")
                    
                    agent_name = missing_skill.get('agent_name', '')
                    skill_name = missing_skill.get('skill_name', agent_name)
                    description = missing_skill.get('skill_description', '') or missing_skill.get('description', '')
                    detailed_description = missing_skill.get('detailed_description', '')
                    trigger_keywords = missing_skill.get('trigger_keywords', [])
                    suggested_actions = missing_skill.get('suggested_actions', [])
                    required_dependencies = missing_skill.get('required_dependencies', [])
                    external_apis = missing_skill.get('external_apis', [])
                    priority = missing_skill.get('priority', 'medium')
                    user_request = missing_skill.get('user_request', task.content or task.type)
                    
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
                    
                    actions_summary = ""
                    if suggested_actions:
                        for action in suggested_actions[:3]:
                            if isinstance(action, dict):
                                actions_summary += f"  - {action.get('name', '未命名')}: {action.get('description', '')}\n"
                            else:
                                actions_summary += f"  - {action}\n"
                    
                    keywords_str = ", ".join(trigger_keywords[:5]) if trigger_keywords else "待分析"
                    deps_str = ", ".join(required_dependencies[:3]) if required_dependencies else "待分析"
                    apis_str = ", ".join(external_apis[:3]) if external_apis else "无"
                    
                    confirm_msg = f"""🔍 检测到缺失技能

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 技能名称: {skill_name}
📁 智能体文件: {agent_name}.py
🎯 优先级: {priority_emoji} {priority.upper()}

📝 功能描述:
{description}

{f"📋 详细说明:\n{detailed_description}" if detailed_description else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 支持的操作:
{actions_summary if actions_summary else "  待分析"}

🔑 触发关键词: {keywords_str}

📦 依赖库: {deps_str}

🌐 外部 API: {apis_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 是否自动创建此智能体？
   - 输入 "是" 或 "y" 确认创建
   - 输入其他内容取消

📄 详细需求文档将保存到: skills/pending/{agent_name}.md

原始请求: {user_request}"""
                    
                    self._pending_skill_confirmation[agent_name] = missing_skill
                    
                    task.result = confirm_msg
                    task.status = TaskStatus.COMPLETED
                    completed_tasks.append(task)
                    return completed_tasks
                
                logger.info("交给LLM处理")
                try:
                    llm_response = await self._call_llm_for_general(task.content or task.type)
                    task.result = llm_response
                    task.status = TaskStatus.COMPLETED
                    
                    if task.params.get("is_workflow"):
                        previous_result = llm_response
                        logger.info(f"💾 工作流: 保存 LLM 结果，长度: {len(str(llm_response))}")
                except Exception as e:
                    logger.error(f"LLM 处理失败: {e}")
                    task.status = TaskStatus.FAILED
                    task.error = f"处理失败: {str(e)}"
                completed_tasks.append(task)

        return completed_tasks

    async def _select_agent(self, task: Task) -> Optional[BaseAgent]:
        """
        选择最适合处理任务的智能体（支持懒加载）

        Args:
            task: 任务

        Returns:
            选中的智能体或 None
        """
        if task.params.get("_force_agent"):
            force_agent = task.params["_force_agent"]
            logger.info(f"🎯 强制使用智能体: {force_agent}")
            return await self._get_or_create_agent(force_agent)

        task_type = task.type
        
        volume_actions = ["volume", "volume_up", "volume_down", "volume_mute", "volume_unmute", "volume_set", "volume_get", "volume_control"]
        if task_type in volume_actions:
            if task.params.get("_force_agent") == "music_agent":
                logger.info(f"🎵 @音乐智能体，使用音乐播放器音量控制")
                return await self._get_or_create_agent("music_agent")
            else:
                logger.info(f"🔊 使用系统音量控制")
                return await self._get_or_create_agent("os_agent")

        url = task.params.get("url", "") or task.params.get("video_name", "") or task.params.get("video_path", "")
        
        if task_type == "play":
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flac', '.webm', '.m3u8', '.ts']
            if url and any(ext in url.lower() for ext in video_extensions):
                logger.info(f"🎬 检测到视频URL，使用视频智能体: {url[:50]}...")
                return await self._get_or_create_agent("video_agent")
            if task.params.get("is_workflow") and url:
                logger.info(f"🎬 工作流播放任务，使用视频智能体")
                return await self._get_or_create_agent("video_agent")
        
        if task_type == "search":
            original_text = task.params.get("original_text", "")
            query = task.params.get("query", "")
            name = task.params.get("name", "")
            
            contact_keywords = ["我妈", "我爸", "我老婆", "我老公", "我儿子", "我女儿", "联系人", "家人", "朋友", "同事"]
            if any(kw in original_text or kw in query or kw in name for kw in contact_keywords):
                logger.info(f"👤 检测到联系人搜索，使用联系人智能体")
                return await self._get_or_create_agent("contact_agent")
            
            if name and not query:
                logger.info(f"👤 检测到联系人查询，使用联系人智能体: {name}")
                return await self._get_or_create_agent("contact_agent")
            
            logger.info(f"🎵 使用音乐搜索")
            return await self._get_or_create_agent("music_agent")

        from ..routing.routing_manager import get_routing_manager
        routing = get_routing_manager()
        task_agent_mapping = routing.get_task_to_agent()

        agent_name = task_agent_mapping.get(task.type)
        
        if agent_name:
            return await self._get_or_create_agent(agent_name)
        
        if self.skill_manager:
            matching_skills = self.skill_manager.find_matching_skills(task.content or task.type)
            if matching_skills:
                skill = matching_skills[0]
                logger.info(f"📚 匹配到 Skill: {skill.metadata.name}")
                skill_detail = self.skill_manager.get_skill_detail(skill.metadata.name)
                if skill_detail:
                    task.params["_skill_info"] = skill_detail
        
        # 根据文件后缀名自动选择智能体（类似Windows文件关联）
        # 检查任务参数中是否有文件路径
        file_path = task.params.get("file_path") or task.params.get("path")
        if file_path:
            agent_name = self.get_agent_for_file(file_path, action="open")
            if agent_name:
                logger.info(f"🎯 根据文件后缀 '{Path(file_path).suffix}' 选择智能体: {agent_name}")
                return await self._get_or_create_agent(agent_name)
        
        # 检查任务内容中是否包含文件路径
        content = task.content
        if content:
            # 确保 content 是字符串
            if not isinstance(content, str):
                content = str(content)
            
            # 尝试从内容中提取文件路径
            import re
            # 匹配常见的文件路径模式
            file_patterns = [
                r'[a-zA-Z]:\\[^<>"|?*\n]+\.\w+',  # Windows绝对路径
                r'\.\\[^<>"|?*\n]+\.\w+',          # 相对路径
                r'[^<>"|?*\s]+\.mp3',
                r'[^<>"|?*\s]+\.mp4',
                r'[^<>"|?*\s]+\.pdf',
                r'[^<>"|?*\s]+\.wav',
                r'[^<>"|?*\s]+\.flac',
            ]
            for pattern in file_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted_path = match.group(0)
                    agent_name = self.get_agent_for_file(extracted_path, action="open")
                    if agent_name:
                        logger.info(f"🎯 从内容中提取文件 '{extracted_path}'，选择智能体: {agent_name}")
                        # 将文件路径添加到任务参数中
                        task.params["file_path"] = extracted_path
                        return await self._get_or_create_agent(agent_name)

        for agent in self.sub_agents.values():
            if agent.has_capability(task.type):
                if agent.status.value != "busy":
                    return agent

        if task.type == "general":
            return self

        return None

    async def _aggregate_results(self, results: List[Task], intent: Dict) -> str:
        """
        汇总任务结果

        Args:
            results: 完成的任务列表
            intent: 原始意图

        Returns:
            汇总后的响应
        """
        success_tasks = [t for t in results if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in results if t.status == TaskStatus.FAILED]

        agent_names = set()
        for task in results:
            if task.assigned_to:
                agent_names.add(task.assigned_to)
        
        self._last_agent_names = list(agent_names) if agent_names else None

        if len(results) == 1:
            task = results[0]
            if task.status == TaskStatus.COMPLETED:
                result = task.result
                
                if task.no_retry:
                    logger.info(f"🚫 任务标记为禁止重试，直接返回结果")
                    return str(result) if result else "✅ 任务完成"
                
                if isinstance(result, dict):
                    if result.get("cannot_handle"):
                        logger.info(f"🔄 子智能体 {result.get('agent')} 无法处理: {result.get('reason')}")
                        
                        missing_info = result.get('missing_info', {})
                        if missing_info:
                            logger.info(f"🔍 尝试从上下文推断缺失信息: {missing_info}")
                            inferred = await self._infer_missing_info(task, missing_info)
                            if inferred:
                                logger.info(f"✅ 推断成功: {inferred}")
                                task.params.update(inferred)
                                agent_name = result.get('agent')
                                if agent_name:
                                    agent = await self._get_or_create_agent(agent_name)
                                    if agent:
                                        await agent.assign_task(task)
                                        return await self._wait_for_task_completion(task)
                        
                        suggestion = result.get('suggestion', '')
                        if suggestion and suggestion in self._agents:
                            logger.info(f"🔄 尝试重新分配给: {suggestion}")
                            new_agent = await self._get_or_create_agent(suggestion)
                            if new_agent:
                                await new_agent.assign_task(task)
                                return await self._wait_for_task_completion(task)
                        
                        logger.info(f"🤖 交给 LLM 处理")
                        llm_response = await self._call_llm_for_general(task.content or task.type)
                        return llm_response
                    
                    if result.get("need_llm"):
                        logger.info(f"🤖 子智能体无法处理，交给 LLM: {result.get('reason')}")
                        llm_response = await self._call_llm_for_general(task.content or task.type)
                        return llm_response
                    
                    if result.get("success") and "qr_code" in result:
                        response = f"🌐 Web服务器访问信息\n"
                        response += f"📍 地址: {result.get('url', '')}\n"
                        response += f"🔑 密码: {result.get('password', '')}\n"
                        response += f"📱 请扫描二维码访问"
                        
                        from ..channels.base import OutgoingMessage
                        return OutgoingMessage(
                            content=response,
                            metadata={"web_server_result": result, "agent_names": list(agent_names)}
                        )
                    
                    if result.get("success"):
                        return result.get("message", "✅ 任务完成")
                    else:
                        return result.get("message", "❌ 任务失败")
                
                result_str = str(result) if result else "✅ 任务完成"
                
                error_patterns = [
                    "❌ 未知的操作",
                    "❌ 不支持",
                    "❌ 无法处理",
                    "❌ 操作失败",
                    "❌ 任务失败",
                    "❌ 执行失败",
                ]
                
                has_error = any(pattern in result_str for pattern in error_patterns)
                
                if has_error:
                    logger.info(f"🔄 子智能体返回错误，尝试 LLM 二次处理: {result_str[:100]}")
                    
                    original_request = task.content or task.params.get("original_text", "")
                    
                    if original_request:
                        llm_response = await self._call_llm_for_general(original_request)
                        
                        if llm_response and "❌" not in llm_response and "无法" not in llm_response:
                            logger.info(f"✅ LLM 二次处理成功")
                            return llm_response
                        else:
                            logger.info(f"⚠️ LLM 也无法处理，返回原始错误")
                            return result_str
                
                skip_llm_patterns = [
                    "安装",
                    "软件",
                    "下载",
                    "卸载",
                    "📈",
                    "股票",
                    "股价",
                    "收盘价",
                    "交易日",
                ]
                
                if any(pattern in result_str for pattern in skip_llm_patterns):
                    return result_str
                
                not_found_patterns = [
                    "您还没有记录",
                    "未检测到",
                    "不存在",
                    "❌ 没有找到",
                    "❌ 未找到",
                ]
                
                if any(pattern in result_str for pattern in not_found_patterns):
                    if "❌" in result_str:
                        logger.info(f"🤖 子智能体未找到结果，交给 LLM 尝试从历史记录查找")
                        llm_response = await self._call_llm_for_general(task.content or task.type)
                        if llm_response and "不知道" not in llm_response and "没有记录" not in llm_response:
                            return llm_response
                
                return result_str
            else:
                return f"❌ 任务失败: {task.error}"

        response_parts = []

        if success_tasks:
            response_parts.append(f"✅ 成功完成 {len(success_tasks)} 个任务")
            for task in success_tasks:
                if task.result:
                    response_parts.append(f"  • {task.type}: {task.result}")

        if failed_tasks:
            response_parts.append(f"❌ {len(failed_tasks)} 个任务失败")
            for task in failed_tasks:
                response_parts.append(f"  • {task.type}: {task.error}")

        return "\n".join(response_parts)

    async def _handle_agent_message(self, message: Message):
        """处理来自子智能体的消息"""
        if message.type == "task_completed":
            task_id = message.data.get("task_id")
            status = message.data.get("status")

            logger.info(f"📬 收到任务完成报告: {task_id} - {status}")

            # 通知用户
            if self._notification_callback:
                agent_name = message.from_agent
                content = f"【{agent_name}】{message.content}"
                await self._notification_callback(content)

        elif message.type == "status_update":
            # 状态更新
            agent_name = message.from_agent
            status = message.data.get("status")
            logger.info(f"📊 '{agent_name}' 状态更新: {status}")
            
        elif message.type == "new_email_notification":
            # 新邮件通知 - 在对话窗口显示
            if self._notification_callback:
                await self._notification_callback(message.content)
        
        elif message.type == "notification":
            # 通用通知消息（如日程提醒）
            if self._notification_callback:
                await self._notification_callback(message.content)

    def set_notification_callback(self, callback: Callable):
        """设置通知回调"""
        self._notification_callback = callback

    def set_play_video_callback(self, callback: Callable):
        """设置视频播放回调"""
        self._play_video_callback = callback

    async def execute_task(self, task: Task) -> Any:
        """
        主智能体执行任务

        主智能体主要负责任务调度，不直接执行具体任务
        """
        if task.type == "general":
            return await self._handle_general_task(task.content)
        if task.type == "create_skill":
            return await self._handle_create_skill(task.params)
        return await self.process_user_request(task.content, task.params)

    async def _handle_create_skill(self, params: Dict) -> str:
        """处理创建缺失技能的任务"""
        agent_name = params.get("agent_name", "")
        skill_name = params.get("skill_name", "")
        description = params.get("skill_description", "") or params.get("description", "")
        detailed_description = params.get("detailed_description", "")
        suggested_actions = params.get("suggested_actions", [])
        trigger_keywords = params.get("trigger_keywords", [])
        required_dependencies = params.get("required_dependencies", [])
        external_apis = params.get("external_apis", [])
        data_sources = params.get("data_sources", [])
        implementation_notes = params.get("implementation_notes", [])
        edge_cases = params.get("edge_cases", [])
        priority = params.get("priority", "medium")
        user_request = params.get("user_request", "")
        auto_implement = params.get("auto_implement", True)
        auto_test = params.get("auto_test", True)
        auto_fix = params.get("auto_fix", True)
        
        logger.info(f"🔨 自动创建缺失技能: {agent_name}")
        
        try:
            pending_skills_dir = Path(__file__).parent.parent.parent / "skills" / "pending"
            pending_skills_dir.mkdir(parents=True, exist_ok=True)
            
            skill_file = pending_skills_dir / f"{agent_name}.md"
            
            if skill_file.exists():
                return f"✅ 技能 {agent_name} 已存在"
            
            skill_content = self._generate_skill_content(
                agent_name=agent_name,
                skill_name=skill_name,
                description=description,
                suggested_actions=suggested_actions,
                user_request=user_request,
                detailed_description=detailed_description,
                trigger_keywords=trigger_keywords,
                required_dependencies=required_dependencies,
                external_apis=external_apis,
                data_sources=data_sources,
                implementation_notes=implementation_notes,
                edge_cases=edge_cases,
                priority=priority
            )
            
            skill_file.write_text(skill_content, encoding='utf-8')
            logger.info(f"✅ 已创建 Skill 文件: {skill_file}")
            
            if auto_implement:
                logger.info(f"🔧 自动生成智能体代码: {agent_name}")
                
                dev_agent = await self._get_or_create_agent("developer_agent")
                if dev_agent:
                    impl_result = await dev_agent.execute_task(Task(
                        type="create_agent_from_skill",
                        content=f"根据 {agent_name}.md 生成智能体",
                        params={"skill_file": str(skill_file), "skill_content": skill_content}
                    ))
                    
                    if impl_result and "✅" in impl_result:
                        if auto_test:
                            logger.info(f"🧪 自动测试智能体: {agent_name}")
                            test_result = await dev_agent.execute_task(Task(
                                type="test_agent",
                                content=f"测试 {agent_name}",
                                params={"agent_name": agent_name}
                            ))
                            
                            if "❌" in test_result:
                                if auto_fix:
                                    logger.info(f"🔧 自动修复智能体: {agent_name}")
                                    fix_result = await dev_agent.execute_task(Task(
                                        type="fix_agent",
                                        content=f"修复 {agent_name}",
                                        params={"agent_name": agent_name, "error": test_result}
                                    ))
                                    
                                    if "✅" in fix_result:
                                        return f"""🔨 检测到缺失技能，已自动创建、实现并修复

📝 Skill 文件: skills/pending/{agent_name}.md
{impl_result}

🧪 测试结果:
{test_result}

🔧 修复结果:
{fix_result}

💡 下一步: 重启应用或使用热加载来使用新智能体

原始请求: {user_request}"""
                                    else:
                                        return f"""🔨 检测到缺失技能，已创建并实现

📝 Skill 文件: skills/pending/{agent_name}.md
{impl_result}

⚠️ 自动修复失败:
{fix_result}

💡 下一步: 手动修复 {agent_name}.py 后重启应用

原始请求: {user_request}"""
                                else:
                                    return f"""🔨 检测到缺失技能，已创建并实现

📝 Skill 文件: skills/pending/{agent_name}.md
{impl_result}

⚠️ 测试发现问题:
{test_result}

💡 下一步: 手动修复 {agent_name}.py 后重启应用

原始请求: {user_request}"""
                            else:
                                return f"""🔨 检测到缺失技能，已自动创建、实现并测试通过

📝 Skill 文件: skills/pending/{agent_name}.md
{impl_result}

🧪 测试结果:
{test_result}

💡 下一步: 重启应用或使用热加载来使用新智能体

原始请求: {user_request}"""
                        else:
                            return f"""🔨 检测到缺失技能，已自动创建并实现

📝 Skill 文件: skills/pending/{agent_name}.md
{impl_result}

💡 下一步: 重启应用或使用热加载来使用新智能体

原始请求: {user_request}"""
                    else:
                        return f"""🔨 检测到缺失技能，已创建 Skill 文档

📝 文件: skills/pending/{agent_name}.md
📋 描述: {description}
🔧 建议操作: {', '.join(suggested_actions)}

⚠️ 自动生成代码失败: {impl_result}

💡 下一步: 手动实现 {agent_name}.py 智能体代码

原始请求: {user_request}"""
            
            return f"""🔨 检测到缺失技能，已自动创建 Skill 文档

📝 文件: skills/pending/{agent_name}.md
📋 描述: {description}
🔧 建议操作: {', '.join(suggested_actions)}

💡 下一步:
1. 查看 skills/pending/{agent_name}.md 文件确认技能定义
2. 实现 {agent_name}.py 智能体代码
3. 将 .md 文件移动到 src/personal_agent/agents/ 目录
4. 在 master.py 中注册智能体

原始请求: {user_request}"""
            
        except Exception as e:
            logger.error(f"创建 Skill 文件失败: {e}")
            return f"❌ 创建 Skill 文件失败: {e}"

    def _generate_skill_content(
        self, 
        agent_name: str, 
        skill_name: str, 
        description: str, 
        suggested_actions: List[str],
        user_request: str,
        detailed_description: str = "",
        trigger_keywords: List[str] = None,
        required_dependencies: List[str] = None,
        external_apis: List[str] = None,
        data_sources: List[str] = None,
        implementation_notes: List[str] = None,
        edge_cases: List[str] = None,
        priority: str = "medium"
    ) -> str:
        """生成详细的 Skill 文件内容"""
        trigger_keywords = trigger_keywords or []
        required_dependencies = required_dependencies or []
        external_apis = external_apis or []
        data_sources = data_sources or []
        implementation_notes = implementation_notes or []
        edge_cases = edge_cases or []
        
        actions_section = ""
        if suggested_actions:
            for action in suggested_actions:
                if isinstance(action, dict):
                    action_name = action.get("name", "未命名操作")
                    action_desc = action.get("description", "描述待补充")
                    action_params = action.get("params", [])
                    action_examples = action.get("examples", [])
                    
                    params_str = "\n".join([f"  - {p}" for p in action_params]) if action_params else "  - 无参数"
                    examples_str = "\n".join([f"  - \"{ex}\" -> action={action_name}" for ex in action_examples]) if action_examples else "  - 示例待补充"
                    
                    actions_section += f"""### {action_name}

**描述**: {action_desc}

**参数**:
{params_str}

**示例**:
{examples_str}

"""
                else:
                    actions_section += f"""### {action}

**描述**: 待补充

**参数**:
  - param1: 参数说明

**示例**:
  - "示例请求" -> action={action}

"""
        else:
            actions_section = "待补充操作列表"

        dependencies_section = "\n".join([f"- {dep}" for dep in required_dependencies]) if required_dependencies else "- 待分析"
        apis_section = "\n".join([f"- {api}" for api in external_apis]) if external_apis else "- 无"
        data_sources_section = "\n".join([f"- {ds}" for ds in data_sources]) if data_sources else "- 无"
        notes_section = "\n".join([f"{i+1}. {note}" for i, note in enumerate(implementation_notes)]) if implementation_notes else "1. 待补充实现注意事项"
        edge_cases_section = "\n".join([f"- {ec}" for ec in edge_cases]) if edge_cases else "- 待补充边缘情况"
        keywords_section = ", ".join([f"`{kw}`" for kw in trigger_keywords]) if trigger_keywords else "待补充"
        
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
        
        return f"""---
name: {skill_name or agent_name}
agent: {agent_name}
description: {description}
version: "1.0.0"
priority: {priority}
tags: ["auto-generated", "missing-skill"]
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: pending
----

# {skill_name or agent_name}

## 📋 概述

**描述**: {description}

**优先级**: {priority_emoji} {priority.upper()}

{f"**详细说明**: {detailed_description}" if detailed_description else ""}

---

## 🎯 触发条件

当用户请求包含以下关键词时触发:

{keywords_section}

**原始用户请求**: "{user_request}"

---

## 🔧 支持的操作

{actions_section}

---

## 📦 依赖项

### Python 库
{dependencies_section}

### 外部 API
{apis_section}

### 数据源
{data_sources_section}

---

## ⚠️ 边缘情况

{edge_cases_section}

---

## 📝 实现注意事项

{notes_section}

---

## 🗂️ 文件结构

```
src/personal_agent/agents/
├── {agent_name}.py          # 智能体主文件
└── __init__.py              # (如需导出)

tests/
└── test_{agent_name}.py     # 测试文件
```

---

## ✅ 开发检查清单

- [ ] 创建 `{agent_name}.py` 文件
- [ ] 实现智能体类，继承自 `BaseAgent`
- [ ] 定义 `KEYWORD_MAPPINGS` 关键词映射
- [ ] 实现 `execute_task` 方法
- [ ] 添加错误处理和日志
- [ ] 编写单元测试
- [ ] 更新 master.py 的智能体注册（如需要）
- [ ] 测试验证功能
- [ ] 更新文档

---

## 📊 示例交互

| 用户输入 | 期望操作 | 期望响应 |
|---------|---------|---------|
| "{user_request}" | 执行对应操作 | 成功/失败提示 |
| (待补充) | (待补充) | (待补充) |

---

## 🔗 相关资源

- API 文档: (待补充)
- 设计文档: (待补充)
- 相关 Issue: (待补充)

---

## 📜 变更历史

| 日期 | 版本 | 变更内容 |
|-----|------|---------|
| {datetime.now().strftime("%Y-%m-%d")} | 1.0.0 | 初始版本，自动生成需求文档 |

---

*此文档由系统自动生成，需要开发者进一步完善和实现。*
"""

    async def _handle_general_task(self, content: str) -> str:
        """处理一般对话任务"""
        from ..config import settings
        import re
        
        # 如果 content 是字典且包含 answer 字段，检查是否是工具调用
        if isinstance(content, dict) and "answer" in content:
            answer = content["answer"]
            logger.info(f"💬 使用工具选择返回的答案: {answer}")
            
            # 检查是否是工具调用（格式：tool_name(param1="value1", param2="value2")）
            tool_call_pattern = r'(\w+)\((.*?)\)'
            match = re.match(tool_call_pattern, answer)
            
            logger.debug(f"🔍 正则匹配: {tool_call_pattern}")
            logger.debug(f"🔍 输入: {answer}")
            logger.debug(f"🔍 匹配结果: {match}")
            
            if match:
                tool_name = match.group(1)
                params_str = match.group(2)
                
                logger.debug(f"🔍 工具名称: {tool_name}")
                logger.debug(f"🔍 参数字符串: {params_str}")
                
                # 解析参数
                params = {}
                if params_str:
                    param_pattern = r'(\w+)="([^"]*)"'
                    logger.debug(f"🔍 参数正则: {param_pattern}")
                    
                    for param_match in re.finditer(param_pattern, params_str):
                        param_name = param_match.group(1)
                        param_value = param_match.group(2)
                        params[param_name] = param_value
                        logger.debug(f"🔍 解析参数: {param_name}={param_value}")
                
                logger.info(f"🔧 检测到工具调用: {tool_name}, 参数: {params}")
                
                # 从工具注册表获取对应的智能体
                from ..tools.agent_tools import get_tools_registry
                registry = get_tools_registry()
                tool = registry.get_tool(tool_name)
                
                if tool:
                    # 创建任务并分配给对应的智能体
                    agent_name = tool.agent_name
                    logger.info(f"📤 将工具调用路由到智能体: {agent_name}")
                    
                    try:
                        agent = await self._get_or_create_agent(agent_name)
                        if agent:
                            task = Task(
                                type=tool_name,
                                content=content.get("original_text", ""),
                                params=params
                            )
                            result = await agent.execute_task(task)
                            return str(result) if result else "✅ 任务完成"
                        else:
                            return f"❌ 无法找到智能体: {agent_name}"
                    except Exception as e:
                        logger.error(f"❌ 执行工具调用失败: {e}")
                        return f"❌ 执行工具调用失败: {str(e)}"
                else:
                    logger.warning(f"⚠️ 未找到工具: {tool_name}")
                    return f"⚠️ 未找到工具: {tool_name}"
            else:
                logger.warning(f"⚠️ 正则匹配失败，未检测到工具调用")
                logger.warning(f"⚠️ 返回原始答案: {answer}")
                return answer
        
        # 确保 content 是字符串
        if not isinstance(content, str):
            logger.warning(f"⚠️ content 不是字符串: {type(content)}")
            return str(content)
        
        content_lower = content.lower().strip()
        user_name = settings.user.name or "主人"
        agent_name = settings.agent.name or "智能助手"
        
        greetings = ["你好", "您好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好"]
        for g in greetings:
            if content_lower.startswith(g) or content_lower == g:
                return f"您好，{user_name}！我是{agent_name}，有什么可以帮您的吗？"
        
        thanks = ["谢谢", "感谢", "thanks", "thank you"]
        for t in thanks:
            if t in content_lower:
                return f"不客气，{user_name}！还有什么我可以帮您的吗？"
        
        bye = ["再见", "拜拜", "bye", "goodbye"]
        for b in bye:
            if b in content_lower:
                return f"再见，{user_name}！有需要随时找我。"
        
        help_keywords = ["帮助", "help", "你能做什么", "你会什么", "功能"]
        for h in help_keywords:
            if h in content_lower:
                return f"""我可以帮您做这些事情：

🎵 **音乐播放** - 播放音乐、暂停、切歌
🌤️ **天气预报** - 查询城市天气
📧 **邮件助手** - 发送和管理邮件
🔍 **网络搜索** - 搜索互联网信息
📁 **文件管理** - 文件操作和管理

试试说："播放周杰伦的歌" 或 "北京天气怎么样"？"""
        
        gap_keywords = ["缺少", "缺失", "什么智能体", "能力分析", "缺口", "建议添加"]
        for g in gap_keywords:
            if g in content_lower:
                return self._get_gap_analysis_report()
        
        return await self._call_llm_for_general(content)

    async def _wait_for_task_completion(self, task: Task, timeout: float = 30.0) -> str:
        """等待任务完成"""
        import asyncio
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if task.status == TaskStatus.COMPLETED:
                result = task.result
                if isinstance(result, dict):
                    if result.get("cannot_handle"):
                        missing_info = result.get('missing_info', {})
                        if missing_info:
                            inferred = await self._infer_missing_info(task, missing_info)
                            if inferred:
                                task.params.update(inferred)
                                agent_name = result.get('agent')
                                if agent_name:
                                    agent = await self._get_or_create_agent(agent_name)
                                    if agent:
                                        await agent.assign_task(task)
                                        continue
                        return await self._call_llm_for_general(task.content or task.type)
                    return result.get("message", str(result))
                return str(result) if result else "✅ 任务完成"
            elif task.status == TaskStatus.FAILED:
                return f"❌ 任务失败: {task.error}"
            await asyncio.sleep(0.1)
        
        return "⏳ 任务处理超时"

    async def _infer_missing_info(self, task: Task, missing_info: Dict) -> Optional[Dict]:
        """从上下文推断缺失的信息"""
        try:
            history_text = self._get_conversation_history(30)
            original_text = task.params.get("original_text", task.content)
            
            missing_desc = ", ".join([f"{k}({v})" for k, v in missing_info.items()])
            
            prompt = f"""根据用户的请求和历史对话，推断缺失的信息。

用户请求: {original_text}

历史对话（最近30条）:
{history_text if history_text else "无历史记录"}

需要推断的信息: {missing_desc}

请分析上下文，提取缺失的信息，返回 JSON 格式：
{{
    "字段名": "推断的值"
}}

如果无法从上下文推断某个字段，就不要包含该字段。
只返回 JSON，不要其他内容。"""

            from ..llm import LLMGateway
            from ..config import settings
            
            llm = LLMGateway(settings.llm)
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            import json
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            if result:
                logger.info(f"🔍 从上下文推断出: {result}")
            return result if result else None
        except Exception as e:
            logger.error(f"推断缺失信息失败: {e}")
            return None
    
    def _get_conversation_history(self, limit: int = 30) -> str:
        """获取历史聊天记录（从历史记录管理器）"""
        try:
            from ..memory.history_manager import history_manager
            return history_manager.get_history_text(limit)
        except Exception as e:
            logger.warning(f"获取历史记录失败: {e}")
            return ""

    async def _call_llm_for_general(self, content: str, context: Dict = None) -> str:
        """调用 LLM 处理一般对话"""
        try:
            from ..llm import LLMGateway
            from ..config import settings
            
            llm = LLMGateway(settings.llm)
            user_name = settings.user.name or "主人"
            agent_name = settings.agent.name or "智能助手"
            
            confirm_keywords = ["好的", "可以", "行", "是的", "确认", "确定", "好", "OK", "ok", "Ok"]
            is_confirmation = content.strip() in confirm_keywords
            
            if is_confirmation and self._pending_action:
                pending = self._pending_action
                self._pending_action = None
                logger.info(f"✅ 用户确认执行待处理操作: {pending}")
                
                action = pending.get("action", "")
                params = pending.get("params", {})
                params["original_text"] = content
                
                if action == "add_contact":
                    task = Task(
                        type="add",
                        content=content,
                        params=params,
                        priority=5
                    )
                    agent = await self._get_or_create_agent("contact_agent")
                    if agent:
                        await agent.assign_task(task)
                        return await self._wait_for_task_completion(task)
                elif action == "general":
                    return await self._execute_pending_action(pending, content)
            
            history_text = self._get_conversation_history(20)
            
            chat_context = context.get("chat_context") if context else None
            if chat_context:
                context_text = "\n".join([
                    f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content'][:500]}"
                    for msg in chat_context[-10:]
                ])
                if context_text:
                    history_text = context_text if not history_text else f"{history_text}\n\n{context_text}"
            
            now = datetime.now()
            current_date = now.strftime("%Y年%m月%d日")
            current_time = now.strftime("%H:%M")
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekday = weekday_names[now.weekday()]
            
            system_prompt = f"""你是{agent_name}，是一个友好的智能助手。用户昵称是{user_name}。

当前时间信息：
- 日期：{current_date}（{weekday}）
- 时间：{current_time}

重要规则：
1. 如果用户问关于个人信息（如家人名字、电话、地址等），请从历史对话记录中查找答案
2. 如果历史记录中有相关信息，直接回答用户
3. 如果历史记录中没有相关信息，告诉用户你还没有记录这个信息，并提示用户可以告诉你
4. 如果用户的问题涉及到需要执行的操作（如添加联系人、发送邮件等），但你缺少参数，先询问用户
5. 如果你能确定所有参数，在回复末尾添加 JSON 标记：<!-- ACTION: {{"action": "操作名", "params": {{参数}}}} -->
6. 操作类型包括：add_contact, send_email, set_reminder 等
7. 对于 add_contact，params 包括：name（姓名）, relationship（关系）, phone, email 等
8. 解析时间时，请使用当前日期 {current_date} 作为基准

最近对话（请从中查找用户提到的个人信息）：
{history_text if history_text else "无历史记录"}
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            response = await llm.chat(messages)
            response_content = response.content.strip()
            
            if response.usage:
                prompt_tokens = response.usage.get("prompt_tokens", 0)
                completion_tokens = response.usage.get("completion_tokens", 0)
                total_tokens = response.usage.get("total_tokens", 0)
                logger.info(f"📊 Token 统计: 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
                try:
                    from ..utils.token_counter import update_token_count
                    update_token_count(total_tokens)
                except Exception:
                    pass
            
            if "<!-- ACTION:" in response_content:
                import re
                match = re.search(r'<!-- ACTION: (\{.*?\}) -->', response_content)
                if match:
                    try:
                        import json
                        action_data = json.loads(match.group(1))
                        self._pending_action = action_data
                        response_content = re.sub(r'<!-- ACTION: \{.*?\} -->', '', response_content).strip()
                        logger.info(f"📌 保存待确认操作: {action_data}")
                    except:
                        pass
            
            return response_content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"我收到了你的消息：{content}\n\n目前我可以帮你播放音乐、查询天气、发送邮件等，试试看吧！"
    
    async def _execute_pending_action(self, pending: Dict, content: str) -> str:
        """执行待处理的操作"""
        action = pending.get("action", "")
        params = pending.get("params", {})
        
        if action == "add_contact":
            task = Task(
                type="add",
                content=content,
                params=params,
                priority=5
            )
            agent = await self._get_or_create_agent("contact_agent")
            if agent:
                await agent.assign_task(task)
                return await self._wait_for_task_completion(task)
        
        return "✅ 操作已完成"

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            "master": self.get_status(),
            "agents": {
                name: agent.get_status()
                for name, agent in self.sub_agents.items()
            },
            "active_tasks": len(self.task_agent_map),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_gap_analysis_report(self) -> str:
        """获取智能体缺口分析报告"""
        try:
            from .gap_analyzer import get_gap_analyzer
            analyzer = get_gap_analyzer()
            return analyzer.get_missing_agents_report()
        except Exception as e:
            logger.warning(f"获取缺口分析报告失败: {e}")
            return "📊 暂时无法获取缺口分析报告，请稍后再试。"
    
    def get_gap_analysis(self) -> Dict:
        """获取详细的缺口分析数据"""
        try:
            from .gap_analyzer import get_gap_analyzer
            analyzer = get_gap_analyzer()
            return analyzer.analyze_patterns(days=30)
        except Exception as e:
            logger.warning(f"获取缺口分析失败: {e}")
            return {"error": str(e)}
    
    def get_skills_prompt(self) -> str:
        """获取 Skills 提示（用于 LLM 上下文）"""
        if self.skill_manager:
            from ..skills import DisclosureLevel
            return self.skill_manager.get_skills_prompt(DisclosureLevel.CARD)
        return ""
    
    def get_all_skill_cards(self) -> List[Dict[str, str]]:
        """获取所有 Skill 卡片"""
        if self.skill_manager:
            return self.skill_manager.get_all_skill_cards()
        return []
    
    async def create_skill_from_request(self, request: str) -> Dict[str, Any]:
        """根据用户请求自动创建 Skill"""
        if not self.skill_manager:
            return {"success": False, "error": "Skill 管理器未初始化"}
        
        try:
            from ..llm import LLMGateway
            from ..config import settings
            
            llm = LLMGateway(settings.llm)
            
            prompt = f"""根据用户请求，生成一个 Skill 定义。

用户请求: {request}

请生成一个符合以下格式的 SKILL.md 内容：

---
name: skill_name
description: 简短描述
version: "1.0.0"
tags: ["tag1", "tag2"]
---

## Description

详细描述这个技能的功能

## When to use

- 触发场景1
- 触发场景2

## How to use

1. 步骤1
2. 步骤2

## Edge cases

- 边缘情况1
- 边缘情况2

只返回 SKILL.md 内容，不要其他说明。"""

            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            skill_content = response.content.strip()
            
            skill = self.skill_manager.skill_parser.parse_content(skill_content)
            if skill and skill.metadata.name != "unknown":
                skill_dir = Path("./skills") / skill.metadata.name
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(skill_content, encoding='utf-8')
                
                self.skill_manager.skills[skill.metadata.name] = skill
                logger.info(f"✅ AI 创建 Skill: {skill.metadata.name}")
                
                return {
                    "success": True,
                    "skill_name": skill.metadata.name,
                    "description": skill.metadata.description,
                    "path": str(skill_dir / "SKILL.md")
                }
            else:
                return {"success": False, "error": "解析 Skill 内容失败"}
                
        except Exception as e:
            logger.error(f"创建 Skill 失败: {e}")
            return {"success": False, "error": str(e)}
