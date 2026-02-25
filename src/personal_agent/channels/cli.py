"""
CLI Channel - Command line interface for testing
"""
import asyncio
from datetime import datetime
from typing import List, Optional
import uuid

from .base import BaseChannel, IncomingMessage, OutgoingMessage, MessageHandler, MessageType


class CLIChannel(BaseChannel):
    name = "cli"

    def __init__(self, user_name: str = "User"):
        self.user_name = user_name
        self._running = False
        self._message_handlers: List[MessageHandler] = []

    async def start(self) -> None:
        self._running = True
        print(f"\n🤖 Agent started. Type your message (or 'quit' to exit):\n")

        while self._running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, f"{self.user_name}: "
                )

                if user_input.lower() in ["quit", "exit", "q"]:
                    await self.stop()
                    break

                if not user_input.strip():
                    continue

                message = IncomingMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id="cli_user",
                    sender_name=self.user_name,
                    content=user_input,
                    message_type=MessageType.TEXT,
                    timestamp=datetime.now(),
                    channel=self.name
                )

                for handler in self._message_handlers:
                    response = handler(message)
                    if asyncio.iscoroutine(response):
                        response = await response
                    if response:
                        await self.send(response)

            except EOFError:
                await self.stop()
                break
            except Exception as e:
                print(f"Error: {e}")

    async def stop(self) -> None:
        self._running = False
        print("\n👋 Agent stopped.")

    async def send(self, message: OutgoingMessage) -> bool:
        try:
            print(f"\n🤖 Agent: {message.content}\n")
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def on_message(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    async def is_running(self) -> bool:
        return self._running
