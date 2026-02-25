"""
Channels Module
"""
from .base import BaseChannel, IncomingMessage, OutgoingMessage, MessageHandler, MessageType
from .cli import CLIChannel
from .web import WebChannel

try:
    from .wechat import WeChatChannel
except ImportError:
    WeChatChannel = None

try:
    from .gui import GUIChannel
except ImportError:
    GUIChannel = None

__all__ = [
    "BaseChannel",
    "IncomingMessage",
    "OutgoingMessage",
    "MessageHandler",
    "MessageType",
    "CLIChannel",
    "WebChannel",
    "WeChatChannel",
    "GUIChannel",
]
