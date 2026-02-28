"""
Agent Manager Dialog - GUI for managing sub-agents
"""
import asyncio
from typing import Dict, List, Optional, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QCheckBox, QWidget, QAbstractItemView, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont
from loguru import logger

from ..config_center import config_center, AgentMeta
from ..multi_agent_system import multi_agent_system


class AgentManagerDialog(QDialog):
    """Dialog for managing sub-agents"""
    
    agents_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🤖 子智能体管理")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)
        
        self._loaded_agents: Set[str] = set()
        self._agent_metadata: Dict[str, AgentMeta] = {}
        
        self._load_agent_info()
        self._init_ui()
        self._apply_styles()
    
    def _load_agent_info(self):
        """Load agent information"""
        self._agent_metadata = config_center.get_all_agents(include_hidden=True)
        
        if multi_agent_system.master and hasattr(multi_agent_system.master, 'sub_agents'):
            self._loaded_agents = set(multi_agent_system.master.sub_agents.keys())
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        header_label = QLabel("查看所有子智能体及其使用说明")
        header_label.setStyleSheet("font-size: 14px; color: #666; padding: 5px 0;")
        layout.addWidget(header_label)
        
        self._create_stats_section(layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["状态", "名称", "描述", "能力", "操作"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 350)
        self.table.setColumnWidth(4, 150)
        
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:hover {
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        layout.addWidget(self.table)
        
        self.table.verticalHeader().setDefaultSectionSize(48)
        
        self._populate_table()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._refresh_agents)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_stats_section(self, layout: QVBoxLayout):
        """Create statistics section"""
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout(stats_group)
        
        total_count = len(self._agent_metadata)
        loaded_count = len(self._loaded_agents)
        hidden_count = sum(1 for m in self._agent_metadata.values() if m.hidden)
        
        self.total_label = QLabel(f"📊 总计: {total_count}")
        self.loaded_label = QLabel(f"✅ 已加载: {loaded_count}")
        self.hidden_label = QLabel(f"🔒 隐藏: {hidden_count}")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.loaded_label)
        stats_layout.addWidget(self.hidden_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
    
    def _populate_table(self):
        """Populate the table with agent data"""
        self.table.setRowCount(0)
        
        sorted_agents = sorted(
            self._agent_metadata.items(),
            key=lambda x: (x[1].hidden, x[1].priority, x[0])
        )
        
        for agent_name, meta in sorted_agents:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            is_loaded = agent_name in self._loaded_agents
            is_hidden = meta.hidden
            
            status_item = QTableWidgetItem()
            if is_loaded:
                status_item.setText("✅")
                status_item.setForeground(QColor("#28a745"))
                status_item.setToolTip("已加载")
            elif is_hidden:
                status_item.setText("🔒")
                status_item.setForeground(QColor("#6c757d"))
                status_item.setToolTip("隐藏")
            else:
                status_item.setText("⏸️")
                status_item.setForeground(QColor("#ffc107"))
                status_item.setToolTip("未加载")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, status_item)
            
            display_name = f"{meta.icon} {meta.display_name or agent_name}"
            name_item = QTableWidgetItem(display_name)
            if is_hidden:
                name_item.setForeground(QColor("#6c757d"))
            self.table.setItem(row, 1, name_item)
            
            desc = meta.description or "-"
            if len(desc) > 50:
                desc = desc[:47] + "..."
            desc_item = QTableWidgetItem(desc)
            if is_hidden:
                desc_item.setForeground(QColor("#6c757d"))
            self.table.setItem(row, 2, desc_item)
            
            capabilities = ", ".join(meta.capabilities[:3])
            if len(meta.capabilities) > 3:
                capabilities += f" (+{len(meta.capabilities) - 3})"
            cap_item = QTableWidgetItem(capabilities or "-")
            if is_hidden:
                cap_item.setForeground(QColor("#6c757d"))
            self.table.setItem(row, 3, cap_item)
            
            action_widget = self._create_action_widget(agent_name, meta, is_hidden)
            self.table.setCellWidget(row, 4, action_widget)
    
    def _create_action_widget(self, agent_name: str, meta: AgentMeta, is_hidden: bool) -> QWidget:
        """Create action buttons for an agent"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(2)
        
        if is_hidden:
            label = QLabel("隐藏")
            label.setStyleSheet("color: #6c757d;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        else:
            help_btn = QPushButton("📖 使用说明")
            help_btn.setFixedSize(120, 36)
            help_btn.clicked.connect(lambda checked, name=agent_name, m=meta: self._show_agent_help(name, m))
            layout.addWidget(help_btn)
        
        layout.addStretch()
        return widget
    
    def _show_agent_help(self, agent_name: str, meta: AgentMeta):
        """Show agent help information"""
        try:
            import asyncio
            
            # 从主智能体获取帮助信息
            if multi_agent_system.master:
                try:
                    help_text = asyncio.run(self._get_agent_help_from_master(agent_name))
                    if help_text:
                        self._show_help_dialog(meta.display_name or agent_name, help_text)
                        return
                except RuntimeError as e:
                    # 如果在已有事件循环中，使用 create_task 方式
                    logger.debug(f"在已有事件循环中，使用异步方式获取帮助：{e}")
                    import nest_asyncio
                    try:
                        nest_asyncio.apply()
                        loop = asyncio.get_event_loop()
                        help_text = loop.run_until_complete(self._get_agent_help_from_master(agent_name))
                        if help_text:
                            self._show_help_dialog(meta.display_name or agent_name, help_text)
                            return
                    except Exception as nest_error:
                        logger.error(f"使用 nest_asyncio 获取帮助失败：{nest_error}")
            
            # 无法获取帮助信息，显示错误
            logger.error(f"❌ 无法获取智能体 {agent_name} 的帮助信息")
            self._show_help_dialog(
                meta.display_name or agent_name, 
                f"❌ 无法获取 {meta.display_name or agent_name} 的帮助信息，请稍后重试"
            )
            
        except Exception as e:
            logger.error(f"获取智能体帮助失败：{e}")
            self._show_help_dialog(
                meta.display_name or agent_name, 
                f"❌ 获取帮助信息失败：{str(e)}"
            )
    
    async def _get_agent_help_from_master(self, agent_name: str) -> Optional[str]:
        """从主智能体获取帮助信息（直接调用 master 的方法）"""
        try:
            # 直接调用 master 的 _get_agent_help_from_skill 方法
            if multi_agent_system.master:
                help_text = await multi_agent_system.master._get_agent_help_from_skill(agent_name)
                if help_text and not help_text.startswith("❌"):
                    return help_text
            return None
            
        except Exception as e:
            logger.error(f"获取智能体帮助失败：{e}")
            return None
    
    def _show_help_dialog(self, title: str, help_text: str):
        """Show help dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📖 {title} - 使用说明")
        dialog.setMinimumSize(500, 400)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(help_text)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        font = QFont("Microsoft YaHei", 10)
        text_edit.setFont(font)
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setFixedWidth(80)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        dialog.exec()
    
    def _get_agent_help_text(self, agent_name: str, meta: AgentMeta) -> str:
        """Get help text for an agent"""
        try:
            if multi_agent_system.master and agent_name in multi_agent_system.master.sub_agents:
                agent = multi_agent_system.master.sub_agents[agent_name]
                if hasattr(agent, '_get_help_info'):
                    return agent._get_help_info()
                elif hasattr(agent, '_get_help'):
                    return agent._get_help()
            
            help_map = {
                "music_agent": """## 🎵 音乐智能体

### 功能说明
音乐智能体可以播放本地音乐文件，支持多种音频格式。

### 使用方式
1. **直接对话**: @音乐智能体 播放周杰伦的歌
2. **播放控制**: 播放、暂停、停止、下一首、上一首
3. **音量控制**: 音量大一点、音量小一点、音量60%
4. **播放模式**: 顺序播放、随机播放、单曲循环
5. **音乐库**: 扫描音乐、查看播放列表

### 示例指令
- "播放周杰伦的稻香"
- "暂停音乐"
- "下一首"
- "音量大一点"
- "随机播放"
- "@音乐智能体 /？"
""",
                "weather_agent": """## 🌤️ 天气智能体

### 功能说明
天气智能体可以查询当前天气和未来天气预报。

### 使用方式
1. **当前天气**: 北京今天天气怎么样
2. **天气预报**: 上海明天天气、广州后天天气
3. **多日预报**: 未来三天天气

### 示例指令
- "北京今天天气"
- "上海明天天气怎么样"
- "广州后天会下雨吗"
- "@天气智能体 /？"
""",
                "tts_agent": """## 🔊 语音合成智能体

### 功能说明
语音合成智能体可以将文字转换为语音并播放。

### 使用方式
1. **直接合成**: @语音合成智能体 今天天气真好
2. **指定音色**: @语音合成智能体 你好 使用音色:longfei_v3
3. **查看音色**: 有哪些音色

### 示例指令
- "@语音合成智能体 你好，世界"
- "@语音合成智能体 欢迎使用 使用音色:zhichu"
- "@语音合成智能体 /？"
""",
                "crawler_agent": """## 🕷️ 爬虫智能体

### 功能说明
爬虫智能体可以搜索网络信息、抓取网页内容。

### 使用方式
1. **搜索**: @爬虫智能体 搜索人工智能
2. **抓取网页**: 抓取 https://example.com
3. **下载文件**: 下载图片/视频

### 示例指令
- "@爬虫智能体 人工智能最新进展"
- "搜索Python教程"
- "@爬虫智能体 /？"
""",
                "stock_query_agent": """## 📈 股票查询智能体

### 功能说明
股票查询智能体可以查询股票实时行情和历史数据。

### 使用方式
1. **查询股票**: 贵州茅台股价
2. **股票代码**: 600519 股票
3. **市场行情**: 大盘走势

### 示例指令
- "贵州茅台股价"
- "查询 000001 股票"
- "@股票智能体 /？"
""",
                "app_agent": """## 📱 应用智能体

### 功能说明
应用智能体可以管理系统应用程序和启动项。

### 使用方式
1. **查看应用**: 查看运行中的应用
2. **启动应用**: 打开微信
3. **关闭应用**: 关闭记事本
4. **启动项管理**: 查看启动项、禁用启动项

### 示例指令
- "查看运行中的应用"
- "打开微信"
- "关闭腾讯元宝"
- "查看启动项"
- "@应用智能体 /？"
""",
                "developer_agent": """## 💻 开发者智能体

### 功能说明
开发者智能体可以辅助代码开发、调试和文档生成。

### 使用方式
1. **代码生成**: 写一个Python脚本
2. **代码解释**: 解释这段代码
3. **Bug修复**: 帮我找bug
4. **文档生成**: 生成API文档

### 示例指令
- "写一个冒泡排序算法"
- "解释这段代码的作用"
- "@开发者智能体 /？"
""",
                "email_agent": """## 📧 邮件智能体

### 功能说明
邮件智能体可以发送和管理电子邮件。

### 使用方式
1. **发送邮件**: 发送邮件给xxx
2. **查看邮件**: 查看最新邮件
3. **邮件搜索**: 搜索包含xxx的邮件

### 示例指令
- "发送邮件给张三"
- "查看最新邮件"
- "@邮件智能体 /？"
""",
                "web_server_agent": """## 🌐 Web服务器智能体

### 功能说明
Web服务器智能体可以启动本地Web服务器，支持文件共享。

### 使用方式
1. **启动服务器**: 启动Web服务器
2. **停止服务器**: 停止Web服务器
3. **查看状态**: Web服务器状态

### 示例指令
- "启动Web服务器"
- "停止Web服务器"
- "@Web服务器智能体 /？"
""",
                "os_agent": """## 🖥️ 系统智能体

### 功能说明
系统智能体可以管理计算机系统设置和资源。

### 使用方式
1. **音量控制**: 静音、取消静音、音量大一点
2. **音频设备**: 切换音频输出、切换音频输入
3. **系统信息**: 系统信息、电池状态、磁盘空间
4. **清理垃圾**: 清理垃圾、清空回收站
5. **启动项**: 查看启动项、禁用启动项

### 示例指令
- "静音"
- "切换音频输出"
- "系统信息"
- "清理垃圾"
- "@系统智能体 /？"
""",
                "image_agent": """## 🖼️ 图片生成智能体

### 功能说明
图片生成智能体可以根据文字描述生成图片。

### 使用方式
1. **生成图片**: 画一只可爱的猫咪
2. **图片风格**: 水彩风格的风景画
3. **图片处理**: 调整图片大小

### 示例指令
- "画一只可爱的猫咪"
- "生成一张山水画"
- "@图片生成智能体 /？"
""",
                "contact_agent": """## 👥 联系人智能体

### 功能说明
联系人智能体可以管理联系人信息。

### 使用方式
1. **添加联系人**: 添加联系人张三 13800138000
2. **查询联系人**: 查询张三的电话
3. **修改联系人**: 修改张三的邮箱

### 示例指令
- "添加联系人李四 13900139000"
- "查询张三的电话"
- "@联系人智能体 /？"
""",
                "qq_bot_agent": """## 🤖 QQ机器人智能体

### 功能说明
QQ机器人智能体可以实现QQ消息的自动回复和处理。

### 使用方式
1. **启动机器人**: 启动QQ机器人
2. **停止机器人**: 停止QQ机器人
3. **查看状态**: QQ机器人状态

### 示例指令
- "启动QQ机器人"
- "停止QQ机器人"
- "@QQ机器人智能体 /？"
""",
            }
            
            if agent_name in help_map:
                return help_map[agent_name]
            
            return f"""## {meta.icon} {meta.display_name or agent_name}

### 功能说明
{meta.description or '暂无描述'}

### 能力
{', '.join(meta.capabilities) if meta.capabilities else '暂无'}

### 使用方式
使用 @{meta.display_name or agent_name} 来调用此智能体。

### 示例指令
- "@{meta.display_name or agent_name} /？"
"""
        except Exception as e:
            logger.error(f"获取智能体帮助信息失败: {e}")
            return f"无法获取 {meta.display_name or agent_name} 的帮助信息"
    
    def _refresh_agents(self):
        """Refresh agent list"""
        config_center.reload()
        self._load_agent_info()
        self._refresh_table()
    
    def _refresh_table(self):
        """Refresh the table display"""
        self._populate_table()
        
        total_count = len(self._agent_metadata)
        loaded_count = len(self._loaded_agents)
        hidden_count = sum(1 for m in self._agent_metadata.values() if m.hidden)
        
        self.total_label.setText(f"📊 总计: {total_count}")
        self.loaded_label.setText(f"✅ 已加载: {loaded_count}")
        self.hidden_label.setText(f"🔒 隐藏: {hidden_count}")
    
    def _apply_styles(self):
        """Apply styles to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
