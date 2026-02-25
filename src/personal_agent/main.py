"""
Main Application Entry Point
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import settings
from .llm import LLMGateway
from .memory import MemoryManager
from .channels import CLIChannel, WebChannel, WeChatChannel, GUIChannel, IncomingMessage, OutgoingMessage


class PersonalAgentApp:
    _instance = None
    
    def __init__(self, channel_type: str = "cli", port: int = 8080):
        PersonalAgentApp._instance = self
        self.channel_type = channel_type
        self.port = port
        self.channel = None
        self._running = False

    def _setup_logging(self):
        log_path = settings.log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<level>{level: <8}</level> | <level>{message}</level>"
        )
        logger.add(
            str(log_path),
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )

    def _create_channel(self):
        if self.channel_type == "cli":
            return CLIChannel()
        elif self.channel_type == "web":
            return WebChannel(host="0.0.0.0", port=self.port)
        elif self.channel_type == "wechat":
            if WeChatChannel is None:
                raise ImportError(
                    "WeChat channel requires itchat. Install with: pip install itchat"
                )
            return WeChatChannel(
                auto_login=settings.wechat.auto_login,
                hot_reload=settings.wechat.hot_reload
            )
        elif self.channel_type == "gui":
            if GUIChannel is None:
                raise ImportError(
                    "GUI channel requires PyQt6. Install with: pip install PyQt6 markdown"
                )
            return GUIChannel()
        else:
            raise ValueError(f"Unknown channel type: {self.channel_type}")

    async def _handle_message(self, incoming: IncomingMessage) -> Optional[OutgoingMessage]:
        try:
            from .multi_agent_system import multi_agent_system
            return await multi_agent_system.process_message(incoming)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return OutgoingMessage(
                content=f"处理消息时出现错误：{str(e)}",
                receiver_id=incoming.sender_id
            )

    async def start(self):
        self._setup_logging()
        logger.info(f"Starting Personal Agent with {self.channel_type} channel")

        data_path = Path("./data")
        data_path.mkdir(parents=True, exist_ok=True)

        for dir_path in settings.security.allowed_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        from .multi_agent_system import multi_agent_system
        
        def progress_callback(message: str, progress: float):
            if self.channel_type == "gui":
                print(f"[启动] {message}")
        
        multi_agent_system.set_progress_callback(progress_callback)
        await multi_agent_system.initialize()

        self.channel = self._create_channel()
        logger.info(f"Channel created: {type(self.channel).__name__}")

        if self.channel_type == "gui":
            await self._start_gui_mode()
        else:
            self.channel.on_message(self._handle_message)
            self._running = True
            logger.info("Personal Agent started successfully, starting channel...")
            await self.channel.start()
            logger.info("Channel start() returned")

    async def _start_gui_mode(self):
        """Start GUI mode with special async handling"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        import markdown

        self._running = True

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        from .channels.gui import ChatWindow
        from .multi_agent_system import multi_agent_system
        chat_window = ChatWindow(multi_agent_system.master)
        window = chat_window.window
        window.show()
        
        logger.info(f"🖥️  GUI interface started, window visible: {window.isVisible()}")

        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(10)
        
        iteration = 0
        while self._running and window.isVisible():
            iteration += 1
            if iteration % 100 == 0:
                logger.debug(f"GUI loop running, iteration {iteration}")
            app.processEvents()
            await asyncio.sleep(0.01)
        
        logger.info(f"GUI loop ended: running={self._running}, visible={window.isVisible()}")
        
        self._running = False

    async def stop(self):
        logger.info("Stopping Personal Agent")
        self._running = False

        try:
            from .multi_agent_system import multi_agent_system
            await multi_agent_system.shutdown()

            if self.channel:
                await self.channel.stop()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.debug("Event loop already closed")
            else:
                raise

        logger.info("Personal Agent stopped")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Personal AI Agent")
    parser.add_argument(
        "--channel", "-c",
        choices=["cli", "web", "wechat", "gui"],
        default="cli",
        help="Communication channel to use"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Port for web channel (default: 8080)"
    )
    args = parser.parse_args()

    app = PersonalAgentApp(channel_type=args.channel, port=args.port)

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await app.stop()


def run():
    asyncio.run(main())
