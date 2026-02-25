"""
Task Manager - 任务管理后台
支持多智能体并发执行、任务优先级、状态跟踪
"""
import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from loguru import logger
import threading


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ManagedTask:
    """被管理的任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    agent_name: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    progress: int = 0
    progress_message: str = ""
    timeout: int = 300
    depends_on: List[str] = field(default_factory=list)
    callback: Optional[Callable] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_name": self.agent_name,
            "action": self.action,
            "priority": self.priority,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error": self.error
        }


class TaskManager:
    """
    任务管理器
    
    功能：
    - 多智能体并发执行
    - 任务优先级队列
    - 任务状态跟踪
    - 任务取消
    - 超时处理
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.tasks: Dict[str, ManagedTask] = {}
        self.pending_queue: asyncio.PriorityQueue = None
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.agent_tasks: Dict[str, List[str]] = {}
        self.max_concurrent_per_agent: int = 2
        self.max_total_concurrent: int = 10
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._processor_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._status_callbacks: List[Callable] = []
        
        logger.info("📋 任务管理器已创建")
    
    def _check_loop_changed(self) -> bool:
        """检查事件循环是否变化"""
        try:
            current_loop = asyncio.get_running_loop()
            if self._event_loop is not None and self._event_loop != current_loop:
                logger.warning("📋 检测到事件循环变化，重置任务管理器")
                self._reset_state()
                return True
        except RuntimeError:
            pass
        return False
    
    def _reset_state(self):
        """重置状态"""
        self._running = False
        self._processor_task = None
        self.pending_queue = None
        self.running_tasks.clear()
        self._event_loop = None
    
    def set_limits(self, max_per_agent: int = 2, max_total: int = 10):
        """设置并发限制"""
        self.max_concurrent_per_agent = max_per_agent
        self.max_total_concurrent = max_total
        logger.info(f"📋 并发限制: 每智能体{max_per_agent}个, 总计{max_total}个")
    
    def add_status_callback(self, callback: Callable):
        """添加状态变化回调"""
        self._status_callbacks.append(callback)
    
    async def _notify_status(self, task: ManagedTask):
        """通知状态变化"""
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.warning(f"状态回调执行失败: {e}")
    
    async def start(self):
        """启动任务管理器"""
        self._check_loop_changed()
        
        if self._running:
            return
        
        self._running = True
        self._event_loop = asyncio.get_running_loop()
        self.pending_queue = asyncio.PriorityQueue()
        
        self._processor_task = asyncio.create_task(self._process_queue())
        
        logger.info("✅ 任务管理器已启动")
    
    async def stop(self):
        """停止任务管理器"""
        if not self._running:
            return
        
        self._running = False
        
        if self._processor_task:
            try:
                self._processor_task.cancel()
                await asyncio.wait_for(self._processor_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            self._processor_task = None
        
        for task_id, atask in list(self.running_tasks.items()):
            try:
                atask.cancel()
            except Exception:
                pass
            if task_id in self.tasks:
                self.tasks[task_id].state = TaskState.CANCELLED
        
        self.running_tasks.clear()
        self.pending_queue = None
        self._event_loop = None
        logger.info("🛑 任务管理器已停止")
    
    def submit(
        self,
        name: str,
        agent_name: str,
        action: str,
        params: Dict[str, Any] = None,
        priority: int = 5,
        timeout: int = 300,
        depends_on: List[str] = None,
        callback: Callable = None
    ) -> str:
        """
        提交新任务
        
        Returns:
            任务ID
        """
        task = ManagedTask(
            name=name,
            agent_name=agent_name,
            action=action,
            params=params or {},
            priority=priority,
            timeout=timeout,
            depends_on=depends_on or [],
            callback=callback
        )
        
        self.tasks[task.id] = task
        
        if agent_name not in self.agent_tasks:
            self.agent_tasks[agent_name] = []
        self.agent_tasks[agent_name].append(task.id)
        
        if self.pending_queue:
            self.pending_queue.put_nowait((-priority, task.created_at.timestamp(), task.id))
        
        task.state = TaskState.QUEUED
        logger.info(f"📥 任务已提交: {name} (ID: {task.id}, 优先级: {priority})")
        
        return task.id
    
    async def _process_queue(self):
        """处理任务队列"""
        while self._running:
            try:
                if not self.pending_queue:
                    await asyncio.sleep(1)
                    continue
                
                try:
                    _, _, task_id = await asyncio.wait_for(
                        self.pending_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                task = self.tasks.get(task_id)
                if not task:
                    continue
                
                if task.state == TaskState.CANCELLED:
                    continue
                
                while not self._can_start_task(task.agent_name):
                    await asyncio.sleep(0.5)
                    if task.state == TaskState.CANCELLED:
                        break
                
                if task.state == TaskState.CANCELLED:
                    continue
                
                if not await self._check_dependencies(task):
                    task.state = TaskState.FAILED
                    task.error = "依赖任务未完成"
                    await self._notify_status(task)
                    continue
                
                atask = asyncio.create_task(self._execute_task(task))
                self.running_tasks[task.id] = atask
                
            except asyncio.CancelledError:
                break
            except RuntimeError as e:
                if "different event loop" in str(e):
                    logger.warning("📋 检测到事件循环变化，重置队列")
                    self._reset_state()
                    break
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"任务队列处理错误: {e}")
                await asyncio.sleep(1)
    
    def _can_start_task(self, agent_name: str) -> bool:
        """检查是否可以启动新任务"""
        total_running = len(self.running_tasks)
        if total_running >= self.max_total_concurrent:
            return False
        
        agent_running = sum(
            1 for tid in self.running_tasks
            if self.tasks.get(tid) and self.tasks[tid].agent_name == agent_name
        )
        
        return agent_running < self.max_concurrent_per_agent
    
    async def _check_dependencies(self, task: ManagedTask) -> bool:
        """检查依赖任务是否完成"""
        for dep_id in task.depends_on:
            dep_task = self.tasks.get(dep_id)
            if not dep_task:
                return False
            if dep_task.state != TaskState.COMPLETED:
                return False
        return True
    
    async def _execute_task(self, task: ManagedTask):
        """执行任务"""
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()
        await self._notify_status(task)
        
        logger.info(f"▶️ 开始执行任务: {task.name} ({task.agent_name})")
        
        try:
            from .multi_agent_system import multi_agent_system
            
            if not multi_agent_system.master:
                raise RuntimeError("系统未初始化")
            
            agent = multi_agent_system.master.sub_agents.get(task.agent_name)
            if not agent:
                agent = await multi_agent_system.master._get_or_create_agent(task.agent_name)
            
            if not agent:
                raise ValueError(f"智能体不存在: {task.agent_name}")
            
            result = await asyncio.wait_for(
                agent.execute_action(task.action, task.params),
                timeout=task.timeout
            )
            
            task.result = result
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"✅ 任务完成: {task.name}")
            
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(task)
                    else:
                        task.callback(task)
                except Exception as e:
                    logger.warning(f"任务回调执行失败: {e}")
            
        except asyncio.TimeoutError:
            task.state = TaskState.TIMEOUT
            task.error = f"任务超时 ({task.timeout}秒)"
            logger.warning(f"⏰ 任务超时: {task.name}")
            
        except asyncio.CancelledError:
            task.state = TaskState.CANCELLED
            logger.info(f"🚫 任务已取消: {task.name}")
            
        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            logger.error(f"❌ 任务失败: {task.name} - {e}")
        
        finally:
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            
            await self._notify_status(task)
    
    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return False
        
        task.state = TaskState.CANCELLED
        
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
        
        logger.info(f"🚫 任务已取消: {task.name}")
        return True
    
    def get_task(self, task_id: str) -> Optional[ManagedTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ManagedTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_agent_tasks(self, agent_name: str) -> List[ManagedTask]:
        """获取指定智能体的任务"""
        task_ids = self.agent_tasks.get(agent_name, [])
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]
    
    def get_running_tasks(self) -> List[ManagedTask]:
        """获取正在运行的任务"""
        return [
            self.tasks[tid] 
            for tid in self.running_tasks 
            if tid in self.tasks
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """获取任务管理器状态"""
        running = len(self.running_tasks)
        pending = sum(1 for t in self.tasks.values() if t.state == TaskState.QUEUED)
        completed = sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.state == TaskState.FAILED)
        
        return {
            "running": running,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "total": len(self.tasks),
            "max_concurrent": self.max_total_concurrent
        }
    
    def update_progress(self, task_id: str, progress: int, message: str = ""):
        """更新任务进度"""
        task = self.tasks.get(task_id)
        if task:
            task.progress = min(100, max(0, progress))
            task.progress_message = message
    
    def clear_completed(self):
        """清除已完成的任务"""
        to_remove = [
            tid for tid, task in self.tasks.items()
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
        ]
        
        for tid in to_remove:
            del self.tasks[tid]
            for agent_name, task_ids in self.agent_tasks.items():
                if tid in task_ids:
                    task_ids.remove(tid)
        
        logger.info(f"🧹 已清除 {len(to_remove)} 个已完成任务")
        return len(to_remove)


task_manager = TaskManager()
