"""
Video Agent - 视频播放智能体
支持常用视频格式播放，使用独立播放器窗口
"""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from ..base import BaseAgent, Task, Message
from ...config import settings

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 导入独立播放器
try:
    from ...video.standalone_player import (
        StandaloneVideoPlayer, show_player, create_player_instance,
        get_player_instance, VideoInfo
    )
    STANDALONE_PLAYER_AVAILABLE = True
    logger.info("✅ 独立视频播放器加载成功")
except ImportError as e:
    logger.error(f"❌ 独立视频播放器加载失败: {e}")
    STANDALONE_PLAYER_AVAILABLE = False
    StandaloneVideoPlayer = None
    show_player = None
    create_player_instance = None
    get_player_instance = None
    VideoInfo = None


class VideoAgent(BaseAgent):
    """视频播放智能体 - 使用独立播放器窗口"""
    
    PRIORITY = 3
    KEYWORD_MAPPINGS = {
        "播放视频": ("play", {}),
        "放视频": ("play", {}),
        "看视频": ("play", {}),
        "打开视频": ("play", {}),
        "暂停视频": ("pause", {}),
        "停止视频": ("stop", {}),
        "继续视频": ("resume", {}),
        "下一个视频": ("next", {}),
        "上一个视频": ("previous", {}),
        "视频列表": ("list", {}),
        "搜索视频": ("search", {}),
        "查找视频": ("search", {}),
    }

    def __init__(self):
        super().__init__(
            name="video_agent",
            description="视频播放智能体 - 支持常用视频格式播放"
        )

        self.register_capability(
            capability="play_video",
            description="播放视频。可以播放指定视频或搜索视频。",
            aliases=[
                "播放视频", "放视频", "看视频", "打开视频",
                "看电影", "看个电影", "放电影", "看个片", "放个片",
                "暂停视频", "暂停播放视频", "停止视频", "停止播放视频",
                "继续视频", "继续播放视频", "下一个视频", "上一个视频",
                "视频列表", "搜索视频", "查找视频"
            ],
            parameters={
                "type": "object",
                "properties": {
                    "video_name": {
                        "type": "string",
                        "description": "视频名称或关键词"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "stop"],
                        "description": "播放控制动作",
                        "default": "play"
                    }
                },
                "required": ["video_name"]
            },
            category="video"
        )
        
        self.register_capability("stop_video", "停止视频")
        self.register_capability("video_control", "视频控制")
        self.register_capability("search_video", "搜索视频")
        self.register_capability("video_library", "视频库")
        
        # 注册支持的文件格式（类似Windows文件关联）
        self.register_file_formats(
            open_formats=[".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"]
        )

        self.supported_formats = [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"]
        self._player_window: Optional[StandaloneVideoPlayer] = None

        logger.info("🎬 视频智能体已初始化（独立播放器模式）")

    def _get_player(self) -> Optional[StandaloneVideoPlayer]:
        """获取播放器实例"""
        if not STANDALONE_PLAYER_AVAILABLE:
            return None
        
        if self._player_window is None:
            self._player_window = get_player_instance()
            if self._player_window is None:
                self._player_window = create_player_instance()
        
        return self._player_window

    def _show_player(self):
        """显示播放器窗口"""
        player = self._get_player()
        if player:
            player.show()
            player.raise_()
            player.activateWindow()
        return player

    def _get_video_library(self) -> Path:
        video_dir = getattr(settings.directory, 'video_library', None)
        if video_dir:
            return Path(video_dir)
        return Path.home() / "Videos"

    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params
        logger.info(f"🎬 执行视频任务: {task_type}")

        # 处理带video_前缀的任务类型
        if task_type.startswith("video_"):
            task_type = task_type[6:]  # 移除 "video_" 前缀

        # 处理 general 类型任务（当强制指定视频智能体时）
        if task_type == "general":
            # 从内容中提取视频URL或视频名
            content = task.content
            # 移除 @视频智能体 前缀
            content = content.replace("@视频智能体", "").strip()
            
            # 检查是否是URL
            url_patterns = [
                r'https?://[^\s<>"\']+[^\s<>"\'.]',
            ]
            import re
            for pattern in url_patterns:
                match = re.search(pattern, content)
                if match:
                    url = match.group(0)
                    logger.info(f"🎬 从general任务中提取到URL: {url}")
                    result = await self._handle_play({"video_name": url})
                    if result and ("未找到" in result or "不存在" in result):
                        task.no_retry = True
                    return result
            
            # 否则作为普通播放处理
            result = await self._handle_play({"video_name": content})
            if result and ("未找到" in result or "不存在" in result):
                task.no_retry = True
            return result

        if task_type == "play":
            result = await self._handle_play(params)
        elif task_type == "play_video":
            result = await self._handle_play(params)
        elif task_type == "stop":
            result = await self._handle_stop(params)
        elif task_type == "pause":
            result = await self._handle_pause(params)
        elif task_type == "resume":
            result = await self._handle_resume(params)
        elif task_type == "next":
            result = await self._handle_next(params)
        elif task_type == "previous":
            result = await self._handle_previous(params)
        elif task_type == "volume":
            result = await self._handle_volume(params)
        elif task_type == "status":
            result = await self._handle_status(params)
        elif task_type == "search":
            result = await self._handle_search(params)
        elif task_type == "list":
            result = await self._handle_list(params)
        else:
            return f"❌ 不支持的视频操作: {task_type}"
        
        if result and ("未找到" in result or "不存在" in result):
            task.no_retry = True
        return result

    async def _handle_play(self, params: Dict) -> str:
        """处理播放请求"""
        if not STANDALONE_PLAYER_AVAILABLE:
            return "❌ 视频播放器不可用"
        
        import re
        
        video_name = params.get("video_name", params.get("query", ""))
        video_path = params.get("video_path") or params.get("file_path")
        directory = params.get("directory")
        url = params.get("url", "")
        
        # 如果有 url 参数（来自工作流），使用它
        if url and not video_name:
            video_name = url
        
        # 转换中文路径格式
        def convert_chinese_path(path_str):
            if not path_str:
                return path_str
            # 将中文"盘"转换为英文":"，并在后面加反斜杠
            path_str = re.sub(r'([a-zA-Z])盘', r'\1:\\', path_str, flags=re.IGNORECASE)
            # 将"目录下的"转换为反斜杠
            path_str = re.sub(r'目录下的\s*', r'\\', path_str, flags=re.IGNORECASE)
            # 移除多余空格
            path_str = path_str.replace(' ', '')
            # 修复双反斜杠
            path_str = re.sub(r'\\+', r'\\', path_str)
            return path_str
        
        video_path = convert_chinese_path(video_path)
        directory = convert_chinese_path(directory)
        video_name = convert_chinese_path(video_name)
        
        # 检查是否是在线视频URL，需要先下载
        if video_name and video_name.startswith("http"):
            return await self._download_and_play(video_name)
        
        logger.info(f"🎬 准备播放视频: video_path={video_path}, directory={directory}, video_name={video_name}")
        
        # 使用信号机制在主线程中播放视频
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app:
            # 获取主窗口
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'chat_window'):
                    main_window = widget
                    break
            
            if main_window and hasattr(main_window, 'chat_window'):
                chat_window = main_window.chat_window
                if hasattr(chat_window, 'signal_helper'):
                    logger.info("🎬 通过信号机制发送播放请求")
                    chat_window.signal_helper.emit_play_video(video_path or "", directory or "", video_name or "")
                else:
                    logger.error("❌ signal_helper 不存在")
            else:
                logger.error("❌ 找不到主窗口")
        else:
            logger.error("❌ QApplication 实例不存在")
        
        # 立即返回结果
        if video_path:
            return f"▶️ 正在准备播放视频..."
        elif directory:
            return f"▶️ 正在准备播放目录视频..."
        elif video_name:
            return f"▶️ 正在准备播放: {video_name}"
        else:
            return "🎬 视频播放器已打开"
    
    async def _download_and_play(self, url: str) -> str:
        """下载在线视频并播放"""
        # 清理URL中的反引号
        url = url.strip('`').strip()
        logger.info(f"🎬 检测到在线视频URL，准备下载: {url}")
        
        # 使用下载智能体下载
        from ..multi_agent_system import multi_agent_system
        
        master = multi_agent_system.master
        if not master:
            return "❌ 主智能体不可用"
        
        download_agent = await master._get_or_create_agent("download_agent")
        
        if not download_agent:
            return "❌ 下载智能体不可用"
        
        # 创建下载任务
        from ..base import Task
        download_task = Task(
            type="download",
            content=f"下载视频: {url}",
            params={"action": "download", "url": url},
            priority=5
        )
        
        # 执行下载
        logger.info(f"📥 开始下载视频: {url}")
        download_result = await download_agent.assign_task(download_task)
        
        if not download_result:
            return "❌ 下载任务分配失败"
        
        # 脉冲询问方式等待下载完成
        from ..base import TaskStatus
        max_wait = 300  # 最多等待300次询问
        wait_interval = 1  # 每次间隔1秒
        wait_count = 0
        
        while wait_count < max_wait:
            # 检查任务状态
            task = download_agent.tasks.get(download_task.id)
            if task:
                if task.status == TaskStatus.COMPLETED:
                    logger.info(f"✅ 下载任务完成: {task.id}")
                    break
                elif task.status == TaskStatus.FAILED:
                    return f"❌ 下载失败: {task.error or '未知错误'}"
                elif task.status == TaskStatus.CANCELLED:
                    return "❌ 下载已取消"
            
            # 等待一段时间后再次询问
            await asyncio.sleep(wait_interval)
            wait_count += 1
            
            # 每10秒输出一次进度
            if wait_count % 10 == 0:
                logger.info(f"⏳ 等待下载完成... ({wait_count}秒)")
        
        if wait_count >= max_wait:
            return "❌ 下载超时"
        
        # 获取下载的文件路径
        task = download_agent.tasks.get(download_task.id)
        if task and task.result:
            # 从结果中提取文件路径
            import re
            match = re.search(r'保存位置:\s*(.+)', task.result)
            if match:
                local_path = match.group(1).strip()
                logger.info(f"✅ 视频下载完成: {local_path}")
                
                # 播放本地文件
                return await self._handle_play({"video_path": local_path})
            
            # 检查文件是否已存在
            exist_match = re.search(r'文件已存在:\s*(.+)', task.result)
            if exist_match:
                filename = exist_match.group(1).strip()
                # 从下载目录获取文件路径
                from ...config import settings
                download_dir = settings.directory.get_download_dir()
                local_path = download_dir / filename
                logger.info(f"✅ 文件已存在: {local_path}")
                return await self._handle_play({"video_path": str(local_path)})
            
            logger.warning(f"无法从结果中提取路径: {task.result}")
        
        return f"✅ 下载完成，但无法获取文件路径"
    
    def _do_play(self, player, video_path, directory, video_name):
        """实际执行播放"""
        from pathlib import Path
        
        logger.info(f"🎬 _do_play 被调用: video_path={video_path}, directory={directory}, video_name={video_name}")
        
        # 优先使用视频路径
        if video_path:
            path = Path(video_path)
            if path.exists() or str(video_path).startswith("http"):
                success = player.play(str(video_path), path.stem if path.exists() else "在线视频")
                if success:
                    logger.info(f"▶️ 正在播放: {path.name if path.exists() else video_path}")
                else:
                    logger.error(f"❌ 播放失败: {video_path}")
            else:
                logger.error(f"❌ 视频文件不存在: {video_path}")
            return
        
        # 如果指定了目录，在该目录下搜索视频
        if directory:
            dir_path = Path(directory)
            if dir_path.exists() and dir_path.is_dir():
                # 查找目录下的所有视频文件
                video_files = []
                for ext in self.supported_formats:
                    video_files.extend(dir_path.glob(f"*{ext}"))
                
                if video_files:
                    # 播放第一个视频
                    first_video = video_files[0]
                    success = player.play(str(first_video), first_video.stem)
                    if success:
                        if len(video_files) > 1:
                            logger.info(f"▶️ 正在播放: {first_video.name}，目录中还有 {len(video_files) - 1} 个视频文件")
                        else:
                            logger.info(f"▶️ 正在播放: {first_video.name}")
                    else:
                        logger.error(f"❌ 播放失败: {first_video}")
                else:
                    logger.error(f"❌ 目录中没有找到视频文件: {directory}")
            else:
                logger.error(f"❌ 目录不存在: {directory}")
            return
        
        # 使用视频名称（可能是URL或搜索关键词）
        if video_name:
            # 检查是否是URL
            if video_name.startswith("http"):
                success = player.play(video_name, "在线视频")
                if success:
                    logger.info("▶️ 正在播放在线视频")
                else:
                    logger.error(f"❌ 播放失败: {video_name}")
                return
            
            # 本地视频搜索
            library = self._get_video_library()
            if library.exists():
                for ext in self.supported_formats:
                    video_file = library / f"{video_name}{ext}"
                    if video_file.exists():
                        success = player.play(str(video_file), video_file.stem)
                        if success:
                            logger.info(f"▶️ 正在播放: {video_file.name}")
                        else:
                            logger.error(f"❌ 播放失败: {video_file}")
                        return
                
                # 模糊搜索
                matches = list(library.glob(f"*{video_name}*"))
                for match in matches:
                    if match.suffix.lower() in self.supported_formats:
                        success = player.play(str(match), match.stem)
                        if success:
                            logger.info(f"▶️ 正在播放: {match.name}")
                        else:
                            logger.error(f"❌ 播放失败: {match}")
                        return
            
            logger.error(f"❌ 未找到视频: {video_name}")
            return
        
        # 没有指定视频，只是显示播放器
        logger.info("🎬 视频播放器已打开")

    async def _handle_stop(self, params: Dict) -> str:
        """处理停止请求"""
        player = self._get_player()
        if player:
            player.stop()
            return "⏹ 已停止播放"
        return "❌ 播放器未启动"

    async def _handle_pause(self, params: Dict) -> str:
        """处理暂停请求"""
        # ffplay 不支持真正的暂停
        return "⏸ 暂停功能需要直接在播放器窗口操作（空格键）"

    async def _handle_resume(self, params: Dict) -> str:
        """处理恢复请求"""
        player = self._get_player()
        if player:
            player.play()
            return "▶️ 继续播放"
        return "❌ 播放器未启动"

    async def _handle_next(self, params: Dict) -> str:
        """处理下一个请求"""
        player = self._get_player()
        if player:
            player._on_next()
            return "⏭ 切换到下一个视频"
        return "❌ 播放器未启动"

    async def _handle_previous(self, params: Dict) -> str:
        """处理上一个请求"""
        player = self._get_player()
        if player:
            player._on_previous()
            return "⏮ 切换到上一个视频"
        return "❌ 播放器未启动"

    async def _handle_volume(self, params: Dict) -> str:
        """处理音量请求"""
        # ffplay 不支持外部音量控制
        return "🔊 音量控制需要在播放器窗口操作（↑↓键）"

    async def _handle_status(self, params: Dict) -> str:
        """处理状态请求"""
        player = self._get_player()
        if not player:
            return "🎬 播放器未启动"
        
        if player.current_video:
            return (
                f"🎬 当前视频: {player.current_video.title}\n"
                f"📊 状态: {'播放中' if player.is_playing else '已停止'}\n"
                f"📁 播放列表: {len(player.playlist)} 个视频"
            )
        return f"🎬 当前未播放视频\n📁 播放列表: {len(player.playlist)} 个视频"

    async def _handle_search(self, params: Dict) -> str:
        """处理搜索请求"""
        query = params.get("query", params.get("video_name", ""))
        
        if not query:
            return "❌ 请提供搜索关键词"
        
        library = self._get_video_library()
        if not library.exists():
            return f"❌ 视频库不存在: {library}"
        
        # 搜索匹配的视频
        results = []
        for ext in self.supported_formats:
            results.extend(library.glob(f"*{query}*{ext}"))
        
        if not results:
            return f"❌ 未找到匹配的视频: {query}"
        
        result_str = f"🔍 找到 {len(results)} 个视频:\n\n"
        for i, video in enumerate(results[:10], 1):
            size_mb = video.stat().st_size / (1024 * 1024)
            result_str += f"{i}. {video.name} ({size_mb:.1f} MB)\n"
        
        if len(results) > 10:
            result_str += f"\n... 还有 {len(results) - 10} 个视频"
        
        return result_str

    async def _handle_list(self, params: Dict) -> str:
        """处理列表请求"""
        library = self._get_video_library()
        if not library.exists():
            return f"❌ 视频库不存在: {library}"
        
        # 获取所有视频
        videos = []
        for ext in self.supported_formats:
            videos.extend(library.glob(f"*{ext}"))
        
        if not videos:
            return f"📁 视频库为空: {library}"
        
        result_str = f"📁 视频库 ({len(videos)} 个视频):\n\n"
        for i, video in enumerate(sorted(videos)[:20], 1):
            size_mb = video.stat().st_size / (1024 * 1024)
            result_str += f"{i}. {video.name} ({size_mb:.1f} MB)\n"
        
        if len(videos) > 20:
            result_str += f"\n... 还有 {len(videos) - 20} 个视频"
        
        return result_str
