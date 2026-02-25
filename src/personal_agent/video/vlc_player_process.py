"""
VLC Player Process - 独立进程运行 VLC 播放器
使用 multiprocessing 在独立进程中运行 PyQt6 界面
"""
import sys
import os
import time
import multiprocessing
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from loguru import logger


def _find_vlc_dir() -> Optional[str]:
    """查找 VLC 目录"""
    project_dir = Path(__file__).parent.parent.parent.parent
    local_vlc = project_dir / "vlc_libs"
    if local_vlc.exists() and (local_vlc / "libvlc.dll").exists():
        return str(local_vlc)
    
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


# 设置 VLC 环境变量
_vlc_dir = _find_vlc_dir()
if _vlc_dir:
    os.environ['PATH'] = _vlc_dir + os.pathsep + os.environ.get('PATH', '')
    os.environ['VLC_PLUGIN_PATH'] = os.path.join(_vlc_dir, 'plugins')


try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


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


class VLCSignals(QObject):
    """VLC 信号"""
    position_changed = pyqtSignal(float)
    time_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)


class VLCEmbeddedPlayer:
    """VLC 嵌入式播放器"""
    
    def __init__(self):
        self._instance: Optional[vlc.Instance] = None
        self._player: Optional[vlc.MediaPlayer] = None
        self._media: Optional[vlc.Media] = None
        self._volume: int = 100
        self.signals = VLCSignals()
        self._init_vlc()
    
    def _init_vlc(self):
        """初始化 VLC"""
        if not VLC_AVAILABLE:
            return
        
        try:
            # VLC 选项 - 使用 Windows GDI 视频输出（最兼容）
            args = [
                '--quiet',
                '--no-video-title-show',
                '--video-on-top',
                '--vout=wingdi',  # Windows GDI 视频输出
                '--no-overlay',   # 禁用覆盖层
            ]
            self._instance = vlc.Instance(args)
            self._player = self._instance.media_player_new()
            self._attach_events()
            logger.info("✅ VLC 播放器初始化成功")
        except Exception as e:
            logger.error(f"初始化 VLC 失败: {e}")
            raise
    
    def _attach_events(self):
        """附加事件"""
        if not self._player:
            return
        
        event_manager = self._player.event_manager()
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
    
    def play(self, video_info: VideoInfo) -> bool:
        """播放视频"""
        if not VLC_AVAILABLE or not self._instance:
            return False
        
        try:
            self.stop()
            
            path = str(video_info.path) if video_info.path else video_info.url
            if not path:
                return False
            
            self._media = self._instance.media_new(path)
            self._player.set_media(self._media)
            
            # 解析媒体以获取信息
            self._media.parse()
            
            # 开始播放
            result = self._player.play()
            if result == -1:
                logger.error("VLC play() 返回 -1")
                return False
            
            self._player.audio_set_volume(self._volume)
            logger.info(f"🎬 VLC 开始播放: {video_info.title}")
            return True
            
        except Exception as e:
            logger.error(f"VLC 播放失败: {e}")
            return False
    
    def stop(self):
        """停止"""
        if self._player:
            self._player.stop()
    
    def pause(self):
        """暂停/继续"""
        if self._player:
            self._player.pause()
    
    def set_position(self, position: float):
        """设置位置"""
        if self._player:
            self._player.set_position(max(0.0, min(1.0, position)))
    
    def set_volume(self, volume: int):
        """设置音量"""
        self._volume = max(0, min(100, volume))
        if self._player:
            self._player.audio_set_volume(self._volume)
    
    def get_volume(self) -> int:
        """获取音量"""
        if self._player:
            return self._player.audio_get_volume()
        return self._volume
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._player.is_playing() if self._player else False
    
    def get_time(self) -> int:
        """获取当前时间"""
        return self._player.get_time() if self._player else 0
    
    def get_duration(self) -> int:
        """获取总时长"""
        return self._player.get_length() if self._player else 0
    
    def set_hwnd(self, hwnd: int):
        """设置窗口句柄"""
        if self._player and sys.platform == "win32":
            try:
                # 使用 ctypes 设置窗口句柄
                import ctypes
                self._player.set_hwnd(hwnd)
                logger.info(f"✅ VLC 窗口句柄设置成功: {hwnd}")
            except Exception as e:
                logger.error(f"设置 VLC 窗口句柄失败: {e}")


class VLCPlayerWindow(QMainWindow):
    """VLC 播放器窗口"""
    
    def __init__(self, video_info: VideoInfo):
        super().__init__()
        self.video_info = video_info
        self.setWindowTitle(f"VLC 视频播放器 - {video_info.title}")
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        self.vlc_player = VLCEmbeddedPlayer()
        self._setup_ui()
        self._connect_signals()
        
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
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFixedSize(80, 35)
        self.stop_btn.setStyleSheet(self._button_style("#dc3545"))
        self.stop_btn.clicked.connect(self._on_stop)
        buttons_layout.addWidget(self.stop_btn)
        
        self.play_btn = QPushButton("⏸ 暂停")
        self.play_btn.setFixedSize(80, 35)
        self.play_btn.setStyleSheet(self._button_style("#e91e63"))
        self.play_btn.clicked.connect(self._on_play_pause)
        buttons_layout.addWidget(self.play_btn)
        
        buttons_layout.addSpacing(30)
        
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: #ffffff; font-size: 16px;")
        buttons_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        buttons_layout.addWidget(self.volume_slider)
        
        buttons_layout.addStretch()
        
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
        self.vlc_player.signals.state_changed.connect(self._on_state_changed)
    
    def play(self):
        """播放"""
        self.status_label.setText("加载中...")
        
        # 确保窗口已显示后再设置句柄
        self.show()
        self.raise_()
        self.activateWindow()
        
        # 等待窗口渲染完成
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._do_play)
        return True
    
    def _do_play(self):
        """实际开始播放"""
        # 设置 VLC 窗口句柄（必须在窗口显示后）
        if sys.platform == "win32":
            hwnd = int(self.video_frame.winId())
            self.vlc_player.set_hwnd(hwnd)
            logger.info(f"🎬 设置 VLC 窗口句柄: {hwnd}")
        
        # 开始播放
        if not self.vlc_player.play(self.video_info):
            self.status_label.setText("播放失败")
    
    def _on_play_pause(self):
        """播放/暂停"""
        self.vlc_player.pause()
    
    def _on_stop(self):
        """停止"""
        self.vlc_player.stop()
    
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
    
    def _update_ui(self):
        """更新 UI"""
        if not self.vlc_player.is_playing():
            return
        
        # 更新时间
        time_ms = self.vlc_player.get_time()
        duration_ms = self.vlc_player.get_duration()
        
        if duration_ms > 0:
            self._duration_ms = duration_ms
            if not self._is_seeking:
                position = time_ms / duration_ms
                self.progress_slider.setValue(int(position * 1000))
        
        self._update_time_label(time_ms, duration_ms)
        
        # 更新音量
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


def run_player_process(video_data: Dict[str, Any]):
    """在独立进程中运行播放器"""
    try:
        video_info = VideoInfo(**video_data)
        
        app = QApplication(sys.argv)
        window = VLCPlayerWindow(video_info)
        window.play()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"播放器进程错误: {e}")
        sys.exit(1)


class VLCPlayerProcess:
    """VLC 播放器进程管理"""
    
    _instance: Optional['VLCPlayerProcess'] = None
    _process: Optional[multiprocessing.Process] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def play(self, video_info: VideoInfo) -> str:
        """播放视频 - 在独立进程中启动"""
        if not VLC_AVAILABLE:
            return "❌ python-vlc 未安装"
        
        if not PYQT_AVAILABLE:
            return "❌ PyQt6 未安装"
        
        try:
            # 停止之前的进程
            self.stop()
            
            # 准备视频数据
            video_data = {
                'title': video_info.title,
                'url': video_info.url,
                'path': str(video_info.path) if video_info.path else None,
                'duration': video_info.duration,
                'width': video_info.width,
                'height': video_info.height,
                'is_online': video_info.is_online
            }
            
            # 创建新进程
            self._process = multiprocessing.Process(
                target=run_player_process,
                args=(video_data,),
                daemon=True
            )
            self._process.start()
            
            return f"▶️ 正在播放: {video_info.title}\n🎮 播放器窗口已打开"
            
        except Exception as e:
            logger.error(f"启动播放器进程失败: {e}")
            return f"❌ 播放失败: {e}"
    
    def stop(self):
        """停止播放器"""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)
            if self._process.is_alive():
                self._process.kill()
        self._process = None
        return "⏹️ 已停止"


# 全局实例
_vlc_player_process: Optional[VLCPlayerProcess] = None


def get_vlc_player_process() -> VLCPlayerProcess:
    """获取 VLC 播放器进程实例"""
    global _vlc_player_process
    if _vlc_player_process is None:
        _vlc_player_process = VLCPlayerProcess()
    return _vlc_player_process
