"""
LLM 工作流规划器 - 使用 LLM 分析任务依赖关系

让 LLM 理解任务语义，规划工作流执行顺序
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
import json

from ..llm.gateway import LLMGateway
from ..config import settings
from .workflow_planner import WorkflowPlanner, WorkflowPlan, WorkflowNode, ExecutionMode


WORKFLOW_PLANNING_PROMPT = """你是一个工作流规划专家。分析用户的任务请求，规划工具调用的执行顺序。

## 可用工具

{tools_description}

## 任务请求

{user_request}

## LLM 已选择的工具调用

{tool_calls_json}

## 规划规则

1. **并行执行**：多个工具之间没有依赖关系时，可以同时执行
2. **串行执行**：后一个工具需要前一个工具的输出时，必须等待
3. **数据依赖**：如果工具参数中有空值或占位符（如 `/path/to/`），需要依赖前序工具填充
4. **文件依赖**：发送邮件的附件必须来自文档生成工具的输出

## 输出格式

请输出 JSON 格式的工作流计划：

```json
{{
  "analysis": "任务分析说明",
  "execution_plan": [
    {{
      "step": 1,
      "parallel": false,
      "tools": ["tool_name"],
      "reason": "执行原因"
    }},
    {{
      "step": 2,
      "parallel": true,
      "tools": ["tool_a", "tool_b"],
      "reason": "这两个工具可以并行执行"
    }}
  ],
  "dependencies": {{
    "tool_name": ["depends_on_tool"]
  }}
}}
```

只输出 JSON，不要其他内容。"""


@dataclass
class LLMWorkflowPlan:
    analysis: str
    execution_plan: List[Dict]
    dependencies: Dict[str, List[str]]
    raw_response: str


class LLMWorkflowPlanner:
    
    def __init__(self, llm: Optional[LLMGateway] = None):
        self.llm = llm or LLMGateway(settings.llm)
        self.rule_planner = WorkflowPlanner()
    
    async def plan_workflow(
        self,
        user_request: str,
        tool_calls: List[Dict],
        tools_description: str = ""
    ) -> LLMWorkflowPlan:
        """
        使用 LLM 规划工作流
        
        Args:
            user_request: 用户原始请求
            tool_calls: LLM 返回的工具调用列表
            tools_description: 可用工具描述
            
        Returns:
            LLMWorkflowPlan: LLM 规划的工作流
        """
        if len(tool_calls) <= 1:
            return LLMWorkflowPlan(
                analysis="单个工具调用，无需规划",
                execution_plan=[{"step": 1, "parallel": False, "tools": [tool_calls[0]["name"]]}],
                dependencies={},
                raw_response=""
            )
        
        prompt = WORKFLOW_PLANNING_PROMPT.format(
            tools_description=tools_description or self._get_default_tools_description(),
            user_request=user_request,
            tool_calls_json=json.dumps(tool_calls, ensure_ascii=False, indent=2)
        )
        
        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            
            plan = self._parse_llm_response(response.content)
            
            logger.info(f"🤖 LLM 工作流规划完成: {plan.analysis}")
            return plan
            
        except Exception as e:
            logger.error(f"LLM 工作流规划失败: {e}")
            return self._fallback_to_rule_planner(tool_calls)
    
    def _parse_llm_response(self, response: str) -> LLMWorkflowPlan:
        """解析 LLM 返回的 JSON"""
        import re
        
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response
        
        json_str = re.sub(r'```.*?```', '', json_str, flags=re.DOTALL)
        json_str = json_str.strip()
        
        if json_str.startswith('{') and json_str.endswith('}'):
            pass
        else:
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
        
        try:
            data = json.loads(json_str)
            return LLMWorkflowPlan(
                analysis=data.get("analysis", ""),
                execution_plan=data.get("execution_plan", []),
                dependencies=data.get("dependencies", {}),
                raw_response=response
            )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始响应: {response[:200]}")
            return LLMWorkflowPlan(
                analysis="解析失败",
                execution_plan=[],
                dependencies={},
                raw_response=response
            )
    
    def _fallback_to_rule_planner(self, tool_calls: List[Dict]) -> LLMWorkflowPlan:
        """回退到规则规划器"""
        rule_plan = self.rule_planner.analyze_tool_calls(tool_calls)
        
        execution_plan = []
        for i, level in enumerate(rule_plan.execution_order):
            execution_plan.append({
                "step": i + 1,
                "parallel": len(level) > 1,
                "tools": level,
                "reason": "规则分析器规划"
            })
        
        dependencies = {}
        for name, node in rule_plan.nodes.items():
            if node.dependencies:
                dependencies[name] = node.dependencies
        
        return LLMWorkflowPlan(
            analysis="使用规则分析器规划",
            execution_plan=execution_plan,
            dependencies=dependencies,
            raw_response=""
        )
    
    def _get_default_tools_description(self) -> str:
        """获取默认工具描述"""
        return """
| 工具名称 | 功能 | 输出类型 | 可提供 |
|---------|------|---------|--------|
| contact_list | 获取通讯录 | data | content, contacts |
| contact_lookup | 查找联系人 | data | content, contact_info |
| search_web | 网络搜索 | data | content, search_result |
| get_weather | 获取天气 | data | content, weather_data |
| save_document | 保存文档 | file_path | attachment, file_path |
| generate_image | 生成图片 | file_path | attachment, image_path |
| send_email | 发送邮件 | status | 无 |
| play_music | 播放音乐 | status | 无 |
| system_control | 系统控制 | status | 无 |
| open_app | 打开应用 | status | 无 |
"""
    
    def to_workflow_plan(self, llm_plan: LLMWorkflowPlan, tool_calls: List[Dict]) -> WorkflowPlan:
        """将 LLM 规划转换为标准 WorkflowPlan"""
        tool_call_map = {tc["name"]: tc for tc in tool_calls}
        
        nodes = {}
        execution_order = []
        
        for step in llm_plan.execution_plan:
            level_tools = step.get("tools", [])
            execution_order.append(level_tools)
            
            for tool_name in level_tools:
                tc = tool_call_map.get(tool_name, {"name": tool_name, "arguments": {}})
                deps = llm_plan.dependencies.get(tool_name, [])
                
                nodes[tool_name] = WorkflowNode(
                    name=tool_name,
                    tool_name=tool_name,
                    arguments=tc.get("arguments", {}),
                    dependencies=deps,
                    execution_mode=ExecutionMode.PARALLEL if step.get("parallel") else ExecutionMode.SEQUENTIAL
                )
        
        return WorkflowPlan(nodes=nodes, execution_order=execution_order)


async def create_llm_workflow_planner() -> LLMWorkflowPlanner:
    """创建 LLM 工作流规划器实例"""
    return LLMWorkflowPlanner()
