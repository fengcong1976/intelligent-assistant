"""启动 GUI 界面 - 简化版本"""
import sys
import os

os.chdir(r"E:\python项目\智能体")
sys.path.insert(0, r"E:\python项目\智能体\src")

from loguru import logger

def main():
    logger.info("Starting Personal Agent GUI...")
    
    from PyQt6.QtWidgets import QApplication
    import qasync
    from personal_agent.config import settings
    from personal_agent.agent.core import Agent
    from personal_agent.llm.gateway import LLMGateway
    from personal_agent.memory.manager import MemoryManager
    from personal_agent.agent.scheduler import TaskScheduler
    from pathlib import Path
    import asyncio
    
    data_path = Path("./data")
    data_path.mkdir(parents=True, exist_ok=True)
    
    for dir_path in settings.security.allowed_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # 创建 Qt 应用
    app = QApplication(sys.argv)
    
    # 使用 qasync 创建事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 设置全局事件循环
    from personal_agent.multi_agent_system import set_global_loop
    set_global_loop(loop)
    
    llm_gateway = LLMGateway(settings.llm)
    
    memory_manager = MemoryManager(
        session_id="default",
        db_path=settings.memory.db_path,
        collection_name=settings.memory.collection
    )
    
    agent = Agent(
        llm_gateway=llm_gateway,
        memory_manager=memory_manager,
        session_id="default"
    )
    
    scheduler = TaskScheduler(storage_path=Path("./data/tasks"))
    
    async def init_and_run():
        await scheduler.start()
        
        from personal_agent.multi_agent_system import multi_agent_system
        await multi_agent_system.initialize()
        
        # 创建简单的 GUI 窗口
        from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel
        from PyQt6.QtCore import Qt
        
        main_window = QMainWindow()
        main_window.setWindowTitle("Personal Agent")
        main_window.setMinimumSize(800, 600)
        
        central = QWidget()
        main_window.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 聊天显示区域
        chat_display = QTextEdit()
        chat_display.setReadOnly(True)
        layout.addWidget(chat_display)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_field = QLineEdit()
        input_field.setPlaceholderText("输入消息...")
        send_btn = QPushButton("发送")
        input_layout.addWidget(input_field)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)
        
        # Web 服务按钮
        web_btn = QPushButton("🌐 启动Web服务")
        web_btn.setCheckable(True)
        layout.addWidget(web_btn)
        
        # Web 服务状态
        web_server_running = False
        web_server_port = 12345
        web_runner = None
        
        async def handle_message(message: str):
            from personal_agent.channels.base import IncomingMessage, MessageType
            from datetime import datetime
            import uuid
            
            incoming = IncomingMessage(
                message_id=str(uuid.uuid4()),
                sender_id="gui_user",
                sender_name="用户",
                content=message,
                message_type=MessageType.TEXT,
                timestamp=datetime.now(),
                channel="gui"
            )
            
            response = await multi_agent_system.process_message(incoming)
            return response.content if response else "无响应"
        
        def send_message():
            text = input_field.text().strip()
            if not text:
                return
            
            chat_display.append(f"<b>你:</b> {text}")
            input_field.clear()
            
            async def process():
                try:
                    response = await handle_message(text)
                    chat_display.append(f"<b>助手:</b> {response}")
                except Exception as e:
                    chat_display.append(f"<b>错误:</b> {str(e)}")
            
            asyncio.create_task(process())
        
        send_btn.clicked.connect(send_message)
        input_field.returnPressed.connect(send_message)
        
        def toggle_web_server():
            nonlocal web_server_running, web_runner
            
            if web_server_running:
                web_server_running = False
                web_btn.setText("🌐 启动Web服务")
                web_btn.setChecked(False)
            else:
                import socket
                
                def get_local_ip():
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        ip = s.getsockname()[0]
                        s.close()
                        return ip
                    except:
                        return "127.0.0.1"
                
                from aiohttp import web
                
                async def handle_index(request):
                    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能助手</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 16px; background: #f5f5f5; }
        h1 { text-align: center; margin-bottom: 16px; }
        #chat { height: calc(100vh - 160px); overflow-y: auto; border: 1px solid #ddd; padding: 16px; border-radius: 12px; background: #fff; }
        .message { margin: 12px 0; padding: 12px; border-radius: 12px; max-width: 85%; }
        .user { background: #e3f2fd; margin-left: auto; }
        .agent { background: #e8f5e9; }
        #input-area { display: flex; gap: 8px; }
        #input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }
        #send { padding: 12px 24px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🤖 智能助手</h1>
    <div id="chat"></div>
    <div id="input-area">
        <input type="text" id="input" placeholder="输入消息...">
        <button id="send">发送</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');
        
        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = '<b>' + (role === 'user' ? '你' : '助手') + ':</b> ' + content.replace(/\\n/g, '<br>');
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
                addMessage('agent', '错误: ' + e.message);
            }
        }
        
        send.onclick = sendMessage;
        input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
    </script>
</body>
</html>
"""
                    return web.Response(text=html, content_type='text/html')
                
                async def handle_chat(request):
                    data = await request.json()
                    message = data.get('message', '')
                    try:
                        response = await handle_message(message)
                        return web.json_response({'response': response})
                    except Exception as e:
                        return web.json_response({'response': f'错误: {str(e)}'})
                
                async def start_web():
                    nonlocal web_runner
                    app_web = web.Application()
                    app_web.router.add_get('/', handle_index)
                    app_web.router.add_post('/chat', handle_chat)
                    
                    web_runner = web.AppRunner(app_web)
                    await web_runner.setup()
                    site = web.TCPSite(web_runner, '0.0.0.0', web_server_port)
                    await site.start()
                    
                    while web_server_running:
                        await asyncio.sleep(1)
                    
                    if web_runner:
                        await web_runner.cleanup()
                
                web_server_running = True
                asyncio.create_task(start_web())
                
                local_ip = get_local_ip()
                web_btn.setText(f"🌐 停止Web服务 ({local_ip}:{web_server_port})")
                web_btn.setChecked(True)
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    main_window,
                    "Web 服务已启动",
                    f"Web 服务已启动！\n\n"
                    f"📱 手机访问: http://{local_ip}:{web_server_port}\n"
                    f"💻 本地访问: http://localhost:{web_server_port}"
                )
        
        web_btn.clicked.connect(toggle_web_server)
        
        main_window.show()
        logger.info("🖥️ GUI interface started")
        
        # 等待窗口关闭
        while main_window.isVisible():
            await asyncio.sleep(0.1)
        
        # 停止 Web 服务
        nonlocal web_server_running
        web_server_running = False
        
        logger.info("GUI closed")
    
    with loop:
        loop.run_until_complete(init_and_run())

if __name__ == "__main__":
    main()
