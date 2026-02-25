"""
Channel Base - Abstract interface for communication channels
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"


@dataclass
class IncomingMessage:
    message_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType
    timestamp: datetime
    channel: str
    raw_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    is_group: bool = False
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    is_mentioned: bool = False


@dataclass
class OutgoingMessage:
    content: str
    message_type: MessageType = MessageType.TEXT
    receiver_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


MessageHandler = Callable[[IncomingMessage], Optional[OutgoingMessage]]


class BaseChannel(ABC):
    name: str

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> bool:
        pass

    @abstractmethod
    def on_message(self, handler: MessageHandler) -> None:
        pass

    @abstractmethod
    async def is_running(self) -> bool:
        pass
