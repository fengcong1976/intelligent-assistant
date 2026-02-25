"""
Agents Module - 智能体模块

包含所有智能体的统一入口
"""

from .base import BaseAgent, Task, TaskStatus
from .master import MasterAgent
from .message_bus import MessageBus
from .agent_scanner import get_agent_scanner

from .email_agent import EmailAgent
from .weather_agent import WeatherAgent
from .music_agent import MusicAgent
from .video_agent import VideoAgent
from .file_agent import FileAgent
from .os_agent import OSAgent
from .contact_agent import ContactAgent
from .calendar_agent import CalendarAgent
from .news_agent import NewsAgent
from .shopping_agent import ShoppingAgent
from .download_agent import DownloadAgent
from .crawler_agent import CrawlerAgent
from .developer_agent import DeveloperAgent
from .document_agent import DocumentAgent
from .image_agent import ImageAgent
from .stock_query_agent import StockQueryAgent
from .app_agent import AppAgent
from .tts_agent import TTSAgent
from .web_server_agent import WebServerAgent
from .travel_itinerary_agent import TravelItineraryAgent
from .homeassistant_agent import HomeAssistantAgent
from .qq_bot_agent import QQBotAgent
from .screen_cast_agent import ScreenCastAgent
from .proactive_agent import ProactiveAgent
from .llm_agent import LLMAgent
from .audio_decrypt_agent import AudioDecryptAgent
from .image_converter_agent import ImageConverterAgent

__all__ = [
    "BaseAgent",
    "Task", 
    "TaskStatus",
    "MasterAgent",
    "MessageBus",
    "get_agent_scanner",

    "EmailAgent",
    "WeatherAgent",
    "MusicAgent",
    "VideoAgent",
    "FileAgent",
    "OSAgent",
    "ContactAgent",
    "CalendarAgent",
    "NewsAgent",
    "ShoppingAgent",
    "DownloadAgent",
    "CrawlerAgent",
    "DeveloperAgent",
    "DocumentAgent",
    "ImageAgent",
    "StockQueryAgent",
    "AppAgent",
    "TTSAgent",
    "WebServerAgent",
    "TravelItineraryAgent",
    "HomeAssistantAgent",
    "QQBotAgent",
    "ScreenCastAgent",
    "ProactiveAgent",
    "LLMAgent",
    "AudioDecryptAgent",
    "ImageConverterAgent",
]
