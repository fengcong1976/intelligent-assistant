"""
Music Player Widget - 专业音乐播放器界面
"""
import sys
from pathlib import Path
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSlider, QComboBox, QGroupBox,
    QSplitter, QFrame, QScrollArea, QMenu, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QAction
from loguru import logger

from .player import MusicPlayer, PlayMode, Song, Playlist


class ScanThread(QThread):
    """后台扫描线程"""
    finished = pyqtSignal(object)
    
    def __init__(self, player, force: bool = False):
        super().__init__()
        self.player = player
        self.force = force
    
    def run(self):
        songs = self.player.scan_music_library(force=self.force)
        self.finished.emit(songs)


class MusicPlayerWidget(QWidget):
    """专业音乐播放器界面"""
    
    song_changed = pyqtSignal(dict)
    state_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, player: MusicPlayer = None):
        super().__init__(parent)
        from ..config import settings
        music_library = settings.directory.get_music_library()
        self.player = player if player else MusicPlayer(music_library=music_library)
        self._cached_songs = self.player.get_cached_songs()
        self._init_ui()
        self._connect_signals()
        self._start_timer()
        self._restore_state()
        
        self.setMinimumSize(900, 600)
        logger.info("🎵 音乐播放器界面已初始化")
    
    def showEvent(self, event):
        """窗口显示时同步当前播放状态"""
        super().showEvent(event)
        self._sync_current_state()
    
    def _sync_current_state(self):
        """同步当前播放状态"""
        if self.player.current_song:
            current_song = self.player.current_song
            for i, song in enumerate(self._cached_songs):
                if song.path == current_song.path:
                    if self.player.current_song_index != i:
                        self.player.current_song_index = i
                    self.song_list.setCurrentRow(i)
                    break
            self._update_now_playing()
            self.play_btn.setText("⏸" if self.player.is_playing else "▶")
    
    def closeEvent(self, event):
        """关闭事件 - 只关闭窗口，不停止音乐"""
        self.player._save_data()
        event.accept()
        self.deleteLater()
    
    def _restore_state(self):
        """恢复上次状态"""
        if self._cached_songs:
            self._refresh_song_list(self._cached_songs)
            self._update_stats()
            
            last_song = self.player.get_last_played_song()
            if last_song:
                logger.info(f"🎵 恢复上次播放: {last_song.title}")
                self.player.current_song = last_song
                
                for i, song in enumerate(self._cached_songs):
                    if song.path == last_song.path:
                        self.player.current_song_index = i
                        self.song_list.setCurrentRow(i)
                        break
                
                self._update_now_playing()
        else:
            self._initial_scan()
    
    def _initial_scan(self):
        """初始化时后台扫描"""
        self.scan_thread = ScanThread(self.player)
        self.scan_thread.finished.connect(self._on_initial_scan_finished)
        self.scan_thread.start()
    
    def _on_initial_scan_finished(self, songs):
        """初始扫描完成"""
        self._cached_songs = songs
        self._refresh_song_list(songs)
        self._update_stats()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板 - 播放列表
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 播放控制和音乐库
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([250, 650])
        layout.addWidget(splitter)
        
        # 底部播放控制栏
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板 - 播放列表"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("🎵 播放列表")
        title.setStyleSheet("""
            QLabel {
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        layout.addWidget(title)
        
        # 播放列表选择
        self.playlist_combo = QComboBox()
        self.playlist_combo.setStyleSheet("""
            QComboBox {
                background-color: #16213e;
                color: #fff;
                border: 1px solid #0f3460;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #e94560;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #fff;
                selection-background-color: #e94560;
            }
        """)
        self.playlist_combo.addItem("所有歌曲", "all")
        self._refresh_playlists()
        layout.addWidget(self.playlist_combo)
        
        # 歌曲列表
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                color: #fff;
                border: none;
                border-radius: 5px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #0f3460;
            }
            QListWidget::item:hover {
                background-color: #1a1a2e;
            }
            QListWidget::item:selected {
                background-color: #e94560;
            }
        """)
        self.song_list.itemDoubleClicked.connect(self._on_song_double_clicked)
        self.song_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.song_list.customContextMenuRequested.connect(self._show_song_context_menu)
        layout.addWidget(self.song_list)
        
        btn_layout = QHBoxLayout()
        
        add_playlist_btn = QPushButton("➕ 新建")
        add_playlist_btn.setStyleSheet(self._get_button_style("#e94560"))
        add_playlist_btn.clicked.connect(self._create_playlist)
        btn_layout.addWidget(add_playlist_btn)
        
        delete_playlist_btn = QPushButton("🗑️ 删除")
        delete_playlist_btn.setStyleSheet(self._get_button_style("#666666"))
        delete_playlist_btn.clicked.connect(self._delete_playlist)
        btn_layout.addWidget(delete_playlist_btn)
        
        scan_btn = QPushButton("🔍 扫描")
        scan_btn.setStyleSheet(self._get_button_style("#0f3460"))
        scan_btn.clicked.connect(self._scan_library)
        btn_layout.addWidget(scan_btn)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板 - 当前播放、歌词和音乐库"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 当前播放信息
        now_playing = self._create_now_playing_widget()
        layout.addWidget(now_playing)
        
        # 歌词显示区域
        lyrics_widget = self._create_lyrics_widget()
        layout.addWidget(lyrics_widget)
        
        # 音乐库浏览
        library_group = QGroupBox("📚 音乐库")
        library_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #fff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        library_layout = QVBoxLayout(library_group)
        
        # 音乐库路径
        path_layout = QHBoxLayout()
        self.library_path_label = QLabel(f"📁 {self.player.music_library}")
        self.library_path_label.setStyleSheet("color: #666; font-size: 12px;")
        path_layout.addWidget(self.library_path_label)
        path_layout.addStretch()
        
        browse_btn = QPushButton("更改目录")
        browse_btn.setStyleSheet(self._get_button_style("#6c757d"))
        browse_btn.clicked.connect(self._change_library_path)
        path_layout.addWidget(browse_btn)
        
        library_layout.addLayout(path_layout)
        
        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 12px;")
        self._update_stats()
        library_layout.addWidget(self.stats_label)
        
        layout.addWidget(library_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_lyrics_widget(self) -> QWidget:
        """创建歌词显示组件"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 歌词标题
        lyrics_title = QLabel("🎵 歌词")
        lyrics_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(lyrics_title)
        
        # 歌词显示区域
        self.lyrics_list = QListWidget()
        self.lyrics_list.setMaximumHeight(120)
        self.lyrics_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px 10px;
                text-align: center;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
        """)
        self.lyrics_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyrics_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyrics_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.lyrics_list)
        
        return widget
    
    def _create_now_playing_widget(self) -> QWidget:
        """创建当前播放信息组件"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 歌曲标题
        self.song_title_label = QLabel("🎵 未播放")
        self.song_title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(self.song_title_label)
        
        # 艺术家和专辑
        self.artist_label = QLabel("艺术家: -")
        self.artist_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.artist_label)
        
        self.album_label = QLabel("专辑: -")
        self.album_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.album_label)
        
        # 进度条
        progress_layout = QHBoxLayout()
        
        self.position_label = QLabel("0:00")
        self.position_label.setStyleSheet("color: #888; font-size: 11px;")
        progress_layout.addWidget(self.position_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_slider, 1)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet("color: #888; font-size: 11px;")
        progress_layout.addWidget(self.duration_label)
        
        layout.addLayout(progress_layout)
        
        return widget
    
    def _create_control_bar(self) -> QWidget:
        """创建底部播放控制栏"""
        bar = QFrame()
        bar.setFixedHeight(80)
        bar.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border-top: 1px solid #0f3460;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)
        
        # 播放控制按钮
        controls = QHBoxLayout()
        controls.setSpacing(10)
        
        prev_btn = QPushButton("⏮")
        prev_btn.setFixedSize(40, 40)
        prev_btn.setStyleSheet(self._get_control_button_style())
        prev_btn.clicked.connect(self._previous_song)
        controls.addWidget(prev_btn)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(50, 50)
        self.play_btn.setStyleSheet(self._get_control_button_style(large=True))
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)
        
        next_btn = QPushButton("⏭")
        next_btn.setFixedSize(40, 40)
        next_btn.setStyleSheet(self._get_control_button_style())
        next_btn.clicked.connect(self._next_song)
        controls.addWidget(next_btn)
        
        layout.addLayout(controls)
        
        # 播放模式
        self.mode_btn = QPushButton("🔀")
        self.mode_btn.setFixedSize(40, 40)
        self.mode_btn.setStyleSheet(self._get_control_button_style())
        self.mode_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(self.mode_btn)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(5)
        
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("color: #fff; font-size: 16px;")
        volume_layout.addWidget(volume_icon)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.player.volume * 100))
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #0f3460;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        layout.addLayout(volume_layout)
        
        layout.addStretch()
        
        # 收藏按钮
        self.favorite_btn = QPushButton("♡")
        self.favorite_btn.setFixedSize(40, 40)
        self.favorite_btn.setStyleSheet(self._get_control_button_style())
        self.favorite_btn.clicked.connect(self._toggle_favorite)
        layout.addWidget(self.favorite_btn)
        
        return bar
    
    def _get_button_style(self, color: str) -> str:
        """获取按钮样式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """
    
    def _get_control_button_style(self, large: bool = False) -> str:
        """获取控制按钮样式"""
        size = "font-size: 24px;" if large else "font-size: 18px;"
        return f"""
            QPushButton {{
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 25px;
                {size}
            }}
            QPushButton:hover {{
                background-color: #ff6b6b;
            }}
        """
    
    def _connect_signals(self):
        """连接信号"""
        self.playlist_combo.currentIndexChanged.connect(self._on_playlist_changed)
    
    def _start_timer(self):
        """启动定时器更新播放状态"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_playback_status)
        self.timer.start(1000)  # 每秒更新一次
    
    def _update_playback_status(self):
        """更新播放状态"""
        if self.player.current_song:
            if self.player.is_music_playing():
                self.player.position = self.player.get_playback_position()
                self.position_label.setText(self._format_time(self.player.position))
                self.progress_slider.setValue(self.player.position)
                
                self._update_lyrics()
            elif self.player.is_playing:
                self.player.is_playing = False
                self._on_song_finished()
    
    def _on_song_finished(self):
        """歌曲播放完成"""
        logger.info("🎵 歌曲播放完成")
        if self.player.next_song():
            self._update_now_playing()
            self.song_list.setCurrentRow(self.player.current_song_index)
        else:
            self.play_btn.setText("▶")
            logger.info("播放列表已结束")
    
    def _update_lyrics(self):
        """更新歌词显示"""
        if not self.player.current_lyrics:
            return
        
        context = self.player.get_lyrics_context(before=2, after=3)
        
        if not context:
            return
        
        current_lyric_text = ""
        for line, is_current in context:
            if is_current:
                current_lyric_text = line.text
        
        if self.lyrics_list.count() != len(context):
            self.lyrics_list.clear()
            for line, is_current in context:
                item = QListWidgetItem(line.text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if is_current:
                    from PyQt6.QtGui import QColor
                    item.setForeground(QColor("#00BFFF"))
                    item.setBackground(Qt.GlobalColor.transparent)
                    font = item.font()
                    font.setBold(True)
                    font.setPointSize(14)
                    item.setFont(font)
                else:
                    font = item.font()
                    font.setPointSize(12)
                    item.setFont(font)
                self.lyrics_list.addItem(item)
        else:
            for i, (line, is_current) in enumerate(context):
                item = self.lyrics_list.item(i)
                if item:
                    item.setText(line.text)
                    if is_current:
                        from PyQt6.QtGui import QColor
                        item.setForeground(QColor("#00BFFF"))
                        item.setBackground(Qt.GlobalColor.transparent)
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(14)
                        item.setFont(font)
                    else:
                        item.setForeground(Qt.GlobalColor.gray)
                        item.setBackground(Qt.GlobalColor.transparent)
                        font = item.font()
                        font.setBold(False)
                        font.setPointSize(12)
                        item.setFont(font)
        
        for i, (line, is_current) in enumerate(context):
            if is_current:
                self.lyrics_list.scrollToItem(
                    self.lyrics_list.item(i),
                    self.lyrics_list.ScrollHint.PositionAtCenter
                )
                break
    
    def _format_time(self, seconds: int) -> str:
        """格式化时间"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    def _refresh_playlists(self):
        """刷新播放列表"""
        current_id = self.playlist_combo.currentData()
        self.playlist_combo.clear()
        self.playlist_combo.addItem("所有歌曲", "all")
        
        for playlist_id, playlist in self.player.playlists.items():
            self.playlist_combo.addItem(f"📁 {playlist.name}", playlist_id)
        
        # 恢复选择
        for i in range(self.playlist_combo.count()):
            if self.playlist_combo.itemData(i) == current_id:
                self.playlist_combo.setCurrentIndex(i)
                break
    
    def _refresh_song_list(self, songs: List[Song]):
        """刷新歌曲列表"""
        self.song_list.clear()
        for song in songs:
            item = QListWidgetItem(f"🎵 {song.title}")
            item.setData(Qt.ItemDataRole.UserRole, song.path)
            item.setToolTip(f"{song.title}\n{song.artist} - {song.album}")
            self.song_list.addItem(item)
    
    def _refresh_history(self):
        """刷新播放历史"""
        self.history_list.clear()
        for path in reversed(self.player.play_history[-20:]):
            item = QListWidgetItem(f"🎵 {Path(path).stem}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.history_list.addItem(item)
    
    def _update_stats(self):
        """更新统计信息"""
        song_count = len(self._cached_songs) if self._cached_songs else 0
        self.stats_label.setText(
            f"📊 共 {song_count} 首歌曲 | "
            f"❤️ {len(self.player.favorites)} 首收藏 | "
            f"📜 {len(self.player.play_history)} 条历史"
        )
    
    def _on_playlist_changed(self, index: int):
        """播放列表变化"""
        playlist_id = self.playlist_combo.currentData()
        
        if playlist_id == "all":
            songs = self._cached_songs
        elif playlist_id in self.player.playlists:
            songs = self.player.playlists[playlist_id].songs
        else:
            songs = []
        
        self._refresh_song_list(songs)
    
    def _on_song_double_clicked(self, item: QListWidgetItem):
        """双击播放歌曲"""
        song_path = item.data(Qt.ItemDataRole.UserRole)
        song = Song(path=song_path)
        
        playlist_id = self.playlist_combo.currentData()
        if playlist_id == "all":
            playlist_id = None
        
        self.player.play(song=song, playlist_id=playlist_id)
        self._update_now_playing()
    
    def _update_now_playing(self):
        """更新当前播放信息"""
        if self.player.current_song:
            song = self.player.current_song
            self.song_title_label.setText(f"🎵 {song.title}")
            self.artist_label.setText(f"艺术家: {song.artist}")
            self.album_label.setText(f"专辑: {song.album}")
            
            duration = song.duration
            if duration <= 0:
                duration = self.player._get_audio_duration(song.path)
                if duration > 0:
                    song.duration = duration
            
            self.duration_label.setText(self._format_time(duration))
            self.progress_slider.setRange(0, duration if duration > 0 else 300)
            
            self.play_btn.setText("⏸" if self.player.is_playing else "▶")
            
            if self.player.is_favorite(song.path):
                self.favorite_btn.setText("❤️")
            else:
                self.favorite_btn.setText("♡")
            
            self.song_changed.emit(song.to_dict())
    
    def _toggle_play(self):
        """切换播放/暂停"""
        if self.player.is_playing:
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            if self.player.current_song:
                self.player.resume()
                self.play_btn.setText("⏸")
            elif self.song_list.count() > 0:
                item = self.song_list.item(0)
                self._on_song_double_clicked(item)
        
        self.state_changed.emit(self.player.get_status())
    
    def _previous_song(self):
        """上一首"""
        if self.player.previous_song():
            self._update_now_playing()
    
    def _next_song(self):
        """下一首"""
        if self.player.next_song():
            self._update_now_playing()
    
    def _toggle_mode(self):
        """切换播放模式"""
        mode = self.player.toggle_play_mode()
        mode_icons = {
            PlayMode.SEQUENCE: "➡️",
            PlayMode.RANDOM: "🔀",
            PlayMode.SINGLE_LOOP: "🔂",
            PlayMode.LIST_LOOP: "🔁"
        }
        self.mode_btn.setText(mode_icons.get(mode, "🔀"))
    
    def _on_volume_changed(self, value: int):
        """音量变化"""
        self.player.set_volume(value / 100.0)
    
    def _toggle_favorite(self):
        """切换收藏"""
        if self.player.current_song:
            path = self.player.current_song.path
            if self.player.is_favorite(path):
                self.player.remove_from_favorites(path)
                self.favorite_btn.setText("♡")
            else:
                self.player.add_to_favorites(path)
                self.favorite_btn.setText("❤️")
            self._update_stats()
    
    def _create_playlist(self):
        """创建播放列表"""
        name, ok = QInputDialog.getText(self, "新建播放列表", "请输入播放列表名称:")
        if ok and name:
            self.player.create_playlist(name)
            self._refresh_playlists()
    
    def _delete_playlist(self):
        """删除播放列表"""
        playlist_id = self.playlist_combo.currentData()
        if playlist_id == "all":
            QMessageBox.warning(self, "提示", "无法删除「所有歌曲」")
            return
        
        if not playlist_id or playlist_id not in self.player.playlists:
            QMessageBox.warning(self, "提示", "请先选择一个播放列表")
            return
        
        playlist_name = self.player.playlists[playlist_id].name
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除播放列表「{playlist_name}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.player.delete_playlist(playlist_id)
            self._refresh_playlists()
    
    def _scan_library(self):
        """扫描音乐库（后台线程，强制重新扫描）"""
        self.scan_thread = ScanThread(self.player, force=True)
        self.scan_thread.finished.connect(self._on_scan_finished)
        self.scan_thread.start()
    
    def _on_scan_finished(self, songs):
        """扫描完成回调"""
        self._cached_songs = songs
        self._refresh_song_list(songs)
        self._update_stats()
        QMessageBox.information(self, "扫描完成", f"找到 {len(songs)} 首歌曲")
    
    def _change_library_path(self):
        """更改音乐库路径"""
        from PyQt6.QtWidgets import QFileDialog
        from ..config import settings
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择音乐库目录", str(self.player.music_library)
        )
        if dir_path:
            self.player.music_library = Path(dir_path)
            self.library_path_label.setText(f"📁 {dir_path}")
            settings.directory.set_music_library(dir_path)
            self._scan_library()
    
    def _show_song_context_menu(self, pos):
        """显示歌曲右键菜单"""
        item = self.song_list.itemAt(pos)
        if not item:
            return
        
        song_path = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #fff;
                border: 1px solid #ddd;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e94560;
                color: white;
            }
        """)
        
        # 播放
        play_action = QAction("▶ 播放", self)
        play_action.triggered.connect(lambda: self._on_song_double_clicked(item))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        # 添加到播放列表
        add_menu = menu.addMenu("➕ 添加到播放列表")
        for playlist_id, playlist in self.player.playlists.items():
            action = QAction(playlist.name, self)
            action.triggered.connect(
                lambda checked, pid=playlist_id, sp=song_path: 
                self._add_to_playlist(pid, sp)
            )
            add_menu.addAction(action)
        
        menu.addSeparator()
        
        # 收藏
        if self.player.is_favorite(song_path):
            fav_action = QAction("💔 取消收藏", self)
            fav_action.triggered.connect(lambda: self._remove_favorite(song_path))
        else:
            fav_action = QAction("❤️ 收藏", self)
            fav_action.triggered.connect(lambda: self._add_favorite(song_path))
        menu.addAction(fav_action)
        
        menu.exec(self.song_list.mapToGlobal(pos))
    
    def _add_to_playlist(self, playlist_id: str, song_path: str):
        """添加歌曲到播放列表"""
        song = Song(path=song_path)
        self.player.add_to_playlist(playlist_id, song)
    
    def _add_favorite(self, song_path: str):
        """添加收藏"""
        self.player.add_to_favorites(song_path)
        self._update_stats()
    
    def _remove_favorite(self, song_path: str):
        """移除收藏"""
        self.player.remove_from_favorites(song_path)
        self._update_stats()
        if self.player.current_song and self.player.current_song.path == song_path:
            self.favorite_btn.setText("♡")
    
    def _play_history_item(self, item: QListWidgetItem):
        """播放历史记录中的歌曲"""
        song_path = item.data(Qt.ItemDataRole.UserRole)
        song = Song(path=song_path)
        self.player.play(song=song)
        self._update_now_playing()
