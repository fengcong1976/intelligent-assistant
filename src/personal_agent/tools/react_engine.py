"""
ReAct Engine - 推理与行动循环引擎

实现 ReAct (Reasoning + Acting) 模式，让 LLM 能够：
1. 推理当前需要做什么
2. 选择并调用合适的工具
3. 观察结果并继续推理
4. 直到完成任务

支持工作流规划：
- 分析工具之间的依赖关系
- 自动判断并行/串行执行
- 按正确顺序执行有依赖的任务
"""
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
from loguru import logger

from ..llm.base import LLMResponse, ToolCall
from ..llm.gateway import LLMGateway
from ..config import settings
from ..agents.base import Task
from .agent_tools import get_tools_registry, AgentTool
from .workflow_planner import WorkflowPlan
from .reverse_workflow_planner import ReverseWorkflowPlanner
from .tool_doc_manager import ToolDocManager


@dataclass
class ReActStep:
    """ReAct 步骤记录"""
    step_type: str  # "thought", "action", "observation", "pending"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    estimated_time: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReActResult:
    """ReAct 执行结果"""
    success: bool
    answer: str
    steps: List[ReActStep] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)


class ToolExecutor:
    """工具执行器 - 负责执行工具调用并返回结果"""
    
    def __init__(self, multi_agent=None):
        self.multi_agent = multi_agent
        self.registry = get_tools_registry()
        self._agent_cache: Dict[str, Any] = {}
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any], original_request: str = None) -> str:
        """执行工具调用 - 直接调用智能体，跳过中间层"""
        if tool_name == "query_tools":
            keyword = arguments.get("keyword", "")
            include_params = arguments.get("include_params", False)
            return self.registry.query_tools(keyword, include_params)
        
        if tool_name == "get_tool_detail":
            tool_name_param = arguments.get("tool_name", "")
            if not tool_name_param:
                return "错误：请提供工具名称"
            
            from .tool_doc_manager import ToolDocManager
            doc_manager = ToolDocManager()
            doc = doc_manager.get_tool_doc(tool_name_param)
            
            if doc:
                return f"【{tool_name_param}】\n{doc}"
            else:
                summary = doc_manager.get_tool_summary(tool_name_param, self.registry)
                if summary:
                    return f"工具「{tool_name_param}」没有详细文档。\n\n{summary}\n\n提示：调用 query_tools() 查看所有可用工具。"
                else:
                    return f"错误：未找到工具「{tool_name_param}」。调用 query_tools() 查看可用工具。"
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return f"错误：未找到工具 '{tool_name}'。调用 query_tools() 查看可用工具。"
        
        agent_name = tool.agent_name
        
        if self.multi_agent and self.multi_agent.master:
            try:
                agent = await self._get_agent_direct(agent_name)
                if not agent:
                    return f"错误：无法获取智能体 '{agent_name}'"
                
                task_content = self._build_task_content(tool_name, arguments)
                
                task = Task(
                    type=tool_name,
                    content=task_content,
                    params=arguments,
                    priority=7
                )
                
                if original_request:
                    task.params["original_request"] = original_request
                
                result = await agent.execute_task(task)
                
                if result:
                    if hasattr(result, 'result') and result.result:
                        return str(result.result)
                    return str(result)
                return "工具执行完成"
                    
            except Exception as e:
                logger.error(f"工具执行失败: {e}")
                return f"工具执行失败: {str(e)}"
        else:
            return f"[模拟执行] 工具 {tool_name} 已调用，参数: {arguments}"
    
    async def _get_agent_direct(self, agent_name: str):
        """直接获取智能体实例，跳过消息总线"""
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
        
        master = self.multi_agent.master
        agent_name_lower = agent_name.lower()
        
        if agent_name_lower in master.sub_agents:
            agent = master.sub_agents[agent_name_lower]
            self._agent_cache[agent_name] = agent
            return agent
        
        agent = await master._get_or_create_agent(agent_name)
        if agent:
            self._agent_cache[agent_name] = agent
        return agent
    
    def _build_task_content(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """构建任务内容"""
        if tool_name == "get_weather":
            city = arguments.get("city", "")
            address = arguments.get("address", "")
            days = arguments.get("days", 0)
            
            location = ""
            if city and address:
                location = f"{city}{address}"
            elif city:
                location = city
            elif address:
                location = address
            
            day_text = ""
            if days == 1:
                day_text = "明天"
            elif days == 2:
                day_text = "后天"
            
            return f"{location}{day_text}天气"
        
        if tool_name == "system_control":
            command = arguments.get("command", "")
            return command
        
        if tool_name == "play_music":
            artist = arguments.get("artist", "")
            song = arguments.get("song", "")
            action = arguments.get("action", "play")
            
            if action != "play":
                return action
            if song:
                return f"播放{song}"
            if artist:
                return f"播放{artist}的歌"
            return "播放音乐"
        
        if tool_name == "contact_lookup":
            name = arguments.get("name", "")
            return f"查找{name}"
        
        if tool_name == "contact_list":
            return "列出所有联系人"
        
        if tool_name == "generate_image":
            prompt = arguments.get("prompt", "")
            return f"生成图片: {prompt}"
        
        if tool_name == "save_document":
            filename = arguments.get("filename", "文档")
            content = arguments.get("content", "")
            content_preview = content[:50] + "..." if len(content) > 50 else content
            return f"保存文档: {filename}"
        
        if tool_name == "send_email":
            recipient = arguments.get("recipient_name", "") or arguments.get("to", "")
            subject = arguments.get("subject", "")
            return f"发送邮件给: {recipient}"
        
        if tool_name == "query_stock":
            stock_code = arguments.get("stock_code", "")
            return f"{stock_code}"
        
        if tool_name == "query_index":
            index_name = arguments.get("index_name", "大盘")
            return f"{index_name}"
        
        parts = []
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            parts.append(f"{key}: {value}")
        return " ".join(parts)


class ReActEngine:
    """
    ReAct 循环引擎
    
    实现 Thought -> Action -> Observation 循环
    """
    
    MAX_ITERATIONS = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    TOOL_TIMEOUT = 60.0
    
    TOOL_TIMEOUTS = {
        "open_app": 180.0,
        "smart_install": 300.0,
        "create_travel_plan": 120.0,
        "generate_image": 120.0,
    }
    
    DIRECT_RETURN_TOOLS = {
        "play_music", "play_video", "get_weather",
        "open_app", "system_control", "find_file", "disk_space",
        "query_stock", "query_index", "get_news", "check_calendar", "download_file",
        "create_travel_plan", "generate_image", "clipboard_write", "take_screenshot",
        "send_email", "save_document"
    }
    
    TOOL_TIME_ESTIMATES = {
        "create_travel_plan": ("生成旅游攻略", "10-20秒"),
        "generate_image": ("生成图片", "20-40秒"),
        "save_document": ("保存文档", "3-5秒"),
        "send_email": ("发送邮件", "5-10秒"),
        "get_weather": ("查询天气", "3-5秒"),
        "get_news": ("获取新闻", "5-10秒"),
        "search_web": ("搜索网络", "5-10秒"),
        "disk_space": ("查询磁盘空间", "1-2秒"),
        "query_stock": ("查询股票", "3-5秒"),
        "query_index": ("查询指数", "3-5秒"),
        "contact_list": ("导出通讯录", "3-5秒"),
        "open_app": ("启动应用", "3秒-3分钟"),
        "smart_install": ("安装应用", "1-3分钟"),
        "clipboard_write": ("复制到剪贴板", "1秒"),
        "take_screenshot": ("截图", "1-2秒"),
    }
    
    def __init__(self, llm: LLMGateway, tool_executor: ToolExecutor):
        self.llm = llm
        self.tool_executor = tool_executor
        self.registry = get_tools_registry()
        self.reverse_planner = ReverseWorkflowPlanner()
        self._context_files: List[str] = []
        self.tool_doc_manager = ToolDocManager()
    
    async def run(
        self,
        user_input: str,
        context: Optional[List[Dict]] = None,
        on_step: Optional[Callable[[ReActStep], None]] = None
    ) -> ReActResult:
        """
        执行 ReAct 循环
        
        Args:
            user_input: 用户输入
            context: 对话上下文
            on_step: 步骤回调函数
        """
        result = ReActResult(success=False, answer="")
        messages, files = self._build_initial_messages(user_input, context)
        self._context_files = files
        
        tool_outputs: Dict[str, str] = {}
        
        for iteration in range(self.MAX_ITERATIONS):
            try:
                if iteration == 0:
                    response = await self._query_and_select_tools(messages)
                else:
                    response = await self._call_llm_with_retry(messages)
                
                if response.tool_calls:
                    if len(response.tool_calls) > 1:
                        tool_calls_data = [
                            {"name": tc.name, "arguments": tc.arguments}
                            for tc in response.tool_calls
                        ]
                        
                        nodes, execution_plan = self.reverse_planner.analyze_tool_calls(tool_calls_data)
                        
                        return await self._execute_interface_driven_workflow(
                            nodes, execution_plan, response.tool_calls, messages, result, on_step, tool_outputs, user_input
                        )
                    
                    tool_call = response.tool_calls[0]
                    
                    time_info = self.TOOL_TIME_ESTIMATES.get(tool_call.name)
                    if time_info and on_step:
                        pending_step = ReActStep(
                            step_type="pending",
                            content=f"⏳ {time_info[0]}中，预计需要 {time_info[1]}，请稍候...",
                            tool_name=tool_call.name,
                            estimated_time=time_info[1]
                        )
                        on_step(pending_step)
                    
                    step = ReActStep(
                        step_type="action",
                        content=f"调用工具: {tool_call.name}",
                        tool_name=tool_call.name,
                        tool_args=tool_call.arguments
                    )
                    result.steps.append(step)
                    if on_step:
                        on_step(step)
                    
                    observation = await self._execute_tool_with_timeout(
                        tool_call.name,
                        tool_call.arguments,
                        original_request=user_input
                    )
                    
                    tool_outputs[tool_call.name] = observation
                    
                    obs_step = ReActStep(
                        step_type="observation",
                        content=observation
                    )
                    result.steps.append(obs_step)
                    if on_step:
                        on_step(obs_step)
                    
                    result.tool_calls.append({
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                        "result": observation
                    })
                    
                    if tool_call.name in self.DIRECT_RETURN_TOOLS:
                        result.success = True
                        result.answer = observation
                        return result
                    
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False)
                            }
                        }]
                    })
                    messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": observation
                        })
                
                elif response.content:
                    result.success = True
                    result.answer = response.content
                    
                    thought_step = ReActStep(
                        step_type="thought",
                        content=response.content
                    )
                    result.steps.append(thought_step)
                    if on_step:
                        on_step(thought_step)
                    
                    break
                
                else:
                    result.answer = "抱歉，我无法处理这个请求。"
                    break
                    
            except Exception as e:
                logger.error(f"ReAct 迭代失败: {e}")
                result.answer = f"处理过程中出现错误: {str(e)}"
                break
        
        if not result.success and not result.answer:
            result.answer = "抱歉，我无法在限定步骤内完成任务。请尝试简化您的问题。"
        
        self._learn_from_interaction(user_input, result.answer)
        
        return result
    
    async def _execute_workflow_plan(
        self,
        plan: WorkflowPlan,
        tool_calls: List[ToolCall],
        messages: List[Dict],
        result: ReActResult,
        on_step: Optional[Callable[[ReActStep], None]],
        tool_outputs: Dict[str, str],
        original_request: str = None
    ) -> ReActResult:
        """
        按工作流计划执行工具调用
        
        Args:
            plan: 工作流计划
            tool_calls: 原始工具调用列表
            messages: 消息历史
            result: 结果对象
            on_step: 步骤回调
            tool_outputs: 工具输出缓存
        """
        tool_call_map = {tc.name: tc for tc in tool_calls}
        
        for level_idx, level in enumerate(plan.execution_order):
            for node_name in level:
                node = plan.get_node(node_name)
                if not node:
                    continue
                
                tool_call = tool_call_map.get(node.tool_name)
                
                args = dict(node.arguments)
                
                args = self._resolve_dependencies(args, node.dependencies, tool_outputs)
                
                step = ReActStep(
                    step_type="action",
                    content=f"调用工具: {node.tool_name}",
                    tool_name=node.tool_name,
                    tool_args=args
                )
                result.steps.append(step)
                if on_step:
                    on_step(step)
                
                observation = await self._execute_tool_with_timeout(
                    node.tool_name,
                    args,
                    original_request=original_request
                )
                
                tool_outputs[node_name] = observation
                
                obs_step = ReActStep(
                    step_type="observation",
                    content=observation
                )
                result.steps.append(obs_step)
                if on_step:
                    on_step(obs_step)
                
                result.tool_calls.append({
                    "name": node.tool_name,
                    "arguments": args,
                    "result": observation
                })
                
                tool_call_id = tool_call.id if tool_call else f"injected_{node.tool_name}"
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": node.tool_name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                        }
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation
                })
        
        all_observations = []
        for node_name, obs in tool_outputs.items():
            if obs and obs.strip():
                all_observations.append(obs)
        
        last_observation = "\n\n".join(all_observations) if all_observations else ""
        result.success = True
        result.answer = last_observation
        return result
    
    async def _execute_interface_driven_workflow(
        self,
        nodes: List[Any],
        execution_plan: List[List[str]],
        tool_calls: List[ToolCall],
        messages: List[Dict],
        result: ReActResult,
        on_step: Optional[Callable[[ReActStep], None]],
        tool_outputs: Dict[str, str],
        original_request: str = None
    ) -> ReActResult:
        """
        按接口驱动的工作流计划执行工具调用
        
        Args:
            nodes: 工作流节点列表
            execution_plan: 执行计划（按层级分组）
            tool_calls: 原始工具调用列表
            messages: 消息历史
            result: 结果对象
            on_step: 步骤回调
            tool_outputs: 工具输出缓存
        """
        tool_call_map = {tc.name: tc for tc in tool_calls}
        
        node_map = {}
        for n in nodes:
            node_map[n.tool_name] = n
            if hasattr(n, 'node_name'):
                node_map[n.node_name] = n
        
        total_steps = sum(len(level) for level in execution_plan)
        if total_steps > 1 and on_step:
            pending_step = ReActStep(
                step_type="pending",
                content=f"正在规划执行 {total_steps} 个任务...",
                estimated_time=self._estimate_total_time([n.tool_name for n in nodes])
            )
            on_step(pending_step)
        
        for level_idx, level in enumerate(execution_plan):
            for node_name in level:
                node = node_map.get(node_name)
                if not node:
                    continue
                
                tool_call = tool_call_map.get(node.tool_name)
                
                args = dict(node.arguments)
                
                args = self._resolve_dependencies(args, node.dependencies, tool_outputs)
                
                time_info = self.TOOL_TIME_ESTIMATES.get(node.tool_name)
                if time_info and on_step:
                    pending_step = ReActStep(
                        step_type="pending",
                        content=f"⏳ {time_info[0]}中，预计需要 {time_info[1]}，请稍候...",
                        tool_name=node.tool_name,
                        estimated_time=time_info[1]
                    )
                    on_step(pending_step)
                
                step = ReActStep(
                    step_type="action",
                    content=f"调用工具: {node.tool_name}",
                    tool_name=node.tool_name,
                    tool_args=args
                )
                result.steps.append(step)
                if on_step:
                    on_step(step)
                
                observation = await self._execute_tool_with_timeout(
                    node.tool_name,
                    args,
                    original_request=original_request
                )
                
                tool_outputs[node_name] = observation
                
                obs_step = ReActStep(
                    step_type="observation",
                    content=observation
                )
                result.steps.append(obs_step)
                if on_step:
                    on_step(obs_step)
                
                result.tool_calls.append({
                    "name": node.tool_name,
                    "arguments": args,
                    "result": observation
                })
                
                tool_call_id = tool_call.id if tool_call else f"injected_{node.tool_name}"
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": node.tool_name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                        }
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": observation
                })
        
        last_observation = list(tool_outputs.values())[-1] if tool_outputs else ""
        result.success = True
        result.answer = last_observation
        return result
    
    def _resolve_dependencies(
        self,
        args: Dict[str, Any],
        dependencies: List[str],
        tool_outputs: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        解析依赖关系，替换参数中的占位符
        
        Args:
            args: 原始参数
            dependencies: 依赖的节点列表
            tool_outputs: 工具输出缓存
        """
        import re
        import os
        
        resolved_args = dict(args)
        
        for key, value in resolved_args.items():
            if isinstance(value, str):
                value_stripped = value.strip()
                placeholder_match = re.match(r'^\{\{([\w_]+)(?:\.([\w_]+))?\}\}$', value_stripped)
                if not placeholder_match:
                    placeholder_match = re.match(r'^\{([\w_]+)(?:\.([\w_]+))?\}$', value_stripped)
                
                if placeholder_match:
                    tool_name = placeholder_match.group(1)
                    field_name = placeholder_match.group(2)
                    
                    for dep_name, dep_output in tool_outputs.items():
                        dep_tool_name = dep_name
                        if '_' in dep_name and not any(dep_name == t for t in ['contact_lookup', 'create_travel_plan', 'send_email', 'generate_image', 'save_document']):
                            dep_tool_name = dep_name.split('_')[0]
                        if dep_name == tool_name or dep_tool_name == tool_name:
                            
                            structured_match = re.search(r'\[STRUCTURED_DATA\](.+?)\[/STRUCTURED_DATA\]', dep_output, re.DOTALL)
                            if structured_match and field_name:
                                try:
                                    structured_data = json.loads(structured_match.group(1))
                                    if field_name in structured_data:
                                        resolved_args[key] = structured_data[field_name]
                                        break
                                except json.JSONDecodeError as e:
                                    logger.warning(f"解析结构化数据失败: {e}")
                            
                            if field_name == "file_path" or field_name == "filepath":
                                path_match = re.search(r'([A-Za-z]:\\[^\n\r]+)', dep_output)
                                if path_match:
                                    resolved_args[key] = path_match.group(1).strip()
                            elif field_name == "content":
                                resolved_args[key] = dep_output
                            elif field_name == "image":
                                resolved_args[key] = dep_output
                            elif field_name is None:
                                resolved_args[key] = dep_output
                            else:
                                path_match = re.search(r'([A-Za-z]:\\[^\n\r]+)', dep_output)
                                if path_match:
                                    resolved_args[key] = path_match.group(1).strip()
                                else:
                                    resolved_args[key] = dep_output
                            break
        
        for dep in dependencies:
            if dep in tool_outputs:
                dep_output = tool_outputs[dep]
                
                if "attachment" in resolved_args:
                    attachment = resolved_args.get("attachment")
                    if not attachment:
                        continue
                    if re.match(r'^\{\{?[\w_]+', str(attachment)):
                        continue
                    
                    fake_patterns = ["/path/", "[待定]", "[附件]", "[文件]", "{attachment}", "{file_path}", "#FILEPATH#", "#filepath#", "%find_file", "%save_document", "%.result."]
                    is_fake = any(p.lower() in str(attachment).lower() for p in fake_patterns)
                    is_fake = is_fake or (not re.search(r'[A-Za-z]:\\', str(attachment)) and not str(attachment).startswith("/"))
                    is_fake = is_fake or (str(attachment).startswith("%") and str(attachment).endswith("%"))
                    
                    if not is_fake and os.path.exists(attachment):
                        pass
                    elif not is_fake and dep in ["generate_image", "save_document", "find_file"]:
                        is_fake = True
                    
                    if is_fake:
                        path_match = re.search(r'已保存[：:]\s*([A-Za-z]:\\[^\n\r]+)', dep_output)
                        if not path_match:
                            path_match = re.search(r'([A-Za-z]:\\[^\n\r]+)', dep_output)
                        
                        if path_match:
                            resolved_args["attachment"] = path_match.group(1).strip()
                
                if "attachment" not in resolved_args and dep in ["save_document", "generate_image", "find_file"]:
                    path_match = re.search(r'已保存[：:]\s*([A-Za-z]:\\[^\n\r]+)', dep_output)
                    if not path_match:
                        path_match = re.search(r'([A-Za-z]:\\[^\n\r]+)', dep_output)
                    
                    if path_match:
                        resolved_args["attachment"] = path_match.group(1).strip()
                
                if "to" in resolved_args:
                    to_value = resolved_args.get("to") or ""
                    fake_email_patterns = ["@example.com", "@example.org", "@test.com", "@fake.com"]
                    is_fake_email = any(p in str(to_value).lower() for p in fake_email_patterns)
                    
                    if is_fake_email or not to_value:
                        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', dep_output)
                        if email_match:
                            resolved_args["to"] = email_match.group(0)
                
                if "to" not in resolved_args and "contact_lookup" in dep:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', dep_output)
                    if email_match:
                        resolved_args["to"] = email_match.group(0)
                
                content_providers = ["create_travel_plan", "search_web", "get_weather", "get_news", "query_stock", "query_index", "crawl_webpage", "search", "web_search", "developer_task"]
                if dep in content_providers or "search" in dep or "crawl" in dep or "developer" in dep:
                    content = resolved_args.get("content", "")
                    if not content or "{previous" in str(content) or "{output:" in str(content):
                        resolved_args["content"] = dep_output
        
        return resolved_args
    
    def _estimate_total_time(self, tool_names: List[str]) -> str:
        """估算总执行时间"""
        total_seconds = 0
        for name in tool_names:
            time_info = self.TOOL_TIME_ESTIMATES.get(name)
            if time_info:
                time_str = time_info[1]
                if "秒" in time_str:
                    parts = time_str.replace("秒", "").split("-")
                    if len(parts) == 2:
                        avg = (int(parts[0]) + int(parts[1])) // 2
                        total_seconds += avg
                    else:
                        total_seconds += int(parts[0])
        
        if total_seconds < 60:
            return f"{total_seconds}秒"
        else:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒" if seconds > 0 else f"{minutes}分钟"
    
    async def run_stream(
        self,
        user_input: str,
        context: Optional[List[Dict]] = None,
        on_step: Optional[Callable[[ReActStep], None]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行 ReAct 循环，逐步返回结果
        """
        result = await self.run(user_input, context, on_step)
        yield result.answer
    
    def _build_initial_messages(
        self,
        user_input: str,
        context: Optional[List[Dict]] = None
    ) -> Tuple[List[Dict], List[str]]:
        """构建初始消息列表，返回 (messages, files)"""
        from ..config import settings as app_settings
        from ..user_config import user_config
        from ..memory.unified_memory import unified_memory
        
        user_name = user_config.user_name or app_settings.user.name or "用户"
        user_formal_name = user_config.formal_name or app_settings.user.formal_name or user_name
        agent_name = app_settings.agent.name or "小智"
        user_city = app_settings.user.city or ""
        user_address = app_settings.user.address or ""
        
        user_location = ""
        if user_city and user_address:
            user_location = f"{user_city}{user_address}"
        elif user_city:
            user_location = user_city
        elif user_address:
            user_location = user_address
        
        location_hint = ""
        if user_location:
            location_hint = f"\n位置：{user_location}"
        
        memory_context = unified_memory.get_memory_for_llm()
        memory_section = ""
        if memory_context and len(memory_context) > 50:
            memory_section = f"""

【用户记忆】
{memory_context}

请根据用户记忆中的信息来个性化回复。例如：
- 使用用户的昵称称呼用户
- 记住用户的偏好和习惯
- 关注用户的重要事件
"""
        
        system_prompt = f"""你是{agent_name}，一个智能助手。{location_hint}{memory_section}

【重要】工具使用规则：
1. 当用户要求执行操作（保存文件、发送邮件、生成图片等），必须先调用 query_tools 工具查询可用工具
2. 不要说"我无法做到"或"我没有这个功能"，而是先查询工具
3. 常用工具关键词：保存、pdf、邮件、天气、图片、音乐、视频、下载、安装

示例：
- 用户："保存成PDF" → 调用 query_tools(keyword="保存") 或 query_tools(keyword="pdf")
- 用户："发邮件" → 调用 query_tools(keyword="邮件")
- 用户："查天气" → 调用 query_tools(keyword="天气")"""

        messages = [{"role": "system", "content": system_prompt}]
        
        files = []
        if context:
            for msg in context:
                if msg.get("role") == "system" and "附件信息" in msg.get("content", ""):
                    import re
                    file_matches = re.findall(r'- (.+)$', msg.get("content", ""), re.MULTILINE)
                    files = [f.strip() for f in file_matches if f.strip()]
                    logger.info(f"📎 从上下文提取附件: {files}")
            messages.extend(context)
        
        messages.append({"role": "user", "content": user_input})
        
        return messages, files
    
    def _get_tool_definitions(self) -> List:
        """获取工具定义"""
        from ..llm.base import ToolDefinition
        
        tools = self.registry.get_all_tools()
        definitions = [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters
            )
            for tool in tools
        ]
        
        definitions.append(ToolDefinition(
            name="query_tools",
            description="查询可用工具。当你不确定有什么工具可用时，调用此工具查询。返回工具列表或指定工具的详细信息。",
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如'邮件'、'天气'。为空则返回所有工具列表"
                    },
                    "include_params": {
                        "type": "boolean",
                        "description": "是否包含参数详情，默认false",
                        "default": False
                    }
                },
                "required": []
            }
        ))
        
        return definitions
    
    def _learn_from_interaction(self, user_input: str, response: str):
        """从交互中学习"""
        try:
            from ..memory.unified_memory import unified_memory
            from ..memory.memory_learner import MemoryLearner
            
            learner = MemoryLearner(unified_memory)
            
            learner.learn_from_message("user", user_input)
            
            unified_memory.add_context(f"用户: {user_input[:100]}")
            
            logger.debug(f"🧠 从交互中学习完成")
            
        except Exception as e:
            logger.debug(f"学习失败（可忽略）: {e}")
    
    def _get_query_tools_definition(self) -> List:
        """获取工具查询定义（第一阶段只发送这个）"""
        from ..llm.base import ToolDefinition
        
        return [
            ToolDefinition(
                name="query_tools",
                description="查询可用工具。【重要】当用户要求保存文件、生成图片、发送邮件等操作时，必须先调用此工具查询相关工具！不要说'我无法做到'，而是先查询工具。关键词示例：保存、pdf、图片、邮件、天气、下载、安装等。",
                parameters={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如'保存'、'pdf'、'邮件'、'天气'"
                        },
                        "include_params": {
                            "type": "boolean",
                            "description": "是否包含参数详情",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="get_tool_detail",
                description="获取工具的详细使用文档，包含功能说明、使用场景、示例和注意事项。当你需要了解某个工具的详细用法时调用此工具。",
                parameters={
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "工具名称，如'send_email'、'save_document'等"
                        }
                    },
                    "required": ["tool_name"]
                }
            ),
            ToolDefinition(
                name="get_instructions",
                description="获取详细操作指南。当你不确定如何使用工具或需要了解规则时调用。",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
    
    async def _call_llm_with_retry(self, messages: List[Dict], tools=None) -> LLMResponse:
        """带重试机制的 LLM 调用"""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self.llm.chat(messages, tools=tools or self._get_tool_definitions()),
                    timeout=self.TOOL_TIMEOUT
                )
                return response
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"LLM 调用超时（{self.TOOL_TIMEOUT}秒）")
                logger.warning(f"⚠️ LLM 调用超时，尝试 {attempt + 1}/{self.MAX_RETRIES}")
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ LLM 调用失败: {e}，尝试 {attempt + 1}/{self.MAX_RETRIES}")
            
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        
        raise last_error or Exception("LLM 调用失败")
    
    async def _query_and_select_tools(self, messages: List[Dict]) -> LLMResponse:
        """两阶段工具选择：先查询，再执行"""
        query_tools = self._get_query_tools_definition()
        
        response = await self._call_llm_with_retry(messages, tools=query_tools)
        
        if response.tool_calls:
            matched_tools = []
            for tool_call in response.tool_calls:
                if tool_call.name == "query_tools":
                    keyword = tool_call.arguments.get("keyword", "")
                    include_params = tool_call.arguments.get("include_params", True)
                    
                    tools_info = self.registry.query_tools(keyword, include_params=include_params)
                    logger.info(f"📚 ReAct查询工具: keyword='{keyword}', 结果长度={len(tools_info)}")
                    
                    matched_tools = self._get_matched_tools(keyword)
                    logger.info(f"📚 匹配到 {len(matched_tools)} 个工具定义")
                    
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False)
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tools_info
                    })
                    
                elif tool_call.name == "get_instructions":
                    instructions = """## 操作指南

1. 先调用 query_tools("关键词") 查询可用工具
2. 根据返回的工具信息调用对应工具
3. 规则：禁止编造文件路径；直接返回工具结果"""
                    
                    logger.info(f"📖 LLM 请求获取操作指南")
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.name,
                                "arguments": "{}"
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": instructions
                    })
            
            if matched_tools:
                return await self._call_llm_with_retry(messages, tools=matched_tools)
            return await self._call_llm_with_retry(messages, tools=query_tools)
        
        return response
    
    def _get_matched_tools(self, keyword: str) -> List:
        """根据关键词获取匹配的工具定义"""
        from ..llm.base import ToolDefinition
        
        all_tools = self.registry.get_all_tools()
        matched = []
        keyword_lower = keyword.lower()
        
        for tool in all_tools:
            if (keyword_lower in tool.name.lower() or 
                keyword_lower in tool.description.lower() or
                any(keyword_lower in tag.lower() for tag in getattr(tool, 'tags', []))):
                matched.append(tool)
        
        return matched if matched else all_tools[:5]
    
    async def _execute_tool_with_timeout(self, tool_name: str, arguments: Dict[str, Any], original_request: str = None) -> str:
        """带超时的工具执行"""
        timeout = self.TOOL_TIMEOUTS.get(tool_name, self.TOOL_TIMEOUT)
        
        if self._context_files and tool_name in ["send_email", "save_document"]:
            if "attachments" not in arguments:
                arguments["attachments"] = self._context_files
                logger.info(f"📎 自动添加附件到工具参数: {self._context_files}")
        
        try:
            return await asyncio.wait_for(
                self.tool_executor.execute(tool_name, arguments, original_request),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            error_msg = f"工具 '{tool_name}' 执行超时（{timeout}秒）"
            logger.error(f"❌ {error_msg}")
            return f"错误：{error_msg}"
    
    def _get_tools_description(self) -> str:
        """获取工具描述文本"""
        tools = self.registry.get_all_tools()
        lines = []
        for tool in tools:
            params_desc = ", ".join(
                f"{k}" + ("(必需)" if k in tool.parameters.get("required", []) else "")
                for k in tool.parameters.get("properties", {}).keys()
            )
            lines.append(f"- **{tool.name}**: {tool.description}")
            if params_desc:
                lines.append(f"  参数: {params_desc}")
        return "\n".join(lines)


def create_react_engine(multi_agent=None) -> ReActEngine:
    """创建 ReAct 引擎实例"""
    from ..llm import LLMGateway
    
    llm = LLMGateway(settings.llm)
    tool_executor = ToolExecutor(multi_agent)
    
    return ReActEngine(llm, tool_executor)
