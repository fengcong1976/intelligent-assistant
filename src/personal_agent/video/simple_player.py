"""
简单视频播放器 - 使用 ffplay 直接播放
"""
import sys
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class VideoInfo:
    """视频信息"""
    title: str
    path: Optional[Path] = None
    url: Optional[str] = None
    duration: float = 0
    width: int = 0
    height: int = 0
    is_online: bool = False


class SimpleVideoPlayer:
    """简单视频播放器 - 使用 ffplay"""
    
    _instance: Optional['SimpleVideoPlayer'] = None
    _current_process: Optional[subprocess.Popen] = None
    _current_video_info: Optional[VideoInfo] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def play(self, video_info: VideoInfo) -> str:
        """播放视频"""
        try:
            # 停止之前的播放
            self.stop()
            
            path = str(video_info.path) if video_info.path else video_info.url
            if not path:
                return "❌ 没有视频路径"
            
            # 构建 ffplay 命令
            cmd = [
                "ffplay",
                "-window_title", video_info.title,
                "-x", "1280",
                "-y", "720",
                "-autoexit",
                "-volume", "100",
                "-tls_verify", "0",
                path
            ]
            
            logger.info(f"🎬 启动 ffplay: {' '.join(cmd)}")
            
            # Windows 启动信息
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_SHOWNORMAL
                
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo
                )
            else:
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # 保存视频信息
            self._current_video_info = video_info
            
            # 监控进程
            threading.Thread(target=self._monitor, daemon=True).start()
            
            # 显示 GUI 视频面板
            self._show_gui_panel(video_info.title)
            
            return f"▶️ 正在播放: {video_info.title}\n🎮 视频面板已显示在右侧"
            
        except Exception as e:
            logger.error(f"播放失败: {e}")
            return f"❌ 播放失败: {e}"
    
    def _show_gui_panel(self, title: str):
        """显示 GUI 视频控制面板（使用 QTimer 在主线程执行）"""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            app = QApplication.instance()
            
            if app:
                # 遍历所有顶层窗口找到 ChatWindow
                for window in app.topLevelWidgets():
                    if hasattr(window, 'chat_window'):
                        chat_window = window.chat_window
                        # 使用 QTimer.singleShot 在主线程执行
                        def show_controls():
                            try:
                                # 显示左侧视频控制面板
                                chat_window.video_control_widget.show()
                                chat_window.video_title_label.setText(f"🎬 {title[:20]}..." if len(title) > 20 else f"🎬 {title}")
                                logger.info(f"🎬 左侧视频控制面板已显示")
                            except Exception as e:
                                logger.error(f"显示控制面板错误: {e}")
                        QTimer.singleShot(0, show_controls)
                        break
        except Exception as e:
            logger.warning(f"显示视频面板失败: {e}")
    
    def _monitor(self):
        """监控播放进程"""
        if self._current_process:
            self._current_process.wait()
            logger.info("🎬 视频播放结束")
            self._current_process = None
            self._current_video_info = None
    
    def stop(self) -> str:
        """停止播放"""
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=2)
            except:
                self._current_process.kill()
            finally:
                self._current_process = None
                self._current_video_info = None
                # 隐藏控制面板
                self._hide_gui_controls()
            return "⏹️ 已停止"
        return "ℹ️ 没有正在播放的视频"
    
    def _hide_gui_controls(self):
        """隐藏 GUI 视频控制面板"""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            app = QApplication.instance()
            if app:
                for window in app.topLevelWidgets():
                    if hasattr(window, 'chat_window'):
                        chat_window = window.chat_window
                        def hide_controls():
                            try:
                                chat_window.video_control_widget.hide()
                                chat_window.video_title_label.setText("🎬 未播放")
                            except Exception as e:
                                logger.error(f"隐藏控制面板错误: {e}")
                        QTimer.singleShot(0, hide_controls)
                        break
        except Exception as e:
            logger.warning(f"隐藏视频面板失败: {e}")
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._current_process is not None and self._current_process.poll() is None


# 全局实例
_simple_player: Optional[SimpleVideoPlayer] = None


def get_simple_player() -> SimpleVideoPlayer:
    """获取播放器实例"""
    global _simple_player
    if _simple_player is None:
        _simple_player = SimpleVideoPlayer()
    return _simple_player
