"""
Settings Dialog - GUI for managing agent settings
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QLineEdit, QComboBox, QCheckBox,
    QSpinBox, QTextEdit, QGroupBox, QFormLayout, QMessageBox,
    QListWidget, QListWidgetItem, QFileDialog, QSplitter, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..config import settings
from ..user_config import user_config


class SettingsDialog(QDialog):
    """Dialog for managing all agent settings"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 智能体设置")
        self.setMinimumSize(800, 600)
        self.resize(900, 650)
        
        self._original_settings = {}
        self._load_current_settings()
        
        self._init_ui()
        self._apply_styles()
    
    def _load_current_settings(self):
        """Load current settings from config"""
        self._original_settings = {
            "llm_provider": settings.llm.provider,
            "dashscope_api_key": settings.llm.dashscope_api_key,
            "dashscope_model": settings.llm.dashscope_model,
            "dashscope_enable_search": settings.llm.dashscope_enable_search,
            "agent_name": settings.agent.name,
            "agent_max_iterations": settings.agent.max_iterations,
            "agent_timeout": settings.agent.timeout,
            "allowed_directories": settings.security.allowed_directories,
            "dangerous_commands": settings.security.dangerous_commands,
            "log_level": settings.log_level,
            "user_name": settings.user.name,
            "user_formal_name": settings.user.formal_name,
            "user_email": settings.user.email,
            "user_phone": settings.user.phone,
            "user_address": settings.user.address,
            "user_city": settings.user.city,
            "user_timezone": settings.user.timezone,
            "agent_name": settings.agent.name,
            "agent_gender": settings.agent.gender,
            "agent_voice": settings.agent.voice,
            "agent_personality": settings.agent.personality,
            "agent_greeting": settings.agent.greeting,
            "agent_avatar": settings.agent.avatar,
            "agent_email": settings.agent.email,
            "agent_email_password": settings.agent.email_password,
            "agent_email_smtp": settings.agent.email_smtp,
            "agent_email_port": settings.agent.email_port,
            "agent_max_iterations": settings.agent.max_iterations,
            "agent_timeout": settings.agent.timeout,
            "music_library": settings.directory.music_library,
            "download_dir": settings.directory.download_dir,
            "documents_dir": settings.directory.documents_dir,
            "pictures_dir": settings.directory.pictures_dir,
            "voice_provider": settings.llm.voice_provider,
            "voice_dashscope_api_key": settings.llm.voice_dashscope_api_key,
            "tts_enabled": settings.llm.tts_enabled,
            "tts_voice": settings.llm.tts_voice,
            "tts_speech_rate": settings.llm.tts_speech_rate,
            "tushare_token": settings.user.tushare_token,
            "homeassistant_enabled": settings.homeassistant.enabled if hasattr(settings, 'homeassistant') else False,
            "homeassistant_url": settings.homeassistant.url if hasattr(settings, 'homeassistant') else "",
            "homeassistant_token": settings.homeassistant.token if hasattr(settings, 'homeassistant') else "",
        }
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_user_tab(), "👤 用户信息")
        tabs.addTab(self._create_agent_tab(), "🤖 智能体设置")
        tabs.addTab(self._create_contacts_tab(), "📖 通讯录")
        tabs.addTab(self._create_directories_tab(), "📁 目录设置")
        tabs.addTab(self._create_llm_tab(), "🧠 大模型设置")
        tabs.addTab(self._create_security_tab(), "🔒 权限设置")
        tabs.addTab(self._create_general_tab(), "📋 通用设置")
        tabs.addTab(self._create_about_tab(), "ℹ️ 关于")
        
        layout.addWidget(tabs)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 保存设置")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def _create_user_tab(self) -> QWidget:
        """Create user info settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        self.user_name = QLineEdit()
        # 优先使用 user_config.json 中的用户名
        display_name = user_config.user_name or self._original_settings["user_name"]
        self.user_name.setText(display_name)
        self.user_name.setPlaceholderText("您的称呼（如：冯老板）")
        basic_layout.addRow("昵称:", self.user_name)
        
        self.user_formal_name = QLineEdit()
        # 优先使用 user_config.json 中的正式名称
        display_formal_name = user_config.formal_name or self._original_settings.get("user_formal_name", "")
        self.user_formal_name.setText(display_formal_name)
        self.user_formal_name.setPlaceholderText("您的正式姓名（用于邮件署名）")
        basic_layout.addRow("正式名称:", self.user_formal_name)
        
        self.user_email = QLineEdit()
        self.user_email.setText(self._original_settings["user_email"])
        self.user_email.setPlaceholderText("your@email.com")
        basic_layout.addRow("邮箱:", self.user_email)
        
        self.user_phone = QLineEdit()
        self.user_phone.setText(self._original_settings["user_phone"])
        self.user_phone.setPlaceholderText("手机号码")
        basic_layout.addRow("电话:", self.user_phone)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        location_group = QGroupBox("位置信息")
        location_layout = QFormLayout()
        
        self.user_city = QLineEdit()
        self.user_city.setText(self._original_settings["user_city"])
        self.user_city.setPlaceholderText("例如：北京、上海")
        location_layout.addRow("城市:", self.user_city)
        
        self.user_address = QLineEdit()
        self.user_address.setText(self._original_settings["user_address"])
        self.user_address.setPlaceholderText("详细地址")
        location_layout.addRow("地址:", self.user_address)
        
        self.user_timezone = QComboBox()
        self.user_timezone.addItems([
            "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo", 
            "Asia/Singapore", "America/New_York", "America/Los_Angeles",
            "Europe/London", "Europe/Paris"
        ])
        self.user_timezone.setCurrentText(self._original_settings["user_timezone"])
        location_layout.addRow("时区:", self.user_timezone)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        hint_group = QGroupBox("💡 使用说明")
        hint_layout = QVBoxLayout()
        
        hint_text = QLabel(
            "• 这些信息将帮助智能体更好地为您服务\n"
            "• 当您询问天气时，会自动使用您设置的城市\n"
            "• 当需要发送邮件或填写表单时，会使用您的邮箱\n"
            "• 所有信息仅保存在本地，不会上传到云端"
        )
        hint_text.setStyleSheet("color: #666; font-size: 12px; line-height: 1.6;")
        hint_layout.addWidget(hint_text)
        
        hint_group.setLayout(hint_layout)
        layout.addWidget(hint_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_agent_tab(self) -> QWidget:
        """Create agent settings tab"""
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)
        outer_layout.setSpacing(10)
        
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()
        
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        avatar_layout = QHBoxLayout()
        
        self.avatar_preview = QLabel()
        self.avatar_preview.setFixedSize(50, 50)
        self.avatar_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_preview.setStyleSheet("""
            QLabel {
                background-color: #10a37f;
                border-radius: 8px;
                font-size: 28px;
            }
        """)
        self._update_avatar_preview(self._original_settings["agent_avatar"])
        avatar_layout.addWidget(self.avatar_preview)
        
        self.agent_avatar = QLineEdit()
        self.agent_avatar.setText(self._original_settings["agent_avatar"])
        self.agent_avatar.setVisible(False)
        avatar_layout.addWidget(self.agent_avatar)
        
        avatar_btn = QPushButton("选择头像")
        avatar_btn.setMaximumWidth(80)
        avatar_btn.clicked.connect(self._show_avatar_picker)
        avatar_layout.addWidget(avatar_btn)
        
        avatar_layout.addStretch()
        
        basic_layout.addRow("头像:", avatar_layout)
        
        self.agent_name = QLineEdit()
        self.agent_name.setText(self._original_settings["agent_name"])
        self.agent_name.setPlaceholderText("智能助手")
        basic_layout.addRow("名称:", self.agent_name)
        
        self.agent_gender = QComboBox()
        self.agent_gender.addItems(["neutral", "male", "female"])
        gender_names = {"neutral": "中性", "male": "男性", "female": "女性"}
        current_gender = self._original_settings["agent_gender"]
        self.agent_gender.setCurrentText(current_gender)
        basic_layout.addRow("性别:", self.agent_gender)
        
        basic_group.setLayout(basic_layout)
        left_column.addWidget(basic_group)
        
        personality_group = QGroupBox("个性设置")
        personality_layout = QFormLayout()
        
        self.agent_personality = QComboBox()
        self.agent_personality.addItems([
            "friendly", "professional", "humorous", "caring", "concise"
        ])
        personality_names = {
            "friendly": "友好亲切",
            "professional": "专业严谨",
            "humorous": "幽默风趣",
            "caring": "温柔体贴",
            "concise": "简洁高效"
        }
        self.agent_personality.setCurrentText(self._original_settings["agent_personality"])
        personality_layout.addRow("性格:", self.agent_personality)
        
        self.agent_greeting = QLineEdit()
        self.agent_greeting.setText(self._original_settings["agent_greeting"])
        self.agent_greeting.setPlaceholderText("自定义问候语（留空使用默认）")
        personality_layout.addRow("问候语:", self.agent_greeting)
        
        personality_group.setLayout(personality_layout)
        left_column.addWidget(personality_group)
        
        voice_group = QGroupBox("声音设置")
        voice_layout = QFormLayout()
        
        self.agent_voice = QComboBox()
        self.agent_voice.addItems([
            "default", "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", 
            "zh-CN-YunyangNeural", "zh-CN-XiaoyiNeural"
        ])
        voice_names = {
            "default": "默认",
            "zh-CN-XiaoxiaoNeural": "晓晓（女声）",
            "zh-CN-YunxiNeural": "云希（男声）",
            "zh-CN-YunyangNeural": "云扬（男声）",
            "zh-CN-XiaoyiNeural": "晓伊（女声）"
        }
        self.agent_voice.setCurrentText(self._original_settings["agent_voice"])
        voice_layout.addRow("语音:", self.agent_voice)
        
        voice_hint = QLabel("💡 语音功能需要安装 pyttsx3 或使用在线TTS服务")
        voice_hint.setStyleSheet("color: #888; font-size: 11px;")
        voice_layout.addRow("", voice_hint)
        
        voice_group.setLayout(voice_layout)
        right_column.addWidget(voice_group)
        
        email_group = QGroupBox("邮箱设置")
        email_layout = QFormLayout()
        
        self.agent_email = QLineEdit()
        self.agent_email.setText(self._original_settings["agent_email"])
        self.agent_email.setPlaceholderText("your@qq.com")
        email_layout.addRow("邮箱:", self.agent_email)
        
        self.agent_email_password = QLineEdit()
        self.agent_email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.agent_email_password.setText(self._original_settings["agent_email_password"])
        self.agent_email_password.setPlaceholderText("授权码或密码")
        email_layout.addRow("授权码:", self.agent_email_password)
        
        smtp_layout = QHBoxLayout()
        self.agent_email_smtp = QComboBox()
        self.agent_email_smtp.addItems([
            "smtp.qq.com", "smtp.163.com", "smtp.gmail.com", 
            "smtp.outlook.com", "smtp.126.com"
        ])
        self.agent_email_smtp.setCurrentText(self._original_settings["agent_email_smtp"])
        smtp_layout.addWidget(self.agent_email_smtp)
        
        self.agent_email_port = QSpinBox()
        self.agent_email_port.setRange(1, 65535)
        self.agent_email_port.setValue(self._original_settings["agent_email_port"])
        smtp_layout.addWidget(QLabel(":"))
        smtp_layout.addWidget(self.agent_email_port)
        smtp_layout.addStretch()
        
        email_layout.addRow("SMTP:", smtp_layout)
        
        email_hint = QLabel("💡 QQ邮箱需要使用授权码，在邮箱设置中开启SMTP服务获取")
        email_hint.setStyleSheet("color: #888; font-size: 11px;")
        email_layout.addRow("", email_hint)
        
        email_group.setLayout(email_layout)
        right_column.addWidget(email_group)
        
        left_column.addStretch()
        right_column.addStretch()
        
        columns_layout.addLayout(left_column, 1)
        columns_layout.addLayout(right_column, 1)
        
        outer_layout.addLayout(columns_layout)
        
        preview_group = QGroupBox("预览效果")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 8px;
            font-size: 13px;
        """)
        preview_layout.addWidget(self.preview_label)
        
        self.agent_name.textChanged.connect(self._update_preview)
        self.agent_avatar.textChanged.connect(self._update_preview)
        self.agent_gender.currentTextChanged.connect(self._update_preview)
        self.agent_personality.currentTextChanged.connect(self._update_preview)
        self.agent_greeting.textChanged.connect(self._update_preview)
        
        self._update_preview()
        
        preview_group.setLayout(preview_layout)
        outer_layout.addWidget(preview_group)
        
        return widget
    
    def _show_avatar_picker(self):
        """Show avatar picker dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择头像")
        dialog.setFixedSize(450, 480)
        
        main_layout = QVBoxLayout(dialog)
        
        layout = QGridLayout()
        
        avatars = [
            "🤖", "🧠", "👾", "🦾", "🦿",
            "😊", "😄", "🥰", "😎", "🤓",
            "🧑‍💻", "👨‍💻", "👩‍💻", "🧙‍♂️", "🧙‍♀️",
            "🦸‍♂️", "🦸‍♀️", "🥷", "🐱", "🐶",
            "🦊", "🐼", "🦁", "🐯", "🐸",
            "🌟", "⭐", "🌙", "☀️", "🔥",
            "💎", "🎯", "🎲", "🎮", "🚀",
        ]
        
        def select_avatar(avatar):
            self.agent_avatar.setText(avatar)
            self._update_avatar_preview(avatar)
            dialog.accept()
        
        for i, avatar in enumerate(avatars):
            btn = QPushButton(avatar)
            btn.setStyleSheet("font-size: 24px; padding: 10px;")
            btn.clicked.connect(lambda checked, a=avatar: select_avatar(a))
            layout.addWidget(btn, i // 5, i % 5)
        
        main_layout.addLayout(layout)
        
        separator = QLabel("")
        separator.setStyleSheet("background-color: #ddd; min-height: 1px; margin: 10px 0;")
        main_layout.addWidget(separator)
        
        upload_layout = QHBoxLayout()
        upload_layout.addWidget(QLabel("上传图片:"))
        
        upload_btn = QPushButton("选择图片...")
        upload_btn.clicked.connect(lambda: self._upload_avatar_image(select_avatar))
        upload_layout.addWidget(upload_btn)
        upload_layout.addStretch()
        
        main_layout.addLayout(upload_layout)
        
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("自定义:"))
        
        custom_input = QLineEdit()
        custom_input.setPlaceholderText("输入表情或文字")
        custom_input.setMaximumWidth(150)
        custom_layout.addWidget(custom_input)
        
        custom_btn = QPushButton("确定")
        custom_btn.clicked.connect(lambda: select_avatar(custom_input.text()) if custom_input.text() else None)
        custom_layout.addWidget(custom_btn)
        custom_layout.addStretch()
        
        main_layout.addLayout(custom_layout)
        
        hint = QLabel("💡 可以选择预设表情、上传图片或输入自定义文字")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(hint)
        
        dialog.exec()
    
    def _upload_avatar_image(self, callback):
        """Upload avatar image"""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        import shutil
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择头像图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        
        if file_path:
            avatar_dir = Path.home() / ".personal_agent" / "avatars"
            avatar_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = avatar_dir / f"avatar{Path(file_path).suffix}"
            
            try:
                shutil.copy(file_path, dest_path)
                callback(str(dest_path))
            except Exception as e:
                QMessageBox.warning(self, "上传失败", f"无法保存头像: {e}")
    
    def _update_avatar_preview(self, avatar_text: str):
        """Update avatar preview display"""
        from pathlib import Path
        from PyQt6.QtGui import QPixmap
        
        if not avatar_text:
            avatar_text = "🤖"
        
        if avatar_text.startswith("/") or avatar_text.startswith("\\") or (len(avatar_text) > 2 and ":" in avatar_text[:3]):
            avatar_path = Path(avatar_text)
            if avatar_path.exists():
                pixmap = QPixmap(str(avatar_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    self.avatar_preview.setPixmap(scaled)
                    self.avatar_preview.setStyleSheet("""
                        QLabel {
                            border-radius: 8px;
                        }
                    """)
                    return
        
        self.avatar_preview.clear()
        self.avatar_preview.setText(avatar_text)
        self.avatar_preview.setStyleSheet("""
            QLabel {
                background-color: #10a37f;
                border-radius: 8px;
                font-size: 28px;
            }
        """)
    
    def _update_preview(self):
        """Update preview label"""
        avatar = self.agent_avatar.text() or "🤖"
        name = self.agent_name.text() or "小助手"
        gender = self.agent_gender.currentText()
        personality = self.agent_personality.currentText()
        greeting = self.agent_greeting.text()
        
        personality_names = {
            "friendly": "友好亲切",
            "professional": "专业严谨",
            "humorous": "幽默风趣",
            "caring": "温柔体贴",
            "concise": "简洁高效"
        }
        
        gender_names = {
            "neutral": "中性",
            "male": "男性",
            "female": "女性"
        }
        
        display_avatar = avatar
        if avatar.startswith("/") or avatar.startswith("\\") or (len(avatar) > 2 and ":" in avatar[:3]):
            display_avatar = "📷"
        
        if greeting:
            preview_greeting = greeting
        else:
            if personality == "friendly":
                preview_greeting = f"您好！我是{name}，很高兴为您服务～"
            elif personality == "professional":
                preview_greeting = f"您好，我是{name}。请问有什么可以帮您？"
            elif personality == "humorous":
                preview_greeting = f"嘿！{name}来啦！今天想聊点啥？😄"
            elif personality == "caring":
                preview_greeting = f"您好呀～我是{name}，有什么我可以帮您的吗？"
            else:
                preview_greeting = f"我是{name}，请说。"
        
        preview_text = f"""{display_avatar} {name}
        
性别: {gender_names.get(gender, gender)}
性格: {personality_names.get(personality, personality)}

示例对话:
用户: 你好
{name}: {preview_greeting}"""
        
        self.preview_label.setText(preview_text)
    
    def _create_contacts_tab(self) -> QWidget:
        """Create contacts management tab"""
        from ..contacts.smart_contact_book import smart_contact_book, Contact
        
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        list_label = QLabel("联系人列表")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.contacts_list = QListWidget()
        self.contacts_list.itemClicked.connect(self._on_contact_selected)
        left_layout.addWidget(self.contacts_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加")
        add_btn.clicked.connect(self._add_contact)
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.clicked.connect(self._delete_contact)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        left_layout.addLayout(btn_layout)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        form_label = QLabel("联系人详情")
        form_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(form_label)
        
        form = QFormLayout()
        
        self.contact_name = QLineEdit()
        self.contact_name.setPlaceholderText("姓名（必填）")
        form.addRow("姓名:", self.contact_name)
        
        self.contact_phone = QLineEdit()
        self.contact_phone.setPlaceholderText("电话号码")
        form.addRow("电话:", self.contact_phone)
        
        self.contact_email = QLineEdit()
        self.contact_email.setPlaceholderText("邮箱地址")
        form.addRow("邮箱:", self.contact_email)
        
        self.contact_company = QLineEdit()
        self.contact_company.setPlaceholderText("公司名称")
        form.addRow("公司:", self.contact_company)
        
        self.contact_position = QLineEdit()
        self.contact_position.setPlaceholderText("职位")
        form.addRow("职位:", self.contact_position)
        
        self.contact_relationship = QLineEdit()
        self.contact_relationship.setPlaceholderText("如：朋友、同事、领导、家人等")
        form.addRow("关系:", self.contact_relationship)
        
        self.contact_address = QLineEdit()
        self.contact_address.setPlaceholderText("地址")
        form.addRow("地址:", self.contact_address)
        
        self.contact_notes = QTextEdit()
        self.contact_notes.setPlaceholderText("备注信息")
        self.contact_notes.setMaximumHeight(80)
        form.addRow("备注:", self.contact_notes)
        
        right_layout.addLayout(form)
        
        save_btn = QPushButton("💾 保存联系人")
        save_btn.clicked.connect(self._save_contact)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        right_layout.addWidget(save_btn)
        
        right_layout.addStretch()
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 500])
        
        layout.addWidget(splitter)
        
        self._refresh_contacts_list()
        
        return widget
    
    def _refresh_contacts_list(self):
        """Refresh the contacts list widget"""
        from ..contacts.smart_contact_book import smart_contact_book
        
        self.contacts_list.clear()
        contacts = smart_contact_book.list_all_contacts()
        for contact in contacts:
            item = QListWidgetItem(f"{contact.name}")
            item.setData(Qt.ItemDataRole.UserRole, contact.name)
            self.contacts_list.addItem(item)
    
    def _on_contact_selected(self, item):
        """Handle contact selection"""
        from ..contacts.smart_contact_book import smart_contact_book
        
        name = item.data(Qt.ItemDataRole.UserRole)
        contact = smart_contact_book.get_contact(name)
        if contact:
            self.contact_name.setText(contact.name)
            self.contact_phone.setText(contact.phone or "")
            self.contact_email.setText(contact.email or "")
            self.contact_company.setText(contact.company or "")
            self.contact_position.setText(contact.position or "")
            self.contact_relationship.setText(contact.relationship or "")
            self.contact_address.setText(contact.address or "")
            self.contact_notes.setText(contact.notes or "")
    
    def _add_contact(self):
        """Add a new contact"""
        self.contact_name.clear()
        self.contact_phone.clear()
        self.contact_email.clear()
        self.contact_company.clear()
        self.contact_position.clear()
        self.contact_relationship.clear()
        self.contact_address.clear()
        self.contact_notes.clear()
        self.contact_name.setFocus()
    
    def _save_contact(self):
        """Save contact to address book"""
        from ..contacts.smart_contact_book import smart_contact_book, Contact
        
        name = self.contact_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入联系人姓名")
            return
        
        existing = smart_contact_book.get_contact(name)
        
        if existing:
            smart_contact_book.add_contact(
                name=name,
                phone=self.contact_phone.text().strip(),
                email=self.contact_email.text().strip(),
                company=self.contact_company.text().strip(),
                position=self.contact_position.text().strip(),
                relationship=self.contact_relationship.text().strip(),
                address=self.contact_address.text().strip(),
                notes=self.contact_notes.toPlainText().strip()
            )
            QMessageBox.information(self, "成功", f"已更新联系人：{name}")
        else:
            smart_contact_book.add_contact(
                name=name,
                phone=self.contact_phone.text().strip(),
                email=self.contact_email.text().strip(),
                company=self.contact_company.text().strip(),
                position=self.contact_position.text().strip(),
                relationship=self.contact_relationship.text().strip(),
                address=self.contact_address.text().strip(),
                notes=self.contact_notes.toPlainText().strip()
            )
            QMessageBox.information(self, "成功", f"已添加联系人：{name}")
        
        self._refresh_contacts_list()
    
    def _delete_contact(self):
        """Delete selected contact"""
        from ..contacts.smart_contact_book import smart_contact_book
        
        current_item = self.contacts_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的联系人")
            return
        
        name = current_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除联系人 '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            smart_contact_book.delete_contact(name)
            self._refresh_contacts_list()
            self._add_contact()
            QMessageBox.information(self, "成功", f"已删除联系人：{name}")

    def _create_directories_tab(self) -> QWidget:
        """Create directories settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        music_group = QGroupBox("🎵 音乐库目录")
        music_layout = QVBoxLayout()
        
        music_hint = QLabel("设置音乐文件的默认存储位置，智能体将在此目录搜索和管理音乐文件")
        music_hint.setStyleSheet("color: #666; font-size: 12px;")
        music_hint.setWordWrap(True)
        music_layout.addWidget(music_hint)
        
        music_path_layout = QHBoxLayout()
        self.music_library_path = QLineEdit()
        self.music_library_path.setText(self._original_settings.get("music_library", ""))
        self.music_library_path.setPlaceholderText("选择音乐库目录...")
        self.music_library_path.setReadOnly(True)
        music_path_layout.addWidget(self.music_library_path, 1)
        
        music_browse_btn = QPushButton("📂 浏览")
        music_browse_btn.setFixedWidth(80)
        music_browse_btn.clicked.connect(self._browse_music_library)
        music_path_layout.addWidget(music_browse_btn)
        
        music_layout.addLayout(music_path_layout)
        
        music_info = QLabel(f"💡 默认位置: {Path.home() / 'Music'}")
        music_info.setStyleSheet("color: #888; font-size: 11px;")
        music_layout.addWidget(music_info)
        
        music_group.setLayout(music_layout)
        layout.addWidget(music_group)
        
        download_group = QGroupBox("📥 下载目录")
        download_layout = QVBoxLayout()
        
        download_hint = QLabel("设置下载文件的默认保存位置")
        download_hint.setStyleSheet("color: #666; font-size: 12px;")
        download_hint.setWordWrap(True)
        download_layout.addWidget(download_hint)
        
        download_path_layout = QHBoxLayout()
        self.download_dir_path = QLineEdit()
        self.download_dir_path.setText(self._original_settings.get("download_dir", ""))
        self.download_dir_path.setPlaceholderText("选择下载目录...")
        self.download_dir_path.setReadOnly(True)
        download_path_layout.addWidget(self.download_dir_path, 1)
        
        download_browse_btn = QPushButton("📂 浏览")
        download_browse_btn.setFixedWidth(80)
        download_browse_btn.clicked.connect(self._browse_download_dir)
        download_path_layout.addWidget(download_browse_btn)
        
        download_layout.addLayout(download_path_layout)
        
        download_info = QLabel(f"💡 默认位置: {Path.home() / 'Downloads'}")
        download_info.setStyleSheet("color: #888; font-size: 11px;")
        download_layout.addWidget(download_info)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        docs_group = QGroupBox("📄 文档目录")
        docs_layout = QVBoxLayout()
        
        docs_hint = QLabel("设置文档文件的默认存储位置")
        docs_hint.setStyleSheet("color: #666; font-size: 12px;")
        docs_hint.setWordWrap(True)
        docs_layout.addWidget(docs_hint)
        
        docs_path_layout = QHBoxLayout()
        self.documents_dir_path = QLineEdit()
        self.documents_dir_path.setText(self._original_settings.get("documents_dir", ""))
        self.documents_dir_path.setPlaceholderText("选择文档目录...")
        self.documents_dir_path.setReadOnly(True)
        docs_path_layout.addWidget(self.documents_dir_path, 1)
        
        docs_browse_btn = QPushButton("📂 浏览")
        docs_browse_btn.setFixedWidth(80)
        docs_browse_btn.clicked.connect(self._browse_documents_dir)
        docs_path_layout.addWidget(docs_browse_btn)
        
        docs_layout.addLayout(docs_path_layout)
        
        docs_info = QLabel(f"💡 默认位置: {Path.home() / 'Documents'}")
        docs_info.setStyleSheet("color: #888; font-size: 11px;")
        docs_layout.addWidget(docs_info)
        
        docs_group.setLayout(docs_layout)
        layout.addWidget(docs_group)
        
        pictures_group = QGroupBox("🖼️ 图片目录")
        pictures_layout = QVBoxLayout()
        
        pictures_hint = QLabel("设置图片文件的默认存储位置")
        pictures_hint.setStyleSheet("color: #666; font-size: 12px;")
        pictures_hint.setWordWrap(True)
        pictures_layout.addWidget(pictures_hint)
        
        pictures_path_layout = QHBoxLayout()
        self.pictures_dir_path = QLineEdit()
        self.pictures_dir_path.setText(self._original_settings.get("pictures_dir", ""))
        self.pictures_dir_path.setPlaceholderText("选择图片目录...")
        self.pictures_dir_path.setReadOnly(True)
        pictures_path_layout.addWidget(self.pictures_dir_path, 1)
        
        pictures_browse_btn = QPushButton("📂 浏览")
        pictures_browse_btn.setFixedWidth(80)
        pictures_browse_btn.clicked.connect(self._browse_pictures_dir)
        pictures_path_layout.addWidget(pictures_browse_btn)
        
        pictures_layout.addLayout(pictures_path_layout)
        
        pictures_info = QLabel(f"💡 默认位置: {Path.home() / 'Pictures'}")
        pictures_info.setStyleSheet("color: #888; font-size: 11px;")
        pictures_layout.addWidget(pictures_info)
        
        pictures_group.setLayout(pictures_layout)
        layout.addWidget(pictures_group)
        
        layout.addStretch()
        
        return widget
    
    def _browse_music_library(self):
        """Browse for music library directory"""
        current_path = self.music_library_path.text() or str(Path.home() / "Music")
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择音乐库目录", current_path
        )
        if dir_path:
            self.music_library_path.setText(dir_path)
    
    def _browse_download_dir(self):
        """Browse for download directory"""
        current_path = self.download_dir_path.text() or str(Path.home() / "Downloads")
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择下载目录", current_path
        )
        if dir_path:
            self.download_dir_path.setText(dir_path)
    
    def _browse_documents_dir(self):
        """Browse for documents directory"""
        current_path = self.documents_dir_path.text() or str(Path.home() / "Documents")
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择文档目录", current_path
        )
        if dir_path:
            self.documents_dir_path.setText(dir_path)
    
    def _browse_pictures_dir(self):
        """Browse for pictures directory"""
        current_path = self.pictures_dir_path.text() or str(Path.home() / "Pictures")
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择图片目录", current_path
        )
        if dir_path:
            self.pictures_dir_path.setText(dir_path)

    def _create_llm_tab(self) -> QWidget:
        """Create LLM settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        provider_group = QGroupBox("模型提供商")
        provider_layout = QFormLayout()
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["dashscope"])
        self.provider_combo.setCurrentText(self._original_settings["llm_provider"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addRow("提供商:", self.provider_combo)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        self.dashscope_group = QGroupBox("通义千问 (Dashscope)")
        dashscope_layout = QFormLayout()
        
        self.dashscope_api_key = QLineEdit()
        self.dashscope_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.dashscope_api_key.setText(self._original_settings["dashscope_api_key"])
        self.dashscope_api_key.setPlaceholderText("输入通义千问 API Key")
        dashscope_layout.addRow("API Key:", self.dashscope_api_key)
        
        self.dashscope_model = QComboBox()
        self.dashscope_model.addItems(["qwen-plus", "qwen-turbo", "qwen-max", "qwen-max-longcontext"])
        self.dashscope_model.setCurrentText(self._original_settings["dashscope_model"])
        dashscope_layout.addRow("模型:", self.dashscope_model)
        
        self.dashscope_search = QCheckBox("启用联网搜索")
        self.dashscope_search.setChecked(self._original_settings["dashscope_enable_search"])
        dashscope_layout.addRow("", self.dashscope_search)
        
        self.dashscope_group.setLayout(dashscope_layout)
        layout.addWidget(self.dashscope_group)
        
        self.voice_group = QGroupBox("🎤 语音识别设置")
        voice_layout = QFormLayout()
        
        self.voice_provider = QComboBox()
        self.voice_provider.addItems(["dashscope", "funasr", "speech_recognition"])
        self.voice_provider.setCurrentText(self._original_settings["voice_provider"])
        voice_layout.addRow("语音识别引擎:", self.voice_provider)
        
        self.voice_dashscope_api_key = QLineEdit()
        self.voice_dashscope_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.voice_dashscope_api_key.setText(self._original_settings["voice_dashscope_api_key"])
        self.voice_dashscope_api_key.setPlaceholderText("输入阿里云 DashScope API Key（用于语音识别）")
        voice_layout.addRow("语音 API Key:", self.voice_dashscope_api_key)
        
        voice_hint = QLabel("💡 语音识别 API Key 可与通义千问共用，也可单独设置")
        voice_hint.setStyleSheet("color: #888; font-size: 11px;")
        voice_layout.addRow("", voice_hint)
        
        self.voice_group.setLayout(voice_layout)
        layout.addWidget(self.voice_group)
        
        self.tts_group = QGroupBox("🔊 语音合成设置 (TTS)")
        tts_layout = QFormLayout()
        
        self.tts_enabled = QCheckBox("启用语音合成")
        self.tts_enabled.setChecked(self._original_settings.get("tts_enabled", True))
        tts_layout.addRow("", self.tts_enabled)
        
        self.tts_voice = QComboBox()
        self.tts_voice.addItems([
            "longyue_v3 - 龙悦v3 (活力女声)",
            "longyingjing_v3 - 龙盈京v3 (京味女声)",
            "longfei_v3 - 龙飞v3 (磁性男声)",
            "longshuo_v3 - 龙硕v3 (沉稳男声)",
            "longjielidou_v3 - 龙杰力豆v3 (童声)",
        ])
        saved_voice = self._original_settings.get("tts_voice", "longyue_v3")
        for i in range(self.tts_voice.count()):
            if self.tts_voice.itemText(i).startswith(saved_voice):
                self.tts_voice.setCurrentIndex(i)
                break
        tts_layout.addRow("语音角色:", self.tts_voice)
        
        self.tts_speech_rate = QComboBox()
        self.tts_speech_rate.addItems(["0.5 - 很慢", "0.75 - 较慢", "1.0 - 正常", "1.25 - 较快", "1.5 - 很快", "2.0 - 极快"])
        saved_rate = str(self._original_settings.get("tts_speech_rate", 1.0))
        for i in range(self.tts_speech_rate.count()):
            if self.tts_speech_rate.itemText(i).startswith(saved_rate):
                self.tts_speech_rate.setCurrentIndex(i)
                break
        tts_layout.addRow("语速:", self.tts_speech_rate)
        
        tts_hint = QLabel("💡 语音合成使用与通义千问相同的 API Key")
        tts_hint.setStyleSheet("color: #888; font-size: 11px;")
        tts_layout.addRow("", tts_hint)
        
        test_tts_btn = QPushButton("🔊 测试语音合成")
        test_tts_btn.clicked.connect(self._test_tts)
        tts_layout.addRow("", test_tts_btn)
        
        self.tts_group.setLayout(tts_layout)
        layout.addWidget(self.tts_group)
        
        layout.addStretch()
        
        self._on_provider_changed(self.provider_combo.currentText())
        
        return widget
    
    def _create_security_tab(self) -> QWidget:
        """Create security settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        dirs_group = QGroupBox("允许访问的目录")
        dirs_layout = QVBoxLayout()
        
        dirs_hint = QLabel("智能体可以访问以下目录中的文件：")
        dirs_hint.setStyleSheet("color: #666; font-size: 12px;")
        dirs_layout.addWidget(dirs_hint)
        
        dirs_list_layout = QHBoxLayout()
        
        self.allowed_dirs_list = QListWidget()
        dirs = self._original_settings["allowed_directories"].split(",")
        for d in dirs:
            d = d.strip()
            if d:
                self.allowed_dirs_list.addItem(d)
        dirs_list_layout.addWidget(self.allowed_dirs_list)
        
        dirs_btn_layout = QVBoxLayout()
        
        add_dir_btn = QPushButton("➕ 添加目录")
        add_dir_btn.clicked.connect(self._add_allowed_dir)
        dirs_btn_layout.addWidget(add_dir_btn)
        
        remove_dir_btn = QPushButton("➖ 移除选中")
        remove_dir_btn.clicked.connect(self._remove_allowed_dir)
        dirs_btn_layout.addWidget(remove_dir_btn)
        
        dirs_btn_layout.addStretch()
        dirs_list_layout.addLayout(dirs_btn_layout)
        
        dirs_layout.addLayout(dirs_list_layout)
        dirs_group.setLayout(dirs_layout)
        layout.addWidget(dirs_group)
        
        cmds_group = QGroupBox("禁止执行的命令")
        cmds_layout = QVBoxLayout()
        
        cmds_hint = QLabel("以下命令关键词将被阻止执行：")
        cmds_hint.setStyleSheet("color: #666; font-size: 12px;")
        cmds_layout.addWidget(cmds_hint)
        
        self.dangerous_commands = QLineEdit()
        self.dangerous_commands.setText(self._original_settings["dangerous_commands"])
        self.dangerous_commands.setPlaceholderText("format, sudo, su, ...")
        cmds_layout.addWidget(self.dangerous_commands)
        
        cmds_note = QLabel("💡 多个命令用逗号分隔，例如: format, sudo, su")
        cmds_note.setStyleSheet("color: #888; font-size: 11px;")
        cmds_layout.addWidget(cmds_note)
        
        cmds_group.setLayout(cmds_layout)
        layout.addWidget(cmds_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        ha_group = QGroupBox("🏠 智能家居配置 (Home Assistant)")
        ha_layout = QVBoxLayout()
        
        ha_enabled_layout = QHBoxLayout()
        self.ha_enabled = QCheckBox("启用智能家居控制")
        self.ha_enabled.setChecked(self._original_settings.get("homeassistant_enabled", False))
        ha_enabled_layout.addWidget(self.ha_enabled)
        ha_enabled_layout.addStretch()
        ha_layout.addLayout(ha_enabled_layout)
        
        ha_hint = QLabel("💡 获取令牌: Home Assistant → 用户设置 → 长期访问令牌 → 创建令牌。未配置时将使用模拟设备进行测试")
        ha_hint.setStyleSheet("color: #666; font-size: 11px;")
        ha_hint.setWordWrap(True)
        ha_layout.addWidget(ha_hint)
        
        ha_inputs_layout = QHBoxLayout()
        
        url_layout = QVBoxLayout()
        url_label = QLabel("Home Assistant URL:")
        self.ha_url = QLineEdit()
        self.ha_url.setText(self._original_settings.get("homeassistant_url", ""))
        self.ha_url.setPlaceholderText("http://homeassistant.local:8123")
        self.ha_url.setMinimumHeight(32)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.ha_url)
        
        token_layout = QVBoxLayout()
        token_label = QLabel("访问令牌:")
        self.ha_token = QLineEdit()
        self.ha_token.setText(self._original_settings.get("homeassistant_token", ""))
        self.ha_token.setPlaceholderText("长期访问令牌")
        self.ha_token.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.ha_token.setMinimumHeight(32)
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.ha_token)
        
        ha_inputs_layout.addLayout(url_layout)
        ha_inputs_layout.addLayout(token_layout)
        ha_layout.addLayout(ha_inputs_layout)
        
        ha_group.setLayout(ha_layout)
        layout.addWidget(ha_group)
        
        data_group = QGroupBox("📊 股票数据源配置")
        data_layout = QFormLayout()
        
        self.tushare_token = QLineEdit()
        self.tushare_token.setText(self._original_settings.get("tushare_token", ""))
        self.tushare_token.setPlaceholderText("Tushare API Token（用于股票查询）")
        self.tushare_token.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.tushare_token.setMinimumHeight(32)
        data_layout.addRow("Tushare Token:", self.tushare_token)
        
        tushare_hint = QLabel("获取 Token: <a href='https://tushare.pro/'>tushare.pro</a>")
        tushare_hint.setOpenExternalLinks(True)
        tushare_hint.setStyleSheet("color: #666; font-size: 11px;")
        data_layout.addRow("", tushare_hint)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        perf_group = QGroupBox("性能配置")
        perf_layout = QFormLayout()
        
        self.max_iterations = QSpinBox()
        self.max_iterations.setRange(1, 50)
        self.max_iterations.setValue(self._original_settings["agent_max_iterations"])
        perf_layout.addRow("最大迭代次数:", self.max_iterations)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(30, 600)
        self.timeout.setValue(self._original_settings["agent_timeout"])
        self.timeout.setSuffix(" 秒")
        perf_layout.addRow("超时时间:", self.timeout)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        log_group = QGroupBox("日志配置")
        log_layout = QFormLayout()
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(self._original_settings["log_level"])
        log_layout.addRow("日志级别:", self.log_level)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        env_group = QGroupBox("环境变量")
        env_layout = QVBoxLayout()
        
        env_hint = QLabel("高级用户可以直接编辑 .env 文件：")
        env_hint.setStyleSheet("color: #666; font-size: 12px;")
        env_layout.addWidget(env_hint)
        
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        self.env_path_label = QLabel(f"📄 {env_path}")
        self.env_path_label.setStyleSheet("color: #0066cc; font-size: 11px;")
        self.env_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        env_layout.addWidget(self.env_path_label)
        
        open_env_btn = QPushButton("📂 打开 .env 文件")
        open_env_btn.clicked.connect(lambda: self._open_file(env_path))
        env_layout.addWidget(open_env_btn)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_about_tab(self) -> QWidget:
        """Create about tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <div style="padding: 20px;">
            <h2 style="color: #333;">🤖 个人智能助手</h2>
            <p style="color: #666; font-size: 14px;">版本: 1.0.0</p>
            
            <h3 style="color: #444;">功能特性</h3>
            <ul style="color: #555; line-height: 1.8;">
                <li>🧠 多模型支持：智谱AI、通义千问、OpenAI</li>
                <li>📁 文件操作：读取、写入、搜索、管理文件</li>
                <li>🌐 联网搜索：实时信息查询</li>
                <li>💻 代码执行：Python、Shell 脚本</li>
                <li>📦 软件安装：自动下载安装常用软件</li>
                <li>🛠️ 技能扩展：支持 OpenClaw 技能</li>
                <li>💬 记忆管理：长期记忆对话历史</li>
            </ul>
            
            <h3 style="color: #444;">技术栈</h3>
            <ul style="color: #555; line-height: 1.8;">
                <li>Python 3.10+</li>
                <li>PyQt6 (GUI)</li>
                <li>LangChain (Agent Framework)</li>
                <li>ChromaDB (Vector Store)</li>
            </ul>
            
            <h3 style="color: #444;">使用提示</h3>
            <p style="color: #555; line-height: 1.6;">
                1. 首次使用请配置大模型 API Key<br>
                2. 根据需要调整权限设置<br>
                3. 可以通过 Skills 管理安装更多技能<br>
                4. 高级设置可直接编辑 .env 文件
            </p>
        </div>
        """)
        
        layout.addWidget(about_text)
        
        return widget
    
    def _on_provider_changed(self, provider: str):
        """Handle provider change"""
        self.dashscope_group.setVisible(provider == "dashscope")
        self.voice_group.setVisible(True)
        self.tts_group.setVisible(provider == "dashscope")
    
    def _test_tts(self):
        """测试语音合成"""
        import asyncio
        import concurrent.futures
        from ..tts import init_tts
        
        api_key = self.dashscope_api_key.text()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入通义千问 API Key")
            return
        
        voice = self.tts_voice.currentText().split(" - ")[0] if " - " in self.tts_voice.currentText() else "zhichu"
        
        def run_test():
            try:
                tts = init_tts(api_key=api_key)
                tts.set_voice(voice)
                
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    success = new_loop.run_until_complete(tts.speak("语音合成测试成功，欢迎使用智能助手！"))
                finally:
                    new_loop.close()
                
                return success
            except Exception as e:
                import traceback
                traceback.print_exc()
                return str(e)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_test)
            result = future.result(timeout=30)
        
        if result is True:
            QMessageBox.information(self, "测试成功", "语音合成测试成功！")
        elif isinstance(result, str):
            QMessageBox.critical(self, "错误", f"语音合成测试失败：{result}")
        else:
            QMessageBox.warning(self, "测试失败", "语音合成测试失败，请检查 API Key 是否正确")
    
    def _add_allowed_dir(self):
        """Add a new allowed directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录")
        if dir_path:
            self.allowed_dirs_list.addItem(dir_path)
    
    def _remove_allowed_dir(self):
        """Remove selected directory"""
        current = self.allowed_dirs_list.currentRow()
        if current >= 0:
            self.allowed_dirs_list.takeItem(current)
    
    def _open_file(self, path: Path):
        """Open file with default editor"""
        if path.exists():
            os.startfile(str(path))
        else:
            QMessageBox.warning(self, "文件不存在", f"文件不存在: {path}")
    
    def _save_settings(self):
        """Save settings to .env file"""
        try:
            env_path = Path(__file__).parent.parent.parent.parent / ".env"
            
            allowed_dirs = []
            for i in range(self.allowed_dirs_list.count()):
                allowed_dirs.append(self.allowed_dirs_list.item(i).text())
            
            new_settings = {
                "LLM_PROVIDER": self.provider_combo.currentText(),
                "DASHSCOPE_API_KEY": self.dashscope_api_key.text(),
                "DASHSCOPE_MODEL": self.dashscope_model.currentText(),
                "DASHSCOPE_ENABLE_SEARCH": str(self.dashscope_search.isChecked()).lower(),
                "AGENT_NAME": self.agent_name.text(),
                "AGENT_GENDER": self.agent_gender.currentText(),
                "AGENT_VOICE": self.agent_voice.currentText(),
                "AGENT_PERSONALITY": self.agent_personality.currentText(),
                "AGENT_GREETING": self.agent_greeting.text(),
                "AGENT_AVATAR": self.agent_avatar.text(),
                "AGENT_EMAIL": self.agent_email.text(),
                "AGENT_EMAIL_PASSWORD": self.agent_email_password.text(),
                "AGENT_EMAIL_SMTP": self.agent_email_smtp.currentText(),
                "AGENT_EMAIL_PORT": str(self.agent_email_port.value()),
                "AGENT_MAX_ITERATIONS": str(self.max_iterations.value()),
                "AGENT_TIMEOUT": str(self.timeout.value()),
                "ALLOWED_DIRECTORIES": ",".join(allowed_dirs),
                "DANGEROUS_COMMANDS": self.dangerous_commands.text(),
                "LOG_LEVEL": self.log_level.currentText(),
                "USER_NAME": self.user_name.text(),
                "USER_FORMAL_NAME": self.user_formal_name.text(),
                "USER_EMAIL": self.user_email.text(),
                "USER_PHONE": self.user_phone.text(),
                "USER_ADDRESS": self.user_address.text(),
                "USER_CITY": self.user_city.text(),
                "USER_TIMEZONE": self.user_timezone.currentText(),
                "MUSIC_LIBRARY_PATH": self.music_library_path.text(),
                "DOWNLOAD_DIR": self.download_dir_path.text(),
                "DOCUMENTS_DIR": self.documents_dir_path.text(),
                "PICTURES_DIR": self.pictures_dir_path.text(),
                "VOICE_PROVIDER": self.voice_provider.currentText(),
                "VOICE_DASHSCOPE_API_KEY": self.voice_dashscope_api_key.text(),
                "TTS_ENABLED": str(self.tts_enabled.isChecked()).lower(),
                "TTS_VOICE": self.tts_voice.currentText().split(" - ")[0] if " - " in self.tts_voice.currentText() else self.tts_voice.currentText(),
                "TTS_SPEECH_RATE": self.tts_speech_rate.currentText().split(" - ")[0] if " - " in self.tts_speech_rate.currentText() else "1.0",
                "TUSHARE_TOKEN": self.tushare_token.text(),
                "HOMEASSISTANT_ENABLED": str(self.ha_enabled.isChecked()).lower(),
                "HOMEASSISTANT_URL": self.ha_url.text(),
                "HOMEASSISTANT_TOKEN": self.ha_token.text(),
            }
            
            existing_content = ""
            if env_path.exists():
                existing_content = env_path.read_text(encoding="utf-8")
            
            lines = existing_content.split("\n")
            updated_keys = set()
            new_lines = []
            
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    key = line.split("=")[0].strip()
                    if key in new_settings:
                        value = new_settings[key]
                        new_lines.append(f"{key}={value}")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            for key, value in new_settings.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}")
            
            env_path.write_text("\n".join(new_lines), encoding="utf-8")
            
            from ..config import settings
            from ..user_config import user_config
            settings.directory.music_library = self.music_library_path.text()
            settings.directory.download_dir = self.download_dir_path.text()
            settings.directory.documents_dir = self.documents_dir_path.text()
            settings.directory.pictures_dir = self.pictures_dir_path.text()
            settings.user.name = self.user_name.text()
            settings.user.city = self.user_city.text()
            settings.agent.name = self.agent_name.text() or "小助手"
            
            # 同步更新 user_config.json
            user_config.user_name = self.user_name.text()
            user_config.formal_name = self.user_formal_name.text()
            
            # 更新 tushare token
            settings.user.tushare_token = self.tushare_token.text()
            
            # 更新 homeassistant 配置
            if hasattr(settings, 'homeassistant'):
                settings.homeassistant.enabled = self.ha_enabled.isChecked()
                settings.homeassistant.url = self.ha_url.text()
                settings.homeassistant.token = self.ha_token.text()
            
            from ..tts import get_tts_manager
            tts = get_tts_manager()
            tts_enabled = self.tts_enabled.isChecked()
            if tts_enabled:
                tts.enable()
            else:
                tts.disable()
            
            QMessageBox.information(
                self,
                "保存成功",
                "设置已保存！\n\n部分设置需要重启智能体才能生效。"
            )
            
            self.settings_changed.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存设置时出错：\n{str(e)}")
    
    def _apply_styles(self):
        """Apply styles to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333;
            }
            QLineEdit, QComboBox, QSpinBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #0078d4;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #e0e0e0;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d4;
            }
        """)
