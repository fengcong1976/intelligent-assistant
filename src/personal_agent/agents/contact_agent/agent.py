"""
Contact Agent - 通讯录智能体
智能管理通讯录，自动提取和保存联系人信息
"""
import asyncio
import re
import json
from typing import Any, Dict, List, Optional
from loguru import logger

from ..base import BaseAgent, Task, Message
from ...contacts.smart_contact_book import SmartContactBook, smart_contact_book


class ContactAgent(BaseAgent):
    """通讯录智能体"""
    
    KEYWORD_MAPPINGS = {
        "联系人": ("list", {}),
        "通讯录": ("list", {}),
        "联系人列表": ("list", {}),
        "查看联系人": ("list", {}),
        "查找联系人": ("search", {}),
        "搜索联系人": ("search", {}),
        "添加联系人": ("add", {}),
        "新建联系人": ("add", {}),
        "删除联系人": ("delete", {}),
        "修改联系人": ("update", {}),
        "更新联系人": ("update", {}),
    }
    
    def __init__(self):
        super().__init__(
            name="contact_agent",
            description="智能通讯录管理 - 自动提取和保存联系人信息"
        )
        
        self.register_capability(
            capability="contact_lookup",
            description="查找联系人信息。当用户询问某人的邮箱、电话、联系方式时必须优先调用此工具。根据姓名或关键词查找通讯录中的联系人。",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "联系人姓名或关键词，如'小聪聪'、'张三'"
                    }
                },
                "required": ["name"]
            },
            category="contact"
        )
        
        self.register_capability(
            capability="contact_list",
            description="列出通讯录中所有联系人。当用户需要查看全部联系人或导出通讯录时调用此工具。用于导出时使用 format='json' 获取结构化数据。",
            parameters={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "输出格式：'text' 为可读文本（默认），'json' 为结构化数据（用于导出）"
                    }
                },
                "required": []
            },
            category="contact"
        )
        
        self.register_capability(
            capability="contact_add",
            description="添加或保存联系人到通讯录。当用户提供新的联系人信息（姓名、邮箱、电话、关系、标签等）时调用此工具。例如：'老板 234566@qq.com 领导'、'保存联系人张三 13800138000'、'添加 小乱了 1000@qq.com 朋友 到通讯录'。支持中文关系描述（如'朋友'、'同事'、'领导'等）。",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "联系人姓名，如'老板'、'张三'、'小乱了'"
                    },
                    "email": {
                        "type": "string",
                        "description": "邮箱地址，如'xxx@qq.com'"
                    },
                    "phone": {
                        "type": "string",
                        "description": "电话号码"
                    },
                    "relationship": {
                        "type": "string",
                        "description": "关系描述，如'朋友'、'同事'、'领导'、'家人'、'同学'等"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表，如['领导', '同事']。如果没有提供relationship，会使用第一个标签作为关系"
                    }
                },
                "required": ["name"]
            },
            category="contact"
        )
        
        self.register_capability("contact_management", "联系人管理")
        self.register_capability("info_extraction", "信息提取")
        self.register_capability("contact_search", "联系人搜索")
        self.register_capability("info_query", "信息查询")
        self.register_capability("natural_query", "自然语言查询")
        
        self.contact_book = smart_contact_book
        self._llm_gateway = None
        
        logger.info("📞 通讯录智能体已初始化")
    
    def _get_llm_gateway(self):
        if self._llm_gateway is None:
            from ...config import settings
            from ...llm import LLMGateway
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway
    
    async def execute_task(self, task: Task) -> Any:
        """执行通讯录任务"""
        task_type = task.type
        params = task.params
        
        logger.info(f"📞 执行通讯录任务: {task_type}")
        
        if task_type in ("add", "create"):
            return await self._handle_add(params)
        elif task_type == "update":
            return await self._handle_update(params)
        elif task_type == "delete":
            return await self._handle_delete(params)
        elif task_type in ("query", "lookup", "get", "contact_lookup"):
            return await self._handle_query(params)
        elif task_type == "search":
            return await self._handle_search(params)
        elif task_type in ("list", "list_contacts"):
            return await self._handle_list(params)
        elif task_type == "extract":
            return await self._handle_extract(params)
        elif task_type == "add_info":
            return await self._handle_add_info(params)
        elif task_type == "get_info":
            return await self._handle_get_info(params)
        elif task_type == "auto_process":
            return await self._handle_auto_process(params)
        elif task_type in ("natural_query", "info_query"):
            return await self._handle_natural_query(params)
        elif task_type == "general":
            return await self._handle_general(params)
        elif task_type == "agent_help":
            return self._get_help_info()
        else:
            return self.cannot_handle(
                reason=f"不支持的通讯录操作: {task_type}",
                suggestion=""
            )
    
    async def _handle_general(self, params: Dict) -> str:
        """处理 general 类型任务，增强意图识别"""
        text = params.get("text", params.get("original_text", "")).lower()
        
        name_keywords = ["的邮箱", "的邮件", "的电话", "的手机", "的信息", "的联系方式"]
        for kw in name_keywords:
            if kw in text:
                name = text.split(kw)[0].strip()
                if name:
                    return await self._handle_query({"name": name})
        
        add_keywords = ["添加", "新增", "创建", "保存"]
        if any(kw in text for kw in add_keywords):
            return await self._handle_add(params)
        
        list_keywords = ["有哪些", "列表", "所有联系人", "全部联系人"]
        if any(kw in text for kw in list_keywords):
            return await self._handle_list(params)
        
        search_keywords = ["找", "搜索", "查找", "有没有"]
        if any(kw in text for kw in search_keywords):
            search_text = text
            for kw in search_keywords:
                search_text = search_text.replace(kw, "")
            return await self._handle_search({"query": search_text.strip()})
        
        return await self._handle_query({"name": text.strip()})
    
    async def _handle_add(self, params: Dict) -> str:
        """添加联系人"""
        name = params.get("name", "")
        
        logger.info(f"📝 _handle_add 接收到的参数: {params}")
        
        if not name:
            return self.cannot_handle(
                reason="请提供联系人姓名",
                missing_info={"name": "联系人姓名", "relationship": "关系（可选）"}
            )
        
        alias = params.get("alias", [])
        if isinstance(alias, str):
            alias = [a.strip() for a in alias.split(",")]
        
        tags = params.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        
        relationship = params.get("relationship", "")
        if tags and not relationship:
            relationship = tags[0] if len(tags) == 1 else ", ".join(tags)
        
        logger.info(f"📝 最终使用的 relationship: {relationship}")
        logger.info(f"📝 最终使用的 tags: {tags}")
        
        contact = self.contact_book.add_contact(
            name=name,
            alias=alias,
            email=params.get("email", ""),
            phone=params.get("phone", ""),
            company=params.get("company", ""),
            position=params.get("position", ""),
            relationship=relationship
        )
        
        return f"✅ 已添加联系人: {contact.name}\n{contact.get_display_info()}"
    
    async def _handle_update(self, params: Dict) -> str:
        """更新联系人"""
        name = params.get("name", "")
        
        if not name:
            return "❌ 请提供联系人姓名"
        
        contact = self.contact_book.get_contact(name)
        if not contact:
            return f"❌ 未找到联系人: {name}"
        
        update_fields = {}
        for field in ["email", "phone", "company", "position", "relationship", "notes"]:
            if field in params and params[field]:
                update_fields[field] = params[field]
        
        if update_fields:
            for key, value in update_fields.items():
                setattr(contact, key, value)
            self.contact_book._save()
        
        return f"✅ 已更新联系人: {contact.name}\n{contact.get_display_info()}"
    
    async def _handle_delete(self, params: Dict) -> str:
        """删除联系人"""
        name = params.get("name", "")
        
        if not name:
            return "❌ 请提供联系人姓名"
        
        if self.contact_book.delete_contact(name):
            return f"✅ 已删除联系人: {name}"
        return f"❌ 未找到联系人: {name}"
    
    async def _handle_query(self, params: Dict) -> str:
        """查询联系人"""
        name = params.get("name", "")
        email = params.get("email", "")
        
        if email:
            results = self.contact_book.search_contacts(email)
            if results:
                if len(results) == 1:
                    contact = results[0]
                    return f"📧 邮箱 {email} 对应的联系人是: {contact.name}"
                else:
                    response = f"📧 找到 {len(results)} 个使用该邮箱的联系人:\n"
                    for c in results:
                        response += f"  • {c.name}\n"
                    return response
            return f"❌ 未找到使用邮箱 {email} 的联系人"
        
        if not name:
            return self.contact_book.get_contact_summary()
        
        contact = self.contact_book.get_contact(name)
        
        if not contact:
            return f"❌ 未找到联系人: {name}"
        
        return contact.get_display_info()
    
    async def _handle_search(self, params: Dict) -> str:
        """搜索联系人"""
        keyword = params.get("keyword", "") or params.get("name", "") or params.get("query", "")
        original_text = params.get("original_text", "")
        
        if not keyword and not original_text:
            return "❌ 请提供搜索关键词"
        
        relationship_map = {
            "我妈": "母亲",
            "我爸": "父亲",
            "我老婆": "妻子",
            "我老公": "丈夫",
            "我儿子": "儿子",
            "我女儿": "女儿",
            "我哥": "哥哥",
            "我弟": "弟弟",
            "我姐": "姐姐",
            "我妹": "妹妹",
            "我爷爷": "爷爷",
            "我奶奶": "奶奶",
            "我外公": "外公",
            "我外婆": "外婆",
        }
        
        relationship = None
        for key, rel in relationship_map.items():
            if key in original_text or key in keyword:
                relationship = rel
                break
        
        if relationship:
            results = self.contact_book.get_contacts_by_relationship(relationship)
            if results:
                if len(results) == 1:
                    contact = results[0]
                    return f"👤 您的{relationship}是: {contact.name}\n{contact.get_display_info()}"
                else:
                    response = f"👤 找到 {len(results)} 位{relationship}:\n"
                    for c in results:
                        response += f"  • {c.name}\n"
                    return response
            return f"❌ 您还没有记录{relationship}的信息\n\n💡 您可以说: \"我妈妈叫XXX\" 来添加"
        
        results = self.contact_book.search_contacts(keyword)
        
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的联系人"
        
        response = f"🔍 找到 {len(results)} 个相关联系人:\n\n"
        for contact in results:
            response += contact.get_display_info() + "\n\n"
        
        return response
    
    async def _handle_list(self, params: Dict) -> str:
        """列出联系人"""
        relationship = params.get("relationship") or params.get("relation")
        format_type = params.get("format", "text")
        
        contacts = self.contact_book.list_all_contacts()
        
        if relationship:
            contacts = self.contact_book.get_contacts_by_relationship(relationship)
            if not contacts:
                return f"📭 没有关系为「{relationship}」的联系人"
        
        if not contacts:
            return "📭 通讯录为空"
        
        if format_type == "json":
            data = []
            for c in sorted(contacts, key=lambda x: x.name):
                data.append({
                    "name": c.name,
                    "email": c.email or "",
                    "phone": c.phone or "",
                    "relationship": c.relationship or ""
                })
            return json.dumps(data, ensure_ascii=False)
        
        lines = [f"📖 通讯录 (共 {len(contacts)} 人)\n"]
        for contact in sorted(contacts, key=lambda c: c.name):
            info_count = len(contact.info_db)
            lines.append(f"• {contact.name}")
            if contact.phone:
                lines[-1] += f" 📞 {contact.phone}"
            if contact.email:
                lines[-1] += f" 📧 {contact.email}"
            if contact.relationship:
                lines[-1] += f" 👥 {contact.relationship}"
            if info_count > 0:
                lines[-1] += f" 📋 {info_count}条信息"
        
        return "\n".join(lines)
    
    async def _handle_extract(self, params: Dict) -> str:
        """从文本提取联系人信息"""
        text = params.get("text", "")
        contact_name = params.get("contact_name")
        
        if not text:
            return "❌ 请提供要提取的文本内容"
        
        result = self.contact_book.extract_and_save_info(text, contact_name)
        
        if not result["contact_name"]:
            return "❌ 未能识别文本中的联系人"
        
        if not result["extracted_info"]:
            return f"📝 已识别联系人: {result['contact_name']}，但未提取到有效信息"
        
        response = f"✅ 已为 {result['contact_name']} 提取并保存以下信息:\n\n"
        for key, value in result["extracted_info"].items():
            response += f"• {key}: {value}\n"
        
        return response
    
    async def _handle_add_info(self, params: Dict) -> str:
        """为联系人添加信息"""
        name = params.get("name", "")
        key = params.get("key", "")
        value = params.get("value", "")
        
        if not name or not key or not value:
            return "❌ 请提供联系人姓名、信息类型和信息内容"
        
        if self.contact_book.add_info_to_contact(name, key, value):
            contact = self.contact_book.get_contact(name)
            return f"✅ 已为 {contact.name} 添加信息: {key} = {value}"
        
        return f"❌ 添加信息失败"
    
    async def _handle_get_info(self, params: Dict) -> str:
        """获取联系人特定信息"""
        name = params.get("name", "")
        key = params.get("key")
        
        if not name:
            return "❌ 请提供联系人姓名"
        
        contact = self.contact_book.get_contact(name)
        if not contact:
            return f"❌ 未找到联系人: {name}"
        
        if key:
            value = contact.get_info(key)
            if value:
                return f"📋 {contact.name} 的 {key}: {value}"
            return f"❌ 未找到 {contact.name} 的 {key} 信息"
        
        all_info = contact.get_all_info()
        if not all_info:
            return f"📋 {contact.name} 暂无额外信息"
        
        response = f"📋 {contact.name} 的详细信息:\n\n"
        for k, v in all_info.items():
            response += f"• {k}: {v}\n"
        
        return response
    
    async def _handle_auto_process(self, params: Dict) -> str:
        """自动处理对话中的联系人信息"""
        text = params.get("text", "")
        
        if not text:
            return ""
        
        result = self.contact_book.extract_and_save_info(text)
        
        if result["saved"]:
            info_str = ", ".join([f"{k}: {v}" for k, v in result["extracted_info"].items()])
            return f"📝 已自动记录 {result['contact_name']} 的信息: {info_str}"
        
        return ""
    
    async def _handle_natural_query(self, params: Dict) -> str:
        """处理自然语言查询"""
        query = params.get("original_text", params.get("query", params.get("content", "")))
        
        if not query:
            return self.cannot_handle(reason="请提供查询内容")
        
        contacts_data = []
        for contact in self.contact_book.list_all_contacts():
            contacts_data.append({
                "name": contact.name,
                "email": contact.email,
                "phone": contact.phone,
                "company": contact.company,
                "position": contact.position,
                "relationship": contact.relationship,
                "notes": contact.notes,
                "info_db": {k: v.value for k, v in contact.info_db.items()}
            })
        
        history_text = self._get_conversation_history()
        
        prompt = f"""你是一个智能通讯录助手。用户有一个关于联系人的问题，请按以下顺序查找信息：

1. 首先在通讯录数据中查找
2. 如果通讯录中没有，再从历史聊天记录中查找
3. 如果都找不到，请诚实告知用户

【通讯录数据】
{json.dumps(contacts_data, ensure_ascii=False, indent=2) if contacts_data else "（通讯录为空）"}

【历史聊天记录】（最近50条）
{history_text if history_text else "（无历史记录）"}

【用户问题】
{query}

请用自然、友好的语言回答用户的问题。如果从历史记录中找到了相关信息，请说明来源。"""

        try:
            llm = self._get_llm_gateway()
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM 处理自然查询失败: {e}")
            return self.cannot_handle(reason=f"处理查询失败: {e}")
    
    def _get_conversation_history(self, limit: int = 50) -> str:
        """获取历史聊天记录"""
        try:
            history = []
            
            from ..main import PersonalAgentApp
            app = PersonalAgentApp._instance
            
            if app and hasattr(app, 'agent') and hasattr(app.agent, 'memory'):
                memory_history = app.agent.memory.get_conversation_history()
                if memory_history:
                    history = memory_history
                    logger.debug(f"从 memory 获取到 {len(history)} 条历史记录")
            
            if not history and app and hasattr(app, 'channel'):
                channel = app.channel
                if hasattr(channel, 'conv_manager') and channel.conv_manager:
                    conv = channel.conv_manager.get_conversation()
                    if conv and hasattr(conv, 'messages'):
                        history = [{"role": m.role, "content": m.content} for m in conv.messages]
                        logger.debug(f"从 conv_manager 获取到 {len(history)} 条历史记录")
            
            if not history:
                history = self._load_conversation_from_file()
                if history:
                    logger.debug(f"从文件获取到 {len(history)} 条历史记录")
            
            if not history:
                logger.warning("未能获取到任何历史记录")
                return ""
            
            lines = []
            for msg in history[-limit:]:
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")
                if content and len(content) > 5:
                    lines.append(f"[{role}] {content[:200]}")
            
            result = "\n".join(lines)
            logger.debug(f"历史记录格式化完成，共 {len(lines)} 条")
            return result
        except Exception as e:
            logger.error(f"获取历史记录失败: {e}")
            return ""
    
    def _load_conversation_from_file(self) -> List[Dict]:
        """直接从文件加载对话历史"""
        try:
            import json
            from pathlib import Path
            
            conv_file = Path("data/conversations/conversation.json")
            if not conv_file.exists():
                return []
            
            with open(conv_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            messages = data.get("messages", [])
            return [{"role": m.get("role", ""), "content": m.get("content", "")} for m in messages]
        except Exception as e:
            logger.warning(f"从文件加载对话失败: {e}")
            return []
    
    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = super().get_status()
        contacts = self.contact_book.list_all_contacts()
        total_info = sum(len(c.info_db) for c in contacts)
        
        status.update({
            "contact_count": len(contacts),
            "total_info_count": total_info,
            "capabilities": [
                "contact_management", "info_extraction",
                "contact_search", "info_query"
            ]
        })
        return status

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 联系人智能体

### 功能说明
联系人智能体可以管理通讯录，支持添加、删除、查询联系人信息。

### 支持的操作
- **添加联系人**：添加新的联系人
- **删除联系人**：删除已有联系人
- **查询联系人**：查找联系人信息
- **更新联系人**：修改联系人信息
- **搜索联系人**：按条件搜索联系人

### 使用示例
- "添加联系人张三，电话13800138000" - 添加新联系人
- "查找李四" - 查询联系人信息
- "删除王五" - 删除联系人
- "更新赵六的邮箱" - 更新联系人信息

### 注意事项
- 联系人信息会保存在本地
- 支持批量导入导出联系人"""

    async def handle_message(self, message: Message):
        """处理来自其他智能体的消息"""
        logger.info(f"📨 收到来自 {message.from_agent} 的消息: {message.message_type}")
        
        if message.message_type == "contact_query":
            name = message.data.get("name", "")
            contact = self.contact_book.get_contact(name)
            
            if contact:
                await self.send_message(
                    to_agent=message.from_agent,
                    message_type="contact_response",
                    content=contact.get_display_info(),
                    data=contact.to_dict()
                )
            else:
                await self.send_message(
                    to_agent=message.from_agent,
                    message_type="contact_response",
                    content=f"未找到联系人: {name}"
                )
        
        elif message.message_type == "auto_extract":
            text = message.data.get("text", "")
            result = self.contact_book.extract_and_save_info(text)
            
            await self.send_message(
                to_agent=message.from_agent,
                message_type="extract_result",
                content=result
            )
    
    def should_process_text(self, text: str) -> bool:
        """判断文本是否需要处理联系人信息"""
        contact_indicators = [
            r"[^\s]{2,4}(总|经理|先生|女士|老师)",
            r"(生日|住址|电话|邮箱|公司|职位|爱好|年龄)",
            r"(的|问|查|告诉|提醒)",
        ]
        
        for pattern in contact_indicators:
            if re.search(pattern, text):
                return True
        
        return False
