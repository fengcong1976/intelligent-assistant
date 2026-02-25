"""
Base Agent - 所有智能体的基类
"""
import asyncio
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from loguru import logger


class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"           # 空闲
    BUSY = "busy"           # 忙碌
    ERROR = "error"         # 错误
    OFFLINE = "offline"     # 离线


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"     # 待处理
    RUNNING = "running"     # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败
    CANCELLED = "cancelled" # 已取消
    NEEDS_CONFIRMATION = "needs_confirmation"  # 需要用户确认


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class Task:
    """任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""                          # 任务类型
    content: str = ""                       # 任务内容
    params: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5                       # 优先级 1-10
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    assigned_to: Optional[str] = None     # 分配给哪个智能体
    created_by: Optional[str] = None      # 由谁创建
    depends_on: List[str] = field(default_factory=list)
    no_retry: bool = False                # 是否禁止重试（由智能体决定）


@dataclass
class Message:
    """智能体间消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""                    # 发送者
    to_agent: str = ""                      # 接收者
    type: str = ""                          # 消息类型
    content: str = ""                       # 消息内容
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False         # 是否需要回复


class BaseAgent:
    """
    智能体基类

    所有专业智能体都继承此类
    """
    
    KEYWORD_MAPPINGS: Dict[str, tuple] = {}
    PRIORITY: int = 5

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.capabilities: List[str] = []       # 能力名称列表
        self.capability_details: Dict[str, Dict] = {}  # 能力详细信息
        self.tasks: Dict[str, Task] = {}        # 任务队列
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: List[Callable] = []
        self._running = False
        self._task_processor: Optional[asyncio.Task] = None
        
        self.supported_open_formats: List[str] = []
        self.supported_edit_formats: List[str] = []
        
        self.skill: Optional[Dict[str, Any]] = None
        self._load_builtin_skill()
    
    @classmethod
    def get_keyword_mappings(cls) -> Dict[str, tuple]:
        """获取关键词映射"""
        return cls.KEYWORD_MAPPINGS
    
    @classmethod
    def get_priority(cls) -> int:
        """获取智能体优先级（数字越小优先级越高）"""
        return cls.PRIORITY
    
    def _load_builtin_skill(self):
        """加载智能体内置的 SKILL.md"""
        try:
            agent_file = Path(__file__).parent / f"{self.name}.py"
            if not agent_file.exists():
                agent_file = Path(__file__).parent / f"{self.name.replace('_agent', '')}_agent.py"
            
            if agent_file.exists():
                skill_file = agent_file.parent / self.name / "SKILL.md"
                if not skill_file.exists():
                    skill_file = agent_file.parent / f"{self.name}.md"
                if not skill_file.exists():
                    skill_file = agent_file.with_suffix(".md")
                
                if skill_file.exists():
                    from ..skills.skill_manager import SkillParser
                    parser = SkillParser()
                    skill_def = parser.parse_file(skill_file)
                    if skill_def:
                        self.skill = {
                            "name": skill_def.metadata.name,
                            "description": skill_def.metadata.description,
                            "help": skill_def.help,
                            "when_to_use": skill_def.when_to_use,
                            "how_to_use": skill_def.how_to_use,
                            "edge_cases": skill_def.edge_cases
                        }
        except Exception as e:
            logger.debug(f"'{self.name}' 无内置 Skill: {e}")
    
    def get_skill_prompt(self) -> str:
        """获取 Skill 提示（用于 LLM 上下文）"""
        if not self.skill:
            return ""
        
        lines = [f"## {self.skill['name']}", f"描述: {self.skill['description']}"]
        
        if self.skill.get('when_to_use'):
            lines.append("\n### 适用场景")
            for item in self.skill['when_to_use']:
                lines.append(f"- {item}")
        
        if self.skill.get('how_to_use'):
            lines.append("\n### 使用方法")
            for item in self.skill['how_to_use']:
                lines.append(f"- {item}")
        
        return "\n".join(lines)

    def register_capability(self, capability: str, description: str, parameters: Dict = None, category: str = "general", aliases: List[str] = None, alias_params: Dict[str, Dict] = None) -> None:
        """注册能力
        
        Args:
            capability: 能力名称
            description: 能力描述
            parameters: 能力所需参数
            category: 能力类别
            aliases: 能力别名列表
            alias_params: 别名对应的参数映射
        """
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.capability_details[capability] = {
                "name": capability,
                "description": description,
                "parameters": parameters or {},
                "category": category,
                "aliases": aliases or [],
                "alias_params": alias_params or {},
                "registered_at": datetime.now().isoformat()
            }
        else:
            logger.debug(f"⚠️ 能力已存在: {capability}")

    def has_capability(self, capability: str) -> bool:
        """检查是否有某能力"""
        return capability in self.capabilities

    def get_capability_details(self, capability: str) -> Optional[Dict]:
        """获取能力详细信息
        
        Args:
            capability: 能力名称
            
        Returns:
            能力详细信息字典，若能力不存在则返回 None
        """
        return self.capability_details.get(capability)

    def get_capabilities_by_category(self, category: str) -> List[str]:
        """按类别获取能力列表
        
        Args:
            category: 能力类别
            
        Returns:
            该类别下的能力名称列表
        """
        return [cap for cap, details in self.capability_details.items() if details.get("category") == category]

    def remove_capability(self, capability: str) -> bool:
        """移除能力
        
        Args:
            capability: 能力名称
            
        Returns:
            移除是否成功
        """
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            if capability in self.capability_details:
                del self.capability_details[capability]
            return True
        else:
            logger.debug(f"⚠️ 能力不存在，无法移除: {capability}")
            return False

    def get_all_capabilities(self, include_details: bool = False) -> Union[List[str], Dict[str, Dict]]:
        """获取所有能力
        
        Args:
            include_details: 是否包含详细信息
            
        Returns:
            若 include_details 为 False，返回能力名称列表
            若 include_details 为 True，返回能力详细信息字典
        """
        if include_details:
            return self.capability_details
        else:
            return self.capabilities

    def register_file_formats(self, open_formats: List[str] = None, edit_formats: List[str] = None):
        if open_formats:
            for fmt in open_formats:
                fmt_lower = fmt.lower()
                if fmt_lower not in self.supported_open_formats:
                    self.supported_open_formats.append(fmt_lower)
        
        if edit_formats:
            for fmt in edit_formats:
                fmt_lower = fmt.lower()
                if fmt_lower not in self.supported_edit_formats:
                    self.supported_edit_formats.append(fmt_lower)

    def can_open_file(self, file_path: str) -> bool:
        """检查是否能打开指定文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_open_formats

    def can_edit_file(self, file_path: str) -> bool:
        """检查是否能编辑指定文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_edit_formats

    async def start(self):
        """启动智能体"""
        self._running = True
        self.status = AgentStatus.IDLE
        self._task_processor = asyncio.create_task(self._process_tasks())
        asyncio.create_task(self._process_messages())

    async def stop(self):
        """停止智能体"""
        self._running = False
        if self._task_processor and not self._task_processor.done():
            self._task_processor.cancel()
        self.status = AgentStatus.OFFLINE

    async def assign_task(self, task: Task) -> bool:
        max_pending = 5
        pending_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        running_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
        
        if running_count > 0:
            logger.warning(f"⚠️ '{self.name}' 正在执行任务，无法接收新任务")
            return False
        
        if pending_count >= max_pending:
            logger.warning(f"⚠️ '{self.name}' 待处理任务过多（{pending_count}），暂时无法接收新任务")
            return False

        task.assigned_to = self.name
        task.status = TaskStatus.PENDING
        self.tasks[task.id] = task
        return True

    async def _process_tasks(self):
        """处理任务队列"""
        while self._running:
            try:
                # 查找待处理的任务
                pending_tasks = [
                    t for t in self.tasks.values()
                    if t.status == TaskStatus.PENDING
                ]

                pending_count = len(pending_tasks)
                if pending_count > 0:
                    logger.debug(f"📋 发现 {pending_count} 个待处理任务")
                    
                    # 按优先级排序
                    pending_tasks.sort(key=lambda t: t.priority)
                    
                    for task in pending_tasks:
                        await self._execute_task(task)

                # 清理已完成的任务（保留最近10个）
                completed_tasks = [
                    task_id for task_id, task in self.tasks.items()
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                ]
                if len(completed_tasks) > 10:
                    remove_count = len(completed_tasks) - 10
                    removed = completed_tasks[:remove_count]
                    for task_id in removed:
                        del self.tasks[task_id]
                    logger.debug(f"🧹 清理了 {remove_count} 个已完成任务")

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ '{self.name}' 任务处理出错: {error_msg}")
                logger.exception(f"📋 任务处理失败详细信息:")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task):
        """执行具体任务 - 子类重写此方法"""
        task_id = task.id
        task_type = task.type
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.status = AgentStatus.BUSY

        try:
            result = await self.execute_task(task)

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            await self._send_completion_report(task)

        except Exception as e:
            error_msg = str(e)
            task.status = TaskStatus.FAILED
            task.error = error_msg
            logger.error(f"❌ '{self.name}' 任务失败: {task_type} (ID: {task_id}, 错误: {error_msg})")
            # 记录详细的错误堆栈
            logger.exception(f"📋 任务失败详细信息:")

        finally:
            self.status = AgentStatus.IDLE
            logger.debug(f"🔄 '{self.name}' 状态已重置为空闲")

    async def execute_task(self, task: Task) -> Any:
        """
        执行任务 - 子类必须重写

        Args:
            task: 任务对象

        Returns:
            任务执行结果
        """
        raise NotImplementedError("子类必须实现 execute_task 方法")

    def cannot_handle(self, reason: str = "", suggestion: str = "", missing_info: Dict = None) -> Dict[str, Any]:
        """
        返回无法处理的结果，让 master 决定下一步

        Args:
            reason: 无法处理的原因
            suggestion: 建议的处理方式
            missing_info: 缺失的信息，如 {"name": "联系人姓名"}，master 会尝试从上下文推断

        Returns:
            标准化的无法处理结果
        """
        return {
            "cannot_handle": True,
            "agent": self.name,
            "reason": reason,
            "suggestion": suggestion,
            "missing_info": missing_info or {}
        }

    async def send_message(self, to_agent: str, message_type: str,
                          content: str, data: Dict = None, requires_response: bool = False):
        """
        发送消息给其他智能体

        Args:
            to_agent: 接收者名称
            message_type: 消息类型
            content: 消息内容
            data: 附加数据
            requires_response: 是否需要回复
        """
        message = Message(
            from_agent=self.name,
            to_agent=to_agent,
            type=message_type,
            content=content,
            data=data or {},
            requires_response=requires_response
        )

        # 通过消息总线发送
        from .message_bus import message_bus
        logger.debug(f"📤 消息总线实例 ID: {id(message_bus)}, 已注册智能体: {list(message_bus._agents.keys())}")
        await message_bus.send_message(message)

        logger.debug(f"📤 '{self.name}' -> '{to_agent}': {message_type}")

    async def _process_messages(self):
        """处理消息队列"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                message_id = message.id
                from_agent = message.from_agent
                message_type = message.type
                
                logger.debug(f"📥 收到消息: {message_type} 来自 {from_agent} (ID: {message_id})")
                await self._handle_message(message)
                logger.debug(f"✅ 消息处理完成: {message_type} (ID: {message_id})")

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ '{self.name}' 消息处理出错: {error_msg}")
                logger.exception(f"📋 消息处理失败详细信息:")
                await asyncio.sleep(0.5)

    async def _handle_message(self, message: Message):
        """处理收到的消息 - 子类可重写"""
        # 调用注册的消息处理器
        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ 消息处理器出错: {error_msg}")
                # 记录详细的错误堆栈
                logger.exception(f"📋 消息处理器失败详细信息:")

    def on_message(self, handler: Callable):
        """注册消息处理器"""
        self.message_handlers.append(handler)

    async def _send_completion_report(self, task: Task):
        """发送任务完成报告给主智能体"""
        await self.send_message(
            to_agent="master",
            message_type="task_completed",
            content=f"任务完成: {task.type}",
            data={
                "task_id": task.id,
                "task_type": task.type,
                "status": task.status.value,
                "result": task.result,
                "error": task.error
            }
        )

    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "capability_count": len(self.capabilities),
            "capability_categories": list(set(details.get("category") for details in self.capability_details.values())),
            "task_count": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "running_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            "supported_file_formats": {
                "open": self.supported_open_formats,
                "edit": self.supported_edit_formats
            }
        }
        
        # 只在调试模式下包含详细能力信息，避免输出过大
        import logging
        if logging.getLogger().level <= logging.DEBUG:
            status["capability_details"] = self.capability_details
        
        return status
