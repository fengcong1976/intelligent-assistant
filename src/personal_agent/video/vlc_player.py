"""
VLC Embedded Player - 使用 python-vlc 嵌入 VLC 播放器
提供完整的播放控制功能
"""
import sys
import os
import time
import threading
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
from loguru import logger


def _find_vlc_dir() -> Optional[str]:
    """查找 VLC 目录（优先使用项目自带的）"""
    # 首先检查项目目录下的 vlc_libs
    project_dir = Path(__file__).parent.parent.parent.parent
    local_vlc = project_dir / "vlc_libs"
    if local_vlc.exists() and (local_vlc / "libvlc.dll").exists():
        return str(local_vlc)
    
    # 然后检查系统安装的 VLC
    possible_dirs = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        r"D:\Program Files\VideoLAN\VLC",
        r"D:\Program Files (x86)\VideoLAN\VLC",
        r"D:\VideoLAN\VLC",
        r"D:\VLC",
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(os.path.join(dir_path, "libvlc.dll")):
            return dir_path
    
    return None


# 在导入 vlc 之前设置环境变量
_vlc_dir = _find_vlc_dir()
if _vlc_dir:
    # 添加 VLC 目录到 PATH
    os.environ['PATH'] = _vlc_dir + os.pathsep + os.environ.get('PATH', '')
    # 设置 VLC 插件路径
    os.environ['VLC_PLUGIN_PATH'] = os.path.join(_vlc_dir, 'plugins')
    logger.info(f"🎬 使用 VLC 目录: {_vlc_dir}")

try:
    import vlc
    VLC_AVAILABLE = True
except ImportError as e:
    VLC_AVAILABLE = False
    logger.warning(f"⚠️ python-vlc 未安装或 VLC 未找到: {e}")

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QPalette, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("⚠️ PyQt6 未安装，无法使用 VLC 播放器界面")


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


class VLCSignals(QObject):
    """VLC 播放器信号"""
    position_changed = pyqtSignal(float)  # 当前位置（0-1）
    time_changed = pyqtSignal(int)        # 当前时间（毫秒）
    duration_changed = pyqtSignal(int)    # 总时长（毫秒）
    state_changed = pyqtSignal(str)       # 状态变化
    finished = pyqtSignal()               # 播放结束
    error = pyqtSignal(str)               # 错误


class VLCEmbeddedPlayer:
    """VLC 嵌入式播放器"""
    
    def __init__(self):
        self._instance: Optional[vlc.Instance] = None
        self._player: Optional[vlc.MediaPlayer] = None
        self._media: Optional[vlc.Media] = None
        self._is_playing: bool = False
        self._current_video: Optional[VideoInfo] = None
        self._volume: int = 100
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor: bool = False
        
        self.signals = VLCSignals()
        self._init_vlc()
    
    def _init_vlc(self):
        """初始化 VLC"""
        if not VLC_AVAILABLE:
            return
        
        try:
            # 查找 VLC 安装目录并设置环境变量
            vlc_path = self._find_vlc_path()
            if vlc_path:
                vlc_dir = os.path.dirname(vlc_path)
                # 添加 VLC 目录到 PATH
                os.environ['PATH'] = vlc_dir + os.pathsep + os.environ.get('PATH', '')
                # 设置 VLC 插件路径
                os.environ['VLC_PLUGIN_PATH'] = os.path.join(vlc_dir, 'plugins')
                logger.info(f"🎬 使用 VLC: {vlc_path}")
            
            # VLC 选项
            args = [
                '--quiet',  # 安静模式
                '--no-video-title-show',  # 不显示视频标题
            ]
            
            self._instance = vlc.Instance(args)
            self._player = self._instance.media_player_new()
            
            # 设置事件监听
            self._attach_events()
            
            logger.info("✅ VLC 播放器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化 VLC 失败: {e}")
            raise
    
    def _find_vlc_path(self) -> Optional[str]:
        """查找 VLC 路径"""
        # 优先使用项目自带的 VLC
        project_dir = Path(__file__).parent.parent.parent.parent
        local_vlc = project_dir / "vlc_libs" / "libvlc.dll"
        if local_vlc.exists():
            return str(local_vlc)
        
        # 然后检查系统安装的 VLC
        possible_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            r"D:\Program Files\VideoLAN\VLC\vlc.exe",
            r"D:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            r"D:\VideoLAN\VLC\vlc.exe",
            r"D:\VLC\vlc.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _attach_events(self):
        """附加 VLC 事件"""
        if not self._player:
            return
        
        event_manager = self._player.event_manager()
        
        # 播放结束
        event_manager.event_attach(
            vlc.EventType.MediaPlayerEndReached,
            lambda e: self.signals.finished.emit()
        )
        
        # 播放状态变化
        event_manager.event_attach(
            vlc.EventType.MediaPlayerPlaying,
            lambda e: self.signals.state_changed.emit("playing")
        )
        
        event_manager.event_attach(
            vlc.EventType.MediaPlayerPaused,
            lambda e: self.signals.state_changed.emit("paused")
        )
        
        event_manager.event_attach(
            vlc.EventType.MediaPlayerStopped,
            lambda e: self.signals.state_changed.emit("stopped")
        )
        
        event_manager.event_attach(
            vlc.EventType.MediaPlayerEncounteredError,
            lambda e: self.signals.error.emit("播放错误")
        )
    
    def play(self, video_info: VideoInfo) -> bool:
        """播放视频"""
        if not VLC_AVAILABLE or not self._instance:
            logger.error("VLC 不可用")
            return False
        
        try:
            # 停止当前播放
            self.stop()
            
            self._current_video = video_info
            
            # 获取视频路径
            path = str(video_info.path) if video_info.path else video_info.url
            if not path:
                logger.error("视频路径为空")
                return False
            
            # 创建媒体
            self._media = self._instance.media_new(path)
            self._player.set_media(self._media)
            
            # 设置窗口句柄（Windows）
            if sys.platform == "win32" and hasattr(self, '_window_id'):
                self._player.set_hwnd(self._window_id)
            
            # 播放
            result = self._player.play()
            if result == -1:
                logger.error("VLC 播放失败")
                return False
            
            self._is_playing = True
            self._stop_monitor = False
            
            # 恢复音量
            self._player.audio_set_volume(self._volume)
            
            # 启动监控线程
            self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
            self._monitor_thread.start()
            
            logger.info(f"🎬 VLC 开始播放: {video_info.title}")
            return True
            
        except Exception as e:
            logger.error(f"VLC 播放失败: {e}")
            self.signals.error.emit(str(e))
            return False
    
    def _monitor(self):
        """监控播放状态"""
        while not self._stop_monitor and self._is_playing:
            try:
                if self._player:
                    # 获取当前时间
                    current_time = self._player.get_time()
                    if current_time > 0:
                        self.signals.time_changed.emit(current_time)
                    
                    # 获取总时长
                    duration = self._player.get_length()
                    if duration > 0:
                        self.signals.duration_changed.emit(duration)
                        
                        # 计算位置
                        if current_time > 0:
                            position = current_time / duration
                            self.signals.position_changed.emit(position)
                
                time.sleep(0.5)  # 每 500ms 更新一次
                
            except Exception as e:
                logger.debug(f"监控线程错误: {e}")
                break
    
    def pause(self) -> bool:
        """暂停/继续"""
        if self._player:
            self._player.pause()
            return True
        return False
    
    def stop(self):
        """停止播放"""
        self._stop_monitor = True
        self._is_playing = False
        
        if self._player:
            self._player.stop()
        
        logger.info("⏹️ VLC 停止播放")
    
    def set_position(self, position: float):
        """设置播放位置（0.0 - 1.0）"""
        if self._player:
            self._player.set_position(max(0.0, min(1.0, position)))
    
    def set_time(self, time_ms: int):
        """设置播放时间（毫秒）"""
        if self._player:
            self._player.set_time(max(0, time_ms))
    
    def set_volume(self, volume: int):
        """设置音量（0-100）"""
        self._volume = max(0, min(100, volume))
        if self._player:
            self._player.audio_set_volume(self._volume)
    
    def get_volume(self) -> int:
        """获取当前音量"""
        if self._player:
            return self._player.audio_get_volume()
        return self._volume
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        if self._player:
            return self._player.is_playing()
        return False
    
    def get_state(self) -> str:
        """获取播放状态"""
        if not self._player:
            return "stopped"
        
        state = self._player.get_state()
        state_map = {
            vlc.State.Playing: "playing",
            vlc.State.Paused: "paused",
            vlc.State.Stopped: "stopped",
            vlc.State.Ended: "ended",
        }
        return state_map.get(state, "unknown")
    
    def get_duration(self) -> int:
        """获取总时长（毫秒）"""
        if self._player:
            return self._player.get_length()
        return 0
    
    def get_time(self) -> int:
        """获取当前时间（毫秒）"""
        if self._player:
            return self._player.get_time()
        return 0


class VLCPlayerWindow(QMainWindow):
    """VLC 播放器窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VLC 视频播放器")
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        # 创建 VLC 播放器
        self.vlc_player = VLCEmbeddedPlayer()
        self._setup_ui()
        self._connect_signals()
        
        # 定时更新
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(500)
        
        self._is_seeking = False
        self._duration_ms = 0
    
    def _setup_ui(self):
        """设置界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 视频显示区域
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000000;")
        self.video_frame.setMinimumHeight(600)
        layout.addWidget(self.video_frame, stretch=1)
        
        # 设置 VLC 窗口句柄
        if sys.platform == "win32":
            self.vlc_player._window_id = int(self.video_frame.winId())
        
        # 控制面板
        control_widget = QWidget()
        control_widget.setStyleSheet("background-color: #2b2b2b;")
        control_widget.setFixedHeight(120)
        layout.addWidget(control_widget)
        
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(20, 10, 20, 10)
        control_layout.setSpacing(10)
        
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
                background: #e91e63;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -4px 0;
                background: #e91e63;
                border-radius: 7px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.progress_slider.sliderReleased.connect(self._on_seek_end)
        progress_layout.addWidget(self.progress_slider, stretch=1)
        
        control_layout.addLayout(progress_layout)
        
        # 控制按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 停止
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFixedSize(80, 35)
        self.stop_btn.setStyleSheet(self._button_style("#dc3545"))
        self.stop_btn.clicked.connect(self._on_stop)
        buttons_layout.addWidget(self.stop_btn)
        
        # 播放/暂停
        self.play_btn = QPushButton("⏸ 暂停")
        self.play_btn.setFixedSize(80, 35)
        self.play_btn.setStyleSheet(self._button_style("#e91e63"))
        self.play_btn.clicked.connect(self._on_play_pause)
        buttons_layout.addWidget(self.play_btn)
        
        # 音量
        buttons_layout.addSpacing(30)
        
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: #ffffff; font-size: 16px;")
        buttons_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #555555;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #e91e63;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: #e91e63;
                border-radius: 6px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        buttons_layout.addWidget(self.volume_slider)
        
        buttons_layout.addStretch()
        
        # 状态
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        buttons_layout.addWidget(self.status_label)
        
        control_layout.addLayout(buttons_layout)
    
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
        self.vlc_player.signals.position_changed.connect(self._on_position_changed)
        self.vlc_player.signals.time_changed.connect(self._on_time_changed)
        self.vlc_player.signals.duration_changed.connect(self._on_duration_changed)
        self.vlc_player.signals.state_changed.connect(self._on_state_changed)
        self.vlc_player.signals.finished.connect(self._on_finished)
    
    def play(self, video_info: VideoInfo):
        """播放视频"""
        self.setWindowTitle(f"VLC 视频播放器 - {video_info.title}")
        self.status_label.setText("加载中...")
        
        if self.vlc_player.play(video_info):
            self.show()
            self.raise_()
            self.activateWindow()
            return True
        return False
    
    def _on_play_pause(self):
        """播放/暂停"""
        self.vlc_player.pause()
    
    def _on_stop(self):
        """停止"""
        self.vlc_player.stop()
        self.progress_slider.setValue(0)
        self._update_time_label(0, self._duration_ms)
    
    def _on_volume_changed(self, value: int):
        """音量改变"""
        self.vlc_player.set_volume(value)
    
    def _on_seek_start(self):
        """开始拖动"""
        self._is_seeking = True
    
    def _on_seek_end(self):
        """结束拖动"""
        self._is_seeking = False
        position = self.progress_slider.value() / 1000.0
        self.vlc_player.set_position(position)
    
    def _on_position_changed(self, position: float):
        """位置改变"""
        if not self._is_seeking:
            self.progress_slider.setValue(int(position * 1000))
    
    def _on_time_changed(self, time_ms: int):
        """时间改变"""
        self._update_time_label(time_ms, self._duration_ms)
    
    def _on_duration_changed(self, duration_ms: int):
        """时长改变"""
        self._duration_ms = duration_ms
        self._update_time_label(self.vlc_player.get_time(), duration_ms)
    
    def _on_state_changed(self, state: str):
        """状态改变"""
        if state == "playing":
            self.play_btn.setText("⏸ 暂停")
            self.status_label.setText("播放中")
        elif state == "paused":
            self.play_btn.setText("▶ 继续")
            self.status_label.setText("已暂停")
        else:
            self.play_btn.setText("▶ 播放")
            self.status_label.setText("已停止")
    
    def _on_finished(self):
        """播放结束"""
        self.play_btn.setText("▶ 播放")
        self.status_label.setText("播放结束")
        self.progress_slider.setValue(0)
    
    def _update_ui(self):
        """更新 UI"""
        # 更新音量显示
        current_volume = self.vlc_player.get_volume()
        if current_volume != self.volume_slider.value():
            self.volume_slider.setValue(current_volume)
    
    def _update_time_label(self, time_ms: int, duration_ms: int):
        """更新时间标签"""
        time_str = self._format_time(time_ms)
        duration_str = self._format_time(duration_ms)
        self.time_label.setText(f"{time_str} / {duration_str}")
    
    @staticmethod
    def _format_time(ms: int) -> str:
        """格式化时间"""
        seconds = ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def closeEvent(self, event):
        """关闭事件"""
        self.vlc_player.stop()
        event.accept()


class VLCGUIPlayer:
    """VLC GUI 播放器管理类"""
    
    _instance: Optional['VLCGUIPlayer'] = None
    _window: Optional[VLCPlayerWindow] = None
    _app: Optional[QApplication] = None
    _player_thread: Optional[threading.Thread] = None
    _pending_video: Optional[VideoInfo] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def play(self, video_info: VideoInfo) -> str:
        """播放视频 - 在后台线程中启动 GUI"""
        if not VLC_AVAILABLE:
            return "❌ python-vlc 未安装"
        
        if not PYQT_AVAILABLE:
            return "❌ PyQt6 未安装"
        
        try:
            # 保存视频信息
            self._pending_video = video_info
            
            # 如果播放器线程已在运行，直接播放
            if self._player_thread and self._player_thread.is_alive():
                if self._window:
                    self._window.play(video_info)
                return f"▶️ 正在播放: {video_info.title}"
            
            # 在后台线程启动播放器
            self._player_thread = threading.Thread(
                target=self._run_player,
                daemon=True
            )
            self._player_thread.start()
            
            return f"▶️ 正在播放: {video_info.title}\n🎮 播放器窗口已打开"
                
        except Exception as e:
            logger.error(f"VLC GUI 播放器错误: {e}")
            return f"❌ 播放失败: {e}"
    
    def _run_player(self):
        """在独立线程中运行播放器"""
        try:
            # 创建 QApplication
            self._app = QApplication.instance()
            if self._app is None:
                self._app = QApplication(sys.argv)
            
            # 创建窗口
            self._window = VLCPlayerWindow()
            
            # 播放视频
            if self._pending_video:
                self._window.play(self._pending_video)
            
            # 运行事件循环
            self._app.exec()
            
        except Exception as e:
            logger.error(f"播放器线程错误: {e}")
    
    def _ensure_window(self) -> bool:
        """确保窗口已创建"""
        if self._window is None:
            logger.warning("播放器窗口未创建")
            return False
        return True
    
    def pause(self) -> str:
        """暂停/继续"""
        if not self._ensure_window():
            return "❌ 播放器未启动"
        self._window.vlc_player.pause()
        return "⏸️ 已暂停/继续"
    
    def stop(self) -> str:
        """停止"""
        if not self._ensure_window():
            return "❌ 播放器未启动"
        self._window.vlc_player.stop()
        return "⏹️ 已停止"
    
    def set_volume(self, volume: int) -> str:
        """设置音量"""
        if not self._ensure_window():
            return "❌ 播放器未启动"
        self._window.vlc_player.set_volume(volume)
        return f"🔊 音量设置为 {volume}%"
    
    def get_status(self) -> dict:
        """获取状态"""
        if not self._ensure_window():
            return {"playing": False}
        return {
            "playing": self._window.vlc_player.is_playing(),
            "state": self._window.vlc_player.get_state(),
            "time": self._window.vlc_player.get_time(),
            "duration": self._window.vlc_player.get_duration(),
            "volume": self._window.vlc_player.get_volume()
        }


# 全局实例
_vlc_gui_player: Optional[VLCGUIPlayer] = None


def get_vlc_gui_player() -> VLCGUIPlayer:
    """获取 VLC GUI 播放器实例"""
    global _vlc_gui_player
    if _vlc_gui_player is None:
        _vlc_gui_player = VLCGUIPlayer()
    return _vlc_gui_player
