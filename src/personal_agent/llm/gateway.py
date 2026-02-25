"""
LLM Gateway - Factory and unified interface
"""
from typing import Optional, Union, List

from ..config import LLMConfig
from .base import BaseLLMProvider, LLMResponse, Message, ToolDefinition
from .zhipu import ZhipuProvider
from .dashscope import DashscopeProvider
from .openai import OpenAIProvider


class LLMGateway:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._provider: Optional[BaseLLMProvider] = None

    @property
    def provider(self) -> BaseLLMProvider:
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> BaseLLMProvider:
        provider_name = self.config.provider.lower()

        if provider_name == "zhipu":
            if not self.config.zhipu_api_key:
                raise ValueError("ZHIPU_API_KEY is required")
            return ZhipuProvider(
                api_key=self.config.zhipu_api_key,
                model=self.config.zhipu_model
            )

        elif provider_name == "dashscope":
            if not self.config.dashscope_api_key:
                raise ValueError("DASHSCOPE_API_KEY is required")
            return DashscopeProvider(
                api_key=self.config.dashscope_api_key,
                model=self.config.dashscope_model,
                enable_search=getattr(self.config, 'dashscope_enable_search', True)
            )

        elif provider_name == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required")
            return OpenAIProvider(
                api_key=self.config.openai_api_key,
                model=self.config.openai_model,
                base_url=self.config.openai_base_url
            )

        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

    async def chat(
        self,
        messages: Union[List[Message], List[dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> LLMResponse:
        return await self.provider.chat(messages, tools, **kwargs)

    async def stream_chat(
        self,
        messages: Union[List[Message], List[dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ):
        async for chunk in self.provider.stream_chat(messages, tools, **kwargs):
            yield chunk
