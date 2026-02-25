# 智能体开发规范文档

本文档定义了智能体代码生成的标准模板和规范，LLM 应严格按照此模板填充实现。

## 1. 文件结构

```
src/personal_agent/agents/{agent_name}.py
```

## 2. 必须导入的模块

```python
"""
{agent_name} - {description}
"""
import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

from .base import BaseAgent, Task, Message
```

**禁止使用**:
- `from src.personal_agent.xxx` (绝对导入)
- 未在上述列表中的模块 (需额外说明原因)

## 3. 类定义模板

```python
class {AgentClass}(BaseAgent):
    """
    {description}
    
    能力:
        - {capability_1}: {capability_1_desc}
        - {capability_2}: {capability_2_desc}
    """
    
    # 优先级: 1-10, 数字越小优先级越高
    # 系统级: 1-2, 应用级: 3-5, 扩展级: 6-10
    PRIORITY: int = {priority}
    
    # 关键词映射: {keyword: (action, params)}
    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "{keyword_1}": ("{action_1}", {{}}),
        "{keyword_2}": ("{action_2}", {{"param": "value"}}),
    }
    
    def __init__(self):
        super().__init__(
            name="{agent_name}",
            description="{description}"
        )
        
        # 注册能力
        self.register_capability("{capability_1}")
        self.register_capability("{capability_2}")
        
        # 注册支持的文件格式 (可选)
        # self.register_file_formats(
        #     open_formats=[".ext1", ".ext2"],
        #     edit_formats=[".ext1"]
        # )
        
        # 初始化私有状态
        self._{private_var}: Optional[Type] = None
        
        logger.info(f"✅ {agent_name} 已初始化")
```

## 4. execute_task 方法模板

```python
async def execute_task(self, task: Task) -> Any:
    """
    执行任务 - 主入口方法
    
    Args:
        task: 任务对象，包含 type, content, params
        
    Returns:
        str: 执行结果消息，或 Dict 格式的结果
    """
    task_type = task.type
    params = task.params or {}
    
    logger.info(f"🔧 {self.name} 执行任务: {task_type}")
    
    try:
        # 任务路由
        if task_type == "{action_1}":
            return await self._handle_{action_1}(params)
        elif task_type == "{action_2}":
            return await self._handle_{action_2}(params)
        elif task_type == "help":
            return self._get_help_info()
        else:
            return self.cannot_handle(
                reason=f"不支持的操作: {task_type}",
                suggestion="",
                missing_info={}
            )
            
    except Exception as e:
        logger.error(f"❌ {self.name} 执行失败: {e}")
        return self.cannot_handle(
            reason=f"执行错误: {str(e)}",
            suggestion=""
        )
```

## 5. 任务处理方法模板

```python
async def _handle_{action}(self, params: Dict) -> str:
    """
    处理 {action} 任务
    
    Args:
        params: 任务参数，可能包含:
            - original_text: 用户原始输入
            - {param_1}: {param_1_desc}
            
    Returns:
        str: 执行结果
    """
    # 1. 参数验证
    required_param = params.get("{required_param}")
    if not required_param:
        return self.cannot_handle(
            reason="缺少必要参数: {required_param}",
            missing_info={"{required_param}": "{required_param_desc}"}
        )
    
    # 2. 执行核心逻辑
    try:
        result = await self._{internal_method}(required_param)
        
        # 3. 返回成功结果
        return f"✅ {success_message}\n{details}"
        
    except SpecificException as e:
        logger.warning(f"⚠️ {action} 处理异常: {e}")
        return f"❌ {error_message}: {str(e)}"
        
    except Exception as e:
        logger.error(f"❌ {action} 未知错误: {e}")
        return self.cannot_handle(
            reason=f"处理失败: {str(e)}",
            suggestion=""
        )
```

## 6. 错误处理规范

### 6.1 使用 cannot_handle 方法

当智能体无法处理任务时，必须使用 `cannot_handle` 方法返回：

```python
return self.cannot_handle(
    reason="无法处理的原因",
    suggestion="建议的处理方式或智能体",
    missing_info={
        "param_name": "参数描述",
        # Master 会尝试从上下文推断这些参数
    }
)
```

### 6.2 错误消息格式

```python
# 成功
"✅ 操作成功: 详情..."

# 警告 (部分成功)
"⚠️ 部分完成: 详情..."

# 错误 (用户可修正)
"❌ 操作失败: 原因..."

# 无法处理 (需要 Master 介入)
return self.cannot_handle(reason="...", suggestion="...")
```

## 7. LLM 调用规范

```python
def _get_llm_gateway(self):
    """获取 LLM 网关实例"""
    from ..llm import LLMGateway
    from ..config import settings
    return LLMGateway(settings.llm)

async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
    """
    调用 LLM
    
    Args:
        prompt: 用户提示
        system_prompt: 系统提示 (可选)
        
    Returns:
        str: LLM 响应内容
    """
    try:
        llm = self._get_llm_gateway()
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await llm.chat(messages)
        return response.content
        
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise
```

## 8. 历史记录访问规范

```python
def _get_conversation_history(self, limit: int = 30) -> str:
    """获取历史聊天记录"""
    try:
        from ..main import PersonalAgentApp
        app = PersonalAgentApp._instance
        
        if app and hasattr(app, 'agent') and hasattr(app.agent, 'memory'):
            history = app.agent.memory.get_conversation_history()
        else:
            # 从文件加载
            history = self._load_history_from_file()
            
        if not history:
            return ""
            
        lines = []
        for msg in history[-limit:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            if content and len(content) > 5:
                lines.append(f"[{role}] {content[:200]}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"获取历史记录失败: {e}")
        return ""

def _load_history_from_file(self) -> List[Dict]:
    """从文件加载历史记录"""
    try:
        import json
        from pathlib import Path
        
        conv_file = Path("data/conversations/conversation.json")
        if not conv_file.exists():
            return []
            
        with open(conv_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return [{"role": m.get("role", ""), "content": m.get("content", "")} 
                for m in data.get("messages", [])]
    except Exception as e:
        logger.warning(f"加载历史文件失败: {e}")
        return []
```

## 9. 帮助信息规范

```python
def _get_help_info(self) -> str:
    """获取帮助信息"""
    return f"""📖 {self.name} 帮助

📝 描述: {self.description}

⚡ 支持的操作:
  • {action_1} - {action_1_desc}
  • {action_2} - {action_2_desc}

🔑 关键词:
  • {keyword_1}
  • {keyword_2}

💡 示例:
  • "{example_1}"
  • "{example_2}"
"""
```

## 10. 完整示例

```python
"""
weather_agent - 天气查询智能体
"""
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger

from .base import BaseAgent, Task


class WeatherAgent(BaseAgent):
    """天气查询智能体"""
    
    PRIORITY: int = 3
    KEYWORD_MAPPINGS: Dict[str, tuple] = {
        "天气": ("query", {}),
        "天气预报": ("forecast", {}),
        "今天天气": ("query", {}),
    }
    
    def __init__(self):
        super().__init__(
            name="weather_agent",
            description="天气查询智能体 - 提供实时天气和预报"
        )
        
        self.register_capability("weather_query")
        self.register_capability("weather_forecast")
        
        self._api_key: Optional[str] = None
        
        logger.info("✅ weather_agent 已初始化")
    
    async def execute_task(self, task: Task) -> Any:
        task_type = task.type
        params = task.params or {}
        
        logger.info(f"🔧 {self.name} 执行任务: {task_type}")
        
        try:
            if task_type == "query":
                return await self._handle_query(params)
            elif task_type == "forecast":
                return await self._handle_forecast(params)
            elif task_type == "help":
                return self._get_help_info()
            else:
                return self.cannot_handle(
                    reason=f"不支持的操作: {task_type}",
                    missing_info={}
                )
        except Exception as e:
            logger.error(f"❌ {self.name} 执行失败: {e}")
            return self.cannot_handle(reason=f"执行错误: {str(e)}")
    
    async def _handle_query(self, params: Dict) -> str:
        city = params.get("city") or params.get("location")
        
        if not city:
            return self.cannot_handle(
                reason="缺少城市信息",
                missing_info={"city": "城市名称"}
            )
        
        try:
            weather_data = await self._fetch_weather(city)
            return self._format_weather(weather_data)
        except Exception as e:
            return f"❌ 查询天气失败: {str(e)}"
    
    async def _fetch_weather(self, city: str) -> Dict:
        # 实现天气获取逻辑
        pass
    
    def _format_weather(self, data: Dict) -> str:
        return f"🌤️ {data['city']} 天气\n🌡️ 温度: {data['temp']}°C"
    
    def _get_help_info(self) -> str:
        return """📖 weather_agent 帮助

⚡ 支持的操作:
  • query - 查询当前天气
  • forecast - 查询天气预报

🔑 关键词:
  • 天气、今天天气、天气预报

💡 示例:
  • "北京天气怎么样"
  • "明天上海天气预报"
"""
```

## 11. 关键词映射规则（重要）

### 11.1 匹配规则
关键词映射使用**完全匹配**，不使用包含匹配。这是为了避免丢失用户意图。

**示例**:
- 用户输入 "播放音乐。" → 清理标点后为 "播放音乐" → 完全匹配 `KEYWORD_MAPPINGS["播放音乐"]`
- 用户输入 "播放" → 完全匹配 `KEYWORD_MAPPINGS["播放"]`
- 用户输入 "播放一首好听的歌" → 无完全匹配 → 交给 LLM 解析

### 11.2 标点清理
系统会自动清理用户输入中的中英文标点符号：
- 中文标点：`。，！？、；：""''（）【】《》`
- 英文标点：`.,!?;:"'()/`

### 11.3 关键词设计原则
1. **使用完整短语**：如 `"播放音乐"` 而非 `"播放"`
2. **覆盖常见表达**：如 `"播放"`、`"放音乐"`、`"听歌"` 都映射到同一操作
3. **避免歧义**：不要使用可能产生歧义的短关键词
4. **不使用包含匹配**：只做完全匹配，复杂意图交给 LLM

### 11.4 关键词映射示例
```python
KEYWORD_MAPPINGS: Dict[str, tuple] = {
    "播放": ("play", {}),           # 单独"播放"时播放音乐
    "播放音乐": ("play", {}),       # "播放音乐"
    "放音乐": ("play", {}),         # 口语化表达
    "听歌": ("play", {}),           # 另一种表达
    "暂停": ("pause", {}),          # 暂停播放
    "暂停音乐": ("pause", {}),      # 完整表达
    "下一首": ("next", {}),         # 切换下一首
    "上一首": ("prev", {}),         # 切换上一首
}
```

## 12. 代码生成检查清单

生成代码后，必须检查以下项目：

- [ ] 导入路径使用相对导入 (`.base` 而非 `src.personal_agent.agents.base`)
- [ ] 类继承自 `BaseAgent`
- [ ] 定义了 `PRIORITY` 常量
- [ ] 定义了 `KEYWORD_MAPPINGS` 字典
- [ ] 关键词使用**完全匹配**，不使用包含匹配
- [ ] 实现了 `execute_task` 方法
- [ ] 使用 `cannot_handle` 处理无法完成的情况
- [ ] 使用 `logger` 记录关键操作
- [ ] 返回消息使用 ✅ ❌ ⚠️ 等图标
- [ ] 实现了 `_get_help_info` 方法
- [ ] 所有异步方法使用 `async/await`
- [ ] 类型注解完整

## 13. 禁止事项

1. **禁止** 使用绝对导入路径
2. **禁止** 在 `__init__` 中执行耗时操作
3. **禁止** 直接返回 `None`（应返回 `cannot_handle` 或错误消息）
4. **禁止** 使用 `print()` 输出（应使用 `logger`）
5. **禁止** 硬编码敏感信息（API Key 等）
6. **禁止** 阻塞式调用（应使用 `async` 版本）
7. **禁止** 在关键词映射中使用包含匹配逻辑
