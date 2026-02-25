"""
Home Assistant Dashboard Widget - 智能家居控制面板
"""
import asyncio
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QSlider, QFrame,
    QSizePolicy, QScrollArea, QGridLayout, QGroupBox, QSpinBox,
    QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon
from loguru import logger


class HomeAssistantWorker(QThread):
    """Home Assistant 后台工作线程"""
    states_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client):
        super().__init__()
        self._running = False
        self.api = api_client

    def run(self):
        """后台线程运行"""
        self._running = True
        while self._running:
            self.msleep(5000)

    def stop(self):
        self._running = False
        self.wait()


class DeviceCard(QFrame):
    """设备卡片"""
    
    state_changed = pyqtSignal(str, str)
    
    def __init__(self, entity_id: str, entity_data: Dict, parent=None):
        super().__init__(parent)
        self.entity_id = entity_id
        self.entity_data = entity_data
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面"""
        domain = self.entity_id.split('.')[0]
        friendly_name = self.entity_data.get('attributes', {}).get('friendly_name', self.entity_id)
        state = self.entity_data.get('state', 'unknown')
        
        is_on = state == 'on'
        
        bg_color = "#e8f5e9" if is_on else "#f5f5f5"
        border_color = "#4caf50" if is_on else "#ddd"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 15px;
                padding: 10px;
            }}
            QFrame:hover {{
                border-color: #2196f3;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        icon_map = {
            'light': '💡',
            'switch': '🔌',
            'climate': '❄️',
            'sensor': '📊',
            'binary_sensor': '📡',
            'scene': '🎬',
            'script': '📜',
            'automation': '⚙️',
        }
        icon = icon_map.get(domain, '📱')
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        name_label = QLabel(friendly_name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        state_map = {
            'on': '🟢 开启',
            'off': '⚫ 关闭',
            'cool': '❄️ 制冷',
            'heat': '🔥 制热',
            'auto': '🔄 自动',
            'dry': '💧 除湿',
            'fan_only': '💨 送风',
        }
        state_text = state_map.get(state, state)
        self.state_label = QLabel(state_text)
        self.state_label.setStyleSheet("font-size: 12px; color: #666;")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.state_label)
        
        if domain in ['light', 'switch', 'climate']:
            btn_layout = QHBoxLayout()
            
            if is_on:
                self.toggle_btn = QPushButton("关闭")
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 8px 16px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)
                self.toggle_btn.clicked.connect(lambda: self._toggle_device('off'))
            else:
                self.toggle_btn = QPushButton("打开")
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4caf50;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 8px 16px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #388e3c;
                    }
                """)
                self.toggle_btn.clicked.connect(lambda: self._toggle_device('on'))
            
            btn_layout.addStretch()
            btn_layout.addWidget(self.toggle_btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)
        
        if domain == 'light' and is_on:
            brightness = self.entity_data.get('attributes', {}).get('brightness', 255)
            brightness_pct = int(brightness * 100 / 255)
            
            brightness_label = QLabel(f"亮度: {brightness_pct}%")
            brightness_label.setStyleSheet("font-size: 11px; color: #888;")
            brightness_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(brightness_label)
        
        if domain == 'climate':
            attrs = self.entity_data.get('attributes', {})
            temp = attrs.get('temperature', '-')
            current_temp = attrs.get('current_temperature', '-')
            
            temp_label = QLabel(f"设定: {temp}°C | 当前: {current_temp}°C")
            temp_label.setStyleSheet("font-size: 11px; color: #888;")
            temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(temp_label)
    
    def _toggle_device(self, action: str):
        """切换设备状态"""
        self.state_changed.emit(self.entity_id, action)
    
    def update_state(self, state: str, attributes: Dict = None):
        """更新状态显示"""
        state_map = {
            'on': '🟢 开启',
            'off': '⚫ 关闭',
        }
        self.state_label.setText(state_map.get(state, state))


class HomeAssistantDashboard(QWidget):
    """Home Assistant 控制面板"""
    
    control_requested = pyqtSignal(str, str, dict)
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entities: Dict[str, Dict] = {}
        self.device_cards: Dict[str, DeviceCard] = {}
        
        self._setup_ui()
        self._setup_timer()
    
    def _setup_ui(self):
        """设置界面"""
        self.setMinimumSize(400, 500)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                background-color: #2196f3;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #2196f3;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("🏠 智能家居控制")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196f3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索设备...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(15)
        
        self.lights_group = QGroupBox("💡 灯光")
        self.lights_layout = QGridLayout(self.lights_group)
        self.lights_layout.setSpacing(10)
        self.scroll_layout.addWidget(self.lights_group)
        
        self.climate_group = QGroupBox("❄️ 空调")
        self.climate_layout = QGridLayout(self.climate_group)
        self.climate_layout.setSpacing(10)
        self.scroll_layout.addWidget(self.climate_group)
        
        self.switches_group = QGroupBox("🔌 开关")
        self.switches_layout = QGridLayout(self.switches_group)
        self.switches_layout.setSpacing(10)
        self.scroll_layout.addWidget(self.switches_group)
        
        self.others_group = QGroupBox("📱 其他设备")
        self.others_layout = QGridLayout(self.others_group)
        self.others_layout.setSpacing(10)
        self.scroll_layout.addWidget(self.others_group)
        
        self.scroll_layout.addStretch()
        
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.count_label = QLabel("设备: 0")
        self.count_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.count_label)
        layout.addLayout(status_layout)
    
    def _setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_refresh)
    
    def _on_refresh(self):
        """刷新设备列表"""
        self.refresh_requested.emit()
    
    def _on_search(self, text: str):
        """搜索设备"""
        text = text.lower()
        for entity_id, card in self.device_cards.items():
            friendly_name = self.entities.get(entity_id, {}).get('attributes', {}).get('friendly_name', '')
            visible = text in friendly_name.lower() or text in entity_id.lower()
            card.setVisible(visible if text else True)
    
    def set_entities(self, entities: Dict[str, Dict]):
        """设置设备列表"""
        self.entities = entities
        
        for i in range(self.lights_layout.count()):
            self.lights_layout.itemAt(i).widget().deleteLater()
        for i in range(self.climate_layout.count()):
            self.climate_layout.itemAt(i).widget().deleteLater()
        for i in range(self.switches_layout.count()):
            self.switches_layout.itemAt(i).widget().deleteLater()
        for i in range(self.others_layout.count()):
            self.others_layout.itemAt(i).widget().deleteLater()
        
        self.device_cards.clear()
        
        lights = []
        climates = []
        switches = []
        others = []
        
        for entity_id, entity_data in entities.items():
            domain = entity_id.split('.')[0]
            if domain == 'light':
                lights.append((entity_id, entity_data))
            elif domain == 'climate':
                climates.append((entity_id, entity_data))
            elif domain == 'switch':
                switches.append((entity_id, entity_data))
            elif domain not in ['sensor', 'binary_sensor', 'automation', 'script', 'scene', 'zone', 'person', 'device_tracker', 'sun']:
                others.append((entity_id, entity_data))
        
        self._add_devices_to_grid(lights, self.lights_layout)
        self._add_devices_to_grid(climates, self.climate_layout)
        self._add_devices_to_grid(switches, self.switches_layout)
        self._add_devices_to_grid(others, self.others_layout)
        
        self.lights_group.setVisible(len(lights) > 0)
        self.climate_group.setVisible(len(climates) > 0)
        self.switches_group.setVisible(len(switches) > 0)
        self.others_group.setVisible(len(others) > 0)
        
        total = len(lights) + len(climates) + len(switches) + len(others)
        self.count_label.setText(f"设备: {total}")
        self.status_label.setText(f"已加载 {total} 个设备")
    
    def _add_devices_to_grid(self, devices: List, layout: QGridLayout):
        """添加设备到网格"""
        for i, (entity_id, entity_data) in enumerate(devices):
            card = DeviceCard(entity_id, entity_data)
            card.state_changed.connect(self._on_device_control)
            
            row = i // 3
            col = i % 3
            layout.addWidget(card, row, col)
            
            self.device_cards[entity_id] = card
    
    def _on_device_control(self, entity_id: str, action: str):
        """设备控制"""
        self.control_requested.emit(entity_id, action, {})
    
    def update_entity_state(self, entity_id: str, state: str, attributes: Dict = None):
        """更新单个设备状态"""
        if entity_id in self.device_cards:
            self.device_cards[entity_id].update_state(state, attributes)
    
    def set_status(self, status: str):
        """设置状态"""
        self.status_label.setText(status)
    
    def start_auto_refresh(self, interval: int = 30000):
        """开始自动刷新"""
        self.update_timer.start(interval)
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.update_timer.stop()
