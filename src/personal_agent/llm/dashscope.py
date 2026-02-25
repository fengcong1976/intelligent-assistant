"""
Dashscope Provider (通义千问)
"""
import json
from typing import Any, Dict, List, Optional, Union
import asyncio

import dashscope
from dashscope import Generation
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, Message, ToolCall, ToolDefinition


class DashscopeProvider(BaseLLMProvider):
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    TIMEOUT = 60.0
    
    def __init__(self, api_key: str, model: str = "qwen-plus", enable_search: bool = True):
        dashscope.api_key = api_key
        self.model = model
        self.enable_search = enable_search

    def _convert_messages(self, messages: Union[List[Message], List[Dict]]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            if isinstance(msg, dict):
                item = {"role": msg["role"], "content": msg.get("content", "")}
                if "tool_calls" in msg:
                    item["tool_calls"] = msg["tool_calls"]
                if "tool_call_id" in msg:
                    item["tool_call_id"] = msg["tool_call_id"]
                if "name" in msg:
                    item["name"] = msg["name"]
            else:
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
        messages: Union[List[Message], List[Dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> LLMResponse:
        import inspect
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_info = ""
        if caller_frame:
            caller_func = caller_frame.f_code.co_name
            caller_file = caller_frame.f_code.co_filename.split('\\')[-1]
            caller_line = caller_frame.f_lineno
            caller_info = f"{caller_file}:{caller_line} {caller_func}()"
        
        msg_count = len(messages) if messages else 0
        total_msg_len = sum(len(str(m)) for m in messages) if messages else 0
        logger.info(f"📊 DashScope chat 被调用: tools={len(tools) if tools else 0}, messages={msg_count}, 总字符={total_msg_len}, 调用者={caller_info}")
        
        call_params = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "result_format": "message",
        }
        
        if tools:
            converted_tools = self._convert_tools(tools)
            call_params["tools"] = converted_tools
            call_params["tool_choice"] = "auto"
            logger.debug(f"DashScope: Passing {len(converted_tools)} tools to LLM")
        
        if self.enable_search:
            call_params["enable_search"] = True
        
        call_params.update(kwargs)

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: Generation.call(**call_params)),
                    timeout=self.TIMEOUT
                )

                if response.status_code != 200:
                    raise Exception(f"DashScope API error: {response.code} - {response.message}")
                
                return self._parse_response(response)
                
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"DashScope API 调用超时（{self.TIMEOUT}秒）")
                logger.warning(f"⚠️ DashScope 调用超时，尝试 {attempt + 1}/{self.MAX_RETRIES}")
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ DashScope 调用失败: {e}，尝试 {attempt + 1}/{self.MAX_RETRIES}")
            
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        
        raise last_error or Exception("DashScope API 调用失败")

    def _parse_response(self, response) -> LLMResponse:
        """解析 DashScope 响应"""
        output = response.output
        
        if output.choices:
            choice = output.choices[0]
            msg = choice.message
            content = msg.get("content", "") if isinstance(msg, dict) else (msg.content if hasattr(msg, 'content') else "")
            finish_reason = choice.finish_reason if hasattr(choice, 'finish_reason') else "stop"
            
            tool_calls = []
            if isinstance(msg, dict):
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        try:
                            args = tc["function"]["arguments"]
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except json.JSONDecodeError:
                                    args = json.loads(args.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))
                            tool_calls.append(ToolCall(
                                id=tc.get("id", ""),
                                name=tc["function"]["name"],
                                arguments=args
                            ))
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"解析tool_call参数失败: {e}, args={tc.get('function', {}).get('arguments', 'N/A')}")
                            continue
            elif hasattr(msg, 'get') and msg.get("tool_calls"):
                for tc in msg.get("tool_calls", []):
                    try:
                        args = tc["function"]["arguments"]
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = json.loads(args.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))
                        tool_calls.append(ToolCall(
                            id=tc.get("id", ""),
                            name=tc["function"]["name"],
                            arguments=args
                        ))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"解析tool_call参数失败: {e}, args={tc.get('function', {}).get('arguments', 'N/A')}")
                        continue
        else:
            content = output.text if hasattr(output, 'text') else output.get('text', '')
            finish_reason = output.finish_reason if hasattr(output, 'finish_reason') else output.get('finish_reason', 'stop')
            tool_calls = []

        usage = response.usage
        logger.debug(f"DashScope usage: {usage}, type: {type(usage)}")
        
        if usage:
            prompt_tokens = usage.input_tokens if hasattr(usage, 'input_tokens') else usage.get('input_tokens', 0)
            completion_tokens = usage.output_tokens if hasattr(usage, 'output_tokens') else usage.get('output_tokens', 0)
            total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else usage.get('total_tokens', 0)
            logger.info(f"📊 DashScope Token: 输入={prompt_tokens}, 输出={completion_tokens}, 总计={total_tokens}")
            
            try:
                from ..utils.token_counter import update_token_count
                update_token_count(total_tokens)
            except Exception as e:
                logger.warning(f"Token计数更新失败: {e}")
        else:
            prompt_tokens = completion_tokens = total_tokens = 0
            logger.warning("DashScope usage 为空")
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        )

    async def stream_chat(
        self,
        messages: Union[List[Message], List[Dict]],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ):
        call_params = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "result_format": "message",
            "stream": True,
        }
        
        if tools:
            call_params["tools"] = self._convert_tools(tools)
        
        if self.enable_search:
            call_params["enable_search"] = True
        
        call_params.update(kwargs)

        responses = Generation.call(**call_params)

        for response in responses:
            if response.status_code == 200:
                output = response.output
                if output.choices:
                    msg = output.choices[0].message
                    content = msg.get("content", "") if isinstance(msg, dict) else (msg.content if hasattr(msg, 'content') else "")
                else:
                    content = output.text if hasattr(output, 'text') else output.get('text', '')
                if content:
                    yield content
