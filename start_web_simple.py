"""启动 Web 界面 - 简化版"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    from aiohttp import web
    
    async def handle_index(request):
        return web.Response(text=_get_html(), content_type='text/html')
    
    async def handle_chat(request):
        data = await request.json()
        message = data.get('message', '')
        
        from personal_agent.multi_agent_system import multi_agent_system
        from personal_agent.channels import IncomingMessage
        from personal_agent.channels.base import MessageType
        from datetime import datetime
        import uuid
        
        incoming = IncomingMessage(
            message_id=str(uuid.uuid4()),
            sender_id="web_user",
            sender_name="Web用户",
            content=message,
            message_type=MessageType.TEXT,
            timestamp=datetime.now(),
            channel="web"
        )
        
        try:
            response = await multi_agent_system.process_message(incoming)
            return web.json_response({'response': response.content if response else '无响应'})
        except Exception as e:
            return web.json_response({'response': f'错误: {str(e)}'})
    
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_post('/chat', handle_chat)
    
    print("🚀 初始化多智能体系统...")
    from personal_agent.multi_agent_system import multi_agent_system
    await multi_agent_system.initialize()
    print("✅ 多智能体系统初始化完成")
    
    print("🌐 启动 Web 服务器...")
    print("📱 手机访问: http://你的电脑IP:12345")
    print("💻 本地访问: http://localhost:12345")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 12345)
    await site.start()
    
    print("✅ Web 服务器已启动，按 Ctrl+C 停止")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n正在停止...")

def _get_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能助手</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 16px; 
            background: #f5f5f5;
            min-height: 100vh;
        }
        h1 { text-align: center; color: #333; margin-bottom: 16px; font-size: 1.5em; }
        #chat { 
            height: calc(100vh - 160px); 
            min-height: 300px;
            overflow-y: auto; 
            border: 1px solid #ddd; 
            padding: 16px; 
            margin-bottom: 16px; 
            border-radius: 12px; 
            background: #fff;
        }
        .message { 
            margin: 12px 0; 
            padding: 12px 16px; 
            border-radius: 12px; 
            max-width: 85%;
            word-wrap: break-word;
        }
        .user { background: #e3f2fd; margin-left: auto; text-align: right; }
        .agent { background: #e8f5e9; margin-right: auto; }
        .label { font-size: 0.8em; color: #666; margin-bottom: 4px; }
        #input-area { display: flex; gap: 8px; }
        #input { 
            flex: 1; 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            font-size: 16px;
        }
        #send { 
            padding: 12px 24px; 
            background: #4CAF50; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
        }
        #send:hover { background: #45a049; }
        #send:disabled { background: #ccc; cursor: not-allowed; }
        .loading { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <h1>🤖 智能助手</h1>
    <div id="chat"></div>
    <div id="input-area">
        <input type="text" id="input" placeholder="输入消息..." autocomplete="off">
        <button id="send">发送</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.innerHTML = '<div class="label">' + (role === 'user' ? '👤 你' : '🤖 助手') + '</div>' +
                           '<div>' + content.replace(/\\n/g, '<br>') + '</div>';
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function setLoading(show) {
            if (show) {
                const div = document.createElement('div');
                div.className = 'message agent loading';
                div.id = 'loading';
                div.textContent = '思考中...';
                chat.appendChild(div);
                chat.scrollTop = chat.scrollHeight;
            } else {
                const loading = document.getElementById('loading');
                if (loading) loading.remove();
            }
        }

        async function sendMessage() {
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            input.disabled = true;
            send.disabled = true;
            setLoading(true);
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                const data = await response.json();
                setLoading(false);
                addMessage('agent', data.response);
            } catch (e) {
                setLoading(false);
                addMessage('agent', '错误: ' + e.message);
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

if __name__ == "__main__":
    asyncio.run(main())
