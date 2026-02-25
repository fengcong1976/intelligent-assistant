"""
Task Executor - 任务执行器和线程池管理

特性：
- 异步任务队列
- 线程池执行阻塞操作
- 任务状态监控
- 超时和取消支持
"""
import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = auto()      # 等待中
    RUNNING = auto()      # 执行中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消
    TIMEOUT = auto()      # 超时


@dataclass
class Task:
    """任务对象"""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5           # 优先级（1-10，数字越小优先级越高）
    timeout: float = 30.0       # 超时时间
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class TaskExecutor:
    """
    任务执行器

    管理异步任务和线程池，确保不阻塞主程序
    """

    def __init__(
        self,
        max_workers: int = 10,
        max_concurrent: int = 20,
        queue_size: int = 1000
    ):
        self.max_workers = max_workers
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size

        # 线程池（用于执行阻塞操作）
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="agent_task_"
        )

        # 任务队列
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._tasks: Dict[str, Task] = {}
        self._running_tasks: Set[str] = set()

        # 控制标志
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

        # 统计
        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
        }

    async def start(self):
        """启动执行器"""
        if self._running:
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"TaskExecutor started with {self.max_workers} workers")

    async def stop(self):
        """停止执行器"""
        if not self._running:
            return

        self._running = False

        # 取消所有运行中的任务
        for task_id in list(self._running_tasks):
            await self.cancel_task(task_id)

        # 停止工作线程
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # 关闭线程池
        self._thread_pool.shutdown(wait=True)
        logger.info("TaskExecutor stopped")

    async def submit(
        self,
        func: Callable,
        *args,
        name: str = "",
        priority: int = 5,
        timeout: float = 30.0,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        提交任务

        Args:
            func: 要执行的函数
            args: 位置参数
            name: 任务名称
            priority: 优先级（1-10）
            timeout: 超时时间
            metadata: 元数据
            kwargs: 关键字参数

        Returns:
            str: 任务ID
        """
        task = Task(
            id=str(uuid.uuid4()),
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {}
        )

        self._tasks[task.id] = task
        self._stats["total_submitted"] += 1

        # 放入队列（优先级高的先执行）
        await self._task_queue.put((priority, time.time(), task))
        logger.debug(f"Task submitted: {task.name} ({task.id})")

        return task.id

    async def submit_coroutine(
        self,
        coro: asyncio.Coroutine,
        name: str = "",
        priority: int = 5,
        timeout: float = 30.0,
        metadata: Optional[Dict] = None
    ) -> str:
        """提交协程任务"""
        async def wrapper():
            return await coro

        return await self.submit(
            wrapper,
            name=name,
            priority=priority,
            timeout=timeout,
            metadata=metadata
        )

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Task]:
        """等待任务完成"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        # 如果已完成，直接返回
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT):
            return task

        # 等待任务完成
        start_time = time.time()
        while task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT):
            await asyncio.sleep(0.1)
            if timeout and (time.time() - start_time) > timeout:
                break

        return task

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self._stats["total_cancelled"] += 1
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
        }

    async def _worker_loop(self):
        """工作循环"""
        while self._running:
            try:
                # 获取任务（带优先级）
                priority, _, task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )

                # 使用信号量限制并发
                async with self._semaphore:
                    await self._execute_task(task)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")

    async def _execute_task(self, task: Task):
        """执行任务"""
        if task.status == TaskStatus.CANCELLED:
            return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._running_tasks.add(task.id)

        logger.info(f"Task started: {task.name} ({task.id})")
        start_time = time.time()

        try:
            # 在线程池中执行
            loop = asyncio.get_event_loop()

            if asyncio.iscoroutinefunction(task.func):
                # 如果是协程函数，直接执行
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                # 如果是普通函数，在线程池中执行
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._thread_pool,
                        lambda: task.func(*task.args, **task.kwargs)
                    ),
                    timeout=task.timeout
                )

            task.result = result
            task.status = TaskStatus.COMPLETED
            self._stats["total_completed"] += 1
            logger.info(f"Task completed: {task.name} ({task.id})")

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = "Task timeout"
            self._stats["total_failed"] += 1
            logger.warning(f"Task timeout: {task.name} ({task.id})")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._stats["total_failed"] += 1
            logger.error(f"Task failed: {task.name} ({task.id}): {e}")

        finally:
            task.completed_at = datetime.now()
            task.execution_time = time.time() - start_time
            self._running_tasks.discard(task.id)


# 全局执行器实例
task_executor = TaskExecutor()
