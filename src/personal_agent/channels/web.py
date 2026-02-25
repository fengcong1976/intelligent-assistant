"""
Web Channel - HTTP/WebSocket interface
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Set
import uuid

from .base import BaseChannel, IncomingMessage, OutgoingMessage, MessageHandler, MessageType

logger = logging.getLogger(__name__)


class WebChannel(BaseChannel):
    name = "web"

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self._running = False
        self._message_handlers: List[MessageHandler] = []
        self._connected_clients: Set = set()
        self._pending_responses: dict = {}
        self._server = None
        self._runner = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._running = True
        self._stop_event.clear()
        
        logger.info(f"🌐 Starting Web server on {self.host}:{self.port}...")

        try:
            from aiohttp import web

            app = web.Application()
            app.router.add_get("/", self._handle_index)
            app.router.add_get("/ws", self._handle_websocket)
            app.router.add_post("/chat", self._handle_chat)

            self._runner = web.AppRunner(app)
            await self._runner.setup()
            self._server = web.TCPSite(self._runner, self.host, self.port)
            await self._server.start()

            logger.info(f"🌐 Web interface started at http://{self.host}:{self.port}")
            logger.info(f"📱 手机访问: http://你的电脑IP:{self.port}")

            while self._running:
                await asyncio.sleep(1)

        except ImportError:
            logger.info("aiohttp not installed, using simple HTTP server")
            await self._start_simple_server()
        except Exception as e:
            logger.error(f"Web server error: {e}")
            raise

    async def _start_simple_server(self):
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        class SimpleHandler(BaseHTTPRequestHandler):
            channel = self

            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = self._get_index_html()
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/chat":
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode("utf-8"))

                    message = IncomingMessage(
                        message_id=str(uuid.uuid4()),
                        sender_id=data.get("user_id", "web_user"),
                        sender_name=data.get("user_name", "User"),
                        content=data.get("message", ""),
                        message_type=MessageType.TEXT,
                        timestamp=datetime.now(),
                        channel=self.channel.name
                    )

                    for handler in self.channel._message_handlers:
                        response = handler(message)
                        if response:
                            self.channel._pending_responses[message.message_id] = response.content

                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    response_data = {
                        "response": self.channel._pending_responses.get(message.message_id, "")
                    }
                    self.wfile.write(json.dumps(response_data).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def _get_index_html(self):
                return WebChannel._get_simple_html()

        server = HTTPServer((self.host, self.port), SimpleHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        logger.info(f"🌐 Simple web interface started at http://{self.host}:{self.port}")

        while self._running:
            await asyncio.sleep(1)

    async def _handle_index(self, request):
        from aiohttp import web
        return web.Response(text=self._get_html(), content_type="text/html")

    async def _handle_websocket(self, request):
        import aiohttp
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)
        self._connected_clients.add(ws)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                message = IncomingMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=data.get("user_id", "ws_user"),
                    sender_name=data.get("user_name", "User"),
                    content=data.get("message", ""),
                    message_type=MessageType.TEXT,
                    timestamp=datetime.now(),
                    channel=self.name
                )

                for handler in self._message_handlers:
                    response = handler(message)
                    if response:
                        await ws.send_json({
                            "type": "response",
                            "content": response.content
                        })

        self._connected_clients.discard(ws)
        return ws

    async def _handle_chat(self, request):
        from aiohttp import web
        data = await request.json()

        message = IncomingMessage(
            message_id=str(uuid.uuid4()),
            sender_id=data.get("user_id", "web_user"),
            sender_name=data.get("user_name", "User"),
            content=data.get("message", ""),
            message_type=MessageType.TEXT,
            timestamp=datetime.now(),
            channel=self.name
        )

        response_content = ""
        for handler in self._message_handlers:
            result = handler(message)
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                response_content = result.content

        return web.json_response({"response": response_content})

    @staticmethod
    def _get_simple_html() -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Personal Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        #chat { height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 8px; }
        .message { margin: 10px 0; padding: 8px; border-radius: 8px; }
        .user { background: #e3f2fd; text-align: right; }
        .agent { background: #e8f5e9; }
        #input-container { display: flex; gap: 10px; }
        #input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
        #send { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🤖 Personal Agent</h1>
    <div id="chat"></div>
    <div id="input-container">
        <input type="text" id="input" placeholder="Type your message...">
        <button id="send">Send</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = '<strong>' + (role === 'user' ? 'You' : 'Agent') + ':</strong> ' + escapeHtml(content);
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        async function sendMessage() {
            const message = input.value.trim();
            if (!message) return;
            addMessage('user', message);
            input.value = '';
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                const data = await response.json();
                addMessage('agent', data.response);
            } catch (e) {
                addMessage('agent', 'Error: ' + e.message);
            }
        }

        send.onclick = sendMessage;
        input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
    </script>
</body>
</html>
"""

    def _get_html(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Agent</title>
    <script src="https://unpkg.com/marked@9.1.6/marked.min.js"></script>
    <script src="https://unpkg.com/dompurify@3.0.6/dist/purify.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/github-markdown-css@5.2.0/github-markdown.min.css">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px; 
            background: #f6f8fa;
        }
        h1 { 
            text-align: center; 
            color: #24292f; 
            margin-bottom: 20px;
        }
        #chat { 
            height: calc(100vh - 200px); 
            min-height: 400px;
            overflow-y: scroll; 
            border: 1px solid #d0d7de; 
            padding: 16px; 
            margin-bottom: 16px; 
            border-radius: 12px; 
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .message { 
            margin: 12px 0; 
            padding: 12px 16px; 
            border-radius: 12px; 
            max-width: 85%;
        }
        .user { 
            background: #ddf4ff; 
            margin-left: auto;
            text-align: right;
        }
        .agent { 
            background: #dafbe1; 
            margin-right: auto;
        }
        .message-header {
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 0.85em;
            opacity: 0.7;
        }
        .message-content {
            text-align: left;
            line-height: 1.6;
        }
        .message-content pre {
            background: #f6f8fa;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 8px 0;
        }
        .message-content code {
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }
        .message-content pre code {
            background: none;
            padding: 0;
        }
        .message-content ul, .message-content ol {
            margin: 8px 0;
            padding-left: 24px;
        }
        .message-content li {
            margin: 4px 0;
        }
        .message-content blockquote {
            border-left: 4px solid #d0d7de;
            margin: 8px 0;
            padding-left: 16px;
            color: #57606a;
        }
        .message-content table {
            border-collapse: collapse;
            margin: 8px 0;
            width: 100%;
        }
        .message-content th, .message-content td {
            border: 1px solid #d0d7de;
            padding: 8px 12px;
        }
        .message-content th {
            background: #f6f8fa;
        }
        #input-container { 
            display: flex; 
            gap: 12px; 
        }
        #input { 
            flex: 1; 
            padding: 12px 16px; 
            border: 1px solid #d0d7de; 
            border-radius: 8px; 
            font-size: 16px;
            outline: none;
        }
        #input:focus {
            border-color: #0969da;
            box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.2);
        }
        #send { 
            padding: 12px 24px; 
            background: #1f883d; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 500;
        }
        #send:hover { 
            background: #1a7f37; 
        }
        #send:active {
            background: #116329;
        }
        #voice { 
            padding: 12px 16px; 
            background: #f6f8fa; 
            color: #24292f; 
            border: 1px solid #d0d7de; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 18px;
        }
        #voice:hover { 
            background: #f3f4f6; 
        }
        #voice.recording { 
            background: #cf222e; 
            color: white;
            border-color: #cf222e;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #d0d7de;
            border-radius: 50%;
            border-top-color: #0969da;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <h1>🤖 Personal Agent</h1>
    <div id="chat"></div>
    <div id="input-container">
        <input type="text" id="input" placeholder="输入消息..." autocomplete="off">
        <button id="voice" title="语音输入（按住说话）">🎤</button>
        <button id="send">发送</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');
        const voice = document.getElementById('voice');
        
        let recognition = null;
        let isRecording = false;
        
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'zh-CN';
            
            recognition.onresult = (event) => {
                let text = event.results[0][0].transcript;
                text = text.replace(/[。，！？、；：,.!?;:]+$/g, '');
                input.value = input.value + text;
                input.focus();
            };
            
            recognition.onerror = (event) => {
                console.error('语音识别错误:', event.error);
                voice.classList.remove('recording');
                voice.textContent = '🎤';
                isRecording = false;
            };
            
            recognition.onend = () => {
                voice.classList.remove('recording');
                voice.textContent = '🎤';
                isRecording = false;
            };
        }
        
        voice.addEventListener('mousedown', () => {
            if (!recognition) {
                alert('您的浏览器不支持语音识别，请使用 Chrome 浏览器');
                return;
            }
            if (isRecording) return;
            isRecording = true;
            voice.classList.add('recording');
            voice.textContent = '⏹️';
            recognition.start();
        });
        
        voice.addEventListener('mouseup', () => {
            if (recognition && isRecording) {
                recognition.stop();
            }
        });
        
        voice.addEventListener('mouseleave', () => {
            if (recognition && isRecording) {
                recognition.stop();
            }
        });

        marked.setOptions({
            breaks: true,
            gfm: true
        });

        function renderMarkdown(text) {
            try {
                const html = marked.parse(text);
                return DOMPurify.sanitize(html);
            } catch (e) {
                return escapeHtml(text).replace(/\\n/g, '<br>');
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function addMessage(role, content, isLoading = false) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            
            const header = document.createElement('div');
            header.className = 'message-header';
            header.textContent = role === 'user' ? '👤 你' : '🤖 助手';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content markdown-body';
            
            if (isLoading) {
                contentDiv.innerHTML = '<span class="loading"></span> 思考中...';
                div.id = 'loading-message';
            } else if (role === 'agent') {
                contentDiv.innerHTML = renderMarkdown(content);
            } else {
                contentDiv.textContent = content;
            }
            
            div.appendChild(header);
            div.appendChild(contentDiv);
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            
            return div;
        }

        function removeLoading() {
            const loading = document.getElementById('loading-message');
            if (loading) loading.remove();
        }

        async function sendMessage() {
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            input.disabled = true;
            send.disabled = true;
            
            addMessage('agent', '', true);
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                const data = await response.json();
                
                removeLoading();
                addMessage('agent', data.response);
            } catch (e) {
                removeLoading();
                addMessage('agent', '❌ 错误: ' + e.message);
            } finally {
                input.disabled = false;
                send.disabled = false;
                input.focus();
            }
        }

        send.onclick = sendMessage;
        input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        
        input.focus();
    </script>
</body>
</html>
"""

    async def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        
        for client in self._connected_clients:
            await client.close()

        if self._runner:
            await self._runner.cleanup()

    async def send(self, message: OutgoingMessage) -> bool:
        try:
            for client in self._connected_clients:
                await client.send_json({
                    "type": "message",
                    "content": message.content
                })
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    def on_message(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    async def is_running(self) -> bool:
        return self._running
