"""
Video GUI Player - 基于 FFmpeg 的 GUI 视频播放器
使用 PyQt6 构建控制界面，FFplay 作为视频显示窗口
"""
import sys
import subprocess
import threading
import time
import re
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass
from loguru import logger

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("⚠️ PyQt6 未安装，无法使用 GUI 视频播放器")


@dataclass
class VideoInfo:
    """视频信息"""
    title: str
    path: Optional[Path] = None
    url: Optional[str] = None
    duration: float = 0  # 秒
    width: int = 0
    height: int = 0
    is_online: bool = False


class PlayerSignals(QObject):
    """播放器信号"""
    position_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    state_changed = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)


class FFmpegPlayer:
    """FFmpeg 播放器 - 管理 ffplay 进程"""
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None
        self._duration: float = 0
        self._position: float = 0
        self._is_playing: bool = False
        self._volume: float = 1.0
        self._title: str = "视频播放"
        self.signals = PlayerSignals()
        
    def play(self, path: str, title: str = "视频播放"):
        """播放视频"""
        self._current_path = path
        self._title = title
        
        # 停止之前的播放
        self.stop()
        
        # 获取视频信息
        self._get_video_info(path)
        
        # 启动 ffplay
        cmd = [
            "ffplay",
            "-window_title", self._title,
            "-x", "1280",
            "-y", "720",
            "-autoexit",
            "-volume", str(int(self._volume * 100)),
            path
        ]
        
        logger.info(f"🎬 FFmpeg 播放命令: {' '.join(cmd)}")
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            self._is_playing = True
            self.signals.state_changed.emit("playing")
            
            # 在后台线程监控播放状态
            threading.Thread(target=self._monitor, daemon=True).start()
            
        except Exception as e:
            logger.error(f"启动 FFmpeg 失败: {e}")
            self.signals.error.emit(str(e))
    
    def _monitor(self):
        """监控播放状态"""
        if self._process:
            self._process.wait()
            self._is_playing = False
            if self._process.returncode == 0:
                self.signals.finished.emit()
            else:
                stderr = self._process.stderr.read() if self._process.stderr else ""
                if stderr:
                    logger.debug(f"FFmpeg stderr: {stderr[:200]}")
            self.signals.state_changed.emit("stopped")
    
    def _get_video_info(self, path: str):
        """获取视频信息"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                try:
                    self._duration = float(result.stdout.strip())
                    self.signals.duration_changed.emit(self._duration)
                except ValueError:
                    pass
        except Exception as e:
            logger.warning(f"获取视频信息失败: {e}")
    
    def stop(self):
        """停止播放"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except:
                self._process.kill()
            finally:
                self._process = None
        self._is_playing = False
        self.signals.state_changed.emit("stopped")
    
    def set_volume(self, volume: float):
        """设置音量（0.0 - 1.0）"""
        self._volume = max(0.0, min(1.0, volume))
        # ffplay 不支持运行时调整音量，需要重启
    
    @property
    def is_playing(self) -> bool:
        return self._is_playing
    
    @property
    def duration(self) -> float:
        return self._duration


class VideoControlPanel(QWidget):
    """视频控制面板"""
    
    def __init__(self, player: FFmpegPlayer):
        super().__init__()
        self.player = player
        self._setup_ui()
        self._connect_signals()
        
        # 定时更新
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(500)  # 每500ms更新
        
        self._current_position = 0
        self._is_seeking = False
        
    def _setup_ui(self):
        """设置界面"""
        self.setWindowTitle("视频控制面板")
        self.setGeometry(100, 850, 1280, 150)
        self.setStyleSheet("background-color: #2b2b2b;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        # 进度条
        progress_layout = QHBoxLayout()
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        progress_layout.addWidget(self.time_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #555555;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #10a37f;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -4px 0;
                background: #10a37f;
                border-radius: 7px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.progress_slider.sliderReleased.connect(self._on_seek_end)
        progress_layout.addWidget(self.progress_slider, stretch=1)
        
        layout.addLayout(progress_layout)
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 停止
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFixedSize(80, 35)
        self.stop_btn.setStyleSheet(self._button_style("#dc3545"))
        self.stop_btn.clicked.connect(self._on_stop)
        controls_layout.addWidget(self.stop_btn)
        
        # 播放/暂停（ffplay 不支持真正的暂停，只是重新播放）
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setFixedSize(80, 35)
        self.play_btn.setStyleSheet(self._button_style("#10a37f"))
        self.play_btn.clicked.connect(self._on_play)
        controls_layout.addWidget(self.play_btn)
        
        # 音量
        controls_layout.addSpacing(30)
        
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: #ffffff; font-size: 16px;")
        controls_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #555555;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #10a37f;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: #10a37f;
                border-radius: 6px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.volume_slider)
        
        controls_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        controls_layout.addWidget(self.status_label)
        
        layout.addLayout(controls_layout)
    
    def _button_style(self, color: str) -> str:
        """按钮样式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """
    
    def _connect_signals(self):
        """连接信号"""
        self.player.signals.state_changed.connect(self._on_state_changed)
        self.player.signals.duration_changed.connect(self._on_duration_changed)
        self.player.signals.finished.connect(self._on_finished)
    
    def _on_play(self):
        """播放按钮"""
        if not self.player.is_playing:
            self.status_label.setText("请重新发送视频链接播放")
    
    def _on_stop(self):
        """停止按钮"""
        self.player.stop()
    
    def _on_volume_changed(self, value: int):
        """音量改变"""
        volume = value / 100.0
        self.player.set_volume(volume)
    
    def _on_seek_start(self):
        """开始拖动"""
        self._is_seeking = True
    
    def _on_seek_end(self):
        """结束拖动"""
        self._is_seeking = False
        # 注意：ffplay 不支持运行时跳转，需要重新启动
        # 这里只是显示位置
    
    def _on_state_changed(self, state: str):
        """状态改变"""
        if state == "playing":
            self.play_btn.setText("⏸ 暂停")
            self.status_label.setText("播放中")
        else:
            self.play_btn.setText("▶ 播放")
            self.status_label.setText("已停止")
    
    def _on_duration_changed(self, duration: float):
        """时长改变"""
        self._update_time_label(0, duration)
    
    def _on_finished(self):
        """播放结束"""
        self.progress_slider.setValue(0)
        self._update_time_label(0, self.player.duration)
    
    def _update_ui(self):
        """更新 UI"""
        # 模拟进度更新（ffplay 不提供实时进度）
        if self.player.is_playing and self.player.duration > 0:
            # 这里只是模拟，实际 ffplay 不提供进度信息
            pass
    
    def _update_time_label(self, position: float, duration: float):
        """更新时间标签"""
        pos_str = self._format_time(position)
        dur_str = self._format_time(duration)
        self.time_label.setText(f"{pos_str} / {dur_str}")
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


class VideoGUIPlayer:
    """视频 GUI 播放器管理类"""
    
    _instance: Optional['VideoGUIPlayer'] = None
    _control_panel: Optional[VideoControlPanel] = None
    _player: Optional[FFmpegPlayer] = None
    _app: Optional[QApplication] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def play(self, video_info: VideoInfo) -> str:
        """播放视频"""
        if not PYQT_AVAILABLE:
            return "❌ PyQt6 未安装，无法使用 GUI 播放器"
        
        try:
            # 确保在主线程中创建 QApplication
            if self._app is None:
                self._app = QApplication.instance()
                if self._app is None:
                    self._app = QApplication(sys.argv)
            
            # 创建播放器
            if self._player is None:
                self._player = FFmpegPlayer()
            
            # 创建控制面板
            if self._control_panel is None:
                self._control_panel = VideoControlPanel(self._player)
            
            # 播放视频
            path = str(video_info.path) if video_info.path else video_info.url
            if not path:
                return "❌ 视频路径为空"
            
            self._player.play(path, video_info.title)
            
            # 显示控制面板
            self._control_panel.show()
            self._control_panel.raise_()
            self._control_panel.activateWindow()
            
            return f"▶️ 正在播放: {video_info.title}\n🎮 控制面板已打开"
            
        except Exception as e:
            logger.error(f"GUI 播放器错误: {e}")
            return f"❌ 播放失败: {e}"
    
    def stop(self) -> str:
        """停止播放"""
        if self._player:
            self._player.stop()
            return "⏹️ 已停止播放"
        return "❌ 播放器未启动"
    
    def get_status(self) -> dict:
        """获取状态"""
        if self._player:
            return {
                "playing": self._player.is_playing,
                "duration": self._player.duration
            }
        return {"playing": False}


# 全局播放器实例
_video_gui_player: Optional[VideoGUIPlayer] = None


def get_video_gui_player() -> VideoGUIPlayer:
    """获取视频 GUI 播放器实例"""
    global _video_gui_player
    if _video_gui_player is None:
        _video_gui_player = VideoGUIPlayer()
    return _video_gui_player
