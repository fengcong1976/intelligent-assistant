"""
FFplay Player with GUI - 使用 ffplay 作为后端，PyQt6 作为界面
"""
import sys
import os
import subprocess
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("⚠️ PyQt6 未安装")


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


class FFplaySignals(QObject):
    """信号"""
    state_changed = pyqtSignal(str)
    finished = pyqtSignal()


class FFplayPlayer:
    """FFplay 播放器"""
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None
        self._title: str = "视频播放"
        self._volume: int = 100
        self._is_playing: bool = False
        self._window_id: Optional[int] = None
        self.signals = FFplaySignals()
    
    def play(self, video_info: VideoInfo) -> bool:
        """播放视频"""
        try:
            self.stop()
            
            path = str(video_info.path) if video_info.path else video_info.url
            if not path:
                return False
            
            self._current_path = path
            self._title = video_info.title
            
            # 构建 ffplay 命令
            cmd = [
                "ffplay",
                "-window_title", self._title,
                "-x", "1280",
                "-y", "720",
                "-autoexit",
                "-volume", str(self._volume),
                "-tls_verify", "0",  # 忽略 SSL 证书验证
                "-timeout", "10000000",  # 设置超时（微秒）
            ]
            
            # 如果有窗口句柄，尝试嵌入（ffplay 不直接支持，但我们可以控制窗口位置）
            cmd.append(path)
            
            logger.info(f"🎬 FFplay 播放命令: {' '.join(cmd)}")
            
            # 启动 ffplay（不捕获输出，让它直接显示窗口）
            if sys.platform == "win32":
                # Windows: 使用 STARTUPINFO 隐藏控制台窗口
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_SHOWNORMAL
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo
                )
            else:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            self._is_playing = True
            self.signals.state_changed.emit("playing")
            
            # 监控线程
            threading.Thread(target=self._monitor, daemon=True).start()
            
            return True
            
        except Exception as e:
            logger.error(f"FFplay 播放失败: {e}")
            return False
    
    def _monitor(self):
        """监控播放状态"""
        if self._process:
            self._process.wait()
            self._is_playing = False
            self.signals.state_changed.emit("stopped")
            self.signals.finished.emit()
    
    def stop(self):
        """停止"""
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
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing and self._process is not None


class FFplayPlayerWindow(QMainWindow):
    """FFplay 播放器控制窗口"""
    
    def __init__(self, video_info: VideoInfo):
        super().__init__()
        self.video_info = video_info
        self.setWindowTitle(f"视频播放器 - {video_info.title}")
        self.setGeometry(100, 850, 1280, 150)
        self.setStyleSheet("background-color: #2b2b2b;")
        
        self.ffplay = FFplayPlayer()
        self._setup_ui()
        self._connect_signals()
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(500)
    
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        
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
        progress_layout.addWidget(self.progress_slider, stretch=1)
        
        layout.addLayout(progress_layout)
        
        # 控制按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFixedSize(80, 35)
        self.stop_btn.setStyleSheet(self._button_style("#dc3545"))
        self.stop_btn.clicked.connect(self._on_stop)
        buttons_layout.addWidget(self.stop_btn)
        
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setFixedSize(80, 35)
        self.play_btn.setStyleSheet(self._button_style("#e91e63"))
        self.play_btn.clicked.connect(self._on_play)
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
        
        layout.addLayout(buttons_layout)
    
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
        self.ffplay.signals.state_changed.connect(self._on_state_changed)
        self.ffplay.signals.finished.connect(self._on_finished)
    
    def play(self):
        """播放"""
        self.status_label.setText("加载中...")
        if self.ffplay.play(self.video_info):
            self.show()
            self.raise_()
            self.activateWindow()
            return True
        self.status_label.setText("播放失败")
        return False
    
    def _on_play(self):
        """播放按钮"""
        if not self.ffplay.is_playing():
            self.ffplay.play(self.video_info)
    
    def _on_stop(self):
        """停止"""
        self.ffplay.stop()
    
    def _on_volume_changed(self, value: int):
        """音量改变 - ffplay 不支持运行时调整"""
        pass
    
    def _on_state_changed(self, state: str):
        """状态改变"""
        if state == "playing":
            self.play_btn.setText("⏸ 暂停")
            self.status_label.setText("播放中")
        else:
            self.play_btn.setText("▶ 播放")
            self.status_label.setText("已停止")
    
    def _on_finished(self):
        """播放结束"""
        self.play_btn.setText("▶ 播放")
        self.status_label.setText("播放结束")
    
    def _update_ui(self):
        """更新 UI"""
        # ffplay 不提供进度信息，这里只是模拟
        pass
    
    def closeEvent(self, event):
        """关闭事件"""
        self.ffplay.stop()
        event.accept()


def run_player_process(video_data: Dict[str, Any]):
    """在独立进程中运行播放器"""
    try:
        video_info = VideoInfo(**video_data)
        
        app = QApplication(sys.argv)
        window = FFplayPlayerWindow(video_info)
        window.play()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"播放器进程错误: {e}")
        sys.exit(1)


class FFplayGUIPlayer:
    """FFplay GUI 播放器管理"""
    
    _instance: Optional['FFplayGUIPlayer'] = None
    _process: Optional[subprocess.Popen] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def play(self, video_info: VideoInfo) -> str:
        """播放视频"""
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
            
            # 使用 multiprocessing 创建独立进程
            import multiprocessing
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
_ffplay_gui_player: Optional[FFplayGUIPlayer] = None


def get_ffplay_gui_player() -> FFplayGUIPlayer:
    """获取 FFplay GUI 播放器实例"""
    global _ffplay_gui_player
    if _ffplay_gui_player is None:
        _ffplay_gui_player = FFplayGUIPlayer()
    return _ffplay_gui_player
