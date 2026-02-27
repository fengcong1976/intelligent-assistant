"""
Email Agent - 邮件管理智能体
专门负责邮件相关任务，支持 LLM 生成邮件内容
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.policy import default as default_policy
from typing import Any, Dict, Optional, List
from pathlib import Path
from loguru import logger

from ..base import BaseAgent, Task, Message


class EmailAgent(BaseAgent):
    """
    邮件管理智能体

    能力：
    - 发送邮件（支持 LLM 生成内容）
    - 接收邮件
    - 管理邮件
    """
    
    KEYWORD_MAPPINGS = {
        "查邮件": ("check_email", {}),
        "检查邮件": ("check_email", {}),
        "看邮件": ("check_email", {}),
        "新邮件": ("check_email", {}),
    }

    def __init__(self):
        super().__init__(
            name="email_agent",
            description="邮件管理智能体 - 负责邮件收发和管理"
        )

        self.register_capability(
            capability="send_email",
            description="发送电子邮件。只需要提供收件人和要传达的信息要点，邮件内容会自动生成。支持发送附件，可以发送图片、文档等文件。",
            parameters={
                "type": "object",
                "properties": {
                    "recipient_name": {
                        "type": "string",
                        "description": "收件人姓名或称呼"
                    },
                    "to": {
                        "type": "string",
                        "description": "收件人邮箱地址（可选）"
                    },
                    "message": {
                        "type": "string",
                        "description": "要传达给收件人的信息要点（不是完整邮件正文）"
                    },
                    "attachment": {
                        "type": "string",
                        "description": "附件文件路径（可选），支持图片、文档等文件。如果用户说'发送到邮箱'或'并发到邮箱'，应该使用前一个工具的结果作为附件"
                    }
                },
                "required": ["recipient_name"]
            },
            category="email"
        )
        
        self.register_capability("email_management", "邮件管理")
        self.register_capability("receive_email", "接收邮件")

        self.sent_count = 0
        self.received_count = 0
        self._llm_gateway = None

        logger.info("📧 邮件管理智能体已初始化")

    def _get_llm_gateway(self):
        """获取 LLM 网关"""
        if self._llm_gateway is None:
            from ...llm import LLMGateway
            from ...config import settings
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway

    async def execute_task(self, task: Task) -> Any:
        """执行邮件相关任务"""
        task_type = task.type
        params = task.params or {}
        original_text = params.get("original_text") or params.get("original_request") or task.content

        logger.info(f"📧 执行邮件任务: {task_type}, original_text={original_text[:50] if original_text else 'None'}...")

        if task_type == "send_email":
            return await self._handle_send_email(original_text, params)

        elif task_type == "send_email_with_music":
            return await self._handle_send_email_with_music(original_text, params)

        elif task_type == "send_current_music_email":
            return await self._handle_send_current_music_email(original_text, params)

        elif task_type == "receive_email":
            return await self._handle_receive_email(params)

        elif task_type == "check_email":
            return await self._handle_check_email()

        elif task_type == "send":
            if params.get("attachment"):
                return await self._handle_send_with_attachment(original_text, params)
            else:
                return await self._handle_send_email(original_text, params)
        
        elif task_type == "send_to_relationship":
            return await self._handle_send_to_relationship(original_text, params)

        elif task_type == "send_with_attachment":
            return await self._handle_send_with_attachment(original_text, params)

        elif task_type == "save_attachment":
            return await self._handle_save_attachment(params)
        
        elif task_type == "general":
            return await self._handle_general(params)
        elif task_type == "agent_help":
            return self._get_help_info()
        else:
            return f"❌ 不支持的邮件操作: {task_type}"
    
    async def _handle_general(self, params: Dict) -> str:
        """处理 general 类型任务，解析邮件发送意图"""
        import re
        text = params.get("text", params.get("original_text", ""))
        
        recipient_patterns = [
            r'发给?([^，。！？,\s]+)',
            r'发送给?([^，。！？,\s]+)',
            r'给([^，。！？,\s]+)[发寄]',
            r'邮件给?([^，。！？,\s]+)',
            r'到([^，。！？,\s]+)邮箱',
            r'发到([^，。！？,\s]+)',
        ]
        
        recipient_name = None
        for pattern in recipient_patterns:
            match = re.search(pattern, text)
            if match:
                recipient_name = match.group(1).strip()
                recipient_name = re.sub(r'邮箱$', '', recipient_name)
                break
        
        if recipient_name:
            new_params = {
                "recipient_name": recipient_name,
                "original_text": text,
                "attachment": params.get("attachment", ""),
                "attachments": params.get("attachments", []),
                "message": params.get("message", "")
            }
            return await self._handle_send_email(text, new_params)
        
        return "❌ 无法识别收件人，请明确指定邮件接收人"

    async def _get_contact_info(self, recipient_name: str) -> Optional[Dict]:
        """获取联系人信息"""
        if "@" in recipient_name:
            return {"email": recipient_name, "relationship": "", "name": recipient_name}
        
        from ...contacts.smart_contact_book import smart_contact_book
        
        contact = smart_contact_book.get_contact(recipient_name)
        if contact:
            return {
                "email": contact.email,
                "name": contact.name,
                "relationship": contact.relationship,
                "company": contact.company,
                "position": contact.position,
                "notes": contact.notes
            }
        
        contacts = smart_contact_book.search_contacts(recipient_name)
        if contacts:
            c = contacts[0]
            return {
                "email": c.email,
                "name": c.name,
                "relationship": c.relationship,
                "company": c.company,
                "position": c.position,
                "notes": c.notes
            }
        
        return None

    async def _generate_email_content(
        self, 
        user_request: str,
        recipient_name: str = None,
        to_email: str = None,
        subject_hint: str = None
    ) -> Dict[str, str]:
        """使用 LLM 生成邮件内容"""
        from ...config import settings
        from ...user_config import user_config
        
        logger.info(f"📧 LLM生成邮件: user_request={user_request[:50] if user_request else 'None'}...")
        
        llm = self._get_llm_gateway()
        
        user_email = settings.user.email or settings.agent.email
        user_name = user_config.user_name or settings.user.name or "用户"
        user_formal_name = user_config.formal_name or settings.user.formal_name or user_name
        agent_name = settings.agent.name or "智能助手"
        
        logger.info(f"📧 生成邮件参数: user_name={user_name}, user_formal_name={user_formal_name}, agent_name={agent_name}")
        logger.info(f"📧 收件人: recipient_name={recipient_name}, to_email={to_email}")
        
        contact_info = None
        if recipient_name:
            contact_info = await self._get_contact_info(recipient_name)
        
        recipient_note = ""
        if recipient_name:
            recipient_note = f"\n收件人名称: {recipient_name}"
            if contact_info:
                if contact_info.get("relationship"):
                    recipient_note += f"\n与我的关系: {contact_info['relationship']}"
                if contact_info.get("company"):
                    recipient_note += f"\n所在公司: {contact_info['company']}"
                if contact_info.get("position"):
                    recipient_note += f"\n职位: {contact_info['position']}"
                if contact_info.get("notes"):
                    recipient_note += f"\n备注: {contact_info['notes']}"
        
        from datetime import datetime
        current_year = datetime.now().year
        zodiac_map = {2024: "龙年", 2025: "蛇年", 2026: "马年", 2027: "羊年", 2028: "猴年"}
        current_zodiac = zodiac_map.get(current_year, "")
        
        is_self_email = (recipient_name in ["我", "自己", "本人"] or to_email == user_email)
        recipient_display = user_name if is_self_email else (recipient_name or "收件人")
        
        prompt = f"""你是一个邮件撰写助手。请根据用户请求撰写邮件。

用户请求: {user_request}
收件人: {recipient_display}{recipient_note}
发件人: {user_formal_name}
智能体名称: {agent_name}

【严格要求】
1. 称呼：直接写收件人名字，禁止加"亲爱的"、"敬爱的"等修饰词
   - 正确：小聪聪，
   - 错误：亲爱的小聪聪，
   
2. 正文：简洁明了，直接传达用户要说的内容，不要扩展太多

3. 署名格式（必须严格遵守）：
   - 格式：{{发件人}}的智能助理 - {{智能体名称}}
   - 正确：{user_formal_name}的智能助理 - {agent_name}
   - 错误：{user_formal_name}、智能助手等

【示例】
收件人：小聪聪
用户请求：告诉他明天早上来开会
正确输出：
小聪聪，

明天早上请来开会。

{user_formal_name}的智能助理 - {agent_name}

【返回格式】
{{
    "subject": "邮件主题",
    "content": "邮件正文"
}}

只返回 JSON。"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            import json
            result = json.loads(response.content.strip().replace("```json", "").replace("```", "").strip())
            
            logger.info(f"📧 LLM 生成邮件: subject={result.get('subject')}")
            logger.info(f"📧 邮件内容预览: {result.get('content', '')[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"LLM 生成邮件内容失败: {e}")
            return {
                "subject": subject_hint or "来自智能助手的邮件",
                "content": f"用户请求: {user_request}\n\n--\n{user_formal_name}的智能助理-{agent_name}"
            }

    async def _handle_send_email(self, original_text: str, params: Dict) -> str:
        """处理发送邮件"""
        from ...config import settings
        from pathlib import Path
        
        to_email = params.get("to")
        if to_email == "null" or to_email == "None":
            to_email = None
        
        fake_email_patterns = ["@example.com", "@example.org", "@test.com", "@fake.com"]
        if to_email and any(p in str(to_email).lower() for p in fake_email_patterns):
            logger.warning(f"📧 忽略假邮箱: {to_email}")
            to_email = None
        
        subject = params.get("subject")
        content = params.get("content") or params.get("body")
        recipient_name = params.get("recipient_name")
        message_content = params.get("message") or params.get("message_content")
        attachments = params.get("attachments", [])
        
        original_text_lower = (original_text or "").lower()
        is_self_request = any(kw in original_text_lower for kw in ["我邮箱", "发给我", "发到我", "我的邮箱", "我自己"])
        
        if is_self_request and not to_email:
            user_email = settings.user.email or settings.agent.email
            if user_email:
                to_email = user_email
                recipient_name = "我"
                logger.info(f"📧 检测到发送给自己，使用用户邮箱: {to_email}")
        
        attachment = params.get("attachment", "")
        
        fake_patterns = ["/path/", "[待定]", "[附件]", "[文件]", "{attachment}", "{file_path}", "#FILEPATH#", "example.com"]
        if attachment and any(p.lower() in str(attachment).lower() for p in fake_patterns):
            logger.warning(f"📧 忽略假附件路径: {attachment}")
            attachment = ""
        
        if attachment and not attachments:
            import re
            file_path_match = re.search(r'[A-Za-z]:\\[^\n\r]+\.\w+', attachment)
            if file_path_match:
                attachment = file_path_match.group(0)
            
            attachment = re.sub(r'([a-zA-Z])盘', r'\1:', attachment, flags=re.IGNORECASE)
            attachment_path = Path(attachment)
            if attachment_path.exists():
                attachments = [str(attachment_path)]
                logger.info(f"📎 添加附件: {attachment_path}")
            else:
                logger.warning(f"⚠️ 附件不存在: {attachment}")
        
        if not attachments:
            logger.warning(f"⚠️ 没有有效附件，跳过附件发送")
        
        if not to_email or "@" not in str(to_email):
            if to_email and "@" not in str(to_email):
                recipient_name = recipient_name or to_email
                logger.info(f"📧 收件人不是邮箱地址，尝试查找联系人: {recipient_name}")
            
            if recipient_name:
                if recipient_name in ["我", "自己", "本人", "我的邮箱"]:
                    user_email = settings.user.email or settings.agent.email
                    if user_email:
                        to_email = user_email
                        logger.info(f"📧 收件人是用户自己，使用默认邮箱: {to_email}")
                    else:
                        return "❌ 请先在设置中配置您的邮箱地址"
                else:
                    contact_info = await self._get_contact_info(recipient_name)
                    if contact_info and contact_info.get("email"):
                        to_email = contact_info["email"]
                        logger.info(f"📧 找到联系人邮箱: {recipient_name} -> {to_email}")
                    else:
                        return f"❌ 找不到联系人「{recipient_name}」的邮箱地址，请先添加联系人信息"
            
            if not to_email or "@" not in str(to_email):
                user_email = settings.user.email or settings.agent.email
                if user_email:
                    to_email = user_email
                    logger.info(f"📧 使用用户默认邮箱: {to_email}")
                else:
                    return "❌ 无法确定收件人邮箱地址"
        
        if not subject or not content:
            email_content = await self._generate_email_content(
                original_text or message_content, 
                recipient_name=recipient_name,
                to_email=to_email,
                subject_hint=subject
            )
            if email_content:
                if not subject:
                    subject = email_content.get("subject", "来自智能助手的邮件")
                if not content:
                    content = email_content.get("content", "")
        
        if not subject or not content:
            return "❌ 邮件主题或内容为空"
        
        from ...user_config import user_config
        user_name = user_config.user_name or settings.user.name or "用户"
        agent_name = settings.agent.name or "智能助手"
        user_formal_name = user_config.formal_name or settings.user.formal_name or settings.user.name or "用户"
        user_email = settings.user.email or settings.agent.email
        is_self_email = (to_email == user_email)
        
        if attachments:
            if is_self_email:
                recipient_display = user_name
                signature = agent_name
            else:
                recipient_display = recipient_name or "您"
                signature = f"{user_formal_name}的智能助理 - {agent_name}"
            
            attachment_name = Path(attachments[0]).name if attachments else "附件"
            content = f"{recipient_display}，\n\n请查收附件：{attachment_name}\n\n{signature}"
            logger.info(f"📧 有附件时使用简洁正文，is_self={is_self_email}")
        
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件发送功能未配置，请在设置中配置邮箱和授权码"
        
        from ...user_config import user_config
        user_formal_name = user_config.formal_name or settings.user.formal_name or settings.user.name or "用户"
        content = self._fix_email_content(content, recipient_name, user_formal_name, is_self_email)
        
        result = await self._send_email(
            to=to_email,
            subject=subject,
            content=content,
            smtp_config=smtp_config,
            attachments=attachments
        )
        
        if result["success"]:
            self.sent_count += 1
            attachment_info = f"\n📎 附件: {len(attachments)} 个" if attachments else ""
            recipients = result.get("recipients", [to_email])
            recipients_str = ", ".join(recipients) if isinstance(recipients, list) else to_email
            await self.send_message(
                to_agent="master",
                message_type="status_update",
                content=f"邮件已发送给 {recipients_str}",
                data={"status": "sent", "to": to_email, "subject": subject}
            )
            content_preview = content[:500] + "..." if len(content) > 500 else content
            return f"✅ 邮件已发送给 {recipients_str}\n主题: {subject}{attachment_info}\n\n📝 邮件内容:\n{content_preview}"
        else:
            return f"❌ 邮件发送失败: {result['error']}"

    async def _handle_send_with_attachment(self, original_text: str, params: Dict) -> str:
        """处理发送带附件的邮件（工作流调用）"""
        from ...config import settings
        from pathlib import Path
        import time
        
        attachment = params.get("attachment", "")
        to_email = params.get("to")
        subject = params.get("subject")
        content = params.get("content")
        recipient_name = params.get("recipient_name") or to_email
        
        logger.info(f"📧 _handle_send_with_attachment 参数: to={to_email}, recipient_name={recipient_name}")
        
        if not to_email or "@" not in str(to_email):
            if recipient_name:
                if recipient_name in ["我", "自己", "本人", "我的邮箱"]:
                    user_email = settings.user.email or settings.agent.email
                    if user_email:
                        to_email = user_email
                        logger.info(f"📧 收件人是用户自己，使用默认邮箱: {to_email}")
                    else:
                        return "❌ 请先在设置中配置您的邮箱地址"
                else:
                    contact_info = await self._get_contact_info(recipient_name)
                    if contact_info and contact_info.get("email"):
                        to_email = contact_info["email"]
                        logger.info(f"📧 找到联系人邮箱: {recipient_name} -> {to_email}")
                    else:
                        return f"❌ 找不到联系人「{recipient_name}」的邮箱地址，请先添加联系人信息"
            
            if not to_email or "@" not in str(to_email):
                user_email = settings.user.email or settings.agent.email
                if user_email:
                    to_email = user_email
                    logger.info(f"📧 使用用户默认邮箱: {to_email}")
                else:
                    return "❌ 无法确定收件人邮箱地址"
        
        logger.info(f"📧 最终收件人地址: {to_email}")
        
        attachments = []
        if attachment:
            attachment_path = Path(attachment)
            if not attachment_path.is_absolute():
                search_paths = [
                    Path.cwd() / attachment,
                    Path.cwd() / "output" / "pdf" / attachment,
                    Path.cwd() / "output" / attachment,
                ]
                
                existing_paths = []
                for search_path in search_paths:
                    if search_path.exists():
                        existing_paths.append(search_path)
                
                if existing_paths:
                    if len(existing_paths) > 1:
                        existing_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        logger.info(f"📎 找到多个附件，选择最新的: {existing_paths[0]}")
                    attachment_path = existing_paths[0]
            
            if attachment_path.exists():
                attachments.append(str(attachment_path))
                logger.info(f"📎 找到附件: {attachment_path}")
            else:
                logger.warning(f"⚠️ 附件不存在: {attachment_path}")
                return f"❌ 附件不存在: {attachment}"
        
        if not subject:
            subject = f"发送文件: {Path(attachment).name}" if attachment else "无主题"
        
        from ...user_config import user_config
        agent_name = settings.agent.name or "智能助手"
        user_formal_name = user_config.formal_name or settings.user.formal_name or settings.user.name or "用户"
        user_name = user_config.user_name or settings.user.name or "用户"
        signature = agent_name if to_email == settings.user.email else f"{user_formal_name}的智能助理-{agent_name}"
        is_self = to_email == settings.user.email
        recipient_display = user_name if is_self else "您"
        attachment_name = Path(attachment).name if attachment else "附件"
        
        if not content or len(content) > 200:
            content = f"{recipient_display}，\n\n请查收附件：{attachment_name}\n\n{signature}"
            logger.info(f"📧 有附件时使用简洁正文")
        
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件发送功能未配置，请在设置中配置邮箱和授权码"
        
        result = await self._send_email(
            to=to_email,
            subject=subject,
            content=content,
            smtp_config=smtp_config,
            attachments=attachments
        )
        
        if result["success"]:
            self.sent_count += 1
            attachment_info = f"\n📎 附件: {attachment}" if attachment else ""
            content_preview = content[:500] + "..." if len(content) > 500 else content
            return f"✅ 邮件已发送给 {to_email}\n主题: {subject}{attachment_info}\n\n📝 邮件内容:\n{content_preview}"
        else:
            return f"❌ 邮件发送失败: {result['error']}"

    async def _handle_send_email_with_music(self, original_text: str, params: Dict) -> str:
        """处理发送带音乐附件的邮件"""
        from ...config import settings
        from ...music.player import MusicPlayer
        
        song_query = params.get("song_query", "")
        to_email = params.get("to")
        subject = params.get("subject")
        content = params.get("content")
        
        if not to_email:
            user_email = settings.user.email or settings.agent.email
            to_email = user_email
        
        found_file = None
        search_result = ""
        
        try:
            music_library = settings.directory.get_music_library()
            player = MusicPlayer(music_library=music_library)
            
            query = song_query.strip()
            query_clean = query.lower().replace(".mp3", "").replace(".MP3", "").strip()
            songs = player.get_cached_songs()
            
            if not songs:
                songs = player.scan_music_library()
            
            for s in songs:
                title_lower = s.title.lower()
                path_lower = s.path.lower()
                filename = Path(s.path).name.lower()
                
                if query.lower() in filename or query.lower() in path_lower:
                    found_file = s.path
                    search_result = f"✅ 找到歌曲: {Path(found_file).name}"
                    break
                
                if query_clean in title_lower or query_clean in filename:
                    found_file = s.path
                    search_result = f"✅ 找到歌曲: {Path(found_file).name}"
                    break
            
            if not found_file:
                search_result = f"❌ 未找到歌曲: {song_query}"
                logger.warning(f"未找到歌曲，查询: '{query}', 清理后: '{query_clean}'")
                logger.info(f"可用歌曲示例: {[s.title for s in songs[:5]]}")
                
        except Exception as e:
            logger.error(f"搜索音乐失败: {e}")
            search_result = f"❌ 搜索音乐时出错: {e}"
        
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件发送功能未配置，请在设置中配置邮箱和授权码"
        
        if not subject:
            if found_file:
                subject = Path(found_file).name
            else:
                subject = f"关于 {song_query} 的邮件"
        
        if not content:
            from ...user_config import user_config
            agent_name = settings.agent.name or "智能助手"
            user_formal_name = user_config.formal_name or settings.user.formal_name or settings.user.name or "用户"
            signature = f"{user_formal_name}的智能助理-{agent_name}" if to_email != settings.user.email else agent_name
            if found_file:
                content = f"附件：{Path(found_file).name}\n\n{search_result}\n\n--\n{signature}"
            else:
                content = f"抱歉，未能在音乐库中找到歌曲「{song_query}」。\n\n{search_result}\n\n--\n{signature}"
        
        attachments = [found_file] if found_file else []
        
        result = await self._send_email(
            to=to_email,
            subject=subject,
            content=content,
            smtp_config=smtp_config,
            attachments=attachments
        )
        
        if result["success"]:
            self.sent_count += 1
            content_preview = content[:500] + "..." if len(content) > 500 else content
            if found_file:
                return f"✅ 邮件已发送给 {to_email}\n主题: {subject}\n📎 附件: {Path(found_file).name}\n\n📝 邮件内容:\n{content_preview}"
            else:
                return f"✅ 邮件已发送给 {to_email}\n主题: {subject}\n\n⚠️ {search_result}\n\n📝 邮件内容:\n{content_preview}"
        else:
            return f"❌ 邮件发送失败: {result['error']}"

    async def _handle_send_current_music_email(self, original_text: str, params: Dict) -> str:
        """处理发送当前播放音乐的邮件"""
        from ...config import settings
        from ...music.player import MusicPlayer
        from ...contacts.smart_contact_book import smart_contact_book
        
        to_email = params.get("to")
        if to_email == "null" or to_email == "None":
            to_email = None
        subject = params.get("subject")
        content = params.get("content")
        recipient_name = params.get("recipient_name")
        
        if recipient_name and not to_email:
            contact = smart_contact_book.get_contact(recipient_name)
            if contact and contact.email:
                to_email = contact.email
                logger.info(f"从联系人找到邮箱: {recipient_name} -> {to_email}")
            else:
                contacts = smart_contact_book.search_contacts(recipient_name)
                if contacts:
                    logger.info(f"搜索联系人 '{recipient_name}' 找到 {len(contacts)} 个结果")
                    for c in contacts:
                        logger.info(f"  - {c.name}: {c.email}")
                    if contacts[0].email:
                        to_email = contacts[0].email
                        logger.info(f"从联系人搜索找到邮箱: {recipient_name} -> {to_email}")
                else:
                    logger.warning(f"未找到联系人: {recipient_name}")
        
        if not to_email:
            if recipient_name:
                return f"❌ 未找到联系人「{recipient_name}」的邮箱，请检查通讯录或直接提供邮箱地址"
            user_email = settings.user.email or settings.agent.email
            to_email = user_email
        
        music_library = settings.directory.get_music_library()
        player = MusicPlayer(music_library=music_library)
        
        current_song = player.current_song
        if not current_song:
            return "❌ 当前没有正在播放的音乐"
        
        found_file = current_song.path
        
        if found_file.lower().endswith('.ncm'):
            from ...music.ncm_decrypt import decrypt_ncm, get_cached_ncm
            decrypted_file = get_cached_ncm(found_file)
            if not decrypted_file:
                logger.info(f"🔓 正在解密 NCM 文件用于邮件附件...")
                decrypted_file = decrypt_ncm(found_file)
            if decrypted_file:
                found_file = decrypted_file
                logger.info(f"✅ NCM 已解密: {found_file}")
            else:
                return f"❌ 无法解密 NCM 文件: {current_song.title}"
        
        if not Path(found_file).exists():
            logger.error(f"❌ 文件不存在: {found_file}")
            return f"❌ 音乐文件不存在: {found_file}"
        
        logger.info(f"📎 准备发送附件: {found_file} ({Path(found_file).stat().st_size} bytes)")
        
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件发送功能未配置，请在设置中配置邮箱和授权码"
        
        if not subject:
            subject = Path(found_file).name
        
        if not content:
            from ...user_config import user_config
            agent_name = settings.agent.name or "智能助手"
            user_formal_name = user_config.formal_name or settings.user.formal_name or settings.user.name or "用户"
            signature = f"{user_formal_name}的智能助理-{agent_name}" if to_email != settings.user.email else agent_name
            content = f"附件：{Path(found_file).name}\n\n这是您当前正在播放的音乐。\n\n--\n{signature}"
        
        attachments = [found_file]
        logger.info(f"📧 准备发送邮件:")
        logger.info(f"  收件人: {to_email}")
        logger.info(f"  主题: {subject}")
        logger.info(f"  附件: {attachments}")
        
        result = await self._send_email(
            to=to_email,
            subject=subject,
            content=content,
            smtp_config=smtp_config,
            attachments=attachments
        )
        
        if result["success"]:
            self.sent_count += 1
            content_preview = content[:500] + "..." if len(content) > 500 else content
            return f"✅ 邮件已发送给 {to_email}\n主题: {subject}\n📎 附件: {Path(found_file).name}\n\n📝 邮件内容:\n{content_preview}"
        else:
            return f"❌ 邮件发送失败: {result['error']}"

    def _fix_email_content(self, content: str, recipient_name: str, user_name: str, is_self_email: bool = False) -> str:
        """修正邮件内容：称呼和署名
        
        Args:
            content: 邮件内容
            recipient_name: 收件人名称
            user_name: 用户名称
            is_self_email: 是否发送给自己
        """
        import re
        from ...config import settings
        
        agent_name = settings.agent.name or "小智"
        
        content = re.sub(r'亲爱的\s*', '', content)
        content = re.sub(r'敬爱的\s*', '', content)
        content = re.sub(r'尊敬的\s*', '', content)
        
        if is_self_email:
            display_name = user_name
        else:
            display_name = recipient_name or "您"
        
        if display_name and not re.search(rf'^{re.escape(display_name)}[，,：:]', content):
            lines = content.split('\n')
            if lines:
                lines[0] = f'{display_name}，'
                content = '\n'.join(lines)
        
        content = re.sub(rf'\n+\s*{re.escape(user_name)}的智能助理\s*[-—]\s*\w+\s*$', '', content)
        content = re.sub(rf'\n+\s*{re.escape(user_name)}的智能助理\s*$', '', content)
        content = re.sub(r'\n+\s*智能助理\s*[-—]\s*\w+\s*$', '', content)
        content = re.sub(r'\n+\s*智能助手\s*[-—]\s*\w+\s*$', '', content)
        content = re.sub(rf'\n+\s*{re.escape(user_name)}\s*$', '', content)
        content = re.sub(rf'\n+\s*{re.escape(agent_name)}\s*$', '', content)
        
        content = content.rstrip()
        
        if is_self_email:
            signature = agent_name
        else:
            signature = f'{user_name}的智能助理 - {agent_name}'
        
        content += f'\n\n{signature}'
        
        return content
    
    def _generate_subject(self, message_content: str) -> str:
        """根据内容生成邮件标题"""
        import re
        
        message_lower = message_content.lower()
        
        meeting_keywords = ["开会", "会议", "讨论", "见面", "商讨"]
        for kw in meeting_keywords:
            if kw in message_content:
                time_match = re.search(r'(明天|后天|今天|周[一二三四五六日]|下周|\d+号|\d+日)', message_content)
                time_str = time_match.group(1) if time_match else ""
                if "早上" in message_content or "上午" in message_content:
                    return f"会议通知{' - ' + time_str + '上午' if time_str else ''}"
                elif "下午" in message_content:
                    return f"会议通知{' - ' + time_str + '下午' if time_str else ''}"
                return f"会议通知{' - ' + time_str if time_str else ''}"
        
        greeting_keywords = ["新年快乐", "生日快乐", "节日快乐", "恭喜", "祝福", "祝贺"]
        for kw in greeting_keywords:
            if kw in message_content:
                return f"祝福 - {kw}"
        
        if "提醒" in message_content or "记得" in message_content:
            return "温馨提醒"
        
        if "通知" in message_content or "告知" in message_content:
            return "通知"
        
        if len(message_content) > 20:
            return message_content[:20] + "..."
        return message_content

    async def _send_email(
        self,
        to: str,
        subject: str,
        content: str,
        smtp_config: Dict,
        attachments: List[str] = None
    ) -> Dict:
        """实际发送邮件（支持多收件人，用逗号分隔）"""
        try:
            
            recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
            if not recipients:
                return {"success": False, "error": "没有有效的收件人"}
            
            valid_recipients = []
            for addr in recipients:
                if "@" in addr and "." in addr:
                    valid_recipients.append(addr)
                else:
                    logger.warning(f"⚠️ 无效的邮箱地址: {addr}")
            
            if not valid_recipients:
                return {"success": False, "error": f"没有有效的邮箱地址，收件人: {recipients}"}
            
            recipients = valid_recipients
            logger.info(f"📧 有效收件人: {recipients}")
            
            msg = MIMEMultipart()
            msg["From"] = smtp_config["user"]
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            
            msg.attach(MIMEText(content, "plain", "utf-8"))
            
            if attachments:
                logger.info(f"📎 处理 {len(attachments)} 个附件")
                for file_path in attachments:
                    path = Path(file_path)
                    if not path.exists():
                        logger.error(f"❌ 附件文件不存在: {file_path}")
                        continue
                    file_size = path.stat().st_size
                    logger.info(f"📎 添加附件: {path.name} ({file_size} bytes)")
                    with open(path, "rb") as f:
                        file_data = f.read()
                        logger.info(f"📎 读取文件完成: {len(file_data)} bytes")
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file_data)
                        encoders.encode_base64(part)
                    
                    filename = path.name
                    try:
                        filename.encode('ascii')
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                    except UnicodeEncodeError:
                        from urllib.parse import quote
                        encoded_filename = quote(filename, safe='')
                        part.add_header(
                            'Content-Disposition',
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )
                    
                    msg.attach(part)
                    logger.info(f"📎 附件已添加到邮件: {path.name}")
            
            import ssl
            context = ssl.create_default_context()
            
            email_bytes = msg.as_bytes(policy=default_policy)
            logger.info(f"📧 邮件总大小: {len(email_bytes)} bytes")
            
            with smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"], context=context) as server:
                server.login(smtp_config["user"], smtp_config["password"])
                server.sendmail(smtp_config["user"], recipients, email_bytes)
            
            logger.info(f"📤 邮件发送成功: {', '.join(recipients)}")
            return {"success": True, "recipients": recipients}
            
        except Exception as e:
            import traceback
            logger.error(f"邮件发送失败: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def _handle_receive_email(self, params: Dict) -> str:
        """处理接收邮件"""
        logger.info("📥 检查新邮件")
        self.received_count += 1
        return "✅ 已检查新邮件"

    async def _handle_check_email(self) -> str:
        """检查邮件状态"""
        return f"📧 已发送: {self.sent_count}, 已接收: {self.received_count}"
    
    async def send_reply(self, to_email: str, subject: str, content: str) -> str:
        """发送回复邮件"""
        logger.info(f"📧 发送回复邮件到: {to_email}")
        
        # 获取 SMTP 配置
        from ...config import settings
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件配置不完整，请检查邮箱设置"
        
        result = await self._send_email(
            to=to_email,
            subject=subject,
            content=content,
            smtp_config=smtp_config
        )
        
        if result.get("success"):
            self.sent_count += 1
            return f"✅ 邮件已发送到: {to_email}"
        else:
            return f"❌ 发送失败: {result.get('error', '未知错误')}"

    async def _handle_save_attachment(self, params: Dict) -> str:
        """处理保存邮件附件到指定目录"""
        import os
        
        save_path = params.get("save_path", "")
        attachments = params.get("attachments", [])
        
        if not save_path:
            return "❌ 未指定保存路径"
        
        if not attachments:
            return "❌ 邮件中没有附件"
        
        # 确保目标目录存在
        try:
            os.makedirs(save_path, exist_ok=True)
            logger.info(f"📁 确保目录存在: {save_path}")
        except Exception as e:
            logger.error(f"❌ 创建目录失败: {e}")
            return f"❌ 创建目录失败: {e}"
        
        saved_files = []
        errors = []
        
        for att in attachments:
            try:
                filename = att.get("filename", "")
                data = att.get("data", b"")
                
                if not filename or not data:
                    continue
                
                # 构建完整保存路径
                file_path = os.path.join(save_path, filename)
                
                # 保存文件
                with open(file_path, "wb") as f:
                    f.write(data)
                
                saved_files.append(filename)
                logger.info(f"✅ 已保存附件: {file_path}")
                
            except Exception as e:
                error_msg = f"保存 {att.get('filename', '未知文件')} 失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # 构建结果信息
        if saved_files:
            result = f"✅ 已成功保存 {len(saved_files)} 个附件到 {save_path}:\n"
            for f in saved_files:
                result += f"  - {f}\n"
        else:
            result = "❌ 没有附件被保存"
        
        if errors:
            result += f"\n⚠️ 保存失败: {len(errors)} 个\n"
            for e in errors:
                result += f"  - {e}\n"
        
        return result.strip()

    async def _handle_send_to_relationship(self, original_text: str, params: Dict) -> str:
        """批量发送邮件给指定关系的联系人"""
        from ...config import settings
        from ...contacts.smart_contact_book import smart_contact_book
        
        relationship = params.get("relationship", "")
        subject = params.get("subject")
        content_template = params.get("content_template") or params.get("content")
        
        if not relationship:
            return "❌ 请指定关系类型，如：家人、同学、同事"
        
        contacts = smart_contact_book.get_contacts_by_relationship(relationship)
        
        if not contacts:
            return f"📭 没有关系为「{relationship}」的联系人"
        
        contacts_with_email = [c for c in contacts if c.email]
        
        if not contacts_with_email:
            return f"❌ 关系为「{relationship}」的联系人都没有邮箱地址"
        
        smtp_config = {
            "host": settings.agent.email_smtp,
            "port": settings.agent.email_port,
            "user": settings.agent.email,
            "password": settings.agent.email_password
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            return "❌ 邮件发送功能未配置，请在设置中配置邮箱和授权码"
        
        if not subject or not content_template:
            email_content = await self._generate_batch_email_content(
                original_text,
                relationship=relationship,
                contact_count=len(contacts_with_email)
            )
            if not subject:
                subject = email_content.get("subject", f"给{relationship}的邮件")
            if not content_template:
                content_template = email_content.get("content_template", "祝您一切顺利！")
        
        success_count = 0
        failed_count = 0
        results = []
        
        for contact in contacts_with_email:
            try:
                personalized_content = content_template.replace("{name}", contact.name)
                
                result = await self._send_email(
                    to=contact.email,
                    subject=subject,
                    content=personalized_content,
                    smtp_config=smtp_config
                )
                
                if result["success"]:
                    success_count += 1
                    results.append(f"✅ {contact.name} ({contact.email})")
                    logger.info(f"📧 批量发送成功: {contact.name}")
                else:
                    failed_count += 1
                    results.append(f"❌ {contact.name}: {result['error']}")
                    logger.warning(f"📧 批量发送失败: {contact.name} - {result['error']}")
                
            except Exception as e:
                failed_count += 1
                results.append(f"❌ {contact.name}: {str(e)}")
                logger.error(f"📧 批量发送异常: {contact.name} - {e}")
        
        summary = f"📧 批量发送完成\n"
        summary += f"关系: {relationship}\n"
        summary += f"成功: {success_count} 封\n"
        summary += f"失败: {failed_count} 封\n\n"
        summary += "详细结果:\n"
        summary += "\n".join(results)
        
        if contacts_with_email:
            skipped = len(contacts) - len(contacts_with_email)
            if skipped > 0:
                summary += f"\n\n⚠️ 有 {skipped} 位联系人没有邮箱地址，已跳过"
        
        return summary

    async def _generate_batch_email_content(
        self,
        user_request: str,
        relationship: str,
        contact_count: int
    ) -> Dict[str, str]:
        """生成批量邮件内容"""
        from ...config import settings
        from datetime import datetime
        
        llm = self._get_llm_gateway()
        
        user_name = settings.user.formal_name or settings.user.name or "用户"
        agent_name = settings.agent.name or "智能助手"
        
        current_year = datetime.now().year
        zodiac_map = {2024: "龙年", 2025: "蛇年", 2026: "马年", 2027: "羊年", 2028: "猴年"}
        current_zodiac = zodiac_map.get(current_year, "")
        
        prompt = f"""你是一个邮件撰写助手。用户想给所有「{relationship}」发送邮件，共 {contact_count} 人。

当前日期: {datetime.now().strftime("%Y年%m月%d日")}（{current_year}年是{current_zodiac}）
用户请求: {user_request}
用户姓名: {user_name}
关系类型: {relationship}

请撰写一封适合批量发送的邮件：
1. 邮件主题：简洁温馨
2. 邮件正文模板：
   - 开头称呼使用 {{name}} 占位符（系统会替换为具体姓名）
   - 内容要适合该关系类型（{relationship}）
   - 表达真诚的情感
   - 结尾要有祝福语
   - 署名: {user_name}的智能助理-{agent_name}

请以 JSON 格式返回：
{{
    "subject": "邮件主题",
    "content_template": "邮件正文模板（使用 {{name}} 作为称呼占位符）"
}}

只返回 JSON，不要其他内容。"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await llm.chat(messages)
            
            import json
            result = json.loads(response.content.strip().replace("```json", "").replace("```", "").strip())
            
            logger.info(f"📧 LLM 生成批量邮件: subject={result.get('subject')}")
            return result
            
        except Exception as e:
            logger.error(f"LLM 生成批量邮件失败: {e}")
            return {
                "subject": f"给{relationship}的祝福",
                "content_template": "{{name}}，祝您一切顺利！\n\n--\n{user_name}的智能助理-{agent_name}"
            }

    def get_status(self) -> Dict:
        """获取智能体状态"""
        status = super().get_status()
        status.update({
            "sent_count": self.sent_count,
            "received_count": self.received_count
        })
        return status

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """## 邮件智能体

### 功能说明
邮件智能体可以发送和接收电子邮件，支持自动生成邮件内容，支持发送附件。

### 支持的操作
- **发送邮件**：发送邮件给指定收件人
- **接收邮件**：检查新邮件
- **发送附件**：发送带有附件的邮件
- **邮件管理**：管理邮件收发记录

### 使用示例
- "给张三发邮件" - 发送邮件给张三
- "发送邮件给李四，内容是..." - 发送指定内容的邮件
- "查邮件" - 检查新邮件
- "把文件发给王五" - 发送带附件的邮件

### 注意事项
- 需要配置邮件服务器信息
- 发送邮件前请确保收件人信息正确
- 大附件可能需要较长时间发送"""
