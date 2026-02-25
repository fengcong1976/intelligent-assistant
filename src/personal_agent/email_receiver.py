"""
Email Receiver - IMAP邮件接收系统
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from loguru import logger

from .config import settings


@dataclass
class ReceivedEmail:
    """接收到的邮件"""
    id: str
    subject: str
    sender: str
    sender_email: str
    to: str
    date: datetime
    body: str
    html_body: str = ""
    attachments: List[Dict] = field(default_factory=list)
    is_read: bool = False
    message_id: str = ""  # 邮件唯一标识
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "to": self.to,
            "date": self.date.isoformat() if self.date else None,
            "body": self.body,
            "is_read": self.is_read
        }


class EmailReceiver:
    """IMAP邮件接收器"""
    
    def __init__(self):
        self.imap_server = settings.agent.email_imap or "imap.qq.com"
        self.imap_port = settings.agent.email_imap_port or 993
        self.email = settings.agent.email
        self.password = settings.agent.email_password
        self._connection = None
        self._last_uid = None
        self._callbacks: List[Callable] = []
    
    def _decode_header_value(self, value: str) -> str:
        """解码邮件头"""
        if not value:
            return ""
        
        decoded_parts = decode_header(value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8', errors='ignore'))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(str(part))
        return ''.join(result)
    
    def _get_email_body(self, msg) -> tuple:
        """提取邮件正文"""
        body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    continue
                
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text = payload.decode(charset, errors='ignore')
                        
                        if content_type == "text/plain" and not body:
                            body = text
                        elif content_type == "text/html" and not html_body:
                            html_body = text
                except Exception as e:
                    logger.warning(f"Failed to decode email part: {e}")
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.warning(f"Failed to decode email body: {e}")
        
        return body, html_body
    
    def _extract_attachments(self, msg) -> List[Dict]:
        """提取邮件附件"""
        attachments = []
        
        if not msg.is_multipart():
            return attachments
        
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" not in content_disposition:
                continue
            
            try:
                filename = part.get_filename()
                if not filename:
                    continue
                
                # 解码文件名
                filename = self._decode_header_value(filename)
                
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                
                content_type = part.get_content_type()
                
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "data": payload,
                    "size": len(payload)
                })
                
                logger.info(f"Extracted attachment: {filename} ({content_type}, {len(payload)} bytes)")
                
            except Exception as e:
                logger.warning(f"Failed to extract attachment: {e}")
        
        return attachments
    
    def _validate_config(self) -> tuple[bool, str]:
        """验证配置"""
        if not self.email:
            return False, "邮箱地址未配置"
        
        if not self.password:
            return False, "邮箱密码未配置"
        
        if not self.imap_server:
            return False, "IMAP服务器地址未配置"
        
        if "@" not in self.email:
            return False, f"邮箱地址格式错误: {self.email}"
        
        return True, "配置验证通过"
    
    def _test_dns_resolution(self) -> tuple[bool, str]:
        """测试DNS解析"""
        import socket
        try:
            ip = socket.gethostbyname(self.imap_server)
            logger.info(f"DNS解析成功: {self.imap_server} -> {ip}")
            return True, f"DNS解析成功: {ip}"
        except socket.gaierror as e:
            error_msg = f"DNS解析失败: {self.imap_server} - {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _test_network_connection(self) -> tuple[bool, str]:
        """测试网络连接"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.imap_server, self.imap_port))
            sock.close()
            
            if result == 0:
                logger.info(f"网络连接成功: {self.imap_server}:{self.imap_port}")
                return True, f"网络连接成功"
            else:
                error_msg = f"网络连接失败: {self.imap_server}:{self.imap_port} - 错误代码: {result}"
                logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"网络连接测试失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def connect(self) -> bool:
        """连接到IMAP服务器"""
        try:
            logger.info("=" * 60)
            logger.info("🔧 开始连接IMAP服务器")
            logger.info("=" * 60)
            
            logger.info(f"📧 邮箱地址: {self.email}")
            logger.info(f"🌐 IMAP服务器: {self.imap_server}:{self.imap_port}")
            
            valid, msg = self._validate_config()
            if not valid:
                logger.error(f"❌ 配置验证失败: {msg}")
                return False
            
            logger.success(f"✅ {msg}")
            
            dns_ok, dns_msg = self._test_dns_resolution()
            if not dns_ok:
                logger.error(f"❌ {dns_msg}")
                logger.error("💡 可能的原因:")
                logger.error("   1. 网络连接问题，请检查网络")
                logger.error("   2. DNS服务器配置问题")
                logger.error("   3. 防火墙阻止了DNS查询")
                logger.error("💡 解决方案:")
                logger.error("   1. 尝试使用其他DNS服务器（如8.8.8.8）")
                logger.error("   2. 检查网络连接")
                logger.error("   3. 暂时禁用邮件监控功能")
                return False
            
            net_ok, net_msg = self._test_network_connection()
            if not net_ok:
                logger.error(f"❌ {net_msg}")
                logger.error("💡 可能的原因:")
                logger.error("   1. IMAP服务器地址错误")
                logger.error("   2. 端口被防火墙阻止")
                logger.error("   3. QQ邮箱IMAP服务未开启")
                logger.error("💡 解决方案:")
                logger.error("   1. 检查QQ邮箱IMAP服务是否开启")
                logger.error("   2. 检查防火墙设置")
                logger.error("   3. 尝试使用SSL端口993")
                return False
            
            import ssl
            context = ssl.create_default_context()
            
            logger.info(f"🔐 正在建立SSL连接...")
            self._connection = imaplib.IMAP4_SSL(
                self.imap_server,
                self.imap_port,
                ssl_context=context
            )
            
            logger.info(f"🔑 正在登录...")
            self._connection.login(self.email, self.password)
            
            logger.info(f"📂 正在选择收件箱...")
            self._connection.select('INBOX')
            
            logger.success(f"✅ 成功连接到IMAP服务器: {self.imap_server}")
            logger.info("=" * 60)
            return True
            
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP协议错误: {e}"
            logger.error(f"❌ {error_msg}")
            logger.error("💡 可能的原因:")
            logger.error("   1. 邮箱密码错误")
            logger.error("   2. 需要使用授权码而非密码")
            logger.error("   3. IMAP服务未开启")
            logger.error("💡 解决方案:")
            logger.error("   1. 登录QQ邮箱，开启IMAP服务")
            logger.error("   2. 生成授权码，使用授权码代替密码")
            logger.error("   3. 检查邮箱设置")
            return False
            
        except Exception as e:
            error_msg = f"连接IMAP服务器失败: {e}"
            logger.error(f"❌ {error_msg}")
            logger.error("💡 建议暂时禁用邮件监控功能")
            logger.info("=" * 60)
            return False
    
    def disconnect(self):
        """断开连接"""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except:
                pass
            self._connection = None
            logger.info("Disconnected from IMAP server")
    
    def _ensure_connection(self) -> bool:
        """确保连接"""
        if not self._connection:
            return self.connect()
        
        try:
            self._connection.noop()
            return True
        except:
            self.disconnect()
            return self.connect()
    
    def mark_as_read(self, email_id: str) -> bool:
        """标记邮件为已读"""
        if not self._ensure_connection():
            return False
        
        try:
            # 添加 \Seen 标志标记为已读
            self._connection.store(email_id.encode(), '+FLAGS', '\\Seen')
            logger.info(f"Marked email {email_id} as read")
            return True
        except Exception as e:
            logger.error(f"Failed to mark email {email_id} as read: {e}")
            return False
    
    def fetch_unread(self, limit: int = 10) -> List[ReceivedEmail]:
        """获取未读邮件"""
        if not self._ensure_connection():
            return []
        
        emails = []
        
        try:
            # 只获取未读邮件
            status, messages = self._connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            
            for email_id in email_ids[-limit:]:
                try:
                    status, msg_data = self._connection.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    subject = self._decode_header_value(msg.get('Subject', ''))
                    sender_full = msg.get('From', '')
                    sender_name, sender_email = parseaddr(sender_full)
                    sender_name = self._decode_header_value(sender_name)
                    
                    date_str = msg.get('Date', '')
                    try:
                        from email.utils import parsedate_to_datetime
                        date = parsedate_to_datetime(date_str)
                    except:
                        date = datetime.now()
                    
                    body, html_body = self._get_email_body(msg)
                    
                    # 提取附件
                    attachments = self._extract_attachments(msg)
                    
                    # 获取邮件唯一标识
                    message_id = msg.get('Message-ID', '') or msg.get('Message-Id', '')
                    if not message_id:
                        # 如果没有 Message-ID，使用其他字段组合生成唯一标识
                        message_id = f"{sender_email}_{date_str}_{subject}"[:100]
                    
                    received = ReceivedEmail(
                        id=email_id.decode(),
                        subject=subject,
                        sender=sender_name or sender_email,
                        sender_email=sender_email,
                        to=msg.get('To', ''),
                        date=date,
                        body=body,
                        html_body=html_body,
                        message_id=message_id,
                        attachments=attachments
                    )
                    
                    emails.append(received)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch email {email_id}: {e}")
                    continue
            
            if emails:  # 只在有新邮件时打印
                logger.info(f"Fetched {len(emails)} unread emails")
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            self.disconnect()
        
        return emails
    
    def fetch_latest(self, limit: int = 5) -> List[ReceivedEmail]:
        """获取最新邮件"""
        if not self._ensure_connection():
            return []
        
        emails = []
        
        try:
            status, messages = self._connection.search(None, 'ALL')
            
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            
            for email_id in reversed(email_ids[-limit:]):
                try:
                    status, msg_data = self._connection.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    subject = self._decode_header_value(msg.get('Subject', ''))
                    sender_full = msg.get('From', '')
                    sender_name, sender_email = parseaddr(sender_full)
                    sender_name = self._decode_header_value(sender_name)
                    
                    date_str = msg.get('Date', '')
                    try:
                        from email.utils import parsedate_to_datetime
                        date = parsedate_to_datetime(date_str)
                    except:
                        date = datetime.now()
                    
                    body, html_body = self._get_email_body(msg)
                    
                    received = ReceivedEmail(
                        id=email_id.decode(),
                        subject=subject,
                        sender=sender_name or sender_email,
                        sender_email=sender_email,
                        to=msg.get('To', ''),
                        date=date,
                        body=body,
                        html_body=html_body
                    )
                    
                    emails.append(received)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch email {email_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            self.disconnect()
        
        return emails
    
    def add_callback(self, callback: Callable):
        """添加新邮件回调"""
        self._callbacks.append(callback)
    
    async def check_new_emails(self) -> List[ReceivedEmail]:
        """检查新邮件"""
        emails = self.fetch_unread()
        
        for email in emails:
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(email)
                    else:
                        callback(email)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        return emails


email_receiver = EmailReceiver()
