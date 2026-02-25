"""
工作流规划器 - 分析任务依赖关系，构建执行计划

核心功能：
1. 分析工具之间的依赖关系
2. 构建工作流图（DAG）
3. 判断哪些任务可以并行，哪些必须串行
4. 生成执行计划

通用性设计：
- 工具依赖规则可配置
- 参数传递基于类型匹配
- 支持并行和串行执行
- 支持动态依赖推断
"""
from typing import Dict, List, Set, Tuple, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json
import re


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class WorkflowNode:
    name: str
    tool_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    output_key: str = ""
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL


@dataclass
class WorkflowPlan:
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    execution_order: List[List[str]] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return len(self.nodes) == 0
    
    def get_node(self, name: str) -> Optional[WorkflowNode]:
        return self.nodes.get(name)


@dataclass
class ToolDependency:
    name: str
    output_type: str
    can_provide: List[str]
    requires_input: List[str]
    description: str


class WorkflowPlanner:
    
    DEFAULT_TOOL_INFO: Dict[str, Dict] = {
        "save_document": {
            "output_type": "file_path",
            "can_provide": ["attachment", "file_path"],
            "requires_input": ["content"],
            "description": "生成文档文件"
        },
        "generate_image": {
            "output_type": "file_path",
            "can_provide": ["attachment", "file_path", "image_path"],
            "requires_input": [],
            "description": "生成图片文件"
        },
        "create_travel_plan": {
            "output_type": "data",
            "can_provide": ["content", "data", "travel_plan"],
            "requires_input": [],
            "description": "生成旅游攻略"
        },
        "contact_list": {
            "output_type": "data",
            "can_provide": ["content", "data", "contacts"],
            "requires_input": [],
            "description": "获取联系人数据"
        },
        "contact_lookup": {
            "output_type": "data",
            "can_provide": ["content", "data", "contact_info"],
            "requires_input": [],
            "description": "查找联系人信息"
        },
        "search_web": {
            "output_type": "data",
            "can_provide": ["content", "data", "search_result"],
            "requires_input": [],
            "description": "搜索网络数据"
        },
        "crawl_webpage": {
            "output_type": "data",
            "can_provide": ["content", "data", "crawl_result"],
            "requires_input": [],
            "description": "爬取网页数据"
        },
        "search": {
            "output_type": "data",
            "can_provide": ["content", "data", "search_result"],
            "requires_input": [],
            "description": "搜索数据"
        },
        "send_email": {
            "output_type": "status",
            "can_provide": [],
            "requires_input": ["attachment", "file_path"],
            "description": "发送邮件"
        },
        "play_music": {
            "output_type": "status",
            "can_provide": [],
            "requires_input": [],
            "description": "播放音乐"
        },
        "get_weather": {
            "output_type": "data",
            "can_provide": ["content", "weather_data"],
            "requires_input": [],
            "description": "获取天气"
        },
        "get_news": {
            "output_type": "data",
            "can_provide": ["content", "data", "news"],
            "requires_input": [],
            "description": "获取新闻"
        },
        "system_control": {
            "output_type": "status",
            "can_provide": [],
            "requires_input": [],
            "description": "系统控制"
        },
        "open_app": {
            "output_type": "status",
            "can_provide": [],
            "requires_input": [],
            "description": "打开应用"
        },
    }
    
    def __init__(self, custom_tool_info: Optional[Dict[str, Dict]] = None):
        self.tool_info = dict(self.DEFAULT_TOOL_INFO)
        if custom_tool_info:
            self.tool_info.update(custom_tool_info)
    
    def register_tool(self, name: str, output_type: str, can_provide: List[str], 
                      requires_input: List[str], description: str = ""):
        """动态注册工具信息"""
        self.tool_info[name] = {
            "output_type": output_type,
            "can_provide": can_provide,
            "requires_input": requires_input,
            "description": description
        }
    
    def analyze_tool_calls(self, tool_calls: List[Dict]) -> WorkflowPlan:
        """
        分析工具调用列表，构建工作流计划
        
        Args:
            tool_calls: LLM 返回的工具调用列表
            
        Returns:
            WorkflowPlan: 工作流执行计划
        """
        if not tool_calls:
            return WorkflowPlan()
        
        if len(tool_calls) == 1:
            node = WorkflowNode(
                name=tool_calls[0]["name"],
                tool_name=tool_calls[0]["name"],
                arguments=tool_calls[0]["arguments"],
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            plan = WorkflowPlan()
            plan.nodes[node.name] = node
            plan.execution_order = [[node.name]]
            return plan
        
        nodes = {}
        for i, tc in enumerate(tool_calls):
            node_name = f"{tc['name']}_{i}" if len([t for t in tool_calls if t['name'] == tc['name']]) > 1 else tc['name']
            node = WorkflowNode(
                name=node_name,
                tool_name=tc["name"],
                arguments=tc["arguments"],
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            nodes[node_name] = node
        
        self._analyze_dependencies(nodes)
        
        execution_order = self._topological_sort(nodes)
        
        return WorkflowPlan(nodes=nodes, execution_order=execution_order)
    
    def _analyze_dependencies(self, nodes: Dict[str, WorkflowNode]):
        """分析节点之间的依赖关系"""
        node_list = list(nodes.values())
        
        for i, node in enumerate(node_list):
            tool_info = self.tool_info.get(node.tool_name, {})
            requires_input = tool_info.get("requires_input", [])
            
            for input_type in requires_input:
                for j in range(i):
                    prev_node = node_list[j]
                    prev_info = self.tool_info.get(prev_node.tool_name, {})
                    can_provide = prev_info.get("can_provide", [])
                    
                    if input_type in can_provide:
                        if prev_node.name not in node.dependencies:
                            node.dependencies.append(prev_node.name)
            
            self._analyze_fake_path_dependency(node, node_list, i)
            
            self._analyze_empty_param_dependency(node, node_list, i)
    
    def _analyze_fake_path_dependency(self, node: WorkflowNode, node_list: List[WorkflowNode], current_idx: int):
        """分析编造路径的依赖"""
        for param_name in ["attachment", "file_path", "image_path"]:
            param_value = node.arguments.get(param_name, "")
            if param_value and self._is_fake_path(param_value):
                for j in range(current_idx):
                    prev_node = node_list[j]
                    prev_info = self.tool_info.get(prev_node.tool_name, {})
                    if prev_info.get("output_type") == "file_path":
                        if prev_node.name not in node.dependencies:
                            node.dependencies.append(prev_node.name)
    
    def _analyze_empty_param_dependency(self, node: WorkflowNode, node_list: List[WorkflowNode], current_idx: int):
        """分析空参数的依赖"""
        tool_info = self.tool_info.get(node.tool_name, {})
        requires_input = tool_info.get("requires_input", [])
        
        for param_name in ["content", "data"]:
            if param_name not in requires_input:
                continue
            param_value = node.arguments.get(param_name, "")
            if param_name not in node.arguments or not param_value or param_value == "{}" or "{previous" in str(param_value):
                for j in range(current_idx):
                    prev_node = node_list[j]
                    prev_info = self.tool_info.get(prev_node.tool_name, {})
                    can_provide = prev_info.get("can_provide", [])
                    if prev_info.get("output_type") == "data" or param_name in can_provide:
                        if prev_node.name not in node.dependencies:
                            node.dependencies.append(prev_node.name)
    
    def _is_fake_path(self, path: str) -> bool:
        """判断是否是编造的路径"""
        fake_patterns = [
            "/path/to/",
            "/path/",
            "\\path\\",
            "./output/",
            "output/xxx",
            "[待定]",
            "[附件]",
            "[文件]",
            "{attachment}",
            "{file_path}",
        ]
        path_lower = path.lower()
        for pattern in fake_patterns:
            if pattern.lower() in path_lower:
                return True
        if not re.search(r'[A-Za-z]:\\', path) and not path.startswith("/"):
            return True
        return False
    
    def _topological_sort(self, nodes: Dict[str, WorkflowNode]) -> List[List[str]]:
        """
        拓扑排序，生成执行顺序
        
        Returns:
            List[List[str]]: 每个内层列表是可以并行执行的节点
        """
        if not nodes:
            return []
        
        in_degree = {name: 0 for name in nodes}
        for node in nodes.values():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[node.name] += 1
        
        execution_order = []
        remaining = set(nodes.keys())
        max_iterations = len(nodes) + 1
        iteration = 0
        
        while remaining and iteration < max_iterations:
            iteration += 1
            ready = [name for name in remaining if in_degree[name] == 0]
            
            if not ready:
                cycle_nodes = self._detect_cycle_nodes(nodes, remaining)
                if cycle_nodes:
                    logger.warning(f"⚠️ 检测到循环依赖: {cycle_nodes}")
                    self._break_cycle(nodes, cycle_nodes)
                    for name in remaining:
                        in_degree[name] = sum(1 for dep in nodes[name].dependencies if dep in remaining)
                    continue
                else:
                    logger.warning("⚠️ 无法解决依赖问题，强制执行剩余节点")
                    ready = list(remaining)
            
            execution_order.append(ready)
            
            for name in ready:
                remaining.remove(name)
                for node in nodes.values():
                    if name in node.dependencies:
                        in_degree[node.name] -= 1
        
        return execution_order
    
    def _detect_cycle_nodes(self, nodes: Dict[str, WorkflowNode], remaining: Set[str]) -> List[str]:
        """检测参与循环的节点"""
        def dfs(node_name: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            visited.add(node_name)
            rec_stack.add(node_name)
            path.append(node_name)
            
            node = nodes.get(node_name)
            if node:
                for dep in node.dependencies:
                    if dep in remaining:
                        if dep not in visited:
                            result = dfs(dep, visited, rec_stack, path)
                            if result:
                                return result
                        elif dep in rec_stack:
                            cycle_start = path.index(dep)
                            return path[cycle_start:]
            
            path.pop()
            rec_stack.remove(node_name)
            return None
        
        visited: Set[str] = set()
        for node_name in remaining:
            if node_name not in visited:
                cycle = dfs(node_name, visited, set(), [])
                if cycle:
                    return cycle
        return []
    
    def _break_cycle(self, nodes: Dict[str, WorkflowNode], cycle_nodes: List[str]) -> None:
        """打破循环依赖"""
        if len(cycle_nodes) >= 2:
            first_node = nodes.get(cycle_nodes[0])
            second_node_name = cycle_nodes[1]
            if first_node and second_node_name in first_node.dependencies:
                first_node.dependencies.remove(second_node_name)
                logger.info(f"🔧 打破循环依赖: 移除 {first_node.name} 对 {second_node_name} 的依赖")
    
    def can_execute_parallel(self, plan: WorkflowPlan) -> bool:
        """判断是否有可并行执行的任务"""
        return any(len(level) > 1 for level in plan.execution_order)
    
    def get_execution_summary(self, plan: WorkflowPlan) -> str:
        """获取执行计划摘要"""
        if plan.is_empty():
            return "无任务"
        
        lines = ["📋 工作流执行计划:"]
        for i, level in enumerate(plan.execution_order):
            if len(level) == 1:
                lines.append(f"  步骤{i+1}: {level[0]}")
            else:
                lines.append(f"  步骤{i+1}: [并行] {', '.join(level)}")
        
        return "\n".join(lines)


def create_workflow_planner(custom_tool_info: Optional[Dict[str, Dict]] = None) -> WorkflowPlanner:
    """创建工作流规划器实例"""
    return WorkflowPlanner(custom_tool_info)
