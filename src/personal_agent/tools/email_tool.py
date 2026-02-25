"""
Email Tool - Send emails via SMTP with retry mechanism
"""
import smtplib
import socket
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from .base import BaseTool, ToolResult, tool_registry
from ..config import settings


class SendEmailTool(BaseTool):
    name = "send_email"
    description = """【重要】发送邮件的唯一工具！当用户要求发邮件、发送通知、发送提醒时必须调用此工具。

使用场景：
- 用户说"给我发个邮件"、"发送邮件到xxx"
- 用户说"邮件通知我"、"发邮件提醒我"
- 用户说"把xxx发送到我邮箱"

参数说明：
- to: 收件人邮箱地址（用户说"发给我"时使用用户设置的邮箱）
- subject: 邮件主题
- body: 邮件正文内容

注意：不要假装发送邮件，必须调用此工具才能真正发送！"""
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "收件人邮箱地址。如果用户说'发给我'，使用用户设置的邮箱地址"
            },
            "subject": {
                "type": "string",
                "description": "邮件主题"
            },
            "body": {
                "type": "string",
                "description": "邮件正文内容"
            },
            "cc": {
                "type": "string",
                "description": "抄送邮箱（可选，多个用逗号分隔）"
            },
            "bcc": {
                "type": "string",
                "description": "密送邮箱（可选，多个用逗号分隔）"
            },
            "attachments": {
                "type": "string",
                "description": "附件文件路径（可选，多个用逗号分隔）"
            },
            "html": {
                "type": "boolean",
                "description": "正文是否为HTML格式（默认false）"
            }
        },
        "required": ["to", "subject", "body"]
    }

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        attachments: str = "",
        html: bool = False
    ) -> tuple:
        email_config = settings.agent
        
        msg = MIMEMultipart()
        msg['From'] = email_config.email
        msg['To'] = to
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        if attachments:
            for file_path in attachments.split(','):
                file_path = file_path.strip()
                if not file_path:
                    continue
                    
                path = Path(file_path)
                if not path.exists():
                    return None, f"Attachment file not found: {file_path}"
                
                # 根据文件扩展名获取 MIME 类型
                import mimetypes
                mime_type, _ = mimetypes.guess_type(str(path))
                if mime_type:
                    main_type, sub_type = mime_type.split('/', 1)
                else:
                    main_type, sub_type = 'application', 'octet-stream'
                
                with open(path, 'rb') as f:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    
                    # 添加 Content-Disposition 头，确保文件名正确显示
                    from email.header import Header
                    filename = path.name
                    # 对中文文件名进行编码
                    try:
                        filename.encode('ascii')
                        # 纯 ASCII 文件名
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                    except UnicodeEncodeError:
                        # 包含非 ASCII 字符，使用 RFC 5987 编码
                        from urllib.parse import quote
                        encoded_filename = quote(filename, safe='')
                        part.add_header(
                            'Content-Disposition',
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )
                    
                    msg.attach(part)
        
        recipients = [addr.strip() for addr in to.split(',')]
        if cc:
            recipients.extend([addr.strip() for addr in cc.split(',')])
        if bcc:
            recipients.extend([addr.strip() for addr in bcc.split(',')])
        
        return msg, recipients

    def _send_with_smtp(
        self,
        msg: MIMEMultipart,
        recipients: List[str],
        smtp_server: str,
        smtp_port: int,
        email: str,
        password: str
    ) -> tuple:
        if smtp_port == 465:
            context = smtplib.ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = 0
            
            server = smtplib.SMTP_SSL(
                smtp_server, 
                smtp_port,
                timeout=30,
                context=context
            )
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        
        server.login(email, password)
        server.sendmail(email, recipients, msg.as_string())
        server.quit()
        
        return True, "OK"

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        attachments: str = "",
        html: bool = False
    ) -> ToolResult:
        email_config = settings.agent
        
        if not email_config.email:
            logger.error("Email not configured")
            return ToolResult(
                success=False,
                output="",
                error="Email not configured. Please set AGENT_EMAIL in settings."
            )
        
        if not email_config.email_password:
            logger.error("Email password not configured")
            return ToolResult(
                success=False,
                output="",
                error="Email password not configured. Please set AGENT_EMAIL_PASSWORD in settings."
            )
        
        msg, recipients_or_error = self._create_message(
            to, subject, body, cc, bcc, attachments, html
        )
        
        if msg is None:
            return ToolResult(
                success=False,
                output="",
                error=recipients_or_error
            )
        
        recipients = recipients_or_error
        smtp_server = email_config.email_smtp
        smtp_port = email_config.email_port
        email = email_config.email
        password = email_config.email_password
        
        max_retries = 3
        retry_delay = 2
        
        errors = []
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                
                self._send_with_smtp(msg, recipients, smtp_server, smtp_port, email, password)
                
                return ToolResult(
                    success=True,
                    output=f"Email sent successfully to: {to}\nSubject: {subject}"
                )
                
            except smtplib.SMTPAuthenticationError as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"SMTP authentication failed. Error: {str(e)}\n\nQQ邮箱需要使用授权码，不是QQ密码！\n获取授权码步骤：\n1. 登录 mail.qq.com\n2. 设置 -> 账户 -> POP3/SMTP服务\n3. 生成授权码（16位字母）\n4. 将授权码填入 AGENT_EMAIL_PASSWORD"
                )
            except smtplib.SMTPServerDisconnected as e:
                errors.append(f"Attempt {attempt + 1}: Server disconnected - This usually means wrong authorization code. Error: {str(e)}")
            except smtplib.SMTPConnectError as e:
                errors.append(f"Attempt {attempt + 1}: Connection failed - {str(e)}")
            except socket.timeout as e:
                errors.append(f"Attempt {attempt + 1}: Connection timeout - {str(e)}")
            except ConnectionResetError as e:
                errors.append(f"Attempt {attempt + 1}: Connection reset - {str(e)}")
            except ConnectionAbortedError as e:
                errors.append(f"Attempt {attempt + 1}: Connection aborted - {str(e)}")
            except OSError as e:
                errors.append(f"Attempt {attempt + 1}: Network error - {str(e)}")
            except smtplib.SMTPException as e:
                errors.append(f"Attempt {attempt + 1}: SMTP error - {str(e)}")
            except Exception as e:
                errors.append(f"Attempt {attempt + 1}: Unexpected error - {str(e)}")
        
        error_msg = "\n".join(errors)
        return ToolResult(
            success=False,
            output="",
            error=f"Failed to send email after {max_retries} attempts:\n{error_msg}"
        )


class CheckEmailConfigTool(BaseTool):
    name = "check_email_config"
    description = "Check if email is properly configured. Use this to verify email settings before sending."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        email_config = settings.agent
        
        status = []
        status.append(f"Email: {email_config.email or 'Not configured'}")
        status.append(f"Password: {'Configured' if email_config.email_password else 'Not configured'}")
        status.append(f"SMTP Server: {email_config.email_smtp}")
        status.append(f"SMTP Port: {email_config.email_port}")
        
        if not email_config.email or not email_config.email_password:
            status.append("\nStatus: NOT READY - Please configure email settings")
            return ToolResult(
                success=False,
                output="\n".join(status),
                error="Email not fully configured"
            )
        
        status.append("\nStatus: READY - Email is configured")
        return ToolResult(
            success=True,
            output="\n".join(status)
        )


class TestEmailConnectionTool(BaseTool):
    name = "test_email_connection"
    description = "Test SMTP connection to verify email settings are working."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        email_config = settings.agent
        
        if not email_config.email or not email_config.email_password:
            return ToolResult(
                success=False,
                output="",
                error="Email not configured. Please set AGENT_EMAIL and AGENT_EMAIL_PASSWORD."
            )
        
        smtp_server = email_config.email_smtp
        smtp_port = email_config.email_port
        
        try:
            if smtp_port == 465:
                context = smtplib.ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = 0
                
                server = smtplib.SMTP_SSL(
                    smtp_server,
                    smtp_port,
                    timeout=30,
                    context=context
                )
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()
            
            server.login(email_config.email, email_config.email_password)
            server.quit()
            
            return ToolResult(
                success=True,
                output=f"SMTP connection test successful!\nServer: {smtp_server}:{smtp_port}\nLogin: OK"
            )
            
        except smtplib.SMTPAuthenticationError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Authentication failed. Error: {str(e)}\n\nQQ邮箱需要使用授权码，不是QQ密码！\n获取授权码步骤：\n1. 登录 mail.qq.com\n2. 设置 -> 账户 -> POP3/SMTP服务\n3. 生成授权码（16位字母）\n4. 将授权码填入 AGENT_EMAIL_PASSWORD"
            )
        except smtplib.SMTPServerDisconnected as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Server disconnected during login - This usually means wrong authorization code.\n\nQQ邮箱需要使用授权码，不是QQ密码！\n获取授权码步骤：\n1. 登录 mail.qq.com\n2. 设置 -> 账户 -> POP3/SMTP服务\n3. 生成授权码（16位字母）\n4. 将授权码填入 AGENT_EMAIL_PASSWORD"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Connection failed: {str(e)}"
            )


def register_email_tools():
    tool_registry.register(SendEmailTool())
    tool_registry.register(CheckEmailConfigTool())
    tool_registry.register(TestEmailConnectionTool())
