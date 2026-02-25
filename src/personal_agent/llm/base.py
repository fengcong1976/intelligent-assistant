"""
LLM Gateway - Unified interface for multiple LLM providers
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCall] = []
    finish_reason: str = ""
    usage: Dict[str, int] = {}


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: Union[List[Message], List[Dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: Union[List[Message], List[Dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ):
        pass
