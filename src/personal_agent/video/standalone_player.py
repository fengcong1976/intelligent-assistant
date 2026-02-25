"""
独立视频播放器 - 类似于音乐播放器的独立窗口
使用 PyQt6 + ffplay 实现
"""
import sys
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QApplication, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon


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


class VideoPlayerThread(QThread):
    """视频播放后台线程"""
    status_changed = pyqtSignal(str)    # 播放状态变化
    video_finished = pyqtSignal()       # 视频播放完成

    def __init__(self):
        super().__init__()
        self._running = False
        self._current_video = None
        self._is_playing = False

    def run(self):
        """后台线程运行"""
        while self._running:
            self.msleep(500)

    def play_video(self, video_info: VideoInfo):
        """播放视频 - 使用系统默认播放器"""
        self.stop_video()
        
        path = str(video_info.path) if video_info.path else video_info.url
        if not path:
            return False
        
        try:
            logger.info(f"🎬 使用系统默认播放器打开: {path}")
            
            import os
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            
            self._current_video = video_info
            self._is_playing = True
            self.status_changed.emit("playing")
            return True
            
        except Exception as e:
            logger.error(f"播放失败: {e}")
            return False

    def stop_video(self):
        """停止视频"""
        self._is_playing = False
        self.status_changed.emit("stopped")

    def start(self):
        self._running = True
        super().start()

    def stop(self):
        self._running = False
        self.stop_video()
        self.wait()


class StandaloneVideoPlayer(QWidget):
    """独立视频播放器窗口"""
    
    # 信号
    play_requested = pyqtSignal(str)  # 请求播放视频
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_video: Optional[VideoInfo] = None
        self.is_playing = False
        self.playlist: List[VideoInfo] = []
        self.current_index = -1
        self._player_thread: Optional[VideoPlayerThread] = None
        
        self._setup_ui()
        self._setup_player_thread()
        
        self.setWindowTitle("🎬 视频播放器")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

    def _setup_ui(self):
        """设置界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #eee;
            }
            QPushButton {
                border: none;
                border-radius: 25px;
                background-color: #e94560;
                color: white;
                font-size: 16px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c73e54;
            }
            QPushButton:pressed {
                background-color: #a63548;
            }
            QPushButton:disabled {
                background-color: #444;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #e94560;
                border-radius: 8px;
            }
            QListWidget {
                background-color: #16213e;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 5px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #e94560;
            }
            QListWidget::item:hover {
                background-color: #0f3460;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("🎬 视频播放器")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #e94560;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 当前播放信息
        self.info_label = QLabel("未播放")
        self.info_label.setStyleSheet("font-size: 14px; color: #aaa;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        # 播放列表
        playlist_label = QLabel("📁 播放列表")
        playlist_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(playlist_label)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.itemClicked.connect(self._on_playlist_item_clicked)
        layout.addWidget(self.playlist_widget)
        
        # 控制按钮区域
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 打开文件按钮
        self.open_btn = QPushButton("📂 打开文件")
        self.open_btn.setFixedSize(120, 45)
        self.open_btn.clicked.connect(self._on_open_file)
        controls_layout.addWidget(self.open_btn)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setFixedSize(100, 45)
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.setEnabled(False)
        controls_layout.addWidget(self.play_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFixedSize(100, 45)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        # 上一个
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(60, 45)
        self.prev_btn.clicked.connect(self._on_previous)
        controls_layout.addWidget(self.prev_btn)
        
        # 下一个
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(60, 45)
        self.next_btn.clicked.connect(self._on_next)
        controls_layout.addWidget(self.next_btn)
        
        layout.addLayout(controls_layout)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        layout.addWidget(self.progress_slider)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _setup_player_thread(self):
        """设置播放线程"""
        self._player_thread = VideoPlayerThread()
        self._player_thread.status_changed.connect(self._on_status_changed)
        self._player_thread.video_finished.connect(self._on_video_finished)
        self._player_thread.start()

    def _on_status_changed(self, status: str):
        """播放状态变化"""
        self.is_playing = (status == "playing")
        if status == "playing":
            self.play_btn.setText("⏸ 暂停")
            self.status_label.setText("正在播放")
            self.stop_btn.setEnabled(True)
        elif status == "paused":
            self.play_btn.setText("▶️ 继续")
            self.status_label.setText("已暂停")
        elif status == "stopped":
            self.play_btn.setText("▶️ 播放")
            self.status_label.setText("已停止")
            self.stop_btn.setEnabled(False)
            self.progress_slider.setValue(0)

    def _on_video_finished(self):
        """视频播放完成"""
        self.status_label.setText("播放完成")
        # 自动播放下一个
        if self.current_index < len(self.playlist) - 1:
            self._on_next()

    def _on_open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg *.3gp);;所有文件 (*.*)"
        )
        if file_path:
            self.add_video(file_path)

    def _on_play(self):
        """播放/暂停"""
        if not self.current_video:
            return
        
        if self.is_playing:
            # ffplay 不支持真正的暂停，只能停止
            self._player_thread.pause_video()
        else:
            self._player_thread.play_video(self.current_video)

    def _on_stop(self):
        """停止"""
        self._player_thread.stop_video()
        self.stop_requested.emit()

    def _on_previous(self):
        """上一个"""
        if self.current_index > 0:
            self.current_index -= 1
            self._play_at_index(self.current_index)

    def _on_next(self):
        """下一个"""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self._play_at_index(self.current_index)

    def _on_playlist_item_clicked(self, item: QListWidgetItem):
        """播放列表项点击"""
        index = self.playlist_widget.row(item)
        self._play_at_index(index)

    def _play_at_index(self, index: int):
        """播放指定索引的视频"""
        if 0 <= index < len(self.playlist):
            self.current_index = index
            self.current_video = self.playlist[index]
            self._update_info()
            self._player_thread.play_video(self.current_video)
            
            # 更新播放列表选中状态
            self.playlist_widget.setCurrentRow(index)

    def _update_info(self):
        """更新播放信息"""
        if self.current_video:
            self.info_label.setText(f"当前: {self.current_video.title}")
            self.play_btn.setEnabled(True)

    def add_video(self, path: str, title: str = None):
        """添加视频到播放列表"""
        path_obj = Path(path)
        if not path_obj.exists() and not path.startswith("http"):
            logger.warning(f"视频文件不存在: {path}")
            return False
        
        video_info = VideoInfo(
            title=title or path_obj.stem,
            path=path_obj if path_obj.exists() else None,
            url=path if path.startswith("http") else None,
            is_online=path.startswith("http")
        )
        
        self.playlist.append(video_info)
        self.playlist_widget.addItem(video_info.title)
        
        # 如果是第一个视频，自动选中
        if len(self.playlist) == 1:
            self.current_index = 0
            self.current_video = video_info
            self._update_info()
        
        return True

    def play(self, path: str = None, title: str = None):
        """播放视频（外部调用接口）"""
        if path:
            # 检查是否已在播放列表中
            for i, video in enumerate(self.playlist):
                video_path = str(video.path) if video.path else video.url
                if video_path == path:
                    self._play_at_index(i)
                    return True
            
            # 添加到播放列表并播放
            if self.add_video(path, title):
                self._play_at_index(len(self.playlist) - 1)
                return True
            return False
        else:
            # 播放当前视频
            if self.current_video:
                self._player_thread.play_video(self.current_video)
                return True
            return False

    def stop(self):
        """停止播放（外部调用接口）"""
        self._on_stop()

    def closeEvent(self, event):
        """关闭事件"""
        if self._player_thread:
            self._player_thread.stop()
        event.accept()


# 全局播放器实例
_player_instance: Optional[StandaloneVideoPlayer] = None


def get_player_instance() -> Optional[StandaloneVideoPlayer]:
    """获取播放器实例"""
    return _player_instance


def create_player_instance() -> StandaloneVideoPlayer:
    """创建播放器实例"""
    global _player_instance
    if _player_instance is None:
        _player_instance = StandaloneVideoPlayer()
    return _player_instance


def show_player() -> StandaloneVideoPlayer:
    """显示播放器窗口"""
    player = create_player_instance()
    player.show()
    player.raise_()
    player.activateWindow()
    return player
