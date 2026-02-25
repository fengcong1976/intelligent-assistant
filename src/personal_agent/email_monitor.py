"""
Email Monitor Service - 邮件监控服务
定期检查新邮件并通知智能体处理
"""
import asyncio
from datetime import datetime
from typing import Optional, Callable, List
from loguru import logger

from .email_receiver import EmailReceiver, ReceivedEmail, email_receiver
from .config import settings


class EmailMonitorService:
    """邮件监控服务"""
    
    def __init__(
        self,
        check_interval: int = 1,  # 改为1秒，提高响应速度
        on_new_email: Optional[Callable] = None
    ):
        self.check_interval = check_interval
        self.on_new_email = on_new_email
        self.receiver = email_receiver
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_ids: set = set()
        self._processed_count = 0
        self._notification_channel = None
        self._master_agent = None
        self._email_agent = None
    
    def set_agents(self, master_agent, email_agent):
        """设置智能体引用"""
        self._master_agent = master_agent
        self._email_agent = email_agent
        self.on_new_email = None
        logger.info("📧 邮件监控已关联智能体")
    
    def set_notification_channel(self, channel):
        """设置通知渠道"""
        self._notification_channel = channel
    
    async def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        
        if self.receiver.connect():
            logger.info(f"Email monitor started, checking every {self.check_interval}s")
            self._task = asyncio.create_task(self._monitor_loop())
        else:
            logger.error("Failed to start email monitor: cannot connect")
            self._running = False
    
    async def stop(self):
        """停止监控"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        self.receiver.disconnect()
        logger.info("Email monitor stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_emails()
            except Exception as e:
                logger.error(f"Email check error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_emails(self):
        """检查新邮件"""
        try:
            emails = self.receiver.fetch_unread(limit=5)
            
            # 使用 Message-ID 去重，避免同一封邮件被重复处理
            new_emails = []
            for e in emails:
                msg_id = e.message_id if e.message_id else e.id
                if msg_id not in self._processed_ids:
                    new_emails.append(e)
                    self._processed_ids.add(msg_id)
            
            for email in new_emails:
                try:
                    await self._handle_new_email(email)
                    self._processed_count += 1
                except Exception as e:
                    logger.error(f"处理邮件失败 [{email.subject}]: {e}")
                finally:
                    # 无论处理成功与否，都标记为已读，避免重复处理
                    try:
                        self.receiver.mark_as_read(email.id)
                    except Exception as e:
                        logger.error(f"标记邮件已读失败 [{email.subject}]: {e}")
            
            if new_emails:
                logger.info(f"Processed {len(new_emails)} new emails (total: {self._processed_count})")
                
        except Exception as e:
            logger.error(f"Failed to check emails: {e}")
    
    def _is_own_email(self, email: ReceivedEmail) -> bool:
        """检查是否是自己发送的邮件"""
        own_emails = [
            settings.agent.email.lower() if settings.agent.email else "",
            settings.user.email.lower() if settings.user.email else "",
        ]
        # 过滤掉空字符串
        own_emails = [e for e in own_emails if e]
        sender_email = email.sender_email.lower() if email.sender_email else ""
        return sender_email in own_emails

    async def _handle_new_email(self, email: ReceivedEmail):
        """处理新邮件 - 区分自己发的邮件和别人发的邮件"""
        logger.info(f"📧 新邮件: {email.sender} - {email.subject}")
        
        # 检查是否是自己发送的邮件
        if self._is_own_email(email):
            await self._handle_own_email(email)
        else:
            await self._handle_others_email(email)

    async def _handle_own_email(self, email: ReceivedEmail):
        """处理自己发送的邮件 - 保持原来的逻辑"""
        # 检查是否是自动回复邮件，避免循环
        if self._is_auto_reply_email(email):
            logger.info(f"📧 检测到自动回复邮件，跳过处理: {email.subject}")
            return
        
        # 检查邮件主题是否以 Re: 开头，如果是则可能是回复邮件，跳过自动处理
        if email.subject.startswith("Re:"):
            logger.info(f"📧 检测到回复邮件，跳过自动处理: {email.subject}")
            return
        
        if self._master_agent and self._email_agent:
            try:
                # 构建附件信息
                attachment_info = ""
                if email.attachments:
                    attachment_info = "\n📎 附件:\n"
                    for att in email.attachments:
                        attachment_info += f"  - {att['filename']} ({att['size']} bytes)\n"
                
                email_content = f"""收到来自 {email.sender} <{email.sender_email}> 的邮件：

主题：{email.subject}
时间：{email.date.strftime("%Y-%m-%d %H:%M") if email.date else "未知"}

内容：
{email.body}
{attachment_info}
请处理这封邮件，如果需要回复，请告诉我回复内容。"""
                
                response = await self._master_agent.process_user_request(
                    request=email_content,
                    context={
                        "source": "email", 
                        "sender_email": email.sender_email, 
                        "email_subject": email.subject,
                        "attachments": email.attachments
                    }
                )
                
                if response and not response.startswith("❌"):
                    await self._email_agent.send_reply(
                        to_email=email.sender_email,
                        subject=f"Re: {email.subject}",
                        content=response
                    )
                
            except Exception as e:
                logger.error(f"处理自己邮件失败: {e}")
        else:
            logger.warning("📧 邮件监控未关联智能体，跳过处理")

    def _is_auto_reply_email(self, email: ReceivedEmail) -> bool:
        """检查是否是自动回复邮件，避免循环"""
        # 检查主题是否包含 Re: 且发件人是自己（说明是自动回复的邮件）
        if email.subject.startswith("Re:") and self._is_own_email(email):
            return True
        # 检查邮件内容是否包含自动回复标记
        if email.body and "此邮件为系统自动回复" in email.body:
            return True
        return False

    async def _handle_others_email(self, email: ReceivedEmail):
        """处理别人发送的邮件 - 在对话框显示并自动回复"""
        # 检查是否是自动回复邮件，避免循环
        if self._is_auto_reply_email(email):
            logger.info(f"📧 检测到自动回复邮件，跳过处理: {email.subject}")
            return
        
        # 格式化邮件通知内容
        time_str = email.date.strftime("%Y-%m-%d %H:%M") if email.date else "未知时间"
        body_preview = email.body[:500] if email.body else "(无正文)"
        
        notification_message = f"""📧 收到新邮件

👤 发件人：{email.sender} <{email.sender_email}>
📎 主题：{email.subject}
📅 时间：{time_str}

📝 内容：
{body_preview}

{'...' if len(email.body) > 500 else ''}"""
        
        # 1. 通知 Master Agent 在对话窗口显示
        if self._master_agent:
            try:
                from .agents.message_bus import message_bus
                from .agents.base import Message
                
                message = Message(
                    from_agent="email_monitor",
                    to_agent="master",
                    type="new_email_notification",
                    content=notification_message,
                    data={
                        "sender": email.sender,
                        "sender_email": email.sender_email,
                        "subject": email.subject,
                        "body": email.body,
                        "date": time_str
                    }
                )
                await message_bus.send_message(message)
            except Exception as e:
                logger.error(f"通知 Master 失败: {e}")
        
        # 2. 自动回复邮件告知已转告（只回复一次，避免循环）
        # 检查是否已经回复过（通过主题判断）
        if self._email_agent and not email.subject.startswith("Re:"):
            try:
                reply_content = f"""您好，{email.sender}！

我已收到您的邮件，主题："{email.subject}"。

您的邮件内容已转告给我的主人，请等待回复。

此邮件为系统自动回复。

谢谢！"""
                
                await self._email_agent.send_reply(
                    to_email=email.sender_email,
                    subject=f"Re: {email.subject}",
                    content=reply_content
                )
                logger.info(f"📧 已发送自动回复给: {email.sender_email}")
            except Exception as e:
                logger.error(f"自动回复邮件失败: {e}")
        else:
            if not self._email_agent:
                logger.warning("📧 邮件智能体未设置，无法发送自动回复")
            else:
                logger.info(f"📧 邮件主题以 Re: 开头，跳过自动回复: {email.subject}")
        
        if self._notification_channel:
            try:
                notification = self._format_notification(email)
                await self._notification_channel.send(notification)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    def _format_notification(self, email: ReceivedEmail) -> str:
        """格式化通知消息"""
        time_str = email.date.strftime("%Y-%m-%d %H:%M") if email.date else "未知时间"
        
        body_preview = email.body[:200] if email.body else "(无正文)"
        if len(email.body) > 200:
            body_preview += "..."
        
        return f"""📧 收到新邮件

👤 发件人：{email.sender} <{email.sender_email}>
📎 主题：{email.subject}
📅 时间：{time_str}

📝 内容预览：
{body_preview}
"""
    
    async def check_now(self) -> List[ReceivedEmail]:
        """立即检查"""
        return await self.receiver.check_new_emails()
    
    def get_status(self) -> dict:
        """获取状态"""
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "processed_count": len(self._processed_ids),
            "connected": self.receiver._connection is not None
        }


email_monitor = EmailMonitorService()
