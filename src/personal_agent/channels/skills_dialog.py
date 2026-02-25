"""
Skills Manager Dialog - GUI for managing skills
"""
import asyncio
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QTabWidget, QWidget, QProgressBar, QMessageBox,
    QSplitter, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ..skills import SkillsRepository, SkillInfo, skills_repository, skill_manager


class SkillsWorker(QThread):
    """Worker thread for fetching skills"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str, int)
    error = pyqtSignal(str)
    
    def __init__(self, repository: SkillsRepository):
        super().__init__()
        self.repository = repository
    
    def run(self):
        async def fetch():
            self.repository.set_progress_callback(
                lambda msg, prog: self.progress.emit(msg, prog)
            )
            skills = await self.repository.fetch_available_skills()
            self.finished.emit(skills)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(fetch())
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()


class DownloadWorker(QThread):
    """Worker thread for downloading skills"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str, int)
    error = pyqtSignal(str)
    
    def __init__(self, repository: SkillsRepository, skill_name: str):
        super().__init__()
        self.repository = repository
        self.skill_name = skill_name
    
    def run(self):
        async def download():
            self.repository.set_progress_callback(
                lambda msg, prog: self.progress.emit(msg, prog)
            )
            result = await self.repository.download_skill(self.skill_name)
            self.finished.emit(result)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(download())
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()


class SkillsManagerDialog(QDialog):
    """Dialog for managing skills"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛠️ Skills 技能管理")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #24292f;
            }
            QPushButton {
                background-color: #1f883d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1a7f37;
            }
            QPushButton:disabled {
                background-color: #8c959f;
            }
            QPushButton#uninstallBtn {
                background-color: #cf222e;
            }
            QPushButton#uninstallBtn:hover {
                background-color: #a40e26;
            }
            QPushButton#refreshBtn {
                background-color: #0969da;
            }
            QPushButton#refreshBtn:hover {
                background-color: #0550ae;
            }
            QListWidget {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background-color: #f6f8fa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #d0d7de;
            }
            QListWidget::item:selected {
                background-color: #ddf4ff;
                color: #24292f;
            }
            QTextEdit {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background-color: #f6f8fa;
                padding: 8px;
            }
            QLineEdit {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 8px;
                background-color: #ffffff;
            }
            QComboBox {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 6px;
                background-color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #d0d7de;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1f883d;
            }
        """)
        
        self.repository = SkillsRepository(Path("skills"))
        self.skills_list: List[SkillInfo] = []
        self.current_skill: Optional[SkillInfo] = None
        
        self._init_ui()
        self._load_skills()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🛠️ Skills 技能管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入技能名称或关键词...")
        self.search_input.textChanged.connect(self._filter_skills)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        category_layout = QHBoxLayout()
        category_label = QLabel("📁 分类:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部")
        self.category_combo.currentTextChanged.connect(self._filter_by_category)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        layout.addLayout(category_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.skills_list_widget = QListWidget()
        self.skills_list_widget.itemClicked.connect(self._on_skill_selected)
        left_layout.addWidget(self.skills_list_widget)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 刷新列表")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.clicked.connect(self._load_skills)
        btn_layout.addWidget(self.refresh_btn)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_frame)
        
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.detail_title = QLabel("选择一个技能查看详情")
        self.detail_title.setFont(QFont("", 14, QFont.Weight.Bold))
        right_layout.addWidget(self.detail_title)
        
        self.detail_info = QTextEdit()
        self.detail_info.setReadOnly(True)
        self.detail_info.setPlaceholderText("技能详情将显示在这里...")
        right_layout.addWidget(self.detail_info)
        
        action_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("📥 安装")
        self.install_btn.clicked.connect(self._install_skill)
        self.install_btn.setEnabled(False)
        action_layout.addWidget(self.install_btn)
        
        self.uninstall_btn = QPushButton("🗑️ 卸载")
        self.uninstall_btn.setObjectName("uninstallBtn")
        self.uninstall_btn.clicked.connect(self._uninstall_skill)
        self.uninstall_btn.setEnabled(False)
        action_layout.addWidget(self.uninstall_btn)
        
        right_layout.addLayout(action_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #57606a; font-size: 12px;")
        right_layout.addWidget(self.status_label)
        
        splitter.addWidget(right_frame)
        
        splitter.setSizes([400, 500])
        layout.addWidget(splitter)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _load_skills(self):
        """Load skills from repository"""
        self.status_label.setText("正在加载技能列表...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.refresh_btn.setEnabled(False)
        
        self.worker = SkillsWorker(self.repository)
        self.worker.finished.connect(self._on_skills_loaded)
        self.worker.progress.connect(self._on_progress)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_skills_loaded(self, skills: List[SkillInfo]):
        """Handle skills loaded"""
        self.skills_list = skills
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"共 {len(skills)} 个技能")
        
        self._update_skills_list()
        self._update_categories()
    
    def _on_progress(self, message: str, progress: int):
        """Handle progress update"""
        self.status_label.setText(message)
        if progress >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
    
    def _on_error(self, error: str):
        """Handle error"""
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"错误: {error}")
        QMessageBox.warning(self, "错误", f"加载技能失败: {error}")
    
    def _update_skills_list(self):
        """Update skills list widget"""
        self.skills_list_widget.clear()
        
        for skill in self.skills_list:
            item = QListWidgetItem()
            
            status_icon = "✅" if skill.installed else "📦"
            item.setText(f"{status_icon} {skill.name}")
            item.setData(Qt.ItemDataRole.UserRole, skill.name)
            
            if skill.installed:
                item.setForeground(Qt.GlobalColor.darkGreen)
            
            self.skills_list_widget.addItem(item)
    
    def _update_categories(self):
        """Update category combo box"""
        categories = set(["全部"])
        for skill in self.skills_list:
            categories.add(skill.category)
        
        self.category_combo.clear()
        self.category_combo.addItems(sorted(categories))
    
    def _filter_skills(self, text: str):
        """Filter skills by search text"""
        for i in range(self.skills_list_widget.count()):
            item = self.skills_list_widget.item(i)
            skill_name = item.data(Qt.ItemDataRole.UserRole)
            skill = next((s for s in self.skills_list if s.name == skill_name), None)
            
            if skill:
                visible = (
                    text.lower() in skill.name.lower() or
                    text.lower() in skill.description.lower() or
                    any(text.lower() in tag.lower() for tag in skill.tags)
                )
                item.setHidden(not visible)
    
    def _filter_by_category(self, category: str):
        """Filter skills by category"""
        for i in range(self.skills_list_widget.count()):
            item = self.skills_list_widget.item(i)
            skill_name = item.data(Qt.ItemDataRole.UserRole)
            skill = next((s for s in self.skills_list if s.name == skill_name), None)
            
            if skill:
                visible = category == "全部" or skill.category == category
                item.setHidden(not visible)
    
    def _on_skill_selected(self, item: QListWidgetItem):
        """Handle skill selection"""
        skill_name = item.data(Qt.ItemDataRole.UserRole)
        self.current_skill = next((s for s in self.skills_list if s.name == skill_name), None)
        
        if self.current_skill:
            self._show_skill_detail(self.current_skill)
    
    def _show_skill_detail(self, skill: SkillInfo):
        """Show skill details"""
        self.detail_title.setText(f"📦 {skill.name}")
        
        status = "✅ 已安装" if skill.installed else "📦 未安装"
        
        info = f"""
<strong>状态:</strong> {status}

<strong>描述:</strong>
{skill.description}

<strong>作者:</strong> {skill.author}
<strong>版本:</strong> {skill.version}
<strong>分类:</strong> {skill.category}
<strong>标签:</strong> {', '.join(skill.tags) if skill.tags else '无'}

<strong>使用说明:</strong>
当用户请求相关功能时，智能体会自动调用此技能。
"""
        
        self.detail_info.setHtml(info)
        
        self.install_btn.setEnabled(not skill.installed)
        self.uninstall_btn.setEnabled(skill.installed)
    
    def _install_skill(self):
        """Install selected skill"""
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.name
        
        self.status_label.setText(f"正在安装 {skill_name}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.install_btn.setEnabled(False)
        
        self.download_worker = DownloadWorker(self.repository, skill_name)
        self.download_worker.finished.connect(self._on_install_finished)
        self.download_worker.progress.connect(self._on_progress)
        self.download_worker.error.connect(self._on_error)
        self.download_worker.start()
    
    def _on_install_finished(self, result: dict):
        """Handle install finished"""
        self.progress_bar.setVisible(False)
        
        if result.get("success"):
            self.status_label.setText("安装成功！")
            QMessageBox.information(self, "成功", result.get("message", "安装成功"))
            
            if self.current_skill:
                self.current_skill.installed = True
                self._update_skills_list()
                self._show_skill_detail(self.current_skill)
        else:
            self.status_label.setText(f"安装失败: {result.get('error', '未知错误')}")
            QMessageBox.warning(self, "失败", f"安装失败: {result.get('error', '未知错误')}")
    
    def _uninstall_skill(self):
        """Uninstall selected skill"""
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.name
        
        reply = QMessageBox.question(
            self,
            "确认卸载",
            f"确定要卸载技能 '{skill_name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            async def uninstall():
                result = await self.repository.uninstall_skill(skill_name)
                return result
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(uninstall())
                
                if result.get("success"):
                    self.status_label.setText("卸载成功！")
                    QMessageBox.information(self, "成功", result.get("message", "卸载成功"))
                    
                    if self.current_skill:
                        self.current_skill.installed = False
                        self._update_skills_list()
                        self._show_skill_detail(self.current_skill)
                else:
                    self.status_label.setText(f"卸载失败: {result.get('error', '未知错误')}")
                    QMessageBox.warning(self, "失败", f"卸载失败: {result.get('error', '未知错误')}")
            finally:
                loop.close()
