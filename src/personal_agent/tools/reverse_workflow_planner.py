"""
反向工作流规划器 - 目标驱动的依赖推导

核心思路：
1. 从 LLM 返回的工具调用列表开始
2. 分析每个工具的输入输出接口
3. 通过接口匹配确定依赖关系
4. 生成正确的执行顺序

这就像函数调用的依赖图，通过接口定义自动推导依赖。
"""
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class DataType(Enum):
    """数据类型枚举"""
    TEXT = "text"
    NUMBER = "number"
    FILE_PATH = "file_path"
    IMAGE = "image"
    ANY = "any"


@dataclass
class DataSlot:
    """数据槽定义"""
    name: str
    data_type: DataType
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class ToolInterface:
    """工具接口定义"""
    name: str
    description: str
    inputs: List[DataSlot]
    outputs: List[DataSlot]
    can_provide: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    agent_name: str = ""


@dataclass
class WorkflowNode:
    """工作流节点"""
    tool_name: str
    tool_interface: ToolInterface
    node_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    resolved_inputs: Dict[str, Any] = field(default_factory=dict)
    unresolved_inputs: List[DataSlot] = field(default_factory=list)
    execution_order: int = 0


class ReverseWorkflowPlanner:
    """反向工作流规划器"""
    
    TOOL_INTERFACES: Dict[str, ToolInterface] = {}
    ALIAS_MAP: Dict[str, str] = {}
    
    @classmethod
    def register_interface(cls, interface: ToolInterface):
        """注册工具接口"""
        cls.TOOL_INTERFACES[interface.name] = interface
        for alias in interface.aliases:
            cls.ALIAS_MAP[alias.lower()] = interface.name
    
    @classmethod
    def get_interface(cls, name: str) -> Optional[ToolInterface]:
        """获取工具接口"""
        if name in cls.TOOL_INTERFACES:
            return cls.TOOL_INTERFACES[name]
        if name.lower() in cls.ALIAS_MAP:
            return cls.TOOL_INTERFACES[cls.ALIAS_MAP[name.lower()]]
        return None
    
    def __init__(self):
        pass
    
    def analyze_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> Tuple[List[WorkflowNode], List[List[str]]]:
        """分析工具调用，生成执行计划"""
        nodes = {}
        name_counts = {}
        
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            arguments = tc.get("arguments", {})
            
            interface = self.get_interface(tool_name)
            if not interface:
                continue
            
            if tool_name in name_counts:
                name_counts[tool_name] += 1
                node_name = f"{tool_name}_{name_counts[tool_name]}"
            else:
                name_counts[tool_name] = 0
                node_name = tool_name
            
            node = WorkflowNode(
                tool_name=tool_name,
                tool_interface=interface,
                node_name=node_name,
                arguments=arguments,
                dependencies=[],
                resolved_inputs=dict(arguments),
                unresolved_inputs=[],
                execution_order=0
            )
            nodes[node_name] = node
        
        missing_tools = self._detect_missing_tools(nodes)
        if missing_tools:
            for missing_tool, target_node, target_arg in missing_tools:
                self._inject_missing_tool(nodes, missing_tool, target_node, target_arg)
        
        self._analyze_dependencies(nodes)
        
        execution_plan = self._topological_sort(nodes)
        
        return list(nodes.values()), execution_plan
    
    def _detect_missing_tools(self, nodes: Dict[str, WorkflowNode]) -> List[Tuple[str, str, str]]:
        """检测占位符引用的缺失工具"""
        missing = []
        existing_tools = {node.tool_name for node in nodes.values()}
        detected = set()
        
        for node_name, node in nodes.items():
            for arg_name, arg_value in node.arguments.items():
                if isinstance(arg_value, str):
                    import re
                    value = arg_value.strip()
                    match = re.match(r'^\{\{([\w_]+)(?:\.[\w_]+)?\}\}$', value)
                    if not match:
                        match = re.match(r'^\{([\w_]+)(?:\.[\w_]+)?\}$', value)
                    if match:
                        ref_tool = match.group(1)
                        if ref_tool not in existing_tools and ref_tool not in detected:
                            missing.append((ref_tool, node_name, arg_name))
                            detected.add(ref_tool)
        
        return missing
    
    def _inject_missing_tool(self, nodes: Dict[str, WorkflowNode], missing_tool: str, target_node: str, target_arg: str):
        """注入缺失的工具调用"""
        if missing_tool in nodes:
            return
        
        if missing_tool == "developer_task":
            target = nodes.get(target_node)
            if target:
                filename = target.arguments.get("filename", "文档")
                base_name = filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '').replace('.txt', '')
                task = f"写一份{base_name}的内容"
                
                interface = self.get_interface("developer_task")
                if interface:
                    injected_node = WorkflowNode(
                        tool_name="developer_task",
                        tool_interface=interface,
                        node_name="developer_task",
                        arguments={"task": task},
                        resolved_inputs={"task": task},
                        execution_order=0
                    )
                    nodes["developer_task"] = injected_node
                    
                    target.arguments[target_arg] = "{developer_task.content}"
                    target.resolved_inputs[target_arg] = "{developer_task.content}"
    
    def _has_duplicate_name(self, tool_calls: List[Dict], name: str) -> bool:
        """检查是否有重复的工具名"""
        count = sum(1 for tc in tool_calls if tc.get("name") == name)
        return count > 1
    
    def _analyze_dependencies(self, nodes: Dict[str, WorkflowNode]):
        """分析节点之间的依赖关系"""
        node_list = list(nodes.items())
        
        for i, (node_name, node) in enumerate(node_list):
            interface = node.tool_interface
            
            for input_slot in interface.inputs:
                arg_value = node.arguments.get(input_slot.name, "")
                
                placeholder_dep = self._parse_placeholder_dependency(arg_value)
                if placeholder_dep:
                    dep_tool_name = placeholder_dep
                    for prev_name, prev_node in node_list:
                        if prev_name == node_name:
                            continue
                        if prev_node.tool_name == dep_tool_name or prev_name == dep_tool_name:
                            node.dependencies.append(prev_name)
                            node.resolved_inputs[input_slot.name] = f"{{output:{prev_name}.{input_slot.name}}}"
                            break
                elif self._is_empty_or_placeholder(arg_value):
                    provider_name, provider_node = self._find_provider_in_list(
                        input_slot, 
                        node_list[:i]
                    )
                    
                    if provider_name and provider_node:
                        node.dependencies.append(provider_name)
                        node.resolved_inputs[input_slot.name] = f"{{output:{provider_name}.{input_slot.name}}}"
                    else:
                        if input_slot.required:
                            node.unresolved_inputs.append(input_slot)
                elif self._should_find_provider_for_value(arg_value, input_slot, node.tool_name):
                    provider_name, provider_node = self._find_provider_for_value(
                        arg_value, 
                        input_slot, 
                        node_list[:i]
                    )
                    if provider_name and provider_node:
                        node.dependencies.append(provider_name)
                        node.resolved_inputs[input_slot.name] = f"{{output:{provider_name}.{input_slot.name}}}"
    
    def _parse_placeholder_dependency(self, value: Any) -> Optional[str]:
        """解析占位符中的依赖工具名"""
        if not isinstance(value, str):
            return None
        
        import re
        value = value.strip()
        match = re.match(r'^\{\{([\w_]+)(?:\.[\w_]+)?\}\}$', value)
        if match:
            return match.group(1)
        match = re.match(r'^\{([\w_]+)(?:\.[\w_]+)?\}$', value)
        if match:
            return match.group(1)
        return None
    
    def _should_find_provider_for_value(self, value: Any, input_slot: DataSlot, tool_name: str) -> bool:
        """判断是否需要为已有值查找提供者"""
        if not isinstance(value, str):
            return False
        
        if tool_name == "send_email" and input_slot.name == "attachment":
            if any(ext in value.lower() for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]):
                return True
            if "图片" in value or "image" in value.lower():
                return True
        
        if tool_name == "save_document" and input_slot.name == "content":
            if value.startswith("data:image") or "attachment://" in value:
                return True
            if len(value) < 100 and ("图片" in value or "image" in value.lower()):
                return True
        
        return False
    
    def _find_provider_for_value(
        self,
        value: Any,
        input_slot: DataSlot,
        node_list: List[Tuple[str, WorkflowNode]]
    ) -> Tuple[Optional[str], Optional[WorkflowNode]]:
        """根据值内容查找提供者"""
        for node_name, node in reversed(node_list):
            if node.tool_name == "generate_image":
                if input_slot.name in ["attachment", "content", "image"]:
                    return node_name, node
            
            if node.tool_name == "save_document":
                if input_slot.name == "attachment":
                    return node_name, node
        
        return None, None
    
    def _is_empty_or_placeholder(self, value: Any) -> bool:
        """检查值是否为空或占位符"""
        if value is None:
            return True
        if isinstance(value, str):
            if not value.strip():
                return True
            import re
            if re.match(r'^\{\{[\w_]+(?:\.[\w_]+)?\}\}$', value.strip()):
                return True
            if re.match(r'^\{[\w_]+(?:\.[\w_]+)?\}$', value.strip()):
                return True
            placeholders = ["[待定]", "[附件]", "[文件]", "{previous", "{output:", "#FILEPATH#", "#filepath#", "%find_file", "%save_document", "%.result."]
            if any(p in value for p in placeholders):
                return True
            if value.startswith("%") and value.endswith("%"):
                return True
        return False
    
    def _find_provider_in_list(
        self,
        input_slot: DataSlot,
        node_list: List[Tuple[str, WorkflowNode]]
    ) -> Tuple[Optional[str], Optional[WorkflowNode]]:
        """在已有节点列表中查找提供者"""
        for node_name, node in node_list:
            for output_slot in node.tool_interface.outputs:
                if output_slot.name == input_slot.name:
                    return node_name, node
                if output_slot.data_type == input_slot.data_type:
                    return node_name, node
                if output_slot.data_type == DataType.ANY or input_slot.data_type == DataType.ANY:
                    return node_name, node
        return None, None
    
    def _topological_sort(self, nodes: Dict[str, WorkflowNode]) -> List[List[str]]:
        """拓扑排序，生成执行层级"""
        in_degree = {name: 0 for name in nodes}
        graph = {name: [] for name in nodes}
        
        for name, node in nodes.items():
            for dep in node.dependencies:
                if dep in nodes:
                    graph[dep].append(name)
                    in_degree[name] += 1
        
        result = []
        queue = [name for name, degree in in_degree.items() if degree == 0]
        
        while queue:
            level = queue.copy()
            result.append(level)
            queue.clear()
            
            for node_name in level:
                for dependent in graph[node_name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        return result
    
    def get_plan_summary(self, nodes: List[WorkflowNode], execution_plan: List[List[str]]) -> str:
        """生成执行计划摘要"""
        lines = ["📋 执行计划:"]
        for i, level in enumerate(execution_plan):
            lines.append(f"  层级 {i+1}: {', '.join(level)}")
        return "\n".join(lines)


def register_default_interfaces():
    """注册默认工具接口"""
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="create_travel_plan",
        description="创建旅行计划",
        inputs=[
            DataSlot("destination", DataType.TEXT, True, "目的地"),
            DataSlot("days", DataType.NUMBER, False, "天数", 3),
            DataSlot("preferences", DataType.TEXT, False, "偏好"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "旅行计划内容"),
        ],
        can_provide=["content", "travel_plan", "itinerary"],
        aliases=["travel", "旅行", "行程", "旅游计划"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="save_document",
        description="保存文档",
        inputs=[
            DataSlot("filename", DataType.TEXT, True, "文件名"),
            DataSlot("content", DataType.TEXT, True, "文档内容"),
            DataSlot("format", DataType.TEXT, False, "格式", "txt"),
        ],
        outputs=[
            DataSlot("file_path", DataType.FILE_PATH, True, "保存的文件路径"),
        ],
        can_provide=["file_path", "document", "file"],
        aliases=["save", "保存", "保存文档", "save_doc"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="send_email",
        description="发送邮件",
        inputs=[
            DataSlot("to", DataType.TEXT, True, "收件人邮箱"),
            DataSlot("subject", DataType.TEXT, True, "邮件主题"),
            DataSlot("content", DataType.TEXT, False, "邮件内容"),
            DataSlot("attachment", DataType.FILE_PATH, False, "附件路径"),
        ],
        outputs=[
            DataSlot("result", DataType.TEXT, True, "发送结果"),
        ],
        can_provide=["result"],
        aliases=["email", "邮件", "发送邮件"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="get_weather",
        description="获取天气信息",
        inputs=[
            DataSlot("city", DataType.TEXT, True, "城市名称"),
            DataSlot("days", DataType.NUMBER, False, "预报天数", 0),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "天气信息"),
        ],
        can_provide=["content", "weather", "天气"],
        aliases=["weather", "天气", "天气预报"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="search_web",
        description="搜索网络信息",
        inputs=[
            DataSlot("query", DataType.TEXT, True, "搜索关键词"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "搜索结果"),
        ],
        can_provide=["content", "search_result", "web_content"],
        aliases=["search", "搜索", "网络搜索", "web_search"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="get_news",
        description="获取新闻",
        inputs=[
            DataSlot("category", DataType.TEXT, False, "新闻类别"),
            DataSlot("count", DataType.NUMBER, False, "数量", 5),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "新闻内容"),
        ],
        can_provide=["content", "news"],
        aliases=["news", "新闻"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="play_music",
        description="播放音乐",
        inputs=[
            DataSlot("song", DataType.TEXT, False, "歌曲名"),
            DataSlot("artist", DataType.TEXT, False, "歌手"),
            DataSlot("action", DataType.TEXT, False, "动作", "play"),
        ],
        outputs=[
            DataSlot("result", DataType.TEXT, True, "播放结果"),
        ],
        can_provide=["result"],
        aliases=["music", "音乐", "播放歌曲"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="contact_list",
        description="列出联系人",
        inputs=[],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "联系人列表"),
        ],
        can_provide=["content", "contacts", "联系人"],
        aliases=["contacts", "联系人列表"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="contact_lookup",
        description="查找联系人",
        inputs=[
            DataSlot("name", DataType.TEXT, True, "联系人姓名"),
        ],
        outputs=[
            DataSlot("email", DataType.TEXT, True, "邮箱地址"),
            DataSlot("phone", DataType.TEXT, False, "电话号码"),
            DataSlot("info", DataType.TEXT, False, "联系人信息"),
        ],
        can_provide=["email", "phone", "info", "contact"],
        aliases=["lookup", "查找联系人", "find_contact"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="generate_image",
        description="生成图片",
        inputs=[
            DataSlot("prompt", DataType.TEXT, True, "图片描述"),
            DataSlot("size", DataType.TEXT, False, "尺寸", "1024*1024"),
        ],
        outputs=[
            DataSlot("file_path", DataType.FILE_PATH, True, "图片文件路径"),
            DataSlot("image", DataType.IMAGE, True, "图片数据"),
        ],
        can_provide=["file_path", "image", "attachment", "图片"],
        aliases=["image", "图片", "生成图片", "画图"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="disk_space",
        description="查询磁盘空间",
        inputs=[
            DataSlot("drive", DataType.TEXT, False, "盘符"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "磁盘空间信息"),
        ],
        can_provide=["content", "disk", "storage"],
        aliases=["disk", "磁盘", "硬盘空间"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="find_file",
        description="搜索文件",
        inputs=[
            DataSlot("pattern", DataType.TEXT, True, "文件名模式"),
            DataSlot("directory", DataType.TEXT, False, "搜索目录"),
        ],
        outputs=[
            DataSlot("file_path", DataType.FILE_PATH, True, "找到的文件路径"),
        ],
        can_provide=["file_path", "file"],
        aliases=["search_file", "搜索文件", "find"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="clipboard_write",
        description="写入剪贴板",
        inputs=[
            DataSlot("text", DataType.TEXT, True, "要写入的文本"),
        ],
        outputs=[
            DataSlot("result", DataType.TEXT, True, "操作结果"),
        ],
        can_provide=["result"],
        aliases=["clipboard", "剪贴板"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="take_screenshot",
        description="截取屏幕",
        inputs=[],
        outputs=[
            DataSlot("file_path", DataType.FILE_PATH, True, "截图文件路径"),
            DataSlot("image", DataType.IMAGE, True, "图片数据"),
        ],
        can_provide=["file_path", "image", "screenshot"],
        aliases=["screenshot", "截图", "截屏"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="query_stock",
        description="查询股票",
        inputs=[
            DataSlot("stock_code", DataType.TEXT, True, "股票代码"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "股票信息"),
        ],
        can_provide=["content", "stock", "股票"],
        aliases=["stock", "股票", "股价"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="query_index",
        description="查询指数",
        inputs=[
            DataSlot("index_name", DataType.TEXT, False, "指数名称", "大盘"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "指数信息"),
        ],
        can_provide=["content", "index", "指数"],
        aliases=["index", "指数", "大盘"]
    ))
    
    ReverseWorkflowPlanner.register_interface(ToolInterface(
        name="developer_task",
        description="开发者任务",
        inputs=[
            DataSlot("task", DataType.TEXT, True, "任务描述"),
        ],
        outputs=[
            DataSlot("content", DataType.TEXT, True, "生成的内容"),
        ],
        can_provide=["content", "code", "text"],
        aliases=["dev", "开发", "code", "生成内容"]
    ))


register_default_interfaces()
