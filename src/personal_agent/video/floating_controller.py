"""
视频播放浮窗控制器 - 悬浮在屏幕上的控制面板
"""
import sys
from pathlib import Path
from typing import Optional, Callable
from loguru import logger

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QGraphicsDropShadowEffect
    )
    from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
    from PyQt6.QtGui import QColor, QFont, QIcon, QCursor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("⚠️ PyQt6 未安装")


class FloatingController(QWidget):
    """悬浮控制面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 拖动相关
        self._dragging = False
        self._drag_position = QPoint()
        
        # 回调函数
        self._on_play_pause: Optional[Callable] = None
        self._on_stop: Optional[Callable] = None
        self._on_volume_change: Optional[Callable] = None
        self._on_seek: Optional[Callable] = None
        
        self._setup_ui()
        self._setup_position()
        
        # 自动隐藏计时器
        self._hide_timer = QTimer()
        self._hide_timer.timeout.connect(self._auto_hide)
        self._hide_timer.start(3000)  # 3秒后开始隐藏
        
        self._is_hidden = False
    
    def _setup_ui(self):
        """设置界面"""
        # 主布局
        self.main_widget = QWidget()
        self.main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_widget)
        
        # 内容布局
        content_layout = QVBoxLayout(self.main_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(8)
        
        # 标题栏（可拖动）
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel("🎬 视频控制")
        self.title_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff5555;
            }
        """)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.hide)
        title_layout.addWidget(self.close_btn)
        
        content_layout.addLayout(title_layout)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setFixedHeight(6)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(100, 100, 100, 150);
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #e91e63;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                margin: -3px 0;
                background: #e91e63;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff4081;
            }
        """)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        content_layout.addWidget(self.progress_slider)
        
        # 控制按钮布局
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        # 停止按钮
        self.stop_btn = self._create_control_btn("⏹", "#ff5252")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self.stop_btn)
        
        # 播放/暂停按钮
        self.play_btn = self._create_control_btn("⏸", "#e91e63")
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)
        
        controls_layout.addStretch()
        
        # 音量图标
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("color: #ffffff; font-size: 14px;")
        controls_layout.addWidget(volume_icon)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFixedHeight(4)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(100, 100, 100, 150);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #4caf50;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                height: 10px;
                margin: -3px 0;
                background: #4caf50;
                border-radius: 5px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.volume_slider)
        
        content_layout.addLayout(controls_layout)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.main_widget.setGraphicsEffect(shadow)
        
        # 设置固定大小
        self.setFixedSize(280, 140)
    
    def _create_control_btn(self, text: str, color: str) -> QPushButton:
        """创建控制按钮"""
        btn = QPushButton(text)
        btn.setFixedSize(36, 36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return btn
    
    def _setup_position(self):
        """设置初始位置（屏幕右下角）"""
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.width() - self.width() - 20,
            screen.height() - self.height() - 100
        )
    
    # ========== 事件处理 ==========
    
    def mousePressEvent(self, event):
        """鼠标按下 - 开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动 - 拖动窗口"""
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放 - 结束拖动"""
        self._dragging = False
        event.accept()
    
    def enterEvent(self, event):
        """鼠标进入 - 显示面板"""
        self._show_full()
        event.accept()
    
    def leaveEvent(self, event):
        """鼠标离开 - 开始计时隐藏"""
        self._hide_timer.start(2000)
        event.accept()
    
    def _auto_hide(self):
        """自动隐藏"""
        if not self.underMouse():
            self._show_minimal()
    
    def _show_full(self):
        """显示完整面板"""
        if self._is_hidden:
            self.main_widget.show()
            self.setFixedSize(280, 140)
            self._is_hidden = False
        self._hide_timer.stop()
    
    def _show_minimal(self):
        """显示最小化面板（只显示标题栏）"""
        self.main_widget.hide()
        self.setFixedSize(280, 30)
        self._is_hidden = True
    
    # ========== 回调设置 ==========
    
    def set_callbacks(self,
                      on_play_pause: Optional[Callable] = None,
                      on_stop: Optional[Callable] = None,
                      on_volume_change: Optional[Callable] = None,
                      on_seek: Optional[Callable] = None):
        """设置回调函数"""
        self._on_play_pause = on_play_pause
        self._on_stop = on_stop
        self._on_volume_change = on_volume_change
        self._on_seek = on_seek
    
    # ========== 按钮事件 ==========
    
    def _on_play_pause_clicked(self):
        """播放/暂停按钮"""
        if self._on_play_pause:
            self._on_play_pause()
    
    def _on_stop_clicked(self):
        """停止按钮"""
        if self._on_stop:
            self._on_stop()
    
    def _on_volume_changed(self, value: int):
        """音量改变"""
        if self._on_volume_change:
            self._on_volume_change(value)
    
    def _on_seek_released(self):
        """进度条释放"""
        if self._on_seek:
            position = self.progress_slider.value() / 1000.0
            self._on_seek(position)
    
    # ========== 状态更新 ==========
    
    def set_playing(self, is_playing: bool):
        """设置播放状态"""
        if is_playing:
            self.play_btn.setText("⏸")
            self.status_label.setText("播放中")
        else:
            self.play_btn.setText("▶")
            self.status_label.setText("已暂停")
    
    def set_progress(self, position: float):
        """设置进度 (0.0 - 1.0)"""
        self.progress_slider.setValue(int(position * 1000))
    
    def set_volume(self, volume: int):
        """设置音量 (0 - 100)"""
        self.volume_slider.setValue(volume)
    
    def set_title(self, title: str):
        """设置标题"""
        self.title_label.setText(f"🎬 {title[:15]}..." if len(title) > 15 else f"🎬 {title}")


class VideoControllerManager:
    """视频控制器管理器"""
    
    _instance: Optional['VideoControllerManager'] = None
    _controller: Optional[FloatingController] = None
    _app: Optional[QApplication] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def show_controller(self, title: str = "视频控制"):
        """显示控制器"""
        if not PYQT_AVAILABLE:
            logger.warning("PyQt6 未安装，无法显示浮窗控制器")
            return
        
        try:
            # 确保有 QApplication
            if QApplication.instance() is None:
                self._app = QApplication(sys.argv)
            
            if self._controller is None:
                self._controller = FloatingController()
            
            self._controller.set_title(title)
            self._controller.show()
            
            # 如果没有事件循环，启动它
            if not self._app:
                self._app = QApplication.instance()
            
            logger.info("🎮 显示视频浮窗控制器")
            
        except Exception as e:
            logger.error(f"显示控制器失败: {e}")
    
    def hide_controller(self):
        """隐藏控制器"""
        if self._controller:
            self._controller.hide()
    
    def set_callbacks(self, **kwargs):
        """设置回调函数"""
        if self._controller:
            self._controller.set_callbacks(**kwargs)
    
    def update_progress(self, position: float):
        """更新进度"""
        if self._controller:
            self._controller.set_progress(position)
    
    def update_playing_state(self, is_playing: bool):
        """更新播放状态"""
        if self._controller:
            self._controller.set_playing(is_playing)


# 全局实例
_controller_manager: Optional[VideoControllerManager] = None


def get_controller_manager() -> VideoControllerManager:
    """获取控制器管理器"""
    global _controller_manager
    if _controller_manager is None:
        _controller_manager = VideoControllerManager()
    return _controller_manager


def show_video_controller(title: str = "视频控制"):
    """显示视频控制器"""
    manager = get_controller_manager()
    manager.show_controller(title)
    return manager
