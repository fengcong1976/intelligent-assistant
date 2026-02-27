"""
下载智能体 - 多线程高速下载管理
支持断点续传、下载进度跟踪、批量下载
"""
import asyncio
import os
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable
from urllib.parse import urlparse, unquote
import hashlib

import aiohttp
import aiofiles
from loguru import logger

from ..base import BaseAgent, Task
from ...config import settings


@dataclass
class DownloadTask:
    """下载任务"""
    url: str
    filename: Optional[str] = None
    save_path: Optional[Path] = None
    total_size: int = 0
    downloaded_size: int = 0
    status: str = "pending"  # pending, downloading, paused, completed, failed
    progress: float = 0.0
    speed: str = "0 B/s"
    error: Optional[str] = None
    threads: int = 4
    chunk_size: int = 8192
    _pause_event: threading.Event = field(default_factory=threading.Event)
    _cancelled: bool = False
    
    def __post_init__(self):
        self._pause_event.set()
    
    def pause(self):
        """暂停下载"""
        self._pause_event.clear()
        self.status = "paused"
    
    def resume(self):
        """恢复下载"""
        self._pause_event.set()
        self.status = "downloading"
    
    def cancel(self):
        """取消下载"""
        self._cancelled = True
        self.status = "cancelled"
    
    def wait_if_paused(self):
        """如果暂停则等待"""
        self._pause_event.wait()


class DownloadAgent(BaseAgent):
    """下载智能体 - 多线程高速下载"""
    
    KEYWORD_MAPPINGS = {
        "下载": ("download", {}),
        "下载文件": ("download", {}),
        "下载视频": ("download", {}),
        "下载图片": ("download", {}),
        "下载进度": ("status", {}),
        "暂停下载": ("pause", {}),
        "继续下载": ("resume", {}),
        "取消下载": ("cancel", {}),
        "下载列表": ("list", {}),
        "下载历史": ("history", {}),
        "批量下载": ("batch_download", {}),
        "全部下载": ("batch_download", {}),
    }
    
    def __init__(self):
        super().__init__(
            name="download_agent",
            description="下载智能体 - 多线程高速下载管理"
        )
        
        self.register_capability(
            capability="download_file",
            description="下载文件。从指定URL下载文件到本地。",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "下载链接"
                    },
                    "save_path": {
                        "type": "string",
                        "description": "保存路径（可选）"
                    }
                },
                "required": ["url"]
            },
            category="download"
        )
        
        self.download_dir = settings.directory.get_download_dir()
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.download_history: List[Dict] = []
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📥 下载智能体已初始化 (下载目录: {self.download_dir})")
    
    def _send_message_to_chat(self, message: str):
        """发送即时消息到对话框"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat_window'):
                        main_window = widget
                        if hasattr(main_window, 'chat_window'):
                            chat_window = main_window.chat_window
                            if hasattr(chat_window, 'signal_helper'):
                                chat_window.signal_helper.emit_append_message("assistant", message)
                                break
        except Exception as e:
            logger.warning(f"发送消息失败: {e}")
    
    async def start(self):
        """启动智能体"""
        await super().start()
        # 创建 SSL 上下文，忽略证书验证
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 创建 aiohttp 会话
        timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=60)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10, ssl=ssl_context)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def stop(self):
        """停止智能体"""
        # 取消所有活动下载
        for task in self.active_downloads.values():
            task.cancel()
        
        # 关闭线程池
        self._executor.shutdown(wait=False)
        
        # 关闭 aiohttp 会话
        if self._session:
            await self._session.close()
        
        await super().stop()
    
    async def execute_task(self, task: Task) -> str:
        """执行任务"""
        action = task.params.get("action", "") or task.type
        if action in ("download_file", "file_download"):
            action = "download"
        action = action.lower()
        params = task.params
        
        logger.info(f"📥 Download Agent 执行: {action}")
        
        try:
            if action == "download":
                return await self._download_file(
                    url=params.get("url"),
                    filename=params.get("filename"),
                    threads=params.get("threads", 4),
                    save_dir=params.get("save_dir") or params.get("directory") or params.get("path")
                )
            elif action == "batch_download":
                return await self._batch_download(
                    urls=params.get("urls", []),
                    threads=params.get("threads", 4)
                )
            elif action == "pause":
                return await self._pause_download(params.get("url"))
            elif action == "resume":
                return await self._resume_download(params.get("url"))
            elif action == "cancel":
                return await self._cancel_download(params.get("url"))
            elif action == "list":
                return await self._list_downloads()
            elif action == "history":
                return await self._show_history()
            elif action == "clear_history":
                return await self._clear_history()
            elif task_type == "agent_help":
                return self._get_help_info()
            else:
                return f"❌ 未知的操作: {action}"
        
        except Exception as e:
            logger.error(f"Download Agent 执行失败: {e}")
            return f"❌ 操作失败: {str(e)}"
    
    def _get_filename_from_url(self, url: str, headers: Optional[dict] = None) -> str:
        """从 URL 或响应头中获取文件名"""
        import re
        
        def clean_filename(name: str) -> str:
            """清理文件名中的非法字符"""
            # Windows 文件名不能包含这些字符
            illegal_chars = r'[<>:"/\\|?*]'
            name = re.sub(illegal_chars, '_', name)
            # 移除首尾空格和点
            name = name.strip('. ')
            return name or "download"
        
        # 尝试从 Content-Disposition 头获取
        if headers:
            content_disp = headers.get("Content-Disposition", "")
            if "filename=" in content_disp:
                # 匹配 filename="xxx" 或 filename=xxx
                match = re.search(r'filename="?([^";\s]+)"?', content_disp)
                if match:
                    filename = match.group(1).strip('"\'')
                    return clean_filename(unquote(filename))
        
        # 从 URL 路径获取
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        if filename:
            return clean_filename(unquote(filename))
        
        # 生成默认文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"download_{url_hash}"
    
    async def _download_file(self, url: Optional[str], filename: Optional[str] = None, 
                            threads: int = 4, progress_callback: Optional[Callable] = None,
                            save_dir: Optional[str] = None) -> str:
        """下载单个文件"""
        if not url:
            return "❌ 请提供下载链接"
        
        # 检查是否已在下载中
        if url in self.active_downloads:
            return f"⏳ 该文件已在下载中: {url}"
        
        # 确定下载目录
        if save_dir:
            target_dir = Path(save_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = self.download_dir
        
        try:
            # 先发送提示消息
            self._send_message_to_chat(f"📥 正在获取文件信息...\n\n🔗 链接: {url[:80]}{'...' if len(url) > 80 else ''}")
            
            # 获取文件信息
            async with self._session.head(url, allow_redirects=True) as response:
                if response.status != 200:
                    return f"❌ 无法访问链接: HTTP {response.status}"
                
                total_size = int(response.headers.get("Content-Length", 0))
                supports_range = "bytes" in response.headers.get("Accept-Ranges", "")
                
                # 确定文件名
                if not filename:
                    filename = self._get_filename_from_url(url, response.headers)
                
                save_path = target_dir / filename
                
                # 检查文件是否已存在
                if save_path.exists():
                    existing_size = save_path.stat().st_size
                    if existing_size == total_size:
                        return f"✅ 文件已存在: {filename}"
                    elif supports_range and existing_size < total_size:
                        logger.info(f"📥 检测到未完成的下载，继续下载: {filename}")
                    else:
                        # 重命名文件
                        stem = save_path.stem
                        suffix = save_path.suffix
                        counter = 1
                        while save_path.exists():
                            save_path = self.download_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                        filename = save_path.name
            
            # 创建下载任务
            download_task = DownloadTask(
                url=url,
                filename=filename,
                save_path=save_path,
                total_size=total_size,
                threads=threads
            )
            self.active_downloads[url] = download_task
            
            # 发送开始下载消息
            size_str = self._format_size(total_size) if total_size > 0 else "未知大小"
            self._send_message_to_chat(f"📥 开始下载...\n\n📄 文件: {filename}\n📊 大小: {size_str}\n📁 保存到: {target_dir}")
            
            # 开始下载
            if supports_range and total_size > 0 and threads > 1:
                # 多线程分块下载
                await self._multi_thread_download(download_task, progress_callback)
            else:
                # 单线程下载
                await self._single_thread_download(download_task, progress_callback)
            
            # 下载完成
            if download_task.status == "completed":
                self.download_history.append({
                    "url": url,
                    "filename": filename,
                    "size": total_size,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "completed"
                })
                return f"✅ 下载完成: {filename}\n📁 保存位置: {save_path}"
            elif download_task.status == "cancelled":
                return f"❌ 下载已取消: {filename}"
            else:
                return f"❌ 下载失败: {download_task.error or '未知错误'}"
        
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return f"❌ 下载失败: {str(e)}"
        finally:
            if url in self.active_downloads:
                del self.active_downloads[url]
    
    async def _single_thread_download(self, task: DownloadTask, 
                                      progress_callback: Optional[Callable] = None):
        """单线程下载"""
        task.status = "downloading"
        start_time = time.time()
        downloaded = 0
        
        try:
            # 检查是否支持断点续传
            resume_pos = 0
            if task.save_path.exists():
                resume_pos = task.save_path.stat().st_size
                if resume_pos > 0:
                    headers = {"Range": f"bytes={resume_pos}-"}
                else:
                    headers = {}
            else:
                headers = {}
            
            async with self._session.get(task.url, headers=headers) as response:
                if response.status not in (200, 206):
                    task.status = "failed"
                    task.error = f"HTTP {response.status}"
                    return
                
                mode = "ab" if resume_pos > 0 else "wb"
                async with aiofiles.open(task.save_path, mode) as f:
                    async for chunk in response.content.iter_chunked(task.chunk_size):
                        task.wait_if_paused()
                        
                        if task._cancelled:
                            task.status = "cancelled"
                            return
                        
                        await f.write(chunk)
                        downloaded += len(chunk)
                        task.downloaded_size = resume_pos + downloaded
                        
                        # 计算进度和速度
                        if task.total_size > 0:
                            task.progress = (task.downloaded_size / task.total_size) * 100
                        
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = task.downloaded_size / elapsed
                            task.speed = self._format_speed(speed)
                        
                        if progress_callback:
                            progress_callback(task)
            
            task.status = "completed"
            task.progress = 100.0
        
        except Exception as e:
            logger.error(f"单线程下载失败: {e}")
            task.status = "failed"
            task.error = str(e)
    
    async def _multi_thread_download(self, task: DownloadTask, 
                                     progress_callback: Optional[Callable] = None):
        """多线程分块下载"""
        task.status = "downloading"
        
        try:
            total_size = task.total_size
            num_threads = min(task.threads, 8)  # 最多8个线程
            chunk_size = total_size // num_threads
            
            # 创建临时文件
            temp_files = []
            tasks = []
            
            for i in range(num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i < num_threads - 1 else total_size - 1
                temp_file = task.save_path.with_suffix(f".part{i}")
                temp_files.append(temp_file)
                tasks.append(self._download_chunk(task.url, start, end, temp_file, task))
            
            # 并发下载所有块
            await asyncio.gather(*tasks)
            
            if task._cancelled:
                task.status = "cancelled"
                # 清理临时文件
                for temp_file in temp_files:
                    if temp_file.exists():
                        temp_file.unlink()
                return
            
            if task.status == "failed":
                return
            
            # 合并文件块
            async with aiofiles.open(task.save_path, "wb") as outfile:
                for temp_file in temp_files:
                    async with aiofiles.open(temp_file, "rb") as infile:
                        while True:
                            chunk = await infile.read(8192)
                            if not chunk:
                                break
                            await outfile.write(chunk)
                    # 删除临时文件
                    temp_file.unlink()
            
            task.status = "completed"
            task.progress = 100.0
        
        except Exception as e:
            logger.error(f"多线程下载失败: {e}")
            task.status = "failed"
            task.error = str(e)
    
    async def _download_chunk(self, url: str, start: int, end: int, 
                              temp_file: Path, task: DownloadTask):
        """下载文件块"""
        headers = {"Range": f"bytes={start}-{end}"}
        
        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status != 206:
                    task.status = "failed"
                    task.error = f"HTTP {response.status}"
                    return
                
                async with aiofiles.open(temp_file, "wb") as f:
                    async for chunk in response.content.iter_chunked(task.chunk_size):
                        task.wait_if_paused()
                        
                        if task._cancelled:
                            return
                        
                        await f.write(chunk)
                        task.downloaded_size += len(chunk)
                        
                        if task.total_size > 0:
                            task.progress = (task.downloaded_size / task.total_size) * 100
        
        except Exception as e:
            logger.error(f"下载块失败: {e}")
            task.status = "failed"
            task.error = str(e)
    
    def _format_speed(self, bytes_per_sec: float) -> str:
        """格式化下载速度"""
        if bytes_per_sec >= 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"
        elif bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.2f} KB/s"
        else:
            return f"{bytes_per_sec:.2f} B/s"
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
        elif size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        elif size >= 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size} B"
    
    async def _batch_download(self, urls: List[str], threads: int = 4) -> str:
        """批量下载 - 并行下载多个文件"""
        if not urls:
            return "❌ 请提供下载链接列表"
        
        logger.info(f"📥 开始批量下载，共 {len(urls)} 个文件")
        
        self._send_message_to_chat(f"📥 开始批量下载，共 {len(urls)} 个文件...")
        
        async def download_with_index(idx: int, url: str) -> tuple:
            result = await self._download_file(url, threads=threads)
            return idx, result
        
        tasks = [download_with_index(i, url) for i, url in enumerate(urls, 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        success_count = 0
        fail_count = 0
        
        for item in sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else 999):
            if isinstance(item, tuple):
                idx, result = item
                output.append(f"{idx}. {result}")
                if result.startswith("✅"):
                    success_count += 1
                else:
                    fail_count += 1
            elif isinstance(item, Exception):
                output.append(f"❌ 下载失败: {str(item)}")
                fail_count += 1
        
        summary = f"\n\n📊 批量下载完成: 成功 {success_count} 个，失败 {fail_count} 个"
        return "\n".join(output) + summary
    
    async def _pause_download(self, url: Optional[str]) -> str:
        """暂停下载"""
        if not url:
            return "❌ 请提供下载链接"
        
        if url not in self.active_downloads:
            return "❌ 未找到该下载任务"
        
        task = self.active_downloads[url]
        task.pause()
        return f"⏸️ 已暂停下载: {task.filename}"
    
    async def _resume_download(self, url: Optional[str]) -> str:
        """恢复下载"""
        if not url:
            return "❌ 请提供下载链接"
        
        if url not in self.active_downloads:
            return "❌ 未找到该下载任务"
        
        task = self.active_downloads[url]
        task.resume()
        return f"▶️ 已恢复下载: {task.filename}"
    
    async def _cancel_download(self, url: Optional[str]) -> str:
        """取消下载"""
        if not url:
            return "❌ 请提供下载链接"
        
        if url not in self.active_downloads:
            return "❌ 未找到该下载任务"
        
        task = self.active_downloads[url]
        task.cancel()
        return f"❌ 已取消下载: {task.filename}"
    
    async def _list_downloads(self) -> str:
        """列出活动下载"""
        if not self.active_downloads:
            return "📥 当前没有活动下载"
        
        lines = ["📥 活动下载:"]
        for url, task in self.active_downloads.items():
            size_str = self._format_size(task.total_size) if task.total_size > 0 else "未知"
            lines.append(f"  • {task.filename}")
            lines.append(f"    状态: {task.status}")
            lines.append(f"    进度: {task.progress:.1f}%")
            lines.append(f"    速度: {task.speed}")
            lines.append(f"    大小: {size_str}")
        
        return "\n".join(lines)
    
    async def _show_history(self) -> str:
        """显示下载历史"""
        if not self.download_history:
            return "📜 暂无下载历史"
        
        lines = ["📜 下载历史:"]
        for item in self.download_history[-20:]:  # 只显示最近20条
            size_str = self._format_size(item.get("size", 0))
            lines.append(f"  • {item['filename']}")
            lines.append(f"    时间: {item['time']}")
            lines.append(f"    大小: {size_str}")
            lines.append(f"    状态: {item['status']}")
        
        return "\n".join(lines)
    
    async def _clear_history(self) -> str:
        """清空下载历史"""
        count = len(self.download_history)
        self.download_history.clear()
        return f"✅ 已清空下载历史，共 {count} 条记录"
    
    def get_capabilities(self) -> list:
        """获取能力列表"""
        return [
            "file_download",
            "batch_download",
            "download_management"
        ]

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 下载智能体

### 功能说明
下载智能体可以下载各种文件，支持多线程下载、断点续传。

### 支持的操作
- **下载文件**：从URL下载文件
- **批量下载**：同时下载多个文件
- **暂停下载**：暂停正在下载的任务
- **恢复下载**：恢复暂停的下载
- **取消下载**：取消下载任务

### 使用示例
- "下载 [文件链接]" - 下载指定文件
- "批量下载这些链接" - 批量下载
- "查看下载进度" - 查看下载状态

### 注意事项
- 支持断点续传
- 大文件下载可能需要较长时间
- 下载的文件会保存在下载目录"""
