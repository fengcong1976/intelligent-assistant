"""
QQ机器人智能体 - 提供QQ消息通信渠道
类似于Web服务器智能体，只负责消息的收发，不处理业务逻辑
业务逻辑由 Master Agent 进行意图解析和任务分配
"""
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, List
from loguru import logger

from ..base import BaseAgent, Task


class QQBotAgent(BaseAgent):
    """
    QQ机器人智能体 - 纯通信渠道
    
    职责：
    1. 启动/停止 QQ 机器人
    2. 接收来自 QQ 的消息，转发给 Master Agent
    3. 将 Master Agent 的处理结果返回给 QQ 用户
    
    不负责：
    - 意图解析（由 Master Agent 处理）
    - 业务逻辑执行（由其他子智能体处理）
    """
    
    PRIORITY = 99
    
    KEYWORD_MAPPINGS = {
        "启动qq机器人": ("start", {}),
        "开启qq机器人": ("start", {}),
        "停止qq机器人": ("stop", {}),
        "关闭qq机器人": ("stop", {}),
        "qq机器人状态": ("status", {}),
        "qq状态": ("status", {}),
    }

    def __init__(self):
        super().__init__(
            name="qq_bot_agent",
            description="QQ机器人智能体 - 提供QQ消息通信渠道，支持群聊、私聊、频道等场景"
        )

        self.register_capability("qq_bot", "QQ机器人功能")
        self.register_capability("qq_message", "QQ消息处理")
        self.register_capability("qq_group", "QQ群聊功能")
        self.register_capability("qq_channel", "QQ频道功能")

        self.bot_running = False
        self._bot_client = None
        self._bot_thread = None
        self._message_handler: Optional[Callable] = None
        self._pending_replies: Dict[str, asyncio.Queue] = {}
        
        self._appid: str = ""
        self._secret: str = ""
        self._intents = None
        
        self._conversations: Dict[str, Dict] = {}

        logger.info("🤖 QQ机器人智能体已初始化")

    def set_message_handler(self, handler: Callable):
        """
        设置消息处理器（由 Master Agent 提供）
        
        Args:
            handler: 异步函数，接收消息内容，返回处理结果
                     签名: async def handler(message: str, metadata: dict) -> str
        """
        self._message_handler = handler
        logger.info("✅ QQBotAgent 消息处理器已设置")

    def configure(self, appid: str, secret: str, intents: List[str] = None):
        """
        配置QQ机器人凭证
        
        Args:
            appid: 机器人AppID
            secret: 机器人AppSecret
            intents: 订阅的事件类型列表
        """
        self._appid = appid
        self._secret = secret
        
        if intents:
            self._intents = self._build_intents(intents)
        
        logger.info(f"🔧 QQ机器人配置已更新: AppID={appid[:8]}...")

    def _build_intents(self, intent_names: List[str]) -> Any:
        """
        构建事件订阅 intents
        
        Args:
            intent_names: 事件名称列表，如 ['public_guild_messages', 'group_and_c2c']
        """
        try:
            import botpy
            
            intents = botpy.Intents.none()
            
            intent_mapping = {
                'guilds': botpy.Intents.guilds,
                'guild_members': botpy.Intents.guild_members,
                'guild_messages': botpy.Intents.guild_messages,
                'guild_message_reactions': botpy.Intents.guild_message_reactions,
                'direct_message': botpy.Intents.direct_message,
                'group_and_c2c': botpy.Intents.group_and_c2c,
                'interaction': botpy.Intents.interaction,
                'message_audit': botpy.Intents.message_audit,
                'forums_event': botpy.Intents.forums_event,
                'audio_action': botpy.Intents.audio_action,
                'public_guild_messages': botpy.Intents.public_guild_messages,
            }
            
            for name in intent_names:
                if name in intent_mapping:
                    setattr(intents, name, True)
                    logger.info(f"  ✅ 订阅事件: {name}")
            
            return intents
        except ImportError:
            logger.warning("⚠️ botpy 未安装，请运行: pip install qq-botpy")
            return None

    async def execute_task(self, task: Task) -> Any:
        """执行任务 - 只处理机器人管理相关任务"""
        task_type = task.type
        params = task.params or {}

        if task_type == "start_qq_bot":
            return await self._start_bot(params)
        elif task_type == "stop_qq_bot":
            return await self._stop_bot()
        elif task_type == "get_qq_status":
            return await self._get_status()
        elif task_type == "send_qq_message":
            return await self._send_message(params)
        elif task_type == "configure_qq_bot":
            return self._configure_bot(params)
        else:
            return {"success": False, "message": f"未知任务类型: {task_type}"}

    def _configure_bot(self, params: Dict) -> Dict[str, Any]:
        """配置机器人"""
        appid = params.get("appid", "")
        secret = params.get("secret", "")
        intents = params.get("intents", ["public_guild_messages", "group_and_c2c"])
        
        if not appid or not secret:
            return {"success": False, "message": "缺少 AppID 或 Secret"}
        
        self.configure(appid, secret, intents)
        return {"success": True, "message": "QQ机器人配置已更新"}

    async def _start_bot(self, params: Dict = None) -> Dict[str, Any]:
        """启动QQ机器人"""
        if self.bot_running:
            return {"success": True, "message": "QQ机器人已在运行中", "status": "running"}
        
        params = params or {}
        
        if params.get("appid"):
            self.configure(
                params.get("appid"),
                params.get("secret"),
                params.get("intents", ["public_guild_messages", "group_and_c2c"])
            )
        
        if not self._appid or not self._secret:
            return {
                "success": False, 
                "message": "请先配置 QQ 机器人凭证（AppID 和 Secret）\n"
                          "1. 访问 https://bot.q.qq.com 注册机器人\n"
                          "2. 获取 AppID 和 AppSecret\n"
                          "3. 在配置文件中设置 qq_bot.appid 和 qq_bot.secret"
            }
        
        try:
            import botpy
            from botpy.message import Message, GroupMessage, DirectMessage, C2CMessage
            
            agent_self = self
            
            class PersonalBotClient(botpy.Client):
                """自定义机器人客户端"""
                
                async def on_ready(self):
                    logger.info(f"🤖 QQ机器人已就绪: {self.robot.name}")
                    agent_self.bot_running = True
                
                async def on_at_message_create(self, message: Message):
                    await agent_self._handle_channel_message(message)
                
                async def on_group_at_message_create(self, message: GroupMessage):
                    await agent_self._handle_group_message(message)
                
                async def on_c2c_message_create(self, message: C2CMessage):
                    await agent_self._handle_c2c_message(message)
                
                async def on_direct_message_create(self, message: DirectMessage):
                    await agent_self._handle_direct_message(message)
            
            intents = self._intents or botpy.Intents(
                public_guild_messages=True,
                group_and_c2c=True
            )
            
            self._bot_client = PersonalBotClient(intents=intents)
            
            def run_bot():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self._bot_client.run(appid=self._appid, secret=self._secret)
                    )
                except Exception as e:
                    logger.error(f"QQ机器人运行错误: {e}")
                    agent_self.bot_running = False
            
            self._bot_thread = threading.Thread(target=run_bot, daemon=True)
            self._bot_thread.start()
            
            await asyncio.sleep(2)
            
            if self.bot_running:
                return {
                    "success": True, 
                    "message": f"✅ QQ机器人已启动\n"
                              f"机器人名称: {self._bot_client.robot.name if hasattr(self._bot_client, 'robot') else '未知'}\n"
                              f"支持: 群聊@消息、私聊消息、频道消息"
                }
            else:
                return {"success": False, "message": "QQ机器人启动失败，请检查配置"}
                
        except ImportError:
            return {
                "success": False, 
                "message": "请先安装 QQ 机器人 SDK:\npip install qq-botpy"
            }
        except Exception as e:
            logger.error(f"启动QQ机器人失败: {e}")
            return {"success": False, "message": f"启动失败: {e}"}

    async def _stop_bot(self) -> Dict[str, Any]:
        """停止QQ机器人"""
        if not self.bot_running:
            return {"success": True, "message": "QQ机器人未在运行", "status": "stopped"}
        
        try:
            if self._bot_client:
                self._bot_client.close()
            
            self.bot_running = False
            self._bot_client = None
            
            logger.info("🛑 QQ机器人已停止")
            return {"success": True, "message": "✅ QQ机器人已停止"}
            
        except Exception as e:
            logger.error(f"停止QQ机器人失败: {e}")
            return {"success": False, "message": f"停止失败: {e}"}

    async def _get_status(self) -> Dict[str, Any]:
        """获取QQ机器人状态"""
        status = {
            "running": self.bot_running,
            "appid": self._appid[:8] + "..." if self._appid else "未配置",
            "configured": bool(self._appid and self._secret),
        }
        
        if self._bot_client and hasattr(self._bot_client, 'robot'):
            status["robot_name"] = self._bot_client.robot.name
            status["robot_id"] = self._bot_client.robot.id
        
        return {
            "success": True,
            "status": status,
            "message": f"QQ机器人状态: {'运行中' if self.bot_running else '已停止'}"
        }

    async def _handle_channel_message(self, message):
        """处理频道@消息"""
        try:
            content = message.content.strip()
            user_id = message.author.id
            channel_id = message.channel_id
            guild_id = message.guild_id
            
            logger.info(f"📺 频道消息 [{guild_id}/{channel_id}] 用户{user_id}: {content}")
            
            metadata = {
                "source": "qq_channel",
                "user_id": user_id,
                "channel_id": channel_id,
                "guild_id": guild_id,
                "message_id": message.id,
            }
            
            response = await self._process_message(content, metadata)
            
            if response:
                await message.reply(content=response)
                
        except Exception as e:
            logger.error(f"处理频道消息失败: {e}")

    async def _handle_group_message(self, message):
        """处理群聊@消息"""
        try:
            content = message.content.strip()
            user_id = message.author.id
            group_id = message.group_id
            
            logger.info(f"👥 群聊消息 [{group_id}] 用户{user_id}: {content}")
            
            metadata = {
                "source": "qq_group",
                "user_id": user_id,
                "group_id": group_id,
                "message_id": message.id,
            }
            
            response = await self._process_message(content, metadata)
            
            if response:
                await message.reply(content=response)
                
        except Exception as e:
            logger.error(f"处理群聊消息失败: {e}")

    async def _handle_c2c_message(self, message):
        """处理私聊消息"""
        try:
            content = message.content.strip()
            user_id = message.author.id
            
            logger.info(f"💬 私聊消息 用户{user_id}: {content}")
            
            metadata = {
                "source": "qq_c2c",
                "user_id": user_id,
                "message_id": message.id,
            }
            
            response = await self._process_message(content, metadata)
            
            if response:
                await self.api.post_c2c_messages(openid=user_id, content=response)
                
        except Exception as e:
            logger.error(f"处理私聊消息失败: {e}")

    async def _handle_direct_message(self, message):
        """处理频道私信消息"""
        try:
            content = message.content.strip()
            user_id = message.author.id
            guild_id = message.guild_id
            
            logger.info(f"✉️ 频道私信 [{guild_id}] 用户{user_id}: {content}")
            
            metadata = {
                "source": "qq_direct",
                "user_id": user_id,
                "guild_id": guild_id,
                "message_id": message.id,
            }
            
            response = await self._process_message(content, metadata)
            
            if response:
                await self.api.post_dms_messages(
                    guild_id=guild_id,
                    content=response
                )
                
        except Exception as e:
            logger.error(f"处理频道私信失败: {e}")

    async def _process_message(self, content: str, metadata: dict) -> Optional[str]:
        """
        处理消息 - 转发给 Master Agent
        
        Args:
            content: 消息内容
            metadata: 消息元数据
            
        Returns:
            处理结果，用于回复用户
        """
        if not content:
            return None
        
        if self._message_handler:
            try:
                response = await self._message_handler(content, metadata)
                return response
            except Exception as e:
                logger.error(f"消息处理器执行失败: {e}")
                return "抱歉，处理您的消息时出现错误。"
        else:
            logger.warning("⚠️ 未设置消息处理器，消息将被忽略")
            return "机器人正在初始化中，请稍后再试。"

    async def _send_message(self, params: Dict) -> Dict[str, Any]:
        """
        主动发送消息
        
        Args:
            params: 包含 target_type, target_id, content 的参数
        """
        if not self.bot_running or not self._bot_client:
            return {"success": False, "message": "QQ机器人未运行"}
        
        target_type = params.get("target_type")
        target_id = params.get("target_id")
        content = params.get("content", "")
        
        if not content:
            return {"success": False, "message": "消息内容不能为空"}
        
        try:
            if target_type == "c2c":
                await self._bot_client.api.post_c2c_messages(openid=target_id, content=content)
            elif target_type == "group":
                await self._bot_client.api.post_group_messages(group_openid=target_id, content=content)
            elif target_type == "channel":
                channel_id = params.get("channel_id")
                await self._bot_client.api.post_message(channel_id=channel_id, content=content)
            else:
                return {"success": False, "message": f"不支持的目标类型: {target_type}"}
            
            return {"success": True, "message": "消息发送成功"}
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return {"success": False, "message": f"发送失败: {e}"}

    async def start(self):
        """启动智能体"""
        await super().start()
        logger.info("🤖 QQ机器人智能体已启动")

    async def stop(self):
        """停止智能体"""
        await self._stop_bot()
        await super().stop()
        logger.info("🤖 QQ机器人智能体已停止")
