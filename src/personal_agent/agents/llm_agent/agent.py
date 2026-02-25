"""
LLM Agent - 大模型对话智能体
直接与 LLM 对话，不经过意图识别
"""
from typing import Any, Dict, Optional
from loguru import logger

from ..base import BaseAgent, Task


class LLMAgent(BaseAgent):
    """
    LLM 对话智能体 - 直接与 LLM 交互
    
    职责：
    1. 直接响应用户的对话请求
    2. 不经过意图识别，直接调用 LLM
    3. 支持多轮对话上下文
    """
    
    KEYWORD_MAPPINGS = {
        "问大模型": ("chat", {}),
        "问ai": ("chat", {}),
        "问人工智能": ("chat", {}),
        "直接问": ("chat", {}),
        "和ai聊天": ("chat", {}),
        "和大模型聊天": ("chat", {}),
        "问llm": ("chat", {}),
    }
    
    def __init__(self):
        super().__init__(
            name="llm_agent",
            description="LLM对话智能体 - 直接与大模型对话，不经过意图识别"
        )
        
        self.register_capability("llm_chat", "LLM对话")
        self.register_capability("direct_chat", "直接对话")
        self.register_capability("conversation", "对话")
        
        self._llm_gateway = None
        self._conversation_history: list = []
        self._max_history = 10
    
    def _get_llm_gateway(self):
        """获取 LLM 网关"""
        if self._llm_gateway is None:
            from ...llm import LLMGateway
            from ...config import settings
            self._llm_gateway = LLMGateway(settings.llm)
        return self._llm_gateway
    
    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params
        
        logger.info(f"🤖 LLM 智能体执行任务: {task_type}")
        
        if task_type == "chat":
            return await self._chat(params)
        elif task_type == "clear_history":
            return await self._clear_history(params)
        else:
            return await self._chat(params)
    
    async def _chat(self, params: Dict) -> str:
        """直接与 LLM 对话"""
        user_input = params.get("query", "") or params.get("message", "") or params.get("original_text", "")
        
        if not user_input:
            return "请输入您想问的问题"
        
        try:
            llm = self._get_llm_gateway()
            
            self._conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            if len(self._conversation_history) > self._max_history * 2:
                self._conversation_history = self._conversation_history[-self._max_history * 2:]
            
            response = await llm.chat(self._conversation_history)
            
            if response and response.content:
                self._conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                return response.content
            else:
                return "抱歉，我暂时无法回答这个问题"
                
        except Exception as e:
            logger.error(f"LLM 对话失败: {e}")
            return f"对话出错: {str(e)}"
    
    async def _clear_history(self, params: Dict) -> str:
        """清空对话历史"""
        self._conversation_history = []
        return "✅ 对话历史已清空"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取智能体能力"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self._capabilities,
            "keyword_mappings": self.KEYWORD_MAPPINGS,
            "supports_conversation": True,
        }
