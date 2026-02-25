"""
Zhipu AI Provider (智谱)
"""
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from zhipuai import ZhipuAI

from .base import BaseLLMProvider, LLMResponse, Message, ToolCall, ToolDefinition


class ZhipuProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "glm-4"):
        self.client = ZhipuAI(api_key=api_key)
        self.model = model

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            item = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            result.append(item)
        return result

    def _convert_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            }
            for t in tools
        ]

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._convert_messages(messages),
            tools=self._convert_tools(tools),
            **kwargs
        )

        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                    ))
                except json.JSONDecodeError as e:
                    logger.warning(f"解析tool_call参数失败: {e}, args={tc.function.arguments}")
                    continue

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    async def stream_chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._convert_messages(messages),
            tools=self._convert_tools(tools),
            stream=True,
            **kwargs
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
