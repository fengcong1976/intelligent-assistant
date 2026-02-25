"""
Music Player Widget - 音乐播放器控制台
"""
import asyncio
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QSlider, QFrame,
    QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon
from loguru import logger


class MusicPlayerThread(QThread):
    """音乐播放后台线程"""
    position_changed = pyqtSignal(int)  # 播放位置变化
    status_changed = pyqtSignal(str)    # 播放状态变化
    song_finished = pyqtSignal()        # 歌曲播放完成

    def __init__(self):
        super().__init__()
        self._running = False
        self._current_song = None
        self._is_playing = False

    def run(self):
        """后台线程运行"""
        while self._running:
            if self._is_playing:
                # 模拟播放进度更新
                self.position_changed.emit(0)
            self.msleep(1000)

    def start_playback(self):
        self._is_playing = True
        self.status_changed.emit("playing")

    def pause_playback(self):
        self._is_playing = False
        self.status_changed.emit("paused")

    def stop_playback(self):
        self._is_playing = False
        self.status_changed.emit("stopped")

    def stop(self):
        self._running = False
        self.wait()


class MusicPlayerWidget(QWidget):
    """音乐播放器控制台界面"""

    # 信号
    play_requested = pyqtSignal(str)  # 请求播放歌曲
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_song = None
        self.is_playing = False
        self.playlist: List[Dict] = []
        self.current_index = -1

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        """设置界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
            QPushButton {
                border: none;
                border-radius: 25px;
                background-color: #07c160;
                color: white;
                font-size: 16px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #06ad56;
            }
            QPushButton:pressed {
                background-color: #059a4c;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #07c160;
            }
            QListWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: #07c160;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #07c160;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                background: #07c160;
                border-radius: 8px;
                margin: -5px 0;
            }
            QLabel {
                color: #333;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel("🎵 音乐播放器")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #07c160;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索歌曲、歌手...")
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍 搜索")
        search_btn.setFixedWidth(100)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # 当前播放信息
        self.current_frame = QFrame()
        self.current_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        current_layout = QVBoxLayout(self.current_frame)

        self.song_label = QLabel("暂无播放")
        self.song_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.song_label)

        self.artist_label = QLabel("-")
        self.artist_label.setStyleSheet("font-size: 14px; color: #666;")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.artist_label)

        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        current_layout.addWidget(self.progress_slider)

        # 时间显示
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #999;")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #999;")
        time_layout.addWidget(self.total_time_label)
        current_layout.addLayout(time_layout)

        layout.addWidget(self.current_frame)

        # 控制按钮
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        controls_layout.addStretch()

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(50, 50)
        self.prev_btn.setStyleSheet("font-size: 20px; border-radius: 25px;")
        self.prev_btn.clicked.connect(self._on_prev)
        controls_layout.addWidget(self.prev_btn)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(70, 70)
        self.play_btn.setStyleSheet("font-size: 28px; border-radius: 35px;")
        self.play_btn.clicked.connect(self._on_play_pause)
        controls_layout.addWidget(self.play_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(50, 50)
        self.next_btn.setStyleSheet("font-size: 20px; border-radius: 25px;")
        self.next_btn.clicked.connect(self._on_next)
        controls_layout.addWidget(self.next_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(50, 50)
        self.stop_btn.setStyleSheet("font-size: 20px; border-radius: 25px; background-color: #ff4444;")
        self.stop_btn.clicked.connect(self._on_stop)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # 音乐源说明
        source_frame = QFrame()
        source_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        source_layout = QVBoxLayout(source_frame)

        source_label = QLabel("🎵 免费网络音乐")
        source_label.setStyleSheet("font-size: 14px; color: #666;")
        source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_layout.addWidget(source_label)

        source_hint = QLabel("使用免费网络音乐资源，无需登录")
        source_hint.setStyleSheet("font-size: 12px; color: #999;")
        source_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_layout.addWidget(source_hint)

        layout.addWidget(source_frame)

        # 播放列表
        playlist_label = QLabel("📋 播放列表")
        playlist_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(playlist_label)

        self.playlist_widget = QListWidget()
        self.playlist_widget.itemClicked.connect(self._on_playlist_item_clicked)
        layout.addWidget(self.playlist_widget)

        # 音量控制
        volume_layout = QHBoxLayout()
        volume_icon = QLabel("🔊")
        volume_layout.addWidget(volume_icon)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)

        self.volume_label = QLabel("80%")
        self.volume_label.setFixedWidth(40)
        volume_layout.addWidget(self.volume_label)

        layout.addLayout(volume_layout)

    def _setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_progress)
        self.update_timer.start(1000)  # 每秒更新一次

    def _on_search(self):
        """搜索歌曲"""
        keyword = self.search_input.text().strip()
        if keyword:
            self.play_requested.emit(f"search:{keyword}")

    def _on_play_pause(self):
        """播放/暂停"""
        if self.is_playing:
            self.pause_requested.emit()
        else:
            if self.current_song:
                self.play_requested.emit(f"play:{self.current_song}")
            else:
                # 播放播放列表第一首
                if self.playlist:
                    self._play_index(0)

    def _on_stop(self):
        """停止"""
        self.stop_requested.emit()

    def _on_next(self):
        """下一首"""
        self.next_requested.emit()

    def _on_prev(self):
        """上一首"""
        self.prev_requested.emit()

    def _on_volume_changed(self, value):
        """音量改变"""
        self.volume_label.setText(f"{value}%")

    def _on_playlist_item_clicked(self, item):
        """播放列表项点击"""
        index = self.playlist_widget.row(item)
        self._play_index(index)

    def _play_index(self, index):
        """播放指定索引的歌曲"""
        if 0 <= index < len(self.playlist):
            self.current_index = index
            song = self.playlist[index]
            self.play_requested.emit(f"play:{song.get('name', '')}")

    def _update_progress(self):
        """更新播放进度"""
        if self.is_playing and self.progress_slider.isEnabled():
            value = self.progress_slider.value()
            if value < self.progress_slider.maximum():
                self.progress_slider.setValue(value + 1)
                self._update_time_labels()

    def _update_time_labels(self):
        """更新时间标签"""
        current = self.progress_slider.value()
        total = self.progress_slider.maximum()
        self.current_time_label.setText(self._format_time(current))
        self.total_time_label.setText(self._format_time(total))

    def _format_time(self, seconds):
        """格式化时间"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    def set_current_song(self, name: str, artist: str = ""):
        """设置当前播放歌曲"""
        self.current_song = name
        self.song_label.setText(name)
        self.artist_label.setText(artist if artist else "未知歌手")

    def set_playing(self, playing: bool):
        """设置播放状态"""
        self.is_playing = playing
        if playing:
            self.play_btn.setText("⏸")
            self.progress_slider.setEnabled(True)
        else:
            self.play_btn.setText("▶")

    def set_progress(self, current: int, total: int):
        """设置播放进度"""
        self.progress_slider.setRange(0, total)
        self.progress_slider.setValue(current)
        self._update_time_labels()

    def add_to_playlist(self, song_info: Dict):
        """添加到播放列表"""
        self.playlist.append(song_info)
        item = QListWidgetItem(f"{song_info.get('name', '未知')} - {song_info.get('artist', '未知歌手')}")
        self.playlist_widget.addItem(item)

    def clear_playlist(self):
        """清空播放列表"""
        self.playlist.clear()
        self.playlist_widget.clear()
        self.current_index = -1

    def show_message(self, message: str):
        """显示消息"""
        self.song_label.setText(message)
        self.artist_label.setText("")


