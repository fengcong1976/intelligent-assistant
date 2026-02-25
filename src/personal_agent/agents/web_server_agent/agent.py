"""
Web服务器智能体 - 提供Web界面通信渠道
类似于邮件智能体，只负责消息的收发，不处理业务逻辑
业务逻辑由 Master Agent 进行意图解析和任务分配
"""
import asyncio
import socket
import secrets
import base64
from io import BytesIO
from typing import Dict, Any, Optional, Callable
from loguru import logger

from ..base import BaseAgent, Task


class WebServerAgent(BaseAgent):
    """
    Web服务器智能体 - 纯通信渠道
    
    职责：
    1. 启动/停止/查询 Web 服务器状态
    2. 接收来自 Web 界面的消息，转发给 Master Agent
    3. 将 Master Agent 的处理结果返回给 Web 用户
    
    不负责：
    - 意图解析（由 Master Agent 处理）
    - 业务逻辑执行（由其他子智能体处理）
    """
    
    KEYWORD_MAPPINGS = {
        "启动服务器": ("start", {}),
        "开启服务器": ("start", {}),
        "停止服务器": ("stop", {}),
        "关闭服务器": ("stop", {}),
        "服务器状态": ("status", {}),
        "服务器密码": ("password", {}),
        "生成密码": ("password", {}),
        "远程访问": ("start", {}),
    }

    def __init__(self):
        super().__init__(
            name="web_server_agent",
            description="Web服务器智能体 - 提供Web界面通信渠道，支持手机等设备远程访问"
        )

        self.register_capability("web_server", "Web服务器")
        self.register_capability("remote_access", "远程访问")
        self.register_capability("mobile_interface", "移动端界面")

        self.server_running = False
        self.server_port = 12345
        self.web_runner = None
        self._message_handler: Optional[Callable] = None
        
        self.access_password: Optional[str] = None
        self.authenticated_sessions: set = set()
        
        self._cached_html = None
        self._cached_html_gzip = None
        self._cache_html()

    def set_message_handler(self, handler: Callable):
        """
        设置消息处理器（由 Master Agent 提供）
        
        Args:
            handler: 异步函数，接收消息内容，返回处理结果
                     签名: async def handler(message: str, metadata: dict) -> str
        """
        self._message_handler = handler
        logger.info("✅ WebServerAgent 消息处理器已设置")

    def _cache_html(self):
        """预缓存 HTML 和压缩版本"""
        import gzip
        self._cached_html = self._get_web_html()
        self._cached_html_gzip = gzip.compress(self._cached_html.encode('utf-8'))
        logger.info(f"✅ Web HTML 已缓存: {len(self._cached_html)} 字节, 压缩后 {len(self._cached_html_gzip)} 字节")

    def generate_password(self) -> str:
        """生成随机访问密码"""
        self.access_password = secrets.token_urlsafe(8)
        return self.access_password

    def generate_qr_code(self, url: str) -> str:
        """生成二维码，返回 base64 编码的图片"""
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return ""

    async def execute_task(self, task: Task) -> Any:
        """执行任务 - 只处理服务器管理相关任务"""
        task_type = task.type
        params = task.params or {}

        port = params.get("port") or self.server_port

        if task_type == "start_web_server":
            return await self._start_server(port)
        elif task_type == "stop_web_server":
            return await self._stop_server()
        elif task_type == "get_web_status":
            return await self._get_status()
        elif task_type == "restart_web_server":
            await self._stop_server()
            return await self._start_server(port)
        elif task_type == "show_qr_code":
            return await self._show_qr_code()
        else:
            return {"success": False, "message": f"未知任务类型: {task_type}"}

    async def _get_local_ip(self) -> str:
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except Exception:
                return "127.0.0.1"

    async def _start_server(self, port: int = 12345) -> Dict[str, Any]:
        """启动Web服务器"""
        if self.server_running:
            local_ip = await self._get_local_ip()
            url = f"http://{local_ip}:{self.server_port}"
            qr_code = self.generate_qr_code(url)
            return {
                "success": False,
                "message": "Web服务器已在运行中",
                "url": url,
                "password": self.access_password,
                "qr_code": qr_code
            }

        self.server_port = port
        self.generate_password()

        try:
            from aiohttp import web

            async def handle_index(request):
                logger.info(f"📥 收到页面请求: {request.remote}")
                return web.Response(
                    body=self._cached_html_gzip,
                    content_type='text/html',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Content-Encoding': 'gzip'
                    }
                )

            async def handle_check_session(request):
                import time
                start = time.time()
                data = await request.json()
                session_id = data.get('session_id', '')
                valid = session_id in self.authenticated_sessions
                elapsed = (time.time() - start) * 1000
                logger.info(f"📥 check_session: session={session_id[:8]}..., valid={valid}, 耗时={elapsed:.1f}ms")
                return web.json_response({'valid': valid})

            async def handle_chat(request):
                import time
                start = time.time()
                data = await request.json()
                message = data.get('message', '')
                session_id = data.get('session_id', '')
                elapsed = (time.time() - start) * 1000
                logger.info(f"📥 chat请求: message={message[:20] if message else '空'}, 耗时={elapsed:.1f}ms")
                
                try:
                    response = await self._handle_web_message(message)
                    return web.json_response({'response': response})
                except Exception as e:
                    logger.error(f"Web消息处理错误: {e}")
                    return web.json_response({'response': f'错误: {str(e)}'})

            async def handle_login(request):
                import time
                start = time.time()
                data = await request.json()
                password = data.get('password', '')
                
                if password == self.access_password:
                    session_id = secrets.token_urlsafe(16)
                    self.authenticated_sessions.add(session_id)
                    elapsed = (time.time() - start) * 1000
                    logger.info(f"📥 login成功: 耗时={elapsed:.1f}ms")
                    return web.json_response({'success': True, 'session_id': session_id})
                else:
                    elapsed = (time.time() - start) * 1000
                    logger.info(f"📥 login失败: 密码错误, 耗时={elapsed:.1f}ms")
                    return web.json_response({'success': False, 'message': '密码错误'})

            async def handle_logout(request):
                data = await request.json()
                session_id = data.get('session_id', '')
                self.authenticated_sessions.discard(session_id)
                return web.json_response({'success': True})

            async def handle_status(request):
                return web.json_response({
                    'status': 'running',
                    'agent': 'web_server_agent',
                    'require_auth': True
                })

            app = web.Application()
            app.router.add_get('/', handle_index)
            app.router.add_get('/index.html', handle_index)
            app.router.add_post('/check_session', handle_check_session)
            app.router.add_post('/chat', handle_chat)
            app.router.add_post('/login', handle_login)
            app.router.add_post('/logout', handle_logout)
            app.router.add_get('/status', handle_status)

            self.web_runner = web.AppRunner(app)
            await self.web_runner.setup()

            site = web.TCPSite(self.web_runner, '0.0.0.0', self.server_port)
            await site.start()

            self.server_running = True
            local_ip = await self._get_local_ip()
            url = f"http://{local_ip}:{self.server_port}"
            qr_code = self.generate_qr_code(url)

            logger.info(f"🌐 Web服务器已启动: {url}")

            return {
                "success": True,
                "message": f"Web服务器已启动",
                "local_ip": local_ip,
                "port": self.server_port,
                "url": url,
                "local_url": f"http://localhost:{self.server_port}",
                "qr_code": qr_code
            }

        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                return {
                    "success": False,
                    "message": f"端口 {port} 已被占用，请尝试其他端口"
                }
            raise
        except Exception as e:
            logger.error(f"启动Web服务器失败: {e}")
            return {
                "success": False,
                "message": f"启动失败: {str(e)}"
            }

    async def _stop_server(self) -> Dict[str, Any]:
        """停止Web服务器"""
        if not self.server_running:
            return {
                "success": True,
                "message": "Web服务器未在运行"
            }

        try:
            if self.web_runner:
                await self.web_runner.cleanup()
                self.web_runner = None

            self.server_running = False
            self.authenticated_sessions.clear()
            logger.info("🛑 Web服务器已停止")

            return {
                "success": True,
                "message": "Web服务器已停止"
            }

        except Exception as e:
            logger.error(f"停止Web服务器失败: {e}")
            return {
                "success": False,
                "message": f"停止失败: {str(e)}"
            }

    async def _get_status(self) -> Dict[str, Any]:
        """获取Web服务器状态"""
        local_ip = await self._get_local_ip()
        url = f"http://{local_ip}:{self.server_port}" if self.server_running else None
        qr_code = self.generate_qr_code(url) if url else None
        
        return {
            "running": self.server_running,
            "port": self.server_port,
            "url": url,
            "qr_code": qr_code
        }

    async def _show_qr_code(self) -> Dict[str, Any]:
        """显示登录二维码"""
        if not self.server_running:
            return {
                "success": False,
                "message": "Web服务器未启动，请先启动服务"
            }
        
        local_ip = await self._get_local_ip()
        url = f"http://{local_ip}:{self.server_port}"
        qr_code = self.generate_qr_code(url)
        
        return {
            "success": True,
            "url": url,
            "qr_code": qr_code
        }

    async def _handle_web_message(self, message: str) -> str:
        """
        处理来自Web界面的消息
        
        不在此处理业务逻辑，而是转发给 Master Agent
        """
        if self._message_handler:
            try:
                response = await self._message_handler(message, {"channel": "web"})
                return response
            except Exception as e:
                logger.error(f"消息处理器执行错误: {e}")
                return f"处理消息时出错: {str(e)}"
        else:
            logger.warning("WebServerAgent 未设置消息处理器，消息将被忽略")
            return "系统未就绪，请稍后再试"

    def _get_web_html(self) -> str:
        """获取Web界面HTML"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>智能助手</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 10px;
        }
        
        .container {
            width: 100%;
            max-width: 800px;
            height: 95vh;
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }
        
        .header .status {
            font-size: 0.8em;
            opacity: 0.8;
        }
        
        .login-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background: #f5f5f5;
        }
        
        .login-container h2 {
            margin-bottom: 20px;
            color: #333;
        }
        
        .login-container input {
            width: 100%;
            max-width: 300px;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            text-align: center;
            margin-bottom: 15px;
        }
        
        .login-container button {
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .login-container button:hover {
            transform: scale(1.05);
        }
        
        .login-error {
            color: #e74c3c;
            margin-top: 10px;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            background: #f5f5f5;
            display: none;
        }
        
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 85%;
            word-wrap: break-word;
            line-height: 1.4;
        }
        
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        
        .message.agent {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .message .sender {
            font-size: 0.75em;
            opacity: 0.7;
            margin-bottom: 4px;
        }
        
        .message .content {
            white-space: pre-wrap;
        }
        
        .input-container {
            padding: 15px;
            background: white;
            border-top: 1px solid #eee;
            display: none;
            gap: 10px;
            position: relative;
        }
        
        .input-container input {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #eee;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .input-container input:focus {
            border-color: #667eea;
        }
        
        .input-container button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .voice-btn {
            padding: 0;
            background: #e74c3c;
            border: none;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            min-width: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            cursor: pointer;
            color: white;
            transition: transform 0.2s, box-shadow 0.2s;
            flex-shrink: 0;
        }
        
        .voice-btn.recording {
            background: #c0392b;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
            70% { box-shadow: 0 0 0 15px rgba(231, 76, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }
        
        .voice-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 5px 15px rgba(231, 76, 60, 0.4);
        }
        
        .voice-btn:active {
            transform: scale(0.95);
        }
        
        .voice-status {
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(231, 76, 60, 0.9);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            display: none;
            z-index: 100;
        }
        
        .voice-status.show {
            display: block;
        }
        
        .input-container button:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .typing {
            display: none;
            padding: 10px;
            text-align: center;
            color: #666;
            font-style: italic;
        }
        
        .typing.show {
            display: block;
        }
        
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            color: white;
        }
        
        .loading-overlay.hidden {
            display: none;
        }
        
        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .loading-text {
            margin-top: 20px;
            font-size: 16px;
        }
        
        .agent-dropdown {
            position: absolute;
            bottom: 100%;
            left: 0;
            right: 60px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            display: none;
            max-height: 200px;
            overflow-y: auto;
            margin-bottom: 5px;
        }
        
        .agent-dropdown.show {
            display: block;
        }
        
        .agent-item {
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        
        .agent-item:last-child {
            border-bottom: none;
        }
        
        .agent-item:hover {
            background: #f5f5f5;
        }
        
        .agent-item .name {
            font-weight: 500;
            color: #333;
        }
        
        .agent-item .desc {
            font-size: 12px;
            color: #888;
            margin-top: 2px;
        }
        
        .input-wrapper {
            position: relative;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        @media (max-width: 600px) {
            .container {
                height: 100vh;
                border-radius: 0;
            }
            
            .header h1 {
                font-size: 1.2em;
            }
            
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay" style="display: none;">
        <div class="loading-spinner"></div>
        <div class="loading-text">正在加载...</div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>🤖 智能助手</h1>
            <div class="status">在线 · 随时为您服务</div>
        </div>
        
        <div class="login-container" id="loginContainer" style="display: none;">
            <h2>🔐 请输入访问密码</h2>
            <input type="password" id="passwordInput" placeholder="输入密码" autocomplete="off">
            <button onclick="login()">登录</button>
            <div class="login-error" id="loginError"></div>
        </div>
        
        <div class="chat-container" id="chat">
            <div class="message agent">
                <div class="sender">助手</div>
                <div class="content">你好！我是你的智能助手，有什么可以帮助你的吗？</div>
            </div>
        </div>
        
        <div class="typing" id="typing">正在处理...</div>
        
        <div class="input-container" id="inputContainer">
            <div class="input-wrapper">
                <div class="agent-dropdown" id="agentDropdown"></div>
                <input type="text" id="input" placeholder="输入消息... (@选择智能体)" autocomplete="off">
            </div>
            <button class="voice-btn" id="voiceBtn" title="语音输入">🎤</button>
            <button id="send">发送</button>
        </div>
    </div>
    
    <script>
        let sessionId = localStorage.getItem('sessionId') || '';
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');
        const typing = document.getElementById('typing');
        const loginContainer = document.getElementById('loginContainer');
        const inputContainer = document.getElementById('inputContainer');
        const passwordInput = document.getElementById('passwordInput');
        const loginError = document.getElementById('loginError');
        const agentDropdown = document.getElementById('agentDropdown');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const voiceBtn = document.getElementById('voiceBtn');
        
        let isRecording = false;
        let recognition = null;
        let finalTranscript = '';
        
        function initSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'zh-CN';
                
                recognition.onstart = () => {
                    finalTranscript = '';
                    showVoiceStatus('🎤 正在录音...');
                };
                
                recognition.onresult = (event) => {
                    let interimTranscript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            interimTranscript += transcript;
                        }
                    }
                    input.value = finalTranscript + interimTranscript;
                    showVoiceStatus('🎤 ' + (finalTranscript + interimTranscript));
                };
                
                recognition.onend = () => {
                    isRecording = false;
                    voiceBtn.classList.remove('recording');
                    voiceBtn.textContent = '🎤';
                    hideVoiceStatus();
                    if (finalTranscript) {
                        input.value = finalTranscript;
                        input.focus();
                    }
                };
                
                recognition.onerror = (event) => {
                    console.error('语音识别错误:', event.error);
                    isRecording = false;
                    voiceBtn.classList.remove('recording');
                    voiceBtn.textContent = '🎤';
                    hideVoiceStatus();
                    if (event.error === 'not-allowed') {
                        alert('请允许浏览器访问麦克风');
                    }
                };
                
                return true;
            }
            return false;
        }
        
        function showVoiceStatus(text) {
            let status = document.getElementById('voiceStatus');
            if (!status) {
                status = document.createElement('div');
                status.id = 'voiceStatus';
                status.className = 'voice-status';
                document.body.appendChild(status);
            }
            status.textContent = text;
            status.classList.add('show');
        }
        
        function hideVoiceStatus() {
            let status = document.getElementById('voiceStatus');
            if (status) {
                status.classList.remove('show');
            }
        }
        
        function toggleVoice(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (!recognition) {
                if (!initSpeechRecognition()) {
                    alert('您的浏览器不支持语音输入功能');
                    return;
                }
            }
            
            if (isRecording) {
                recognition.stop();
                isRecording = false;
                voiceBtn.classList.remove('recording');
                voiceBtn.textContent = '🎤';
                hideVoiceStatus();
            } else {
                finalTranscript = '';
                recognition.start();
                isRecording = true;
                voiceBtn.classList.add('recording');
                voiceBtn.textContent = '⏹';
            }
        }
        
        voiceBtn.addEventListener('click', toggleVoice);
        voiceBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            toggleVoice(e);
        });
        
        function hideLoading() {
            loadingOverlay.style.display = 'none';
        }
        
        function showLoading() {
            loadingOverlay.style.display = 'flex';
        }
        
        const agents = [
            {name: '通讯录智能体', alias: '通讯录', desc: '管理联系人信息'},
            {name: '音乐智能体', alias: '音乐', desc: '播放音乐歌曲'},
            {name: '视频智能体', alias: '视频', desc: '播放视频内容'},
            {name: '邮件智能体', alias: '邮件', desc: '发送和管理邮件'},
            {name: '天气智能体', alias: '天气', desc: '查询天气预报'},
            {name: '文件智能体', alias: '文件', desc: '文件操作管理'},
            {name: '爬虫智能体', alias: '爬虫', desc: '网页数据抓取'},
            {name: '开发智能体', alias: '开发', desc: '代码开发辅助'},
            {name: '系统智能体', alias: '系统', desc: '系统控制操作'},
            {name: '应用智能体', alias: '应用', desc: '应用程序管理'},
            {name: '下载智能体', alias: '下载', desc: '文件下载管理'},
            {name: '新闻智能体', alias: '新闻', desc: '新闻资讯查询'},
            {name: 'PDF智能体', alias: 'PDF', desc: 'PDF文档处理'},
            {name: 'Web服务智能体', alias: 'Web服务', desc: 'Web服务管理'}
        ];
        
        function showAgentDropdown(filter) {
            const filtered = filter 
                ? agents.filter(a => a.name.includes(filter) || a.alias.includes(filter))
                : agents;
            
            if (filtered.length === 0) {
                agentDropdown.classList.remove('show');
                return;
            }
            
            agentDropdown.innerHTML = filtered.map(a => 
                '<div class="agent-item" data-name="' + a.name + '">' +
                '<div class="name">@' + a.name + '</div>' +
                '<div class="desc">' + a.desc + '</div>' +
                '</div>'
            ).join('');
            
            agentDropdown.classList.add('show');
            
            document.querySelectorAll('.agent-item').forEach(item => {
                item.onclick = () => {
                    const name = item.dataset.name;
                    input.value = '@' + name + ' ';
                    agentDropdown.classList.remove('show');
                    input.focus();
                };
            });
        }
        
        input.addEventListener('input', (e) => {
            const value = input.value;
            if (value === '@') {
                showAgentDropdown('');
            } else if (value.startsWith('@')) {
                const filter = value.substring(1);
                showAgentDropdown(filter);
            } else {
                agentDropdown.classList.remove('show');
            }
        });
        
        input.addEventListener('blur', () => {
            setTimeout(() => agentDropdown.classList.remove('show'), 200);
        });
        
        async function checkSession() {
            console.log('[DEBUG] 开始检查 session...');
            const startTime = performance.now();
            
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get('token');
            console.log('[DEBUG] URL token:', token ? '有' : '无');
            
            sessionId = 'auto_login_' + Date.now();
            console.log('[DEBUG] 自动登录，总耗时:', (performance.now() - startTime).toFixed(0), 'ms');
            showChat();
        }
        
        async function login() {
            const password = passwordInput.value.trim();
            if (!password) return;
            
            loginError.textContent = '';
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: password})
                });
                const data = await response.json();
                
                if (data.success) {
                    sessionId = data.session_id;
                    localStorage.setItem('sessionId', sessionId);
                    showChat();
                } else {
                    loginError.textContent = data.message || '密码错误';
                    passwordInput.value = '';
                }
            } catch (e) {
                loginError.textContent = '连接失败，请重试';
            }
        }
        
        function showChat() {
            loginContainer.style.display = 'none';
            chat.style.display = 'block';
            inputContainer.style.display = 'flex';
            input.focus();
        }
        
        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = '<div class="sender">' + (role === 'user' ? '你' : '助手') + '</div>' +
                           '<div class="content">' + content.replace(/\\n/g, '<br>') + '</div>';
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function showTyping(show) {
            typing.className = show ? 'typing show' : 'typing';
        }
        
        async function sendMessage() {
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            input.disabled = true;
            send.disabled = true;
            showTyping(true);
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message, session_id: sessionId})
                });
                const data = await response.json();
                
                if (data.need_auth) {
                    localStorage.removeItem('sessionId');
                    sessionId = '';
                    location.reload();
                    return;
                }
                
                addMessage('agent', data.response);
            } catch (e) {
                addMessage('agent', '❌ 连接失败，请检查网络');
            } finally {
                input.disabled = false;
                send.disabled = false;
                showTyping(false);
                input.focus();
            }
        }
        
        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') login();
        });
        
        send.onclick = sendMessage;
        input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        
        // 初始化语音识别
        initSpeechRecognition();
        
        checkSession();
    </script>
</body>
</html>'''

    async def stop(self):
        """停止智能体"""
        await self._stop_server()
        await super().stop()
