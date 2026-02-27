"""
Multi-Agent System - 多智能体系统管理器
负责初始化和协调所有智能体
支持子智能体懒加载
"""
import asyncio
import threading
from typing import Optional, Dict, Any
from loguru import logger

from .agents import MasterAgent
from .agents.base import Task
from .channels import IncomingMessage, OutgoingMessage
from .task_manager import task_manager, TaskState
from .tts import get_tts_manager


_global_loop: Optional[asyncio.AbstractEventLoop] = None
_global_lock = asyncio.Lock()
_loop_thread: Optional[threading.Thread] = None


def get_global_loop() -> asyncio.AbstractEventLoop:
    """获取或创建全局事件循环"""
    global _global_loop, _loop_thread
    
    if _global_loop is None or _global_loop.is_closed():
        _global_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_global_loop)
        
        ready_event = threading.Event()
        
        def run_loop():
            asyncio.set_event_loop(_global_loop)
            ready_event.set()
            _global_loop.run_forever()
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
        
        ready_event.wait(timeout=5)
    
    return _global_loop


class MultiAgentSystem:
    """
    多智能体系统

    管理所有智能体的生命周期和协作
    子智能体采用懒加载模式，按需创建
    """

    def __init__(self):
        self.master: Optional[MasterAgent] = None
        self._initialized = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._auto_speak_callback = None
        self._progress_callback = None
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self._progress_callback = callback
    
    def _report_progress(self, message: str, progress: float = None):
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(message, progress)

    async def initialize(self):
        """初始化多智能体系统（仅初始化主智能体）"""
        if self._initialized:
            return

        self._report_progress("🚀 启动中...", 0.1)

        self.loop = asyncio.get_running_loop()
        
        self._preload_metadata()

        self.master = MasterAgent()
        self.master.multi_agent = self
        await self.master.start()
        
        await task_manager.start()
        task_manager.set_limits(max_per_agent=2, max_total=8)
        
        await self._setup_email_monitor()
        await self._setup_os_agent()
        await self._setup_web_server_agent()
        await self._load_session()

        self._initialized = True
        self._report_progress("✅ 启动完成！", 1.0)
    
    async def _load_session(self):
        """加载会话数据"""
        try:
            from .session_manager import simple_session_manager
            messages = simple_session_manager.get_messages(limit=5)
        except Exception as e:
            pass
    
    def _preload_metadata(self):
        """预加载智能体元数据和关键词映射（不创建实例）"""
        from .agents.agent_scanner import get_agent_scanner
        from .intent.intent_parser import IntentParser
        
        scanner = get_agent_scanner()
        scanner.scan_agents(use_cache=False)
        
        parser = IntentParser()
        parser._collect_keyword_mappings(force_reload=True)
    
    async def _setup_email_monitor(self):
        """设置邮件监控"""
        try:
            from .email_monitor import email_monitor
            from .agents.email_agent import EmailAgent
            
            email_agent = EmailAgent()
            await email_agent.start()
            self.master.register_sub_agent(email_agent)
            
            email_monitor.set_agents(self.master, email_agent)
            await email_monitor.start()
            
        except Exception as e:
            logger.warning(f"邮件监控配置失败: {e}")

    async def _setup_os_agent(self):
        """设置操作系统智能体"""
        try:
            from .agents.os_agent import OSAgent
            
            os_agent = OSAgent()
            await os_agent.start()
            self.master.register_sub_agent(os_agent)
            
        except Exception as e:
            logger.warning(f"操作系统智能体配置失败: {e}")

    async def _setup_web_server_agent(self):
        """设置Web服务器智能体"""
        try:
            from .agents.web_server_agent import WebServerAgent
            
            web_server_agent = WebServerAgent()
            await web_server_agent.start()
            
            async def handle_web_message(message: str, metadata: dict) -> str:
                """处理来自Web的消息，转发给Master Agent"""
                return await self.master.process_user_request(message, context=metadata)
            
            web_server_agent.set_message_handler(handle_web_message)
            self.master.register_sub_agent(web_server_agent)
            
        except Exception as e:
            logger.warning(f"Web服务器智能体配置失败: {e}")

    async def shutdown(self):
        """关闭多智能体系统"""
        logger.info("🛑 关闭多智能体系统...")
        
        try:
            from .session_manager import simple_session_manager
            simple_session_manager.save_session()
            logger.info("💾 会话已保存")
        except Exception as e:
            logger.warning(f"保存会话失败: {e}")
        
        try:
            from .email_monitor import email_monitor
            await email_monitor.stop()
        except Exception as e:
            logger.warning(f"停止邮件监控失败: {e}")
        
        try:
            await task_manager.stop()
        except Exception as e:
            logger.warning(f"停止任务管理器失败: {e}")

        if self.master:
            for agent_name, agent in list(self.master.sub_agents.items()):
                try:
                    agent._running = False
                    if agent._task_processor and not agent._task_processor.done():
                        agent._task_processor.cancel()
                    agent.status = "offline"
                    logger.info(f"🛑 已停止智能体: {agent_name}")
                except Exception as e:
                    logger.warning(f"停止智能体 {agent_name} 时出现问题（已忽略）: {e}")
            
            try:
                self.master._running = False
                if self.master._task_processor and not self.master._task_processor.done():
                    self.master._task_processor.cancel()
                self.master.status = "offline"
            except Exception as e:
                logger.warning(f"停止主智能体时出现问题（已忽略）: {e}")

        self._initialized = False
        logger.info("✅ 多智能体系统已关闭")

    async def process_message(self, incoming: IncomingMessage) -> OutgoingMessage:
        """
        处理用户消息

        通过主智能体进行任务分配和处理
        """
        if not self._initialized:
            await self.initialize()

        try:
            from .session_manager import simple_session_manager
            
            simple_session_manager.add_message("user", incoming.content, incoming.metadata)

            files = []
            if incoming.metadata and "files" in incoming.metadata:
                files = incoming.metadata["files"]
            
            tool_name = incoming.metadata.get("tool_name") if incoming.metadata else None
            tool_args = incoming.metadata.get("tool_args") if incoming.metadata else None
            direct_params = incoming.metadata.get("direct_params") if incoming.metadata else None
            chat_context = incoming.metadata.get("context") if incoming.metadata else None

            timeout_sent = False
            
            async def check_timeout():
                nonlocal timeout_sent
                await asyncio.sleep(1.0)
                if not timeout_sent:
                    timeout_sent = True
                    logger.info(f"⏳ 处理时间超过1秒，发送提示消息")
                    simple_session_manager.add_message("system", "⏳ 正在处理中，请稍候...")
                    if hasattr(self.master, '_send_temp_message'):
                        self.master._send_temp_message("⏳ 正在处理中，请稍候...")

            timeout_task = asyncio.create_task(check_timeout())

            response_content = await self.master.process_user_request(
                request=incoming.content,
                context={
                    "sender_id": incoming.sender_id,
                    "message_type": incoming.message_type.value,
                    "files": files,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "direct_params": direct_params,
                    "chat_context": chat_context
                }
            )

            timeout_sent = True
            if not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass

            if isinstance(response_content, OutgoingMessage):
                response_content.receiver_id = incoming.sender_id
                simple_session_manager.add_message("assistant", response_content.content)
                
                skip_auto_speak = response_content.metadata and response_content.metadata.get("skip_auto_speak", False)
                if not skip_auto_speak:
                    self._speak_response(response_content.content)
                
                return response_content

            agent_names = None
            if hasattr(self.master, '_last_agent_names'):
                agent_names = self.master._last_agent_names

            simple_session_manager.add_message("assistant", response_content)

            skip_auto_speak = incoming.metadata and incoming.metadata.get("skip_auto_speak", False)
            if not skip_auto_speak:
                self._speak_response(response_content)
            
            return OutgoingMessage(
                content=response_content,
                receiver_id=incoming.sender_id,
                message_type=incoming.message_type,
                metadata={"agent_names": agent_names} if agent_names else None
            )

        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
            from .session_manager import simple_session_manager
            simple_session_manager.add_message("system", f"错误: {str(e)}")
            return OutgoingMessage(
                content=f"处理消息时出现错误：{str(e)}",
                receiver_id=incoming.sender_id,
                message_type=incoming.message_type
            )

    def _speak_response(self, text: str):
        """异步语音合成响应（仅 master 响应）"""
        import time
        start_time = time.time()
        
        if not text or not isinstance(text, str):
            return
        
        import re
        clean_text = re.sub(r'[📍🔑📱🌐✅❌📋🎯📎📝🔊]', '', text)
        clean_text = re.sub(r'https?://\S+', '', clean_text)
        clean_text = clean_text.strip()
        
        if not clean_text or len(clean_text) < 2:
            return
        
        logger.info(f"🔊 开始语音合成，文本长度: {len(clean_text)} 字符")
        
        if self._auto_speak_callback:
            try:
                self._auto_speak_callback(text)
                logger.info(f"🔊 语音合成回调完成，耗时: {time.time() - start_time:.2f}秒")
                return
            except Exception as e:
                logger.debug(f"自动播放回调失败: {e}")
        
        try:
            tts = get_tts_manager()
            if tts.is_enabled():
                import threading
                
                def _speak_in_thread():
                    synth_start = time.time()
                    try:
                        tts.speak_sync(clean_text)
                        logger.info(f"🔊 语音合成播放完成，总耗时: {time.time() - start_time:.2f}秒，合成耗时: {time.time() - synth_start:.2f}秒")
                    except Exception as e:
                        logger.debug(f"语音播放失败: {e}")
                
                thread = threading.Thread(target=_speak_in_thread, daemon=True)
                thread.start()
        except Exception as e:
            logger.debug(f"语音合成失败: {e}")
    
    def set_auto_speak_callback(self, callback):
        """设置自动播放回调"""
        self._auto_speak_callback = callback

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        if not self.master:
            return {"status": "not_initialized"}

        return self.master.get_system_status()
    
    def reload_agents(self) -> Dict[str, Any]:
        """热更新智能体元数据和关键词映射"""
        from .agents.agent_scanner import get_agent_scanner, refresh_agents
        from .intent.intent_parser import IntentParser
        
        scanner = get_agent_scanner()
        agents = scanner.refresh()
        
        parser = IntentParser()
        parser._collect_keyword_mappings(force_reload=True)
        
        if self.master and hasattr(self.master, '_intent_parser'):
            self.master._intent_parser._collect_keyword_mappings(force_reload=True)
        
        if self.master and hasattr(self.master, 'sub_agents'):
            for agent_name, agent in self.master.sub_agents.items():
                if hasattr(agent, 'reload_config'):
                    try:
                        agent.reload_config()
                        logger.info(f"🔄 智能体 {agent_name} 配置已重载")
                    except Exception as e:
                        logger.warning(f"重载智能体 {agent_name} 配置失败: {e}")
        
        logger.info(f"🔄 智能体热更新完成，共 {len(agents)} 个智能体")
        return {
            "status": "success",
            "agents_count": len(agents),
            "agents": list(agents.keys())
        }

    async def direct_command(self, agent_name: str, command: str, params: Dict = None) -> str:
        """
        直接向某个智能体发送命令

        Args:
            agent_name: 智能体名称
            command: 命令类型
            params: 命令参数

        Returns:
            执行结果
        """
        agent_map = {
            "music": self.music_agent,
            "email": self.email_agent,
            "file": self.file_agent,
            "crawler": self.crawler_agent
        }

        agent = agent_map.get(agent_name)
        if not agent:
            return f"❌ 智能体 '{agent_name}' 不存在"

        # 创建任务
        task = Task(
            type=command,
            content=f"直接命令: {command}",
            params=params or {}
        )

        # 分配任务
        success = await agent.assign_task(task)
        if not success:
            return f"❌ 智能体 '{agent_name}' 忙碌中"

        # 等待任务完成
        from .agents.base import TaskStatus
        logger.info(f"⏳ 等待任务完成，当前状态: {task.status}")
        max_wait = 300  # 最多等待30秒
        wait_count = 0
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            await asyncio.sleep(0.1)
            wait_count += 1
            if wait_count % 10 == 0:
                logger.info(f"⏳ 等待中... 当前状态: {task.status}")
            if wait_count > max_wait:
                logger.error("⏳ 等待任务超时")
                return "❌ 等待任务超时"

        logger.info(f"✅ 任务完成，状态: {task.status}, 结果: {task.result}")

        if task.status == TaskStatus.COMPLETED:
            return str(task.result) if task.result else "✅ 命令执行成功"
        else:
            return f"❌ 命令执行失败: {task.error}"


def shutdown_global_loop():
    """关闭全局事件循环"""
    global _global_loop, _loop_thread
    
    if _global_loop and not _global_loop.is_closed():
        _global_loop.call_soon_threadsafe(_global_loop.stop)
        if _loop_thread:
            _loop_thread.join(timeout=2)
        _global_loop.close()
        _global_loop = None
        _loop_thread = None
        logger.info("✅ 全局事件循环已关闭")


# 全局多智能体系统实例
multi_agent_system = MultiAgentSystem()
